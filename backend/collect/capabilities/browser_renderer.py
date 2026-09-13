"""
能力 · 浏览器渲染（L2）
=======================

仅用于**公开页面**的渲染：页面本身可访问，只是内容由 JS 在客户端填充。

不承担任何对抗性职责——不处理验证码、不绕付费墙、不伪造指纹。
浏览器运行时缺失时优雅降级（返回 DEGRADE），让调度器回退到其他能力。

资源约束：Lite 形态下 Chromium 按需启动、用后释放，避免常驻占用。
"""
from __future__ import annotations

import logging
from typing import Optional

from collect.ratelimit import AdaptiveRateLimiter
from collect.registry import (
    Capability,
    CapabilityLayer,
    CollectRequest,
    CollectResult,
    CostEstimate,
    ExecContext,
)

logger = logging.getLogger(__name__)

HARD_BLOCK_PROTECTIONS = frozenset({"captcha", "cloudflare", "paywall", "forbidden"})

# 渲染等待策略：等网络空闲，但设上限避免长尾页面拖垮任务
DEFAULT_RENDER_TIMEOUT_MS = 20000
MAX_TEXT_CHARS = 20000


def playwright_available() -> tuple[bool, str]:
    """检查渲染运行时是否可用。"""
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False, "playwright 未安装"
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError as exc:
        return False, f"playwright.async_api 不可用: {exc}"
    return True, "ok"


class BrowserRenderer(Capability):
    """公开页面渲染。"""

    name = "browser_renderer"
    layer = CapabilityLayer.L2
    priority = 5

    def __init__(self, timeout_ms: int = DEFAULT_RENDER_TIMEOUT_MS) -> None:
        self.timeout_ms = timeout_ms

    def score(self, profile: dict, request: CollectRequest) -> float:
        access = self._access(profile)
        if access.get("protection") in HARD_BLOCK_PROTECTIONS:
            return 0.0

        structure = self._structure(profile)
        # 只在页面确实像 JS 空壳时才推荐渲染
        if structure.get("needs_render"):
            return 0.8
        return 0.15

    def cost_estimate(self, request: CollectRequest) -> CostEstimate:
        pages = min(request.max_items, 10)
        # 浏览器实例是最重的资源，成本显著高于纯 HTTP
        return CostEstimate(
            requests=pages, seconds=pages * 3.0, memory_mb=320
        )

    async def execute(
        self, profile: dict, request: CollectRequest, ctx: ExecContext
    ) -> CollectResult:
        available, reason = playwright_available()
        if not available:
            # 优雅降级：让调度器回退到 L1 能力
            return CollectResult.degrade(f"渲染运行时不可用（{reason}）")

        fetcher = getattr(ctx, "fetcher", None)
        url = request.target_url or profile.get("sample_url")
        if not url:
            return CollectResult.degrade("未提供目标 URL")

        # robots 检查在进入浏览器前完成，避免渲染被排除的路径
        if fetcher is not None and getattr(fetcher, "robots_check", None):
            if not fetcher.robots_check(url):
                return CollectResult.failed("robots 排除该路径，不进入渲染")

        html, error = await self._render(url)
        if html is None:
            return CollectResult.degrade(f"渲染失败：{error}")

        from discover.fields import extract_fields_from_page

        specs = extract_fields_from_page(html, url)
        wanted = {f.get("name") for f in request.fields} if request.fields else None
        payload = {
            s.name: (s.sample[:MAX_TEXT_CHARS] if isinstance(s.sample, str) else s.sample)
            for s in specs
            if not wanted or s.name in wanted
        }
        if not payload:
            return CollectResult.degrade("渲染后仍未提取到字段")

        completeness = round(
            len(payload) / max(1, len(wanted) if wanted else len(specs)), 4
        )
        return CollectResult.ok(
            [
                {
                    "payload": payload,
                    "text": payload.get("content", "") or "",
                    "source_url": url,
                    "_completeness": completeness,
                }
            ],
            cost=self.cost_estimate(request),
            meta={"capability": self.name, "rendered": True},
        )

    # ------------------------------------------------------------------ #

    async def _render(self, url: str) -> tuple[Optional[str], str]:
        """在浏览器中加载页面并取回渲染后的 HTML。

        浏览器按需启动、用完即关，不保持常驻实例。
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - 已在上层检查
            return None, str(exc)

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True, args=["--disable-dev-shm-usage"]
                )
                try:
                    context = await browser.new_context(
                        user_agent=(
                            "WebInsightAgent/3.0 (+data-collection; "
                            "contact: platform-operator)"
                        )
                    )
                    page = await context.new_page()
                    await page.goto(
                        url, wait_until="domcontentloaded", timeout=self.timeout_ms
                    )
                    html = await page.content()
                    await context.close()
                    return html, "ok"
                finally:
                    await browser.close()
        except Exception as exc:  # noqa: BLE001 - 渲染失败要降级而非中断任务
            return None, f"{type(exc).__name__}: {str(exc)[:160]}"

    @staticmethod
    def _access(profile: dict) -> dict:
        return profile.get("access") or {}

    @staticmethod
    def _structure(profile: dict) -> dict:
        return profile.get("structure") or {}
