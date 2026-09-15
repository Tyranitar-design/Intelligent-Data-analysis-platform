# -*- coding: utf-8 -*-
"""F7 演示资产采集 · 截图 + 演示 GIF

流程：
1. 起后端(:8000) + 前端(:5174)
2. Playwright 录屏（1280x720）：showcase 星云 -> discover -> collect -> compliance
3. 关键页截图（8 张，1280x720）
4. ffmpeg 两遍法 webm -> GIF（fps=8, 宽 880, <=5MB 预算）
5. 资产落 ``docs/assets/demo/``

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\capture_demo_assets.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ASSETS_DIR = PROJECT_ROOT / "docs" / "assets" / "demo"
VIDEO_DIR = PROJECT_ROOT / "docs" / "assets" / ".video-tmp"

API = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5174"

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows


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


def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    import glob

    for candidate in glob.glob(r"D:\ffmpeg\*\bin\ffmpeg.exe"):
        return candidate
    return None


def main() -> int:
    procs: list[subprocess.Popen] = []
    try:
        # [1] 服务
        print("[1] start services ...", flush=True)
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
        procs.append(
            subprocess.Popen(
                [node, str(vite_js), "dev", "--port", "5174", "--host", "127.0.0.1"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NEW_PROCESS_GROUP,
            )
        )
        if not (wait_http(f"{API}/health", 120) and wait_http(f"{FRONTEND}/", 60)):
            raise RuntimeError("services not ready")

        # [2] 录屏 + 截图
        print("[2] record video + screenshots ...", flush=True)
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=str(VIDEO_DIR),
                record_video_size={"width": 1280, "height": 720},
            )
            page = context.new_page()

            # -- showcase 星云（滚动） --
            page.goto(f"{FRONTEND}/showcase", wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.screenshot(path=str(ASSETS_DIR / "shot-01-showcase.png"))
            for _ in range(4):
                page.mouse.wheel(0, 520)
                page.wait_for_timeout(700)

            # -- 工作台 --
            page.goto(f"{FRONTEND}/", wait_until="networkidle")
            page.wait_for_timeout(1600)
            page.screenshot(path=str(ASSETS_DIR / "shot-02-dashboard.png"))

            # -- discover --
            page.goto(f"{FRONTEND}/discover", wait_until="networkidle")
            page.wait_for_timeout(1800)
            page.screenshot(path=str(ASSETS_DIR / "shot-03-discover.png"))
            page.mouse.wheel(0, 420)
            page.wait_for_timeout(900)

            # -- collect --
            page.goto(f"{FRONTEND}/collect", wait_until="networkidle")
            page.wait_for_timeout(1800)
            page.screenshot(path=str(ASSETS_DIR / "shot-04-collect.png"))
            page.mouse.wheel(0, 420)
            page.wait_for_timeout(900)

            # -- datasets 详情（版本历史 + 检索） --
            page.goto(f"{FRONTEND}/datasets/2", wait_until="networkidle")
            page.wait_for_timeout(1800)
            page.screenshot(path=str(ASSETS_DIR / "shot-05-dataset-detail.png"))

            # -- compliance 矩阵 --
            page.goto(f"{FRONTEND}/compliance", wait_until="networkidle")
            page.wait_for_timeout(1800)
            page.screenshot(path=str(ASSETS_DIR / "shot-06-compliance.png"))
            page.mouse.wheel(0, 400)
            page.wait_for_timeout(900)

            # -- monitor 保留卡 --
            page.goto(f"{FRONTEND}/monitor", wait_until="networkidle")
            page.wait_for_timeout(1600)
            page.screenshot(path=str(ASSETS_DIR / "shot-07-monitor.png"))

            # -- 审计 --
            page.goto(f"{FRONTEND}/audit", wait_until="networkidle")
            page.wait_for_timeout(1600)
            page.screenshot(path=str(ASSETS_DIR / "shot-08-audit.png"))

            video_path = page.video.path() if page.video else None
            context.close()
            browser.close()

        print(f"[3] video: {video_path}", flush=True)

        # [3] ffmpeg -> GIF
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            print("[warn] ffmpeg not found; skip GIF", flush=True)
            return 0
        print("[4] convert to GIF ...", flush=True)
        palette = VIDEO_DIR / "palette.png"
        gif_path = ASSETS_DIR / "demo.gif"
        # 预算控制：截 22s 精华 + fps 6 + 宽 760（<=5MB，验收 5.1-5）
        vf_common = "fps=6,scale=760:-1:flags=lanczos"
        trim = ["-ss", "2", "-t", "22"]
        subprocess.run(
            [ffmpeg, "-y", *trim, "-i", str(video_path), "-vf", f"{vf_common},palettegen", str(palette)],
            capture_output=True, check=True,
        )
        subprocess.run(
            [
                ffmpeg, "-y", *trim, "-i", str(video_path), "-i", str(palette),
                "-lavfi", f"{vf_common}[x];[x][1:v]paletteuse", "-loop", "0", str(gif_path),
            ],
            capture_output=True, check=True,
        )
        size_mb = gif_path.stat().st_size / 1024 / 1024
        print(f"[ok] GIF: {gif_path} ({size_mb:.2f} MB)", flush=True)
        if size_mb <= 5:
            shutil.rmtree(VIDEO_DIR, ignore_errors=True)
        else:
            print(
                f"[warn] GIF still {size_mb:.2f} MB > 5MB; webm kept at {VIDEO_DIR}",
                flush=True,
            )
        print("[done]", flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {type(exc).__name__}: {exc}", flush=True)
        return 1
    finally:
        print("[5] cleanup services ...", flush=True)
        for proc in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=15,
                )
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
