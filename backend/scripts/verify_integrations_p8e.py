# -*- coding: utf-8 -*-
"""接入管理 · 实机验证门禁（P8e）

验证内容（真实链路）：

1. `GET /mcp` 服务概览（protocol / tool_count / auth_configured）
2. `POST /api/v1/mcp/selftest` 协议自检（initialize 握手）
3. **fail-closed 实证**：无凭据的 tools/call 被拒 + 审计留痕
4. `GET /api/v1/mcp/stats` 聚合更新（denied 计数）
5. 前端 `/integrations` 渲染 + 点击「测试连通」E2E + 截图
6. 证据落盘 `docs/evidence/p8e-integrations/`

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_integrations_p8e.py
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
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "p8e-integrations"

API = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5174"

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows


def http(method: str, path: str, payload=None, timeout: float = 120.0, base: str = API):
    url = f"{base}{path}"
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

        # [3] 服务概览
        print("[3] /mcp overview ...", flush=True)
        _, info = http("GET", "/mcp", timeout=30)
        checks.append((
            "mcp overview (protocol + tools + auth)",
            info.get("protocol") == "json-rpc-2.0-over-http"
            and info.get("tool_count", 0) >= 7
            and isinstance(info.get("tools"), list),
            f"tools={info.get('tool_count')} auth={info.get('auth_configured')}",
        ))

        # [4] 协议自检
        print("[4] selftest (initialize handshake) ...", flush=True)
        _, selftest = http("POST", "/api/v1/mcp/selftest", timeout=30)
        checks.append((
            "selftest initialize handshake",
            selftest.get("ok") is True and bool(selftest.get("server")),
            f"server={selftest.get('server')} elapsed={selftest.get('elapsed_ms')}ms",
        ))

        # [5] fail-closed 实证：无凭据 tools/call 被拒 + 审计留痕
        print("[5] fail-closed proof (no credential tool call) ...", flush=True)
        _, stats_before = http("GET", "/api/v1/mcp/stats", timeout=30)
        status, rpc_resp = http(
            "POST", "/mcp",
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "analyze_site",
                    "arguments": {"url": "https://example.com/"},
                },
            },
            timeout=60,
        )
        has_error = isinstance(rpc_resp, dict) and "error" in rpc_resp
        error_code = (rpc_resp.get("error") or {}).get("code") if has_error else None
        checks.append((
            "unauthenticated tool call rejected (fail-closed)",
            has_error,
            f"error_code={error_code}",
        ))

        _, stats_after = http("GET", "/api/v1/mcp/stats", timeout=30)
        checks.append((
            "rejection is audited",
            stats_after.get("total", 0) == stats_before.get("total", 0) + 1
            and stats_after.get("by_result", {}).get("denied", 0)
            >= stats_before.get("by_result", {}).get("denied", 0) + 1,
            f"total {stats_before.get('total')} -> {stats_after.get('total')} "
            f"denied={stats_after.get('by_result', {}).get('denied')}",
        ))

        # [6] 前端页面 + 测试连通 E2E
        print("[6] frontend integrations page + selftest click ...", flush=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"{FRONTEND}/integrations", wait_until="networkidle")
            page.wait_for_selector("text=工具清单", timeout=20000)
            page.wait_for_timeout(1000)
            body_text = page.locator("body").inner_text()
            checks.append((
                "integrations page renders",
                "工具清单" in body_text
                and "调用统计" not in body_text  # 统计区标题为「按工具/最近调用」，用下列断言
                or ("工具清单" in body_text and "按工具" in body_text),
                "",
            ))

            # 点击「测试连通」→ 等待握手成功文案
            page.click("text=测试连通")
            page.wait_for_selector("text=initialize 握手成功", timeout=15000)
            checks.append(("selftest button E2E", True, "handshake text appeared"))
            page.wait_for_timeout(600)
            page.screenshot(
                path=str(EVIDENCE_DIR / "integrations-page.png"), full_page=True
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

    print("\n=== P8E INTEGRATIONS VERIFY RESULTS ===", flush=True)
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
