# -*- coding: utf-8 -*-
"""P8 合规中心 · 实机验证门禁

验证内容（真实链路）：

1. 种子数据：analyze 3 个公开站点，产生 proceed / confirm_required 判定
2. `/verdicts/stats` 聚合断言（总数 / 决策分布 / 矩阵）
3. `PATCH /verdicts/{uid}/authorization` 补齐授权：confirm_required → proceed
   （写回操作者与依据；审计留痕）
4. 前端 `/compliance` 页面渲染（Playwright + 截图）
5. 证据落盘 docs/evidence/p8-compliance/

数据策略：种子判定与审计**保留**（平台资产）；本脚本不做清理。

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_compliance_p8.py
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
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "p8-compliance"

API = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5174"

SEED_TARGETS = [
    "https://example.com/",
    "https://www.iana.org/",
    "https://docs.python.org/3/",
]

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows


def http(method: str, path: str, payload=None, timeout: float = 90.0):
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

        # [2] 基线统计
        _, before = http("GET", "/api/v1/discover/verdicts/stats")
        before_total = before["total"]

        # [3] 种子数据：analyze 公开站点（无声明 → 覆盖 confirm_required 场景）
        print("[3] seeding verdicts (analyze public sites) ...", flush=True)
        confirm_uids: list[str] = []
        proceed_count = 0
        for target in SEED_TARGETS:
            status, result = http(
                "POST", "/api/v1/discover/analyze", {"url": target}, timeout=120
            )
            compliance = result.get("compliance") or {}
            decision = compliance.get("decision")
            if decision == "confirm_required":
                confirm_uids.append(compliance["verdict_id"])
            elif decision == "proceed":
                proceed_count += 1
            print(f"    {target} -> {decision}", flush=True)
        checks.append((
            "seed verdicts created",
            len(confirm_uids) + proceed_count >= 3,
            f"confirm_required={len(confirm_uids)} proceed={proceed_count}",
        ))
        checks.append((
            "example.com is confirm_required (no declaration)",
            len(confirm_uids) >= 1,
            f"{len(confirm_uids)} pending verdict(s)",
        ))

        # [4] stats 聚合断言
        print("[4] stats aggregation ...", flush=True)
        _, after = http("GET", "/api/v1/discover/verdicts/stats")
        checks.append((
            "stats total grows by seeds",
            after["total"] >= before_total + 3,
            f"{before_total} -> {after['total']}",
        ))
        checks.append((
            "stats by_decision populated",
            after["by_decision"]["confirm_required"] >= 1 and after["total"] >= 3,
            str(after["by_decision"]),
        ))
        checks.append((
            "stats matrix non-empty",
            len(after["matrix"]) >= 1,
            f"{len(after['matrix'])} cells",
        ))

        # [5] 补齐授权：confirm_required → proceed（写回 + 解锁）
        print("[5] confirm authorization (unlock) ...", flush=True)
        target_uid = confirm_uids[0]
        status, resp = http(
            "PATCH",
            f"/api/v1/discover/verdicts/{target_uid}/authorization",
            {"basis": "official", "operator": "yg-verify", "note": "P8 验收：公开演示站点"},
        )
        unlocked = resp.get("unlocked") is True
        updated = resp.get("verdict", {})
        checks.append((
            "authorization confirmed and unlocked",
            unlocked
            and updated.get("decision") == "proceed"
            and updated.get("dimensions", {}).get("authorization") == "B1"
            and updated.get("operator") == "yg-verify",
            f"decision={updated.get('decision')} operator={updated.get('operator')}",
        ))

        # [6] 前端页面（Playwright）
        print("[6] frontend compliance page ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"{FRONTEND}/compliance", wait_until="networkidle")
            page.wait_for_selector("text=合规中心", timeout=20000)
            page.wait_for_timeout(1500)
            body_text = page.locator("body").inner_text()
            rendered = (
                "判定总数" in body_text
                and "可访问性 × 授权基础" in body_text
                and "全部判定" in body_text
            )
            checks.append(("compliance page renders", rendered, ""))
            page.screenshot(path=str(EVIDENCE_DIR / "compliance-page.png"))
            page.screenshot(
                path=str(EVIDENCE_DIR / "compliance-page-full.png"), full_page=True
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

    print("\n=== P8 COMPLIANCE VERIFY RESULTS ===", flush=True)
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
