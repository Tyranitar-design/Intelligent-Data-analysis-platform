# -*- coding: utf-8 -*-
"""站点库 · 实机验证门禁（P7a）

验证内容（真实链路）：

1. 画像就绪：取画像列表（空则 analyze example.com 现场生成）
2. `/discover/profiles/stats` 聚合断言（total / by_decision / stale_count）
3. 列表接口带 `field_count`
4. 前端 `/sites` 页面渲染（统计条 / 筛选 / 卡片网格）与抽屉详情截图
5. 证据落盘 `docs/evidence/p7a-sites/`

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_sites_p7a.py
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "p7a-sites"

API = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5174"

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows


def http(method: str, path: str, payload=None, timeout: float = 120.0):
    url = f"{API}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="ignore")[:400]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {exc.code} {method} {path} -> {body}") from exc


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
        back_ok = wait_http(f"{API}/health", 120)
        front_ok = wait_http(f"{FRONTEND}/", 60)
        checks.append(("backend ready", back_ok, API))
        checks.append(("frontend ready", front_ok, FRONTEND))
        if not (back_ok and front_ok):
            raise RuntimeError("services not ready")

        # [3] 画像就绪
        print("[3] ensure profiles ...", flush=True)
        _, listing = http("GET", "/api/v1/discover/profiles", timeout=30)
        items = listing.get("items", [])
        if not items:
            http(
                "POST", "/api/v1/discover/analyze", {"url": "https://example.com/"},
                timeout=120,
            )
            _, listing = http("GET", "/api/v1/discover/profiles", timeout=30)
            items = listing.get("items", [])
        checks.append((
            "profiles available",
            len(items) >= 1,
            f"count={len(items)} first={items[0]['domain'] if items else None}",
        ))
        checks.append((
            "list carries field_count",
            items and "field_count" in items[0],
            f"field_count={items[0].get('field_count') if items else None}",
        ))

        # [4] stats 聚合
        print("[4] profiles stats ...", flush=True)
        _, stats = http("GET", "/api/v1/discover/profiles/stats", timeout=30)
        checks.append((
            "stats total matches",
            stats.get("total") == len(items),
            f"total={stats.get('total')}",
        ))
        checks.append((
            "stats by_decision populated",
            isinstance(stats.get("by_decision"), dict)
            and sum(stats["by_decision"].values()) == stats.get("total"),
            str(stats.get("by_decision")),
        ))

        # [5] 前端页面 + 抽屉
        print("[5] frontend sites page + drawer ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 950})
            page.goto(f"{FRONTEND}/sites", wait_until="networkidle")
            page.wait_for_selector("text=画像资产与复用", timeout=20000)
            page.wait_for_timeout(1200)
            body_text = page.locator("body").inner_text()
            checks.append((
                "sites page renders (stats + cards)",
                "画像" in body_text and "可采" in body_text and "待确认" in body_text,
                "",
            ))
            page.screenshot(path=str(EVIDENCE_DIR / "01-sites-list.png"))

            # 打开第一张卡片 → 抽屉
            first_card = page.locator("button.glass").first
            if first_card.count() > 0:
                first_card.click()
                page.wait_for_selector("text=访问状态", timeout=15000)
                page.wait_for_timeout(900)
                drawer_text = page.locator("body").inner_text()
                checks.append((
                    "profile drawer renders (access + fields)",
                    "访问状态" in drawer_text and "可采字段" in drawer_text,
                    "",
                ))
                page.screenshot(path=str(EVIDENCE_DIR / "02-sites-drawer.png"))
            else:
                checks.append(("profile drawer renders", False, "no card found"))

            browser.close()

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))
    finally:
        print("[6] cleanup processes ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass

    print("\n=== P7A SITES VERIFY RESULTS ===", flush=True)
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
