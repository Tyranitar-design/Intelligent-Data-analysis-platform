# -*- coding: utf-8 -*-
"""验证码自动处理（采集主流程接入点）

探测页面验证码 → 识别 / 出票 → 注入 / 填写 → 提交 → 断言解锁。

支持三层：
- **token 型**（reCAPTCHA v2 / hCaptcha / Turnstile）：CapSolver 出票 + antibot_injector 注入
- **图片型**：ddddocr（本地免费）→ CapSolver 兜底 + 自动填写
- **滑块型**：缺口检测 + 拟人拖拽（已就绪；页面特征检测需站点特异性配置）

用法（采集流程中）::

    result = await handle_captcha(page, solver=CaptchaSolver(), submit_selector="#go")
    if not result["success"]:
        ... 降级（记录事件 / 人机协同）
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .antibot_injector import inject_token
from .captcha_solver import CaptchaSolver

logger = logging.getLogger(__name__)

DETECT_PAGE_SCRIPT = """
() => {
    const q = (sel) => document.querySelector(sel);
    if (q('textarea[name="g-recaptcha-response"], #g-recaptcha-response')) {
        const el = q('.g-recaptcha[data-sitekey]') || q('[data-sitekey]');
        return { kind: 'recaptcha_v2', sitekey: el ? el.getAttribute('data-sitekey') : null };
    }
    if (q('textarea[name="h-captcha-response"], input[name="h-captcha-response"], .h-captcha')) {
        const el = q('.h-captcha[data-sitekey]') || q('[data-sitekey]');
        return { kind: 'hcaptcha', sitekey: el ? el.getAttribute('data-sitekey') : null };
    }
    if (q('input[name="cf-turnstile-response"], .cf-turnstile')) {
        const el = q('.cf-turnstile[data-sitekey]');
        const hooked = (window.__sitekeys || [])[0] || null;
        return { kind: 'turnstile', sitekey: el ? el.getAttribute('data-sitekey') : hooked };
    }
    const img = q(
        'img[src*="captcha"], img[id*="captcha"], img[alt*="captcha"], img[id*="verify"], img[src*="verify"]'
    );
    if (img) {
        const sel = img.id ? '#' + img.id : 'img[src*="captcha"]';
        return { kind: 'image', selector: sel };
    }
    return { kind: null };
}
"""

IMAGE_FILL_SCRIPT = """
(imgSel) => {
    const img = document.querySelector(imgSel);
    const scope = (img && (img.closest('form') || img.parentElement)) || document;
    const inp = scope.querySelector('input[type="text"], input:not([type])');
    if (!inp) return null;
    if (inp.id) return '#' + inp.id;
    if (inp.name) return `input[name="${inp.name}"]`;
    return null;
}
"""


async def detect_page_captcha(page) -> Dict[str, Any]:
    """探测页面验证码：返回 ``{kind, sitekey?, selector?}``（无 → kind=None）。"""
    try:
        return await page.evaluate(DETECT_PAGE_SCRIPT) or {"kind": None}
    except Exception as exc:  # noqa: BLE001
        logger.warning("验证码探测失败: %s", exc)
        return {"kind": None}


async def handle_captcha(
    page,
    *,
    solver: Optional[CaptchaSolver] = None,
    page_url: Optional[str] = None,
    submit_selector: Optional[str] = None,
) -> Dict[str, Any]:
    """检测并处理页面验证码。

    Returns:
        {"success": bool, "kind": str|None, "source": str|None, "error": str|None}
    """
    solver = solver or CaptchaSolver()
    detected = await detect_page_captcha(page)
    kind = detected.get("kind")
    if not kind:
        return {"success": False, "kind": None, "source": None, "error": "未检测到验证码"}

    result: Dict[str, Any] = {
        "success": False,
        "kind": kind,
        "source": None,
        "error": None,
    }

    # ---- token 型 ----
    if kind in ("recaptcha_v2", "hcaptcha", "turnstile"):
        sitekey = detected.get("sitekey")
        if not sitekey:
            result["error"] = "sitekey 缺失"
            return result
        solve = await solver.solve_antibot_token(kind, sitekey, page_url or page.url)
        result["source"] = solve.get("source")
        if not solve.get("success"):
            result["error"] = solve.get("error")
            return result
        injected = await inject_token(page, kind, solve["token"])
        result["success"] = bool(injected)
        if not injected:
            result["error"] = "注入失败（响应字段未找到）"

    # ---- 图片型 ----
    elif kind == "image":
        selector = detected.get("selector") or "img"
        image_data = await solver.get_captcha_image(page, selector)
        if not image_data:
            result["error"] = "验证码图片获取失败"
            return result
        solve = await solver.solve_image_captcha(image_data)
        result["source"] = solve.get("source")
        if not solve.get("success"):
            result["error"] = solve.get("error")
            return result
        fill_selector = await page.evaluate(IMAGE_FILL_SCRIPT, selector)
        if not fill_selector:
            result["error"] = "未找到填写框"
            return result
        await page.fill(fill_selector, solve["solution"])
        result["success"] = True

    # ---- 滑块型（能力就绪，页面特征检测需站点配置） ----
    elif kind == "slider":
        result["error"] = "slider 检测需站点特异性配置（缺口检测 + 拟人拖拽已就绪）"
    else:
        result["error"] = f"未知类型: {kind}"

    # ---- 提交 ----
    if result["success"] and submit_selector:
        try:
            await page.click(submit_selector, timeout=3000)
        except Exception as exc:  # noqa: BLE001
            logger.warning("提交点击失败: %s", exc)

    return result
