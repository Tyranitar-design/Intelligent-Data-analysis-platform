# -*- coding: utf-8 -*-
"""验证码自动化链（V1 图片本地 OCR / V2 滑块缺口检测 / V3 打码平台兜底）

决策（2026-09-15 修订）：自动化优先（本地识别），打码平台兜底，人机协同最后防线。

- V1 图片验证码：ddddocr 本地识别（离线、免费）→ 失败且有 key 时 2captcha
- V2 滑块验证码：OpenCV 边缘检测定位缺口 → 返回滑动距离
- V3 打码平台：2captcha 协议（图片 base64 / 点击坐标），key 经 ``CAPTCHA_API_KEY`` 环境变量
- 页面集成：``get_captcha_image`` / ``solve_captcha_on_page``（Playwright 页面直接调用）

无 API Key 时本地路径全额可用（V1/V2）；平台路径优雅降级并返回结构化错误。
"""
import asyncio
import base64
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DDDDOCR = None  # 延迟单例：首次调用加载模型（约百毫秒级）


def _get_ddddocr():
    """ddddocr 单例（未安装时返回 None，不抛错）。"""
    global _DDDDOCR
    if _DDDDOCR is None:
        try:
            import ddddocr  # noqa: PLC0415

            _DDDDOCR = ddddocr.DdddOcr(show_ad=False)
            logger.info("ddddocr 本地识别器已加载")
        except Exception as exc:  # noqa: BLE001
            logger.warning("ddddocr 不可用: %s", exc)
            _DDDDOCR = False
    return _DDDDOCR or None


class CaptchaSolver:
    """验证码识别器（本地 OCR + OpenCV + 打码平台兜底）。

    免费优先链：ddddocr（图片）/ OpenCV（滑块）→ CapSolver → 2captcha。
    """

    def __init__(
        self,
        api_key: str = None,
        provider: str = "2captcha",
        capsolver_key: str = None,
    ):
        """
        Args:
            api_key: 2captcha 协议 Key（缺省读 ``CAPTCHA_API_KEY`` 环境变量）
            provider: 兜底打码平台（2captcha 协议）
            capsolver_key: CapSolver Key（缺省读 ``CAPSOLVER_API_KEY`` 环境变量）
        """
        self.api_key = api_key or os.environ.get("CAPTCHA_API_KEY")
        self.provider = provider
        self._capsolver_key = capsolver_key or os.environ.get("CAPSOLVER_API_KEY")
        self._capsolver = None

    def _get_capsolver(self):
        """懒加载 CapSolver 客户端（key 缺失时 available=False，调用处降级）。"""
        if self._capsolver is None:
            from .capsolver_client import CapSolverClient

            self._capsolver = CapSolverClient(api_key=self._capsolver_key)
        return self._capsolver

    # ------------------------------------------------------------------ #
    # V1 · 图片验证码
    # ------------------------------------------------------------------ #
    async def solve_image_captcha(self, image_data: bytes) -> Dict[str, Any]:
        """识别图片验证码：ddddocr 本地 → 打码平台兜底。

        Returns:
            {"success": bool, "solution": str|None, "source": str, "error": str|None}
        """
        ocr = _get_ddddocr()
        if ocr is not None:
            try:
                text = await asyncio.to_thread(ocr.classification, image_data)
                text = (text or "").strip()
                if text:
                    return {
                        "success": True,
                        "solution": text,
                        "source": "ddddocr",
                        "error": None,
                    }
                logger.info("ddddocr 返回空结果，尝试打码平台兜底")
            except Exception as exc:  # noqa: BLE001
                logger.warning("ddddocr 识别失败: %s", exc)

        # 兜底 1：CapSolver（V3；轻任务可能同步返回）
        capsolver = self._get_capsolver()
        if capsolver.available:
            result = await capsolver.solve_image(image_data)
            if result.get("success"):
                return {
                    "success": True,
                    "solution": result.get("text"),
                    "source": "capsolver",
                    "error": None,
                }
            logger.warning("CapSolver 图片识别失败: %s", result.get("error"))

        # 兜底 2：2captcha 协议
        if self.api_key:
            return await self._solve_via_2captcha(image_data)

        return {
            "success": False,
            "solution": None,
            "source": "none",
            "error": "ddddocr 不可用且未配置打码平台 Key",
        }

    # ------------------------------------------------------------------ #
    # V2 · 滑块验证码
    # ------------------------------------------------------------------ #
    async def solve_slider_captcha(
        self, image_data: bytes, background_data: bytes = None
    ) -> Dict[str, Any]:
        """滑块缺口检测：返回滑动距离（缺口左缘 x 坐标）。

        Args:
            image_data: 缺口背景图（常规单图输入）
            background_data: 可选——提供时优先作为背景图检测

        Returns:
            {"success": bool, "distance": int|None, "source": str, "error": str|None}
        """
        target = background_data or image_data
        try:
            distance = await asyncio.to_thread(self._detect_gap, target)
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "distance": None,
                "source": "opencv-canny",
                "error": f"缺口检测异常: {exc}",
            }
        if distance is None:
            return {
                "success": False,
                "distance": None,
                "source": "opencv-canny",
                "error": "未检测到缺口",
            }
        return {
            "success": True,
            "distance": distance,
            "source": "opencv-canny",
            "error": None,
        }

    @staticmethod
    def _detect_gap(image_bytes: bytes) -> Optional[int]:
        """缺口定位：暗区阈值 → 轮廓矩形（面积最大候选）；找不到时 Canny 边缘兜底。

        缺口区域在背景图中表现为明显异色块（通常暗色/阴影），阈值法比
        Canny 边缘更精确且不受边缘抖动影响；边缘法作为亮色缺口的兜底。
        """
        import cv2  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415

        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None

        def _pick(contours) -> Optional[int]:
            best: Optional[tuple[int, int]] = None  # (x, area)
            for cnt in contours:
                x, _y, w, h = cv2.boundingRect(cnt)
                if 25 <= w <= 90 and 25 <= h <= 90 and w * h >= 900:
                    if best is None or w * h > best[1]:
                        best = (x, w * h)
            return best[0] if best else None

        # 路径 1：暗色缺口（阈值分离）
        _, binary = cv2.threshold(img, 100, 255, cv2.THRESH_BINARY_INV)
        found = _pick(
            cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        )
        if found is not None:
            return found

        # 路径 2：边缘兜底（亮色缺口）
        edges = cv2.Canny(img, 80, 200)
        return _pick(
            cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0]
        )

    # ------------------------------------------------------------------ #
    # V3 · 打码平台兜底（2captcha 协议）
    # ------------------------------------------------------------------ #
    async def _solve_via_2captcha(
        self, image_data: bytes, method: str = "base64", **params: Any
    ) -> Dict[str, Any]:
        """2captcha 协议：提交任务 → 轮询取结果。"""
        import httpx  # noqa: PLC0415

        b64 = base64.b64encode(image_data).decode("ascii")
        payload = {
            "key": self.api_key,
            "method": method,
            "body": b64,
            "json": 1,
            **params,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post("https://2captcha.com/in.php", data=payload)
                submitted = resp.json()
                if submitted.get("status") != 1:
                    return {
                        "success": False,
                        "solution": None,
                        "source": "2captcha",
                        "error": f"提交失败: {submitted.get('request')}",
                    }
                task_id = submitted["request"]

                for _ in range(10):  # 10 × 3s
                    await asyncio.sleep(3)
                    query = await client.get(
                        "https://2captcha.com/res.php",
                        params={
                            "key": self.api_key,
                            "action": "get",
                            "id": task_id,
                            "json": 1,
                        },
                    )
                    result = query.json()
                    if result.get("status") == 1:
                        return {
                            "success": True,
                            "solution": result.get("request"),
                            "source": "2captcha",
                            "error": None,
                        }
                    if result.get("request") != "CAPCHA_NOT_READY":
                        return {
                            "success": False,
                            "solution": None,
                            "source": "2captcha",
                            "error": str(result.get("request")),
                        }
                return {
                    "success": False,
                    "solution": None,
                    "source": "2captcha",
                    "error": "轮询超时（30s）",
                }
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "solution": None,
                "source": "2captcha",
                "error": f"平台请求异常: {exc}",
            }

    async def solve_click_captcha(
        self, image_data: bytes, instructions: str = None
    ) -> Dict[str, Any]:
        """点击类验证码：走打码平台坐标识别（需 key；``textinstructions`` 参数）。"""
        if not self.api_key:
            return {
                "success": False,
                "points": None,
                "source": "none",
                "error": "点击验证码需要打码平台 API Key（CAPTCHA_API_KEY）",
            }
        params = {}
        if instructions:
            params["textinstructions"] = instructions
        result = await self._solve_via_2captcha(
            image_data, method="base64", **params
        )
        if result.get("success"):
            points = []
            try:
                for pair in str(result["solution"]).split(";"):
                    x_str, y_str = pair.split(",")
                    points.append((int(x_str), int(y_str)))
            except Exception:  # noqa: BLE001
                pass
            return {
                "success": bool(points),
                "points": points or None,
                "source": result.get("source"),
                "error": None if points else "平台返回坐标解析失败",
            }
        return {
            "success": False,
            "points": None,
            "source": result.get("source"),
            "error": result.get("error"),
        }

    # ------------------------------------------------------------------ #
    # V4 · 行为验证码 token（CapSolver）
    # ------------------------------------------------------------------ #
    async def solve_antibot_token(
        self, kind: str, sitekey: str, page_url: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """行为验证码出票：``kind`` ∈ recaptcha_v2 / hcaptcha / turnstile。

        出票后配合 ``antibot_injector.inject_token`` 写入页面。
        """
        capsolver = self._get_capsolver()
        if not capsolver.available:
            return {
                "success": False,
                "token": None,
                "source": "capsolver",
                "error": "未配置 CAPSOLVER_API_KEY",
            }
        if kind == "recaptcha_v2":
            return await capsolver.solve_recaptcha_v2(sitekey, page_url, **kwargs)
        if kind == "hcaptcha":
            return await capsolver.solve_hcaptcha(sitekey, page_url, **kwargs)
        if kind == "turnstile":
            return await capsolver.solve_turnstile(sitekey, page_url, **kwargs)
        return {
            "success": False,
            "token": None,
            "source": "capsolver",
            "error": f"unknown kind: {kind}",
        }

    # ------------------------------------------------------------------ #
    # 页面集成（Playwright）
    # ------------------------------------------------------------------ #
    async def get_captcha_image(self, page, selector: str = "img") -> Optional[bytes]:
        """从页面获取验证码图片（元素截图，async Playwright API）。"""
        try:
            img = await page.query_selector(selector)
            if not img:
                return None
            return await img.screenshot()
        except Exception as exc:  # noqa: BLE001
            logger.error("获取验证码图片失败: %s", exc)
            return None

    async def solve_captcha_on_page(
        self, page, captcha_type: str = "image", selector: str = "img"
    ) -> Dict[str, Any]:
        """在页面上识别验证码（图片 / 滑块 / 点击三条路径）。"""
        image_data = await self.get_captcha_image(page, selector)
        if not image_data:
            return {"success": False, "error": "无法获取验证码图片"}

        if captcha_type == "image":
            return await self.solve_image_captcha(image_data)
        if captcha_type == "slider":
            return await self.solve_slider_captcha(image_data)
        if captcha_type == "click":
            return await self.solve_click_captcha(image_data)
        return {"success": False, "error": f"不支持的验证码类型: {captcha_type}"}
