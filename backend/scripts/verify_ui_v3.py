# -*- coding: utf-8 -*-
"""UI v3 全页体检 · 实机验证门禁

遍历全部 16 个路由：每页渲染断言 + 全页截图 + 控制台错误收集。
（`/collect/:id` 与 `/datasets/:id` 的 id 从 API 动态获取。）

证据落盘 `docs/evidence/ui-v3/`。

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_ui_v3.py
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "ui-v4" / "all-pages"

API = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5174"

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows


def http_json(path: str, timeout: float = 30.0):
    with urllib.request.urlopen(f"{API}{path}", timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


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

        # [2] 动态取详情页 id
        jobs = http_json("/api/v1/collect/jobs?limit=5").get("items", [])
        job_id = jobs[0]["job_id"] if jobs else 1
        datasets = http_json("/api/v1/collect/datasets?limit=5").get("items", [])
        dataset_id = datasets[0]["dataset_id"] if datasets else 1

        pages = [
            ("/", "平台概览", "01-dashboard"),
            ("/discover", "站点分析", "02-discover"),
            ("/sites", "站点库", "03-sites"),
            ("/collect", "采集任务", "04-collect"),
            (f"/collect/{job_id}", "执行管道", "05-job-detail"),
            ("/schedules", "调度中心", "06-schedules"),
            ("/datasets", "数据集", "07-datasets"),
            (f"/datasets/{dataset_id}", "字段概览", "08-dataset-detail"),
            ("/compare", "对比分析", "09-compare"),
            ("/analytics", "数据分析", "10-analytics"),
            ("/reports", "分析报告", "11-reports"),
            ("/compliance", "合规中心", "12-compliance"),
            ("/audit", "审计日志", "13-audit"),
            ("/monitor", "运行监视", "14-monitor"),
            ("/integrations", "接入管理", "15-integrations"),
            ("/showcase", "数据在此流动", "16-showcase"),
        ]

        # [3] 遍历
        print(f"[3] touring {len(pages)} pages ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            console_errors: list[str] = []
            page.on(
                "console",
                lambda msg: (
                    console_errors.append(msg.text) if msg.type == "error" else None
                ),
            )

            for route, needle, shot in pages:
                page.goto(f"{FRONTEND}{route}", wait_until="networkidle")
                try:
                    page.wait_for_selector(f"text={needle}", timeout=20000)
                    page.wait_for_timeout(850)
                    page.screenshot(path=str(EVIDENCE_DIR / f"{shot}.png"))
                    checks.append((f"{route}", True, needle))
                except Exception as exc:  # noqa: BLE001
                    checks.append((f"{route}", False, f"{type(exc).__name__}: {exc}"))

            severe = [e for e in console_errors if "favicon" not in e.lower()]
            checks.append((
                "no console errors across tour",
                len(severe) == 0,
                f"{len(severe)}: {severe[:3]}",
            ))
            browser.close()

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))
    finally:
        print("[4] cleanup processes ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass

    print("\n=== UI V3 ALL-PAGES VERIFY RESULTS ===", flush=True)
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
