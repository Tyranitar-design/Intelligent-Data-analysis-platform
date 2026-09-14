# -*- coding: utf-8 -*-
"""E2 调度闭环 · 实机验证门禁（v5 蓝图 P7 · 定时调度）

验证内容（真实链路，直连 uvicorn + vite dev）：

1. 计划创建：真实判别 example.com（公开站点）
2. 调度规则 CRUD：创建（next_run 计算）→ 暂停（清空）→ 恢复（重算）
3. 自动触发：把 next_run 改到过去 → 调度循环（2s 间隔）自动创建并执行任务
4. 手动触发：POST /run 再次执行
5. 前端 /schedules 页面渲染（Playwright + 截图）
6. 证据落盘 docs/evidence/e2-verify/

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_schedules_e2.py

结束自动清理：停止进程 + 删除本次测试产生的数据（计划/规则/任务/画像/判定）。
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "e2-verify"
MAIN_DB = BACKEND_DIR / "data_platform.db"

API = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5174"
TARGET_URL = "https://example.com/"

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows


def http(method: str, path: str, payload=None, timeout: float = 60.0):
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
            body = exc.read().decode("utf-8", errors="ignore")[:600]
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


def find_schedule(schedule_id: int) -> dict | None:
    _, payload = http("GET", "/api/v1/collect/schedules")
    for item in payload.get("items", []):
        if item["schedule_id"] == schedule_id:
            return item
    return None


def db_force_due(schedule_id: int) -> None:
    """把一条规则的 next_run_at 改到过去（模拟到点），供调度循环拾取。"""
    con = sqlite3.connect(str(MAIN_DB), timeout=15)
    try:
        con.execute(
            "UPDATE collect_schedules SET next_run_at = datetime('now','localtime','-5 minutes') "
            "WHERE id = ?",
            (schedule_id,),
        )
        con.commit()
    finally:
        con.close()


def db_cleanup(plan_id: int, profile_id: int | None) -> None:
    con = sqlite3.connect(str(MAIN_DB), timeout=15)
    try:
        cur = con.cursor()
        cur.execute(
            "DELETE FROM collect_items WHERE job_id IN "
            "(SELECT id FROM collect_jobs WHERE plan_id = ?)",
            (plan_id,),
        )
        cur.execute(
            "DELETE FROM collect_tasks WHERE job_id IN "
            "(SELECT id FROM collect_jobs WHERE plan_id = ?)",
            (plan_id,),
        )
        cur.execute("DELETE FROM collect_jobs WHERE plan_id = ?", (plan_id,))
        cur.execute("DELETE FROM collect_schedules WHERE plan_id = ?", (plan_id,))
        cur.execute("DELETE FROM collect_plans WHERE id = ?", (plan_id,))
        if profile_id:
            cur.execute(
                "DELETE FROM compliance_verdicts WHERE profile_id = ?", (profile_id,)
            )
            cur.execute("DELETE FROM site_profiles WHERE id = ?", (profile_id,))
        con.commit()
    finally:
        con.close()


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    procs: list[subprocess.Popen] = []
    schedule_id: int | None = None
    plan_id: int | None = None
    profile_id: int | None = None
    plan_a_id: int | None = None
    profile_a: int | None = None

    try:
        # [1] 启动服务
        print("[1] starting backend (:8000, tick=2s) ...", flush=True)
        py = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
        env = dict(os.environ)
        env["SCHEDULE_TICK_SECONDS"] = "2"
        procs.append(
            subprocess.Popen(
                [str(py), "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
                cwd=str(BACKEND_DIR),
                env=env,
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

        # [3a] 反例：未声明授权 → confirm_required → 调度创建应被合规门拦截
        print("[3a] plan without declaration (expect confirm_required) ...", flush=True)
        status, plan_a = http("POST", "/api/v1/collect/plan", {"url": TARGET_URL}, timeout=90)
        plan_a_id = plan_a["plan"]["plan_id"]
        profile_a = plan_a["plan"].get("profile_id")
        decision_a = plan_a.get("compliance", {}).get("decision")
        checks.append((
            "plan A confirm_required (no declaration)",
            decision_a == "confirm_required",
            f"plan_id={plan_a_id} decision={decision_a}",
        ))
        try:
            http(
                "POST", "/api/v1/collect/schedules",
                {"name": "e2-verify blocked-plan", "plan_id": plan_a_id,
                 "frequency": "daily", "time_of_day": "06:00"},
            )
            rejected = False
        except RuntimeError as exc:
            rejected = "HTTP 400" in str(exc)
        checks.append((
            "compliance gate rejects confirm_required plan",
            rejected,
            "blocked by compliance gate" if rejected else "NOT rejected",
        ))

        # [3b] 正例：声明 official → proceed → 可创建调度
        print("[3b] plan with declared authorization (expect proceed) ...", flush=True)
        status, plan_b = http(
            "POST", "/api/v1/collect/plan",
            {"url": TARGET_URL, "declared_authorization": "official",
             "force_refresh": True},
            timeout=90,
        )
        plan_id = plan_b["plan"]["plan_id"]
        profile_id = plan_b["plan"].get("profile_id")
        decision_b = plan_b.get("compliance", {}).get("decision")
        checks.append((
            "plan B proceed (declared official)",
            decision_b == "proceed",
            f"plan_id={plan_id} decision={decision_b}",
        ))

        # [4] 调度规则 CRUD
        print("[4] schedule create / pause / resume ...", flush=True)
        status, resp = http(
            "POST",
            "/api/v1/collect/schedules",
            {"name": "e2-verify daily", "plan_id": plan_id, "frequency": "daily",
             "time_of_day": "06:00"},
        )
        schedule = resp["schedule"]
        schedule_id = schedule["schedule_id"]
        checks.append((
            "schedule created with next_run",
            bool(schedule["next_run_at"]) and schedule["frequency_text"] == "每天 06:00",
            f"next={schedule['next_run_at']}",
        ))

        _, resp = http("PATCH", f"/api/v1/collect/schedules/{schedule_id}",
                       {"enabled": False})
        paused = resp["schedule"]
        checks.append(("pause clears next_run", paused["next_run_at"] is None, ""))

        _, resp = http("PATCH", f"/api/v1/collect/schedules/{schedule_id}",
                       {"enabled": True})
        resumed = resp["schedule"]
        checks.append(("resume recomputes next_run", bool(resumed["next_run_at"]),
                       f"next={resumed['next_run_at']}"))

        # [5] 自动触发：把 next_run 改到过去，等调度循环拾取
        print("[5] forcing due + waiting for schedule loop ...", flush=True)
        db_force_due(schedule_id)
        deadline = time.time() + 40
        auto_triggered: dict | None = None
        while time.time() < deadline:
            item = find_schedule(schedule_id)
            if item and (item["run_count"] or 0) >= 1:
                auto_triggered = item
                break
            time.sleep(2)
        checks.append((
            "schedule loop auto-triggered",
            auto_triggered is not None,
            f"run_count={auto_triggered['run_count'] if auto_triggered else 0} "
            f"last_job={auto_triggered['last_job_id'] if auto_triggered else None}",
        ))
        if auto_triggered and auto_triggered.get("last_job_id"):
            _, job_resp = http("GET", f"/api/v1/collect/jobs/{auto_triggered['last_job_id']}")
            checks.append((
                "auto-triggered job recorded",
                job_resp.get("status") in ("succeeded", "partial", "failed"),
                f"job={auto_triggered['last_job_id']} status={job_resp.get('status')} items={job_resp.get('items_count')}",
            ))

        # [6] 手动触发
        print("[6] manual run ...", flush=True)
        _, resp = http("POST", f"/api/v1/collect/schedules/{schedule_id}/run",
                       timeout=120)
        result = resp["result"]
        manual_count = resp["schedule"]["run_count"]
        checks.append((
            "manual run executed",
            bool(result.get("job_id")) and manual_count >= 2,
            f"job={result.get('job_id')} status={result.get('status')} run_count={manual_count}",
        ))

        # [7] 前端页面（Playwright）
        print("[7] frontend page check ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{FRONTEND}/schedules", wait_until="networkidle")
            page.wait_for_selector("text=调度中心", timeout=20000)
            page.wait_for_timeout(1200)
            body_text = page.locator("body").inner_text()
            rendered = "新建调度" in body_text and "e2-verify daily" in body_text
            checks.append(("frontend schedules page renders list", rendered, ""))
            page.screenshot(path=str(EVIDENCE_DIR / "schedules-page.png"))
            browser.close()

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))
    finally:
        print("[8] cleanup ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass
        try:
            removed: list[str] = []
            if plan_id is not None:
                db_cleanup(plan_id, profile_id)
                removed.append(f"plan={plan_id}")
            if plan_a_id is not None:
                db_cleanup(plan_a_id, profile_a)
                removed.append(f"plan={plan_a_id}")
            checks.append(("cleanup test data", True, ", ".join(removed) or "nothing"))
        except Exception as exc:  # noqa: BLE001
            checks.append(("cleanup test data", False, str(exc)))

    print("\n=== E2 VERIFY RESULTS ===", flush=True)
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
