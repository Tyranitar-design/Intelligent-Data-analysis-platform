# -*- coding: utf-8 -*-
"""Dashboard v5 升级 · 实机门禁（环形进度 + 迷你曲线 + 截图）

验证：
1. 页面渲染（平台概览抬头）
2. RingProgress 存在（SVG circle + stroke-dasharray）
3. Sparkline 存在（SVG path 曲线）
4. 截图存证（对比 v5 升级效果）

证据：docs/evidence/dashboard-v5/

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_dashboard_v5.py
"""
from __future__ import annotations

import subprocess
import time
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "dashboard-v5"

API = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5174"

CREATE_NEW_PROCESS_GROUP = 0x00000200


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
        print("[1] start services ...", flush=True)
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
        procs.append(
            subprocess.Popen(
                [node, str(vite_js), "dev", "--port", "5174", "--host", "127.0.0.1"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NEW_PROCESS_GROUP,
            )
        )
        if not (wait_http(f"{API}/health", 120) and wait_http(f"{FRONTEND}/", 60)):
            raise RuntimeError("services not ready")

        print("[2] dashboard v5 checks ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"{FRONTEND}/", wait_until="networkidle")
            page.wait_for_timeout(2500)

            body_text = page.locator("body").inner_text()
            checks.append(("页面渲染（平台概览）", "平台概览" in body_text, ""))

            ring_count = page.evaluate(
                "() => document.querySelectorAll('svg circle[stroke-dasharray]').length"
            )
            checks.append((
                "环形进度（RingProgress）",
                int(ring_count) >= 2,
                f"rings={ring_count}",
            ))

            spark_count = page.evaluate(
                '() => document.querySelectorAll(\'svg path[class*="stroke-primary"]\').length'
            )
            checks.append((
                "迷你曲线（Sparkline）",
                int(spark_count) >= 2,
                f"sparks={spark_count}",
            ))

            page.screenshot(
                path=str(EVIDENCE_DIR / "dashboard-v5.png"), full_page=True
            )
            checks.append(("截图存证", True, "dashboard-v5.png"))
            browser.close()

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))
    finally:
        print("[3] cleanup ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass

    print("\n=== DASHBOARD V5 RESULTS ===", flush=True)
    all_ok = True
    lines = []
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        line = f"  [{mark}] {name} -- {detail}"
        print(line, flush=True)
        lines.append(line)
        all_ok = all_ok and ok
    verdict = "all checks passed" if all_ok else "failures present"
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
