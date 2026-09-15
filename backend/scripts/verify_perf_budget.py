# -*- coding: utf-8 -*-
"""首屏预算门禁（v5 验收 5.1-2）· 生产构建实测

验证内容（vite preview 服务 dist 产物，无后端依赖）：
1. 首屏 `/` 的 JS 请求序列**不含** chart-vendor（echarts）与 nebula-scene（three.js）
2. 首屏 gzip 合计 <= 300KB（从 dist 文件实算，含 css/JS 的可压缩部分）
3. `/analytics` 按需加载图表 chunk（懒加载生效），页面渲染（body 文本非空）
4. 无页面级 JS 异常（pageerror）
5. 证据落盘 ``docs/evidence/perf-budget/``

运行（backend/ 下，先确保已 ``npm run build``）：
    .\\venv\\Scripts\\python.exe scripts\\verify_perf_budget.py
"""
from __future__ import annotations

import gzip
import json
import subprocess
import time
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "perf-budget"

PREVIEW = "http://127.0.0.1:5175"

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows

BUDGET_KB = 300.0


def gzip_kb(path: Path) -> float:
    data = path.read_bytes()
    return len(gzip.compress(data, 9)) / 1024


def wait_http(url: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.8)
    return False


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    procs: list[subprocess.Popen] = []

    try:
        # [1] 解析 index.html 的首屏资源（生产产物）
        print("[1] parse dist/index.html ...", flush=True)
        html = (DIST_DIR / "index.html").read_text(encoding="utf-8")
        first_load: list[str] = []
        for line in html.splitlines():
            if "assets/" not in line:
                continue
            for token in line.split('"'):
                if token.startswith("/assets/") and (
                    token.endswith(".js") or token.endswith(".css")
                ):
                    first_load.append(token.lstrip("/"))
        first_load = sorted(set(first_load))

        names = [p.rsplit("/", 1)[-1] for p in first_load]
        checks.append((
            "index.html does not preload chart-vendor",
            not any(n.startswith("chart-vendor") for n in names),
            f"first-load={names}",
        ))
        checks.append((
            "index.html does not preload nebula-scene",
            not any(n.startswith("nebula-scene") for n in names),
            "",
        ))

        # [2] 首屏 gzip 预算实算
        total_kb = 0.0
        detail_bits = []
        for rel in first_load:
            f = DIST_DIR / rel
            if f.exists():
                kb = gzip_kb(f)
                total_kb += kb
                detail_bits.append(f"{f.name}={kb:.1f}")
        checks.append((
            f"first-load gzip <= {BUDGET_KB:.0f}KB",
            total_kb <= BUDGET_KB,
            f"total={total_kb:.1f}KB :: " + " ".join(detail_bits),
        ))

        # [3] vite preview 冒烟：真实请求序列 + 懒加载
        print("[2] preview smoke ...", flush=True)
        node = subprocess.run(
            ["where", "node"], capture_output=True, text=True, shell=True
        ).stdout.strip().splitlines()[0]
        vite_js = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
        procs.append(
            subprocess.Popen(
                [node, str(vite_js), "preview", "--port", "5175", "--host", "127.0.0.1"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NEW_PROCESS_GROUP,
            )
        )
        if not wait_http(f"{PREVIEW}/", 60):
            raise RuntimeError("preview not ready")

        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            page_errors: list[str] = []
            page.on("pageerror", lambda e: page_errors.append(str(e)))
            js_requests: list[str] = []
            page.on(
                "request",
                lambda r: js_requests.append(r.url)
                if r.url.endswith(".js")
                else None,
            )

            page.goto(f"{PREVIEW}/", wait_until="networkidle")
            page.wait_for_timeout(1200)
            home_js = [
                u.rsplit("/", 1)[-1] for u in js_requests if "/assets/" in u
            ]
            checks.append((
                "real first paint: no chart-vendor request",
                not any(n.startswith("chart-vendor") for n in home_js),
                f"js={home_js}",
            ))
            checks.append((
                "real first paint: no nebula-scene request",
                not any(n.startswith("nebula-scene") for n in home_js),
                "",
            ))

            # [3b] /analytics 懒加载
            before = len(js_requests)
            page.goto(f"{PREVIEW}/analytics", wait_until="networkidle")
            page.wait_for_timeout(1500)
            analytics_js = [
                u.rsplit("/", 1)[-1] for u in js_requests[before:]
            ]
            checks.append((
                "analytics lazy chunk loads on demand",
                any(n.startswith("Analytics-") for n in analytics_js),
                f"js={analytics_js}",
            ))
            body_text = page.locator("body").inner_text()
            checks.append((
                "analytics page renders",
                len(body_text) > 30,
                f"body_chars={len(body_text)}",
            ))

            checks.append((
                "no page errors",
                len(page_errors) == 0,
                "; ".join(page_errors[:3]),
            ))

            page.screenshot(
                path=str(EVIDENCE_DIR / "analytics-lazy.png"), full_page=False
            )
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

    print("\n=== PERF BUDGET VERIFY RESULTS ===", flush=True)
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
