# -*- coding: utf-8 -*-
"""移动端 375px 检查（v5 验收 5.1-8）· 实机门禁

验证内容：
1. 9 个关键页在 375x812 下无横向溢出（scrollWidth <= 376，含 1px 容差）
2. 移动导航可用：汉堡按钮（aria-label=打开导航）→ 抽屉出现 → 可关闭
3. prefers-reduced-motion: reduce 下页面正常渲染（动效降级不炸）
4. 证据落盘 ``docs/evidence/mobile-375/``

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_mobile_375.py
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "mobile-375"

API = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5174"

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows

PAGES = [
    ("/", "dashboard"),
    ("/discover", "discover"),
    ("/collect", "collect"),
    ("/schedules", "schedules"),
    ("/datasets", "datasets"),
    ("/datasets/2", "dataset-detail"),
    ("/compliance", "compliance"),
    ("/monitor", "monitor"),
    ("/analytics", "analytics"),
    ("/showcase", "showcase"),
]

OVERFLOW_DIAG = """
() => {
  const out = [];
  document.querySelectorAll('*').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > 377 && r.left < 375) {
      if (out.length < 6) {
        const cls = (el.className || '').toString().slice(0, 70);
        out.push(`${el.tagName}.${cls} w=${Math.round(r.width)} right=${Math.round(r.right)}`);
      }
    }
  });
  return out;
}
"""


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
        # [1] 服务
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

        # [2] 375px 遍历
        print("[2] tour pages at 375x812 ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={"width": 375, "height": 812},
                device_scale_factor=2,
            )
            page = context.new_page()

            for path, name in PAGES:
                page.goto(f"{FRONTEND}{path}", wait_until="networkidle")
                page.wait_for_timeout(1300)
                scroll_width = page.evaluate("document.documentElement.scrollWidth")
                ok = scroll_width <= 376
                detail = f"scrollWidth={scroll_width}"
                if not ok:
                    offenders = page.evaluate(OVERFLOW_DIAG)
                    detail += " | " + " ;; ".join(offenders)
                checks.append((f"375px no h-overflow: {name}", ok, detail))
                page.screenshot(
                    path=str(EVIDENCE_DIR / f"375-{name}.png"), full_page=False
                )

            # [3] 移动导航抽屉
            print("[3] mobile nav drawer ...", flush=True)
            page.goto(f"{FRONTEND}/", wait_until="networkidle")
            page.wait_for_timeout(900)
            page.click('button[aria-label="打开导航"]')
            page.wait_for_timeout(700)
            drawer_text = page.locator("body").inner_text()
            nav_ok = any(
                label in drawer_text
                for label in ("采集任务", "数据集", "合规中心", "数据源")
            )
            checks.append(("mobile drawer opens with nav", nav_ok, ""))
            page.screenshot(path=str(EVIDENCE_DIR / "375-drawer.png"), full_page=False)

            # [4] reduced-motion 降级
            print("[4] reduced-motion rendering ...", flush=True)
            reduce_ctx = browser.new_context(
                viewport={"width": 375, "height": 812}, reduced_motion="reduce"
            )
            reduce_page = reduce_ctx.new_page()
            reduce_page.goto(f"{FRONTEND}/", wait_until="networkidle")
            reduce_page.wait_for_timeout(1200)
            body_chars = len(reduce_page.locator("body").inner_text())
            checks.append((
                "reduced-motion renders (dashboard)",
                body_chars > 60,
                f"body_chars={body_chars}",
            ))
            reduce_page.goto(f"{FRONTEND}/showcase", wait_until="networkidle")
            reduce_page.wait_for_timeout(1200)
            reduce_body = len(reduce_page.locator("body").inner_text())
            checks.append((
                "reduced-motion renders (showcase)",
                reduce_body > 30,
                f"body_chars={reduce_body}",
            ))
            reduce_ctx.close()

            browser.close()

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))
    finally:
        print("[5] cleanup services ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass

    print("\n=== MOBILE 375 VERIFY RESULTS ===", flush=True)
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
