# -*- coding: utf-8 -*-
"""CapSolver 客户端（V3 图片识别 + V4 行为验证码 token）

支持任务类型：
- ``ImageToTextTask``：图片验证码（**可能同步返回**——createTask 响应即含 solution）
- ``ReCaptchaV2TaskProxyLess`` / ``HCaptchaTaskProxyLess`` / ``AntiTurnstileTaskProxyLess``：token 型

Key 来源：构造参数 → ``CAPSOLVER_API_KEY`` 环境变量。绝不打印、绝不落盘。
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

API_BASE = "https://api.capsolver.com"
CREATE_TASK = f"{API_BASE}/createTask"
GET_RESULT = f"{API_BASE}/getTaskResult"
GET_BALANCE = f"{API_BASE}/getBalance"


class CapSolverClient:
    """CapSolver HTTP 客户端（异步）。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        poll_interval: float = 3.0,
        max_polls: int = 40,
    ) -> None:
        self.api_key = (api_key or os.environ.get("CAPSOLVER_API_KEY") or "").strip()
        self.poll_interval = poll_interval
        self.max_polls = max_polls

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    # ------------------------------------------------------------------ #
    # 通用：提交 + 等待（处理同步返回与轮询两条路径）
    # ------------------------------------------------------------------ #
    async def _create_and_wait(self, task: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio

        import httpx

        if not self.api_key:
            return {"success": False, "error": "未配置 CAPSOLVER_API_KEY", "solution": None}
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(
                    CREATE_TASK, json={"clientKey": self.api_key, "task": task}
                )
                created = resp.json()
                if created.get("errorId"):
                    return {
                        "success": False,
                        "error": created.get("errorDescription")
                        or created.get("errorCode"),
                        "solution": None,
                    }
                # ImageToText 等轻任务可能同步直接返回
                if created.get("status") == "ready" and created.get("solution") is not None:
                    return {
                        "success": True,
                        "solution": created["solution"],
                        "synced": True,
                    }
                task_id = created.get("taskId")
                if not task_id:
                    return {"success": False, "error": "createTask 未返回 taskId", "solution": None}
                for _ in range(self.max_polls):
                    await asyncio.sleep(self.poll_interval)
                    query = await client.post(
                        GET_RESULT,
                        json={"clientKey": self.api_key, "taskId": task_id},
                    )
                    result = query.json()
                    if result.get("errorId"):
                        return {
                            "success": False,
                            "error": result.get("errorDescription") or result.get("errorCode"),
                            "solution": None,
                        }
                    if result.get("status") == "ready":
                        return {
                            "success": True,
                            "solution": result.get("solution"),
                            "synced": False,
                        }
                return {
                    "success": False,
                    "error": f"轮询超时（{self.max_polls}×{self.poll_interval}s）",
                    "solution": None,
                }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": f"{type(exc).__name__}: {exc}", "solution": None}

    # ------------------------------------------------------------------ #
    # V3 · 图片验证码
    # ------------------------------------------------------------------ #
    async def solve_image(self, image_bytes: bytes) -> Dict[str, Any]:
        import base64

        b64 = base64.b64encode(image_bytes).decode("ascii")
        result = await self._create_and_wait({"type": "ImageToTextTask", "body": b64})
        if result.get("success"):
            solution = result.get("solution") or {}
            return {
                "success": True,
                "text": solution.get("text"),
                "confidence": solution.get("confidence"),
                "source": "capsolver",
                "error": None,
            }
        return {
            "success": False,
            "text": None,
            "confidence": None,
            "source": "capsolver",
            "error": result.get("error"),
        }

    # ------------------------------------------------------------------ #
    # V4 · 行为验证码（token 型）
    # ------------------------------------------------------------------ #
    async def solve_recaptcha_v2(
        self, sitekey: str, page_url: str, invisible: bool = False
    ) -> Dict[str, Any]:
        task = {
            "type": "ReCaptchaV2TaskProxyLess",
            "websiteURL": page_url,
            "websiteKey": sitekey,
            "isInvisible": invisible,
        }
        return await self._token_task(task)

    async def solve_hcaptcha(
        self, sitekey: str, page_url: str, invisible: bool = False
    ) -> Dict[str, Any]:
        task = {
            "type": "HCaptchaTaskProxyLess",
            "websiteURL": page_url,
            "websiteKey": sitekey,
            "isInvisible": invisible,
        }
        return await self._token_task(task)

    async def solve_turnstile(
        self,
        sitekey: str,
        page_url: str,
        action: Optional[str] = None,
        cdata: Optional[str] = None,
    ) -> Dict[str, Any]:
        task = {
            "type": "AntiTurnstileTaskProxyLess",
            "websiteURL": page_url,
            "websiteKey": sitekey,
        }
        if action:
            task["action"] = action
        if cdata:
            task["cdata"] = cdata
        return await self._token_task(task)

    async def _token_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        result = await self._create_and_wait(task)
        if result.get("success"):
            solution = result.get("solution") or {}
            token = solution.get("gRecaptchaResponse") or solution.get("token")
            if token:
                return {"success": True, "token": token, "source": "capsolver", "error": None}
            return {"success": False, "token": None, "source": "capsolver", "error": "solution 无 token"}
        return {
            "success": False,
            "token": None,
            "source": "capsolver",
            "error": result.get("error"),
        }

    # ------------------------------------------------------------------ #
    # 辅助：余额
    # ------------------------------------------------------------------ #
    async def get_balance(self) -> Optional[float]:
        import httpx

        if not self.api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(GET_BALANCE, json={"clientKey": self.api_key})
                body = resp.json()
                if body.get("errorId") == 0:
                    return float(body.get("balance"))
        except Exception:  # noqa: BLE001
            return None
        return None
