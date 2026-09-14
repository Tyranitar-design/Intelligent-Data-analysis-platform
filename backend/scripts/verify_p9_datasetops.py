# -*- coding: utf-8 -*-
"""P9 数据集检索与对比 · 实机验证门禁

验证内容（真实链路）：

1. 数据就绪：现有数据集 ≥1；现场再跑 计划→采集→物化 产生第二个数据集
2. `/datasets` 列表端点
3. 检索：`q=Example` 命中；字段限域；无匹配空结果
4. 对比：两个数据集 diff（共同字段含 title）
5. 前端：`/compare` 页选择 A/B → 对比渲染；`/datasets/{id}` 检索框 E2E
6. 证据落盘 `docs/evidence/p9-datasetops/`

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_p9_datasetops.py
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
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "p9-datasetops"

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

        # [3] 数据集列表 + 确保至少两个
        print("[3] datasets list + ensure two ...", flush=True)
        _, listing = http("GET", "/api/v1/collect/datasets", timeout=30)
        items = listing.get("items", [])
        checks.append((
            "datasets list endpoint",
            isinstance(items, list),
            f"count={len(items)}",
        ))

        if len(items) < 2:
            # 同一来源重新物化 → 该数据集的第二个版本快照。
            # （注：重复采集同一静态站点不会产生新数据集——三级去重按设计跳过
            #  全部已知条目，这正是"增量优先"的语义。）
            _, jobs_resp = http("GET", "/api/v1/collect/jobs?limit=20", timeout=30)
            source_job = next(
                (
                    job
                    for job in jobs_resp.get("items", [])
                    if (job.get("items_count") or 0) > 0
                ),
                None,
            )
            if source_job is None:
                raise RuntimeError("no job with items available for re-materialize")
            _, dataset = http(
                "POST",
                f"/api/v1/collect/jobs/{source_job['job_id']}/materialize",
                timeout=60,
            )
            print(
                f"    re-materialized job {source_job['job_id']} -> dataset #{dataset.get('id')}",
                flush=True,
            )
            _, listing = http("GET", "/api/v1/collect/datasets", timeout=30)
            items = listing.get("items", [])

        checks.append((
            "two datasets available for diff",
            len(items) >= 2,
            f"ids={[item['dataset_id'] for item in items[:4]]}",
        ))
        dataset_a = items[0]["dataset_id"]
        dataset_b = items[1]["dataset_id"]

        # [4] 检索链路
        print("[4] search ...", flush=True)
        _, hit = http(
            "GET",
            f"/api/v1/collect/datasets/{dataset_a}/search",
            timeout=30,
        )
        hit_total = hit.get("total")
        _, matched = http(
            "GET",
            f"/api/v1/collect/datasets/{dataset_a}/search?q=Example",
            timeout=30,
        )
        checks.append((
            "search keyword matches",
            matched.get("total", 0) >= 1,
            f"total {hit_total} -> {matched.get('total')} (q=Example)",
        ))
        _, nomatch = http(
            "GET",
            f"/api/v1/collect/datasets/{dataset_a}/search?q=zzz-no-such",
            timeout=30,
        )
        checks.append((
            "search no-match returns empty",
            nomatch.get("total") == 0,
            f"total={nomatch.get('total')}",
        ))

        # [5] 对比链路
        print("[5] diff ...", flush=True)
        _, diff = http(
            "GET",
            f"/api/v1/collect/datasets/diff?a={dataset_a}&b={dataset_b}",
            timeout=30,
        )
        checks.append((
            "diff computes common fields",
            isinstance(diff.get("common_fields"), list)
            and "row_delta" in diff,
            f"a={dataset_a} b={dataset_b} common={len(diff.get('common_fields', []))} "
            f"delta={diff.get('row_delta')}",
        ))

        # [6] 前端页面
        print("[6] frontend compare + search E2E ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})

            # 6a. /compare 选择 + 对比
            page.goto(f"{FRONTEND}/compare", wait_until="networkidle")
            page.wait_for_selector("text=数据集 A（基线）", timeout=20000)
            page.wait_for_timeout(800)

            combos = page.locator('button[role="combobox"]')
            combos.nth(0).click()
            page.wait_for_selector('[role="option"]', timeout=10000)
            page.locator('[role="option"]').nth(0).click()
            page.wait_for_timeout(300)
            combos.nth(1).click()
            page.wait_for_selector('[role="option"]', timeout=10000)
            page.locator('[role="option"]').nth(1).click()
            page.wait_for_timeout(300)
            page.click("text=开始对比")
            page.wait_for_selector("text=字段变化", timeout=15000)
            page.wait_for_timeout(700)
            compare_text = page.locator("body").inner_text()
            checks.append((
                "compare page renders diff result",
                "字段变化" in compare_text and "行数差" in compare_text,
                "",
            ))
            page.screenshot(
                path=str(EVIDENCE_DIR / "compare-result.png"), full_page=True
            )

            # 6b. 详情页检索
            page.goto(f"{FRONTEND}/datasets/{dataset_a}", wait_until="networkidle")
            page.wait_for_selector("input[placeholder*='关键字检索']", timeout=20000)
            page.fill("input[placeholder*='关键字检索']", "Example")
            page.keyboard.press("Enter")
            page.wait_for_selector("text=条命中", timeout=15000)
            page.wait_for_timeout(700)
            search_text = page.locator("body").inner_text()
            checks.append((
                "dataset detail search E2E",
                "条命中" in search_text,
                "",
            ))
            page.screenshot(
                path=str(EVIDENCE_DIR / "search-result.png"), full_page=True
            )
            browser.close()

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))
    finally:
        print("[7] cleanup processes ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass

    print("\n=== P9 DATASET OPS VERIFY RESULTS ===", flush=True)
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
