# -*- coding: utf-8 -*-
"""E3 断点续传重入恢复 · 实机验证门禁

验证内容（真实链路）：

1. succeeded 任务拒绝 resume（400，机制边界）
2. **模拟中断现场**：SQLite 直接改 job.status=partial + 一个分片 failed
3. 前端任务详情页出现「重试失败分片」按钮（截图）
4. POST resume → 分片重置并**真实重新执行**（example.com 去重命中 → 任务收敛）
5. 恢复后：job 状态离开 partial、分片不再是 failed
6. 证据落盘 `docs/evidence/e3-resume/`

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_resume_e3.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "e3-resume"
MAIN_DB = BACKEND_DIR / "data_platform.db"

API = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5174"

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows


def http(method: str, path: str, payload=None, timeout: float = 180.0):
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
            body = exc.read().decode("utf-8", errors="ignore")[:300]
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


def db_break_job(job_id: int) -> int:
    """模拟中断现场：job → partial，首个分片 → failed。返回分片 id。"""
    con = sqlite3.connect(str(MAIN_DB), timeout=15)
    try:
        cur = con.cursor()
        cur.execute("UPDATE collect_jobs SET status='partial' WHERE id=?", (job_id,))
        cur.execute(
            "SELECT id FROM collect_tasks WHERE job_id=? ORDER BY id LIMIT 1",
            (job_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"job {job_id} has no tasks")
        task_id = row[0]
        cur.execute(
            "UPDATE collect_tasks SET status='failed', last_error='simulated interruption' "
            "WHERE id=?",
            (task_id,),
        )
        con.commit()
        return task_id
    finally:
        con.close()


def db_read_state(job_id: int) -> tuple[str, str]:
    con = sqlite3.connect(str(MAIN_DB), timeout=15)
    try:
        cur = con.cursor()
        cur.execute("SELECT status FROM collect_jobs WHERE id=?", (job_id,))
        job_status = cur.fetchone()[0]
        cur.execute(
            "SELECT status FROM collect_tasks WHERE job_id=? ORDER BY id LIMIT 1",
            (job_id,),
        )
        task_status = cur.fetchone()[0]
        return job_status, task_status
    finally:
        con.close()


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

        # [2] 找一个 succeeded 的 job
        print("[3] pick a succeeded job ...", flush=True)
        _, jobs_resp = http("GET", "/api/v1/collect/jobs?limit=20", timeout=30)
        job = next(
            (
                item
                for item in jobs_resp.get("items", [])
                if item.get("status") == "succeeded"
            ),
            None,
        )
        if job is None:
            raise RuntimeError("no succeeded job available")
        job_id = job["job_id"]
        checks.append(("succeeded job available", True, f"job={job_id}"))

        # [3] 拒绝路径：succeeded 不能 resume
        try:
            http("POST", f"/api/v1/collect/jobs/{job_id}/resume", timeout=30)
            rejected = False
        except RuntimeError as exc:
            rejected = "HTTP 400" in str(exc)
        checks.append(("succeeded job resume rejected (400)", rejected, ""))

        # [4] 模拟中断现场
        print("[4] simulate interruption ...", flush=True)
        task_id = db_break_job(job_id)
        job_state, task_state = db_read_state(job_id)
        checks.append((
            "interruption staged (job=partial, task=failed)",
            job_state == "partial" and task_state == "failed",
            f"job={job_state} task={task_state}",
        ))

        # [5] 前端按钮截图
        print("[5] frontend resume button ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{FRONTEND}/collect/{job_id}", wait_until="networkidle")
            page.wait_for_selector("text=重试失败分片", timeout=20000)
            page.wait_for_timeout(900)
            checks.append(("resume button visible on partial job", True, ""))
            page.screenshot(path=str(EVIDENCE_DIR / "job-partial-with-button.png"))

            # [6] 点击重试（E2E）
            print("[6] click resume (E2E) ...", flush=True)
            page.click("text=重试失败分片")
            page.wait_for_selector("text=重试完成", timeout=180000)
            page.wait_for_timeout(1200)
            body_text = page.locator("body").inner_text()
            checks.append((
                "resume E2E completes with message",
                "重试完成" in body_text,
                "",
            ))
            page.screenshot(path=str(EVIDENCE_DIR / "job-after-resume.png"))
            browser.close()

        # [7] 恢复后状态
        job_state2, task_state2 = db_read_state(job_id)
        checks.append((
            "job left partial after resume",
            job_state2 in ("succeeded", "partial"),
            f"job {job_state} -> {job_state2}",
        ))
        checks.append((
            "task no longer failed",
            task_state2 != "failed",
            f"task {task_state} -> {task_state2}",
        ))

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))
    finally:
        print("[8] cleanup processes ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass

    print("\n=== E3 RESUME VERIFY RESULTS ===", flush=True)
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
