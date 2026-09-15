# -*- coding: utf-8 -*-
"""D4 检索深化 · 实机验证门禁

验证内容（真实链路，主库 ds2 的 "Example Domain" 数据）：

1. 服务就绪（backend :8000 / frontend :5174）
2. 多关键字 AND：**逆序** "Domain Example" 命中（旧整串实现为 0——
   该断言即 D4 分词语义的证据）；缺词不命中；单词向后兼容
3. 时间过滤：date_field=title 参与计算（date("Example Domain")=NULL → 0 条，
   证明过滤真的生效）；无 date_field 的 date_from → 400；非法字段 → 400
4. 前端：`/datasets/2` 多词检索 E2E + 时间过滤展开行（选择字段 + 日期 → 0 条命中 + 摘要）
5. 证据落盘 ``docs/evidence/d4-search/``

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_d4_search_plus.py
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "d4-search"

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
        return exc.code, {"detail": body}


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

        # [3] 多关键字 AND（逆序命中 = 分词语义证据）
        print("[3] multi-keyword ...", flush=True)
        _, single = http(
            "GET",
            "/api/v1/collect/datasets/2/search?q=Example",
            timeout=30,
        )
        checks.append((
            "single keyword backward-compatible",
            single.get("total") == 1,
            f"total={single.get('total')}",
        ))

        _, reversed_pairs = http(
            "GET",
            "/api/v1/collect/datasets/2/search?q=Domain%20Example",
            timeout=30,
        )
        checks.append((
            "multi keyword AND (reversed order hits)",
            reversed_pairs.get("total") == 1,
            f"total={reversed_pairs.get('total')} (整串实现应为 0)",
        ))

        _, missing_word = http(
            "GET",
            "/api/v1/collect/datasets/2/search?q=Domain%20zzz-no-such",
            timeout=30,
        )
        checks.append((
            "multi keyword requires all words",
            missing_word.get("total") == 0,
            f"total={missing_word.get('total')}",
        ))

        # [4] 时间过滤
        print("[4] date filter ...", flush=True)
        _, date_ok = http(
            "GET",
            "/api/v1/collect/datasets/2/search?date_field=title&date_from=2000-01-01",
            timeout=30,
        )
        checks.append((
            "date filter participates (non-date values excluded)",
            date_ok.get("total") == 0,
            f"total={date_ok.get('total')} (过滤前为 1)",
        ))

        status, _ = http(
            "GET",
            "/api/v1/collect/datasets/2/search?date_from=2000-01-01",
            timeout=30,
        )
        checks.append((
            "date_from without date_field -> 400",
            status == 400,
            f"status={status}",
        ))

        status, _ = http(
            "GET",
            "/api/v1/collect/datasets/2/search?date_field=nope&date_from=2000-01-01",
            timeout=30,
        )
        checks.append((
            "invalid date_field -> 400",
            status == 400,
            f"status={status}",
        ))

        # [5] 前端
        print("[5] frontend search E2E ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})

            page.goto(f"{FRONTEND}/datasets/2", wait_until="networkidle")
            page.wait_for_selector("input[placeholder*='关键字']", timeout=20000)

            # 5a. 多词检索
            page.fill("input[placeholder*='关键字']", "Domain Example")
            page.keyboard.press("Enter")
            page.wait_for_timeout(900)
            body_text = page.locator("body").inner_text()
            checks.append((
                "frontend multi-keyword search",
                "条命中" in body_text,
                "",
            ))

            # 5b. 时间过滤展开 + 应用
            page.click("button:has-text('时间过滤')")
            page.wait_for_timeout(400)
            combos = page.locator('button[role="combobox"]')
            combos.nth(1).click()
            page.wait_for_selector('[role="option"]', timeout=10000)
            page.locator('[role="option"]:has-text("title")').first.click()
            page.fill('input[aria-label="起始日期"]', "2000-01-01")
            page.click("button:has-text('检索')")
            page.wait_for_timeout(900)
            body_text2 = page.locator("body").inner_text()
            checks.append((
                "frontend date filter applied",
                "时间「2000-01-01" in body_text2.replace(" ", " ")
                or "2000-01-01" in body_text2,
                "",
            ))
            page.screenshot(
                path=str(EVIDENCE_DIR / "search-filter.png"), full_page=True
            )
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

    print("\n=== D4 SEARCH PLUS VERIFY RESULTS ===", flush=True)
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
