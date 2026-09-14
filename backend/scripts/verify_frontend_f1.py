# -*- coding: utf-8 -*-
"""F1 动效基础设施 · 实机验证门禁（v5 蓝图 P11a）

验证内容（每条都有断言或采样证据）：
1. 工作台渲染：品牌、4 张统计卡、导航齐全
2. CountUp 数字滚动：统计值从占位收敛为数字
3. 页面转场：导航切换 → URL 变化 + 新页内容渲染（AnimatePresence 在跑）
4. reduced-motion 守护：模拟 reduce 偏好 → 页面完整渲染、无 JS 错误
5. 证据落盘：截图 + 控制台检查结果 → docs/evidence/f1-verify/

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_frontend_f1.py

前置：frontend 依赖已安装（脚本自起 vite dev + uvicorn，结束自动清理）。
"""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "f1-verify"

FRONTEND_URL = "http://127.0.0.1:5174"
BACKEND_URL = "http://127.0.0.1:8000"

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows


def wait_http(url: str, timeout: float = 120.0, label: str = "") -> bool:
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
        # [1] 前端 dev server（用 dev 模式以验证 vite 代理链路）
        print("[1] starting frontend dev server (:5174) ...", flush=True)
        node = subprocess.run(
            ["where", "node"], capture_output=True, text=True, shell=True
        ).stdout.strip().splitlines()[0]
        vite_js = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
        procs.append(
            subprocess.Popen(
                [node, str(vite_js), "dev", "--port", "5174", "--host", "127.0.0.1"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NEW_PROCESS_GROUP,
            )
        )

        # [2] 后端（供前端代理取数）
        print("[2] starting backend (:8000) ...", flush=True)
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

        # [3] 等就绪
        print("[3] waiting for readiness ...", flush=True)
        front_ready = wait_http(FRONTEND_URL + "/", 60, "frontend")
        back_ready = wait_http(BACKEND_URL + "/health", 120, "backend")
        checks.append(("frontend ready", front_ready, FRONTEND_URL))
        checks.append(("backend ready", back_ready, BACKEND_URL))
        if not (front_ready and back_ready):
            raise RuntimeError("services not ready")

        # [4] Playwright 验证
        from playwright.sync_api import sync_playwright

        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        console_errors: list[str] = []

        with sync_playwright() as p:
            browser = p.chromium.launch()

            # ---- 场景 1：常规模式 ----
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
            )
            page.goto(FRONTEND_URL + "/", wait_until="networkidle")

            page.wait_for_selector("text=WebInsight", timeout=20000)
            checks.append(("brand visible", True, "WebInsight"))

            cards = page.locator(".animate-rise").count()
            checks.append(("stat cards rendered (>=4)", cards >= 4, f"found {cards}"))

            # CountUp 收敛：等动画（0.9s）完成后统计卡内应有数字
            page.wait_for_timeout(1700)
            first_card_text = page.locator(".animate-rise").first.inner_text().replace("\n", " | ")
            has_number = any(ch.isdigit() for ch in first_card_text)
            checks.append(("countup shows number", has_number, first_card_text))

            page.screenshot(path=str(EVIDENCE_DIR / "01-dashboard.png"))

            # 页面转场：采样 main 直接子元素的 opacity（动画中间值 = 在跑的证据）
            page.click('a[href="/discover"]')
            samples: list[str] = []
            for _ in range(8):
                value = page.evaluate(
                    "() => { const el = document.querySelector('main > div');"
                    " return el ? getComputedStyle(el).opacity : null }"
                )
                samples.append(str(value))
                page.wait_for_timeout(50)
            mid_values = [s for s in samples if s not in ("None", "0", "1")]
            checks.append(
                ("transition has in-between frames", len(mid_values) > 0, f"samples={samples}")
            )

            page.wait_for_url("**/discover", timeout=10000)
            page.wait_for_timeout(700)
            body_text = page.locator("body").inner_text()
            checks.append(
                ("discover page rendered", "站点分析" in body_text, page.url)
            )
            page.screenshot(path=str(EVIDENCE_DIR / "02-discover.png"))

            # 返回工作台
            page.click('a[href="/"]')
            page.wait_for_url(FRONTEND_URL + "/", timeout=10000)
            page.wait_for_timeout(700)
            checks.append(("route back to dashboard", True, page.url))

            # ---- 场景 2：reduced-motion ----
            ctx2 = browser.new_context(
                reduced_motion="reduce", viewport={"width": 1440, "height": 900}
            )
            page2 = ctx2.new_page()
            errors2: list[str] = []
            page2.on(
                "console",
                lambda msg: errors2.append(msg.text) if msg.type == "error" else None,
            )
            page2.goto(FRONTEND_URL + "/", wait_until="networkidle")
            page2.wait_for_selector("text=WebInsight", timeout=20000)
            cards2 = page2.locator(".animate-rise").count()
            # reduced-motion 下 CountUp 应直接落终值（无需等待动画）
            page2.wait_for_timeout(400)
            rm_text = page2.locator(".animate-rise").first.inner_text().replace("\n", " | ")
            checks.append(
                ("reduced-motion renders + final values", cards2 >= 4 and any(ch.isdigit() for ch in rm_text), rm_text)
            )
            page2.screenshot(path=str(EVIDENCE_DIR / "03-dashboard-reduced-motion.png"))
            ctx2.close()

            # ---- 控制台错误 ----
            severe = [e for e in console_errors if "favicon" not in e.lower()]
            checks.append(
                ("no console errors (normal mode)", len(severe) == 0, f"{len(severe)}: {severe[:3]}")
            )
            severe2 = [e for e in errors2 if "favicon" not in e.lower()]
            checks.append(
                ("no console errors (reduced-motion)", len(severe2) == 0, f"{len(severe2)}: {severe2[:2]}")
            )

            browser.close()

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))
    finally:
        print("[4] cleaning up processes ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    timeout=15,
                )
            except Exception:
                pass

    # [5] 结果
    print("\n=== F1 VERIFY RESULTS ===", flush=True)
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
