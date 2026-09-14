# -*- coding: utf-8 -*-
"""展示岛（L3）· 实机验证门禁

验证内容：

1. `/showcase` 页面渲染（主文案 + 场景挂载）
2. 场景模式判定：WebGL 就绪（canvas 挂载）或按设计降级
3. **降级链实证**：`prefers-reduced-motion: reduce` 下不加载 three.js、走静态星云
4. 控制台无错误
5. 证据落盘 `docs/evidence/l3-showcase/`

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_showcase_l3.py
"""
from __future__ import annotations

import os
import subprocess
import time
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "l3-showcase"

FRONTEND = "http://127.0.0.1:5174"

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows


def wait_http(url: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1.0)
    return False


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    procs: list[subprocess.Popen] = []

    try:
        # [1] 启动服务
        print("[1] starting backend (:8000) ...", flush=True)
        py = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
        procs.append(
            subprocess.Popen(
                [str(py), "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
                cwd=str(BACKEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NEW_PROCESS_GROUP,
            )
        )
        node = subprocess.run(
            ["where", "node"], capture_output=True, text=True, shell=True
        ).stdout.strip().splitlines()[0]
        vite_js = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
        print("[2] starting frontend dev server (:5174) ...", flush=True)
        procs.append(
            subprocess.Popen(
                [node, str(vite_js), "dev", "--port", "5174", "--host", "127.0.0.1"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NEW_PROCESS_GROUP,
            )
        )
        back_ok = wait_http("http://127.0.0.1:8000/health", 120)
        front_ok = wait_http(f"{FRONTEND}/", 90)
        checks.append(("backend ready", back_ok, "http://127.0.0.1:8000"))
        checks.append(("frontend ready", front_ok, FRONTEND))
        if not (back_ok and front_ok):
            raise RuntimeError("services not ready")

        # [2] 常规模式：场景挂载
        print("[3] showcase page (normal mode) ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 950})
            console_errors: list[str] = []
            page.on(
                "console",
                lambda msg: (
                    console_errors.append(msg.text) if msg.type == "error" else None
                ),
            )
            page.goto(f"{FRONTEND}/showcase", wait_until="networkidle")
            page.wait_for_selector("text=数据在此流动", timeout=20000)
            page.wait_for_timeout(2800)  # 等 three 初始化 + 渲染若干帧

            body = page.locator("body").inner_text()
            mode = (
                "webgl"
                if "Three.js 场景运行中" in body
                else "fallback"
                if "降级" in body
                else "unknown"
            )
            canvas_count = page.locator("canvas[data-nebula]").count()
            checks.append((
                "showcase page renders",
                "数据在此流动" in body,
                f"mode={mode}",
            ))
            checks.append((
                "scene mounted (webgl or designed fallback)",
                mode in ("webgl", "fallback"),
                f"mode={mode} canvas={canvas_count}",
            ))
            if mode == "webgl":
                checks.append((
                    "webgl canvas attached",
                    canvas_count >= 1,
                    f"canvas={canvas_count}",
                ))
            page.screenshot(path=str(EVIDENCE_DIR / "showcase-scene.png"))

            # [3] 降级链：reduced-motion
            print("[4] reduced-motion fallback ...", flush=True)
            ctx = browser.new_context(
                reduced_motion="reduce", viewport={"width": 1440, "height": 950}
            )
            page2 = ctx.new_page()
            page2.goto(f"{FRONTEND}/showcase", wait_until="networkidle")
            page2.wait_for_selector("text=数据在此流动", timeout=20000)
            page2.wait_for_timeout(1200)
            body2 = page2.locator("body").inner_text()
            nebula_canvas2 = page2.locator("canvas[data-nebula]").count()
            checks.append((
                "reduced-motion skips three.js (static nebula)",
                "降级" in body2 and nebula_canvas2 == 0,
                f"nebula_canvas={nebula_canvas2}",
            ))
            page2.screenshot(path=str(EVIDENCE_DIR / "showcase-fallback.png"))
            ctx.close()

            severe = [e for e in console_errors if "favicon" not in e.lower()]
            checks.append((
                "no console errors",
                len(severe) == 0,
                f"{len(severe)}: {severe[:2]}",
            ))
            browser.close()

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))
    finally:
        print("[5] cleanup processes ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass

    print("\n=== L3 SHOWCASE VERIFY RESULTS ===", flush=True)
    all_ok = True
    lines = []
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        line = f"  {mark}  {name}  --  {detail}"
        print(line, flush=True)
        lines.append(line)
        all_ok = all_ok and ok

    verdict = "all checks passed" if all_ok else "FAILURES PRESENT"
    print(f"RESULT: {verdict}", flush=True)
    try:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / "result.txt").write_text(
            "\n".join(lines) + f"\nRESULT: {verdict}\n", encoding="utf-8"
        )
    except OSError:
        pass
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
