# -*- coding: utf-8 -*-
"""数据集详情 · 实机验证门禁（P8c）

验证内容（真实链路）：

1. 数据集就绪：取最新 ds_ 数据集（无则用 计划→采集→物化 链现场创建）
2. 元信息接口：`/collect/datasets/{id}/preview` 返回 dataset（schema / lineage / pii_policy / statistics）
3. 导出链路：`/analytics/export/{id}` CSV 与 JSON 均返回有效内容
4. 前端 `/datasets/{id}` 页面渲染（字段概览 / 血缘 / 预览）与截图
5. 证据落盘 `docs/evidence/p8c-dataset/`

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_dataset_detail_p8c.py
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
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "p8c-dataset"

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


def fetch_text(path: str, timeout: float = 60.0) -> tuple[int, str, str]:
    """读取非 JSON 响应，返回 (status, text, content_type)。"""
    request = urllib.request.Request(f"{API}{path}")
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return (
            resp.status,
            resp.read().decode("utf-8", errors="ignore"),
            resp.headers.get("Content-Type", ""),
        )


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


def ensure_dataset() -> int:
    """取最新 ds_ 数据集；没有则现场跑一条 计划→采集→物化。"""
    _, tables = http("GET", "/api/v1/data/tables")
    candidates = [
        t for t in tables.get("tables", [])
        if str(t.get("name", "")).startswith("ds_")
    ]
    if candidates:
        return int(str(candidates[0]["name"]).replace("ds_", "", 1))
    # 现场创建
    _, plan_resp = http(
        "POST", "/api/v1/collect/plan",
        {"url": "https://example.com/", "declared_authorization": "official"},
    )
    _, run_resp = http(
        "POST", "/api/v1/collect/run",
        {"plan_id": plan_resp["plan"]["plan_id"]}, timeout=180,
    )
    _, dataset = http(
        "POST", f"/api/v1/collect/jobs/{run_resp['job']['job_id']}/materialize"
    )
    return int(dataset["id"])


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

        # [3] 数据集就绪 + 元信息
        print("[3] dataset + meta ...", flush=True)
        dataset_id = ensure_dataset()
        _, preview = http(
            "GET", f"/api/v1/collect/datasets/{dataset_id}/preview",
            timeout=30,
        )
        meta = preview.get("dataset") or {}
        checks.append((
            "preview carries dataset meta",
            bool(meta.get("id")) and meta.get("row_count") is not None,
            f"dataset={dataset_id} name={meta.get('name')}",
        ))
        checks.append((
            "meta has schema/lineage/pii fields",
            "schema" in meta and "lineage" in meta and "pii_policy" in meta,
            f"schema={'yes' if meta.get('schema') is not None else 'null'} "
            f"lineage={'yes' if meta.get('lineage') else 'empty'}",
        ))
        checks.append((
            "preview rows readable",
            isinstance(preview.get("rows"), list) and len(preview.get("rows")) >= 0,
            f"rows={len(preview.get('rows') or [])} / total={preview.get('total')}",
        ))

        # [4] 导出链路
        print("[4] export csv / json ...", flush=True)
        status_csv, csv_text, csv_type = fetch_text(
            f"/api/v1/analytics/export/{dataset_id}?format=csv"
        )
        checks.append((
            "csv export works",
            status_csv == 200 and len(csv_text) > 0,
            f"bytes={len(csv_text)} type={csv_type.split(';')[0]}",
        ))
        status_json, json_text, _ = fetch_text(
            f"/api/v1/analytics/export/{dataset_id}?format=json"
        )
        json_ok = False
        try:
            json.loads(json_text)
            json_ok = True
        except Exception:
            pass
        checks.append((
            "json export works",
            status_json == 200 and json_ok,
            f"bytes={len(json_text)}",
        ))

        # [5] 前端页面
        print("[5] frontend dataset detail ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"{FRONTEND}/datasets/{dataset_id}", wait_until="networkidle")
            page.wait_for_selector("text=字段概览", timeout=20000)
            page.wait_for_timeout(1300)
            body_text = page.locator("body").inner_text()
            checks.append((
                "dataset detail renders (fields + lineage + preview)",
                "字段概览" in body_text
                and "字段级血缘" in body_text
                and "数据预览" in body_text,
                f"dataset={dataset_id}",
            ))
            page.screenshot(
                path=str(EVIDENCE_DIR / "dataset-detail.png"), full_page=True
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

    print("\n=== P8C DATASET VERIFY RESULTS ===", flush=True)
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
