"""
前后端联通性验证
================

启动后端 -> 轮询等待就绪 -> 验证端点 -> 启动前端 -> 验证代理 -> 清理。

两个设计要点：

1. 轮询而非固定 sleep：后端冷启动需 15~25 秒（依赖多），固定等待要么浪费时间
   要么不够。轮询能在就绪的第一时间继续。
2. 必须杀进程树：npm run dev 会派生 vite，只 terminate npm 会留下孤儿 vite
   继续占端口，导致下次启动报 "Port already in use"。

用法：

    cd backend
    ./venv/Scripts/python.exe scripts/verify_stack.py
    ./venv/Scripts/python.exe scripts/verify_stack.py --backend-only

输出全用 ASCII 标记：Windows 控制台默认 GBK，勾叉类符号会触发
UnicodeEncodeError 而中断脚本。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

BACKEND_PORT = 8000
FRONTEND_PORT = 5174

BACKEND_ENDPOINTS = (
    "/health",
    "/capabilities",
    "/api/v1/data/overview",
    "/api/v1/collect/jobs",
    "/api/v1/collect/registry",
    "/api/v1/analytics/types",
    "/api/v1/discover/profiles",
    "/mcp",
)

PROXIED_ENDPOINTS = (
    "/capabilities",
    "/api/v1/data/overview",
    "/api/v1/analytics/types",
)


def wait_http(url: str, timeout: float = 70.0, interval: float = 1.5) -> bool:
    """轮询等待 URL 返回 2xx。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if 200 <= response.status < 300:
                    return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def http_status(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            return str(response.status)
    except urllib.error.HTTPError as exc:
        return str(exc.code)
    except Exception as exc:
        return "ERR:" + type(exc).__name__


def start_backend() -> subprocess.Popen:
    python = BACKEND / "venv" / "Scripts" / "python.exe"
    if not python.exists():
        python = BACKEND / "venv" / "bin" / "python"
    return subprocess.Popen(
        [str(python), "-m", "uvicorn", "api.main:app",
         "--host", "127.0.0.1", "--port", str(BACKEND_PORT), "--log-level", "warning"],
        cwd=str(BACKEND),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start_frontend() -> subprocess.Popen:
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    return subprocess.Popen(
        [npm, "run", "dev", "--", "--port", str(FRONTEND_PORT), "--strictPort", "--host", "127.0.0.1"],
        cwd=str(FRONTEND),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=(sys.platform == "win32"),
    )


def terminate(process, name: str) -> None:
    """结束进程及其子进程。"""
    if process is None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                           capture_output=True, check=False)
        else:
            process.terminate()
        process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
    print("  stopped: " + name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-only", action="store_true")
    args = parser.parse_args()

    backend = None
    frontend = None
    failures = 0

    try:
        print("[1] starting backend (:%d) ..." % BACKEND_PORT)
        backend = start_backend()
        base = "http://127.0.0.1:%d" % BACKEND_PORT

        if not wait_http(base + "/health"):
            print("  FAIL: backend not ready within timeout")
            return 1
        print("  backend ready")

        print("[2] backend endpoints")
        for path in BACKEND_ENDPOINTS:
            status = http_status(base + path)
            ok = status.startswith("2") or status in ("401", "403", "422")
            failures += 0 if ok else 1
            print("  %s %6s  %s" % ("OK  " if ok else "FAIL", status, path))

        if args.backend_only:
            return 0 if failures == 0 else 1

        print("[3] starting frontend (:%d) ..." % FRONTEND_PORT)
        frontend = start_frontend()
        fe = "http://127.0.0.1:%d" % FRONTEND_PORT

        if not wait_http(fe, timeout=90):
            print("  FAIL: frontend not ready within timeout")
            failures += 1
        else:
            print("  frontend ready")
            print("[4] frontend page and proxy")

            home = http_status(fe + "/")
            ok_home = home.startswith("2")
            failures += 0 if ok_home else 1
            print("  %s %6s  / (index page)" % ("OK  " if ok_home else "FAIL", home))

            for path in PROXIED_ENDPOINTS:
                status = http_status(fe + path)
                ok = status.startswith("2") or status in ("401", "403", "422")
                failures += 0 if ok else 1
                print("  %s %6s  %s (via proxy)" % ("OK  " if ok else "FAIL", status, path))

        if failures:
            print("RESULT: %d check(s) failed" % failures)
        else:
            print("RESULT: all checks passed")
        return 0 if failures == 0 else 1

    finally:
        print("[cleanup]")
        terminate(frontend, "frontend")
        terminate(backend, "backend")


if __name__ == "__main__":
    raise SystemExit(main())
