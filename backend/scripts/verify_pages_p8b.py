# -*- coding: utf-8 -*-
"""P8b/F2 页面三连 · 实机验证门禁

验证内容（真实链路）：

1. 数据链：计划（声明 official → proceed）→ 真实采集 example.com → 物化为数据集
2. 合规解锁：analyze 新站点产生 confirm_required → 补齐授权（审计留痕）
3. 三个页面渲染与截图：
   - `/`                 工作台 Hero
   - `/collect/{job}`    任务详情（管道 / 时间线 / 降级链 / 条目）
   - `/audit`            审计日志
4. 证据落盘 `docs/evidence/p8b-f2/`

数据策略：plan / job / dataset / 判定 / 审计均**保留**（真实使用痕迹，展示资产）。

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_pages_p8b.py
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
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "p8b-f2"

API = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5174"
TARGET_URL = "https://example.com/"

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

        # [3] 数据链：计划 → 采集 → 物化
        print("[3] plan -> run -> materialize ...", flush=True)
        _, plan_resp = http(
            "POST", "/api/v1/collect/plan",
            {"url": TARGET_URL, "declared_authorization": "official"},
        )
        plan_id = plan_resp["plan"]["plan_id"]
        decision = (plan_resp.get("compliance") or {}).get("decision")
        checks.append((
            "plan created (proceed)",
            decision == "proceed",
            f"plan_id={plan_id} decision={decision}",
        ))

        _, run_resp = http(
            "POST", "/api/v1/collect/run", {"plan_id": plan_id}, timeout=180
        )
        job = run_resp.get("job", {})
        job_id = job.get("job_id")
        checks.append((
            "collect run completed",
            job.get("status") in ("succeeded", "partial") and job_id is not None,
            f"job={job_id} status={job.get('status')} items={job.get('items_count')}",
        ))

        _, dataset = http(
            "POST", f"/api/v1/collect/jobs/{job_id}/materialize", timeout=60
        )
        checks.append((
            "materialized to dataset",
            bool(dataset.get("id")),
            f"dataset={dataset.get('id')} rows={dataset.get('row_count')} cols={dataset.get('column_count')}",
        ))

        # [4] 合规解锁（产生审计留痕）
        print("[4] analyze + unlock (audit trail) ...", flush=True)
        _, analyzed = http(
            "POST", "/api/v1/discover/analyze", {"url": "https://www.iana.org/"},
            timeout=120,
        )
        compliance = analyzed.get("compliance") or {}
        uid = compliance.get("verdict_id")
        checks.append((
            "fresh confirm_required verdict",
            compliance.get("decision") == "confirm_required" and bool(uid),
            f"decision={compliance.get('decision')}",
        ))
        if uid:
            _, unlocked = http(
                "PATCH",
                f"/api/v1/discover/verdicts/{uid}/authorization",
                {"basis": "official", "operator": "verify-p8b", "note": "页面验证用"},
            )
            checks.append((
                "unlocked with audit trail",
                unlocked.get("unlocked") is True,
                f"operator=verify-p8b",
            ))

        _, audit = http("GET", "/api/v1/audit/logs", timeout=30)
        has_confirm_log = any(
            item.get("action") == "compliance.authorization_confirmed"
            for item in audit.get("items", [])
        )
        checks.append((
            "audit log shows unlock action",
            has_confirm_log,
            f"total={audit.get('total')}",
        ))

        # [5] 三个页面（Playwright）
        print("[5] page screenshots (dashboard / job detail / audit) ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 950})

            # 5a. 工作台 Hero
            page.goto(f"{FRONTEND}/", wait_until="networkidle")
            page.wait_for_selector("text=任意站点，从可采判定到洞察报告", timeout=20000)
            page.wait_for_timeout(1200)
            checks.append(("dashboard hero renders", True, "slogan found"))
            page.screenshot(path=str(EVIDENCE_DIR / "01-dashboard-hero.png"))

            # 5b. 任务详情
            page.goto(f"{FRONTEND}/collect/{job_id}", wait_until="networkidle")
            page.wait_for_selector("text=执行管道", timeout=20000)
            page.wait_for_timeout(1200)
            detail_text = page.locator("body").inner_text()
            checks.append((
                "job detail renders (pipeline + items)",
                "执行管道" in detail_text and "采集条目" in detail_text,
                f"job={job_id}",
            ))
            page.screenshot(path=str(EVIDENCE_DIR / "02-job-detail.png"), full_page=True)

            # 5c. 审计日志
            page.goto(f"{FRONTEND}/audit", wait_until="networkidle")
            page.wait_for_selector("text=留痕记录", timeout=20000)
            page.wait_for_timeout(1200)
            audit_text = page.locator("body").inner_text()
            checks.append((
                "audit page renders with unlock action",
                "留痕记录" in audit_text and "compliance.authorization_confirmed" in audit_text,
                "",
            ))
            page.screenshot(path=str(EVIDENCE_DIR / "03-audit.png"))

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

    print("\n=== P8b/F2 VERIFY RESULTS ===", flush=True)
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
