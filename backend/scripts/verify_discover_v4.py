# -*- coding: utf-8 -*-
"""Discover v4 专项验证 · 实机门禁

流程：真实分析 example.com → 等待 v4 组件渲染（圆弧/矩阵/速率）→ 截图。

证据落盘 `docs/evidence/ui-v4/`。

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_discover_v4.py
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
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "ui-v4"

API = "http://127.0.0.1:8000"
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
        back_ok = wait_http(f"{API}/health", 120)
        front_ok = wait_http(f"{FRONTEND}/", 60)
        checks.append(("backend ready", back_ok, API))
        checks.append(("frontend ready", front_ok, FRONTEND))
        if not (back_ok and front_ok):
            raise RuntimeError("services not ready")

        print("[3] analyze example.com on /discover ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1080})
            console_errors: list[str] = []
            page.on(
                "console",
                lambda msg: (
                    console_errors.append(msg.text) if msg.type == "error" else None
                ),
            )

            page.goto(f"{FRONTEND}/discover", wait_until="networkidle")
            page.fill("input[placeholder*='https']", "https://example.com/")
            page.click("text=开始分析")
            page.wait_for_selector("text=检测置信度", timeout=90000)
            page.wait_for_selector("text=字段覆盖矩阵", timeout=15000)
            page.wait_for_selector("text=请求速率基线", timeout=15000)
            page.wait_for_timeout(1400)

            body = page.locator("body").inner_text()
            checks.append((
                "v4 components rendered (gauge + matrix + rate)",
                "检测置信度" in body and "字段覆盖矩阵" in body and "请求速率基线" in body,
                "",
            ))
            checks.append((
                "structure rows rendered",
                "结构识别结果" in body and "列表结构" in body,
                "",
            ))
            page.screenshot(path=str(EVIDENCE_DIR / "discover-v4.png"), full_page=True)

            # Collect v4（对标第二张目标图）
            page.goto(f"{FRONTEND}/collect", wait_until="networkidle")
            page.wait_for_selector("text=数据管道", timeout=20000)
            page.wait_for_timeout(1100)
            body2 = page.locator("body").inner_text()
            checks.append((
                "collect v4 renders (kpi + pipeline + activity)",
                "总采集条目" in body2 and "数据管道" in body2 and "实时活动" in body2,
                "",
            ))
            page.screenshot(path=str(EVIDENCE_DIR / "collect-v4.png"), full_page=True)

            severe = [e for e in console_errors if "favicon" not in e.lower()]
            checks.append(("no console errors", len(severe) == 0, f"{len(severe)}: {severe[:2]}"))
            browser.close()

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))
    finally:
        print("[4] cleanup processes ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass

    print("\n=== DISCOVER V4 VERIFY RESULTS ===", flush=True)
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
