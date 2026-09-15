# -*- coding: utf-8 -*-
"""P9b 审计点 + 版本历史 + 保留报告 · 实机验证门禁

验证内容（真实链路）：

1. 服务就绪（backend :8000 / frontend :5174）
2. 审计点端到端：现场触发一次导出 → 主库 audit_logs 出现 ``export.dataset`` 记录
3. 版本历史：``/collect/datasets/2/versions`` 返回同计划版本链（ds1 + ds2）
4. 保留报告：``/monitor/retention`` 四类资产 + 总行数
5. 前端三页：
   - ``/datasets/2`` 版本历史卡（v1/v2 + 当前标记）
   - ``/compare?a=2&b=1`` URL 预选自动出对比结果
   - ``/monitor`` 数据保留（只读）卡
6. 证据落盘 ``docs/evidence/p9b-audit-versions/``

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_p9b_audit_versions.py
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "p9b-audit-versions"
MAIN_DB = BACKEND_DIR / "data_platform.db"

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

        # [3] 版本链数据就绪（ds1/ds2 同挂 job1）
        print("[3] versions chain ...", flush=True)
        _, versions = http("GET", "/api/v1/collect/datasets/2/versions", timeout=30)
        chain_ids = [v["id"] for v in versions.get("versions", [])]
        checks.append((
            "versions chain returns [1, 2]",
            chain_ids == [1, 2] and versions.get("current_index") == 1,
            f"ids={chain_ids} idx={versions.get('current_index')} plan={versions.get('plan_id')}",
        ))

        # [4] 审计点端到端：导出触发 → 主库出现审计记录
        print("[4] audit e2e via export ...", flush=True)
        url = f"{API}/api/v1/analytics/export/2?format=csv"
        with urllib.request.urlopen(url, timeout=60) as resp:
            body = resp.read()
        export_ok = resp.status == 200 and len(body) > 0
        con = sqlite3.connect(MAIN_DB)
        try:
            row = con.execute(
                "SELECT principal_id, action, result, target_id, detail "
                "FROM audit_logs WHERE action='export.dataset' AND target_id='2' "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
        finally:
            con.close()
        checks.append((
            "export wrote audit log",
            export_ok and row is not None and row[2] == "ok",
            f"log={row}",
        ))

        # [5] 保留报告
        print("[5] retention report ...", flush=True)
        _, retention = http("GET", "/api/v1/monitor/retention", timeout=30)
        tables = retention.get("tables", {})
        checks.append((
            "retention has 4 assets + total",
            all(k in tables for k in (
                "collect_items", "datasets", "audit_logs", "compliance_verdicts",
            )) and retention.get("total_rows", 0) > 0,
            f"total={retention.get('total_rows')} ds={tables.get('datasets', {}).get('count')}",
        ))

        # [6] 前端三页
        print("[6] frontend pages E2E ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})

            # 6a. 数据集详情 → 版本历史卡
            page.goto(f"{FRONTEND}/datasets/2", wait_until="networkidle")
            page.wait_for_selector("text=版本历史", timeout=20000)
            page.wait_for_timeout(800)
            detail_text = page.locator("body").inner_text()
            checks.append((
                "dataset detail shows version card",
                "版本历史" in detail_text and "当前" in detail_text,
                f"v1 {'v1' in detail_text} v2 {'v2' in detail_text}",
            ))
            page.screenshot(
                path=str(EVIDENCE_DIR / "dataset-versions.png"), full_page=True
            )

            # 6b. 对比页 URL 预选 → 自动出结果
            page.goto(f"{FRONTEND}/compare?a=2&b=1", wait_until="networkidle")
            page.wait_for_selector("text=字段变化", timeout=20000)
            page.wait_for_timeout(700)
            compare_text = page.locator("body").inner_text()
            checks.append((
                "compare auto-runs from url params",
                "字段变化" in compare_text and "行数差" in compare_text,
                "",
            ))
            page.screenshot(
                path=str(EVIDENCE_DIR / "compare-preselect.png"), full_page=True
            )

            # 6c. 监视页 → 数据保留卡
            page.goto(f"{FRONTEND}/monitor", wait_until="networkidle")
            page.wait_for_selector("text=数据保留", timeout=20000)
            page.wait_for_timeout(800)
            monitor_text = page.locator("body").inner_text()
            checks.append((
                "monitor shows retention card",
                "数据保留（只读）" in monitor_text and "采集条目" in monitor_text,
                "",
            ))
            page.screenshot(
                path=str(EVIDENCE_DIR / "monitor-retention.png"), full_page=True
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

    print("\n=== P9B AUDIT / VERSIONS / RETENTION VERIFY RESULTS ===", flush=True)
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
