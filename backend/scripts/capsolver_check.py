# -*- coding: utf-8 -*-
"""CapSolver 检查工具（余额 / 连通性 / 快速任务探活）

Key 来源（二选一，绝不打印、绝不落盘）：
    --key-file <path>   或环境变量 CAPSOLVER_API_KEY

用法（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\capsolver_check.py --key-file <path>
    .\\venv\\Scripts\\python.exe scripts\\capsolver_check.py --key-file <path> --image <captcha.png>   # ImageToText 探活
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

CREATE_TASK = "https://api.capsolver.com/createTask"
GET_RESULT = "https://api.capsolver.com/getTaskResult"
GET_BALANCE = "https://api.capsolver.com/getBalance"


def load_key(args) -> str:
    if args.key_file:
        return Path(args.key_file).read_text(encoding="utf-8").strip()
    key = (os.environ.get("CAPSOLVER_API_KEY") or "").strip()
    if not key:
        print("[error] 需要 --key-file 或环境变量 CAPSOLVER_API_KEY", file=sys.stderr)
        raise SystemExit(2)
    return key


def main() -> int:
    parser = argparse.ArgumentParser(description="CapSolver 检查")
    parser.add_argument("--key-file", default=None)
    parser.add_argument("--image", default=None, help="可选：验证码 PNG 路径（ImageToText 探活）")
    args = parser.parse_args()

    key = load_key(args)
    print(f"[key] loaded (length={len(key)}, not printed)")

    import httpx

    with httpx.Client(timeout=30) as client:
        # 1) 余额
        try:
            resp = client.post(GET_BALANCE, json={"clientKey": key})
            body = resp.json()
            print(f"[balance] http={resp.status_code} errorId={body.get('errorId')} "
                  f"balance={body.get('balance')} msg={body.get('errorDescription')}")
        except Exception as exc:  # noqa: BLE001
            print(f"[balance] FAIL {type(exc).__name__}: {exc}")

        # 2) 图片识别探活（可选）
        if args.image:
            img = Path(args.image).read_bytes()
            b64 = base64.b64encode(img).decode("ascii")
            payload = {
                "clientKey": key,
                "task": {"type": "ImageToTextTask", "module": "common", "body": b64},
            }
            submitted = client.post(CREATE_TASK, json=payload).json()
            print(f"[image-task] create errorId={submitted.get('errorId')} "
                  f"taskId={submitted.get('taskId')} msg={submitted.get('errorDescription')}")
            task_id = submitted.get("taskId")
            if task_id:
                for _ in range(12):
                    time.sleep(2)
                    r = client.post(
                        GET_RESULT, json={"clientKey": key, "taskId": task_id}
                    ).json()
                    if r.get("status") == "ready":
                        solution = r.get("solution") or {}
                        print(f"[image-task] ready text={solution.get('text')!r}")
                        break
                    if r.get("errorId"):
                        print(f"[image-task] error {r.get('errorDescription')}")
                        break
                else:
                    print("[image-task] timeout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
