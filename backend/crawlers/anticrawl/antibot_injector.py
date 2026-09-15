# -*- coding: utf-8 -*-
"""行为验证码页面注入器（V4 配套）：sitekey 检测 + 响应字段写入

- ``detect_sitekey``：提取 sitekey（data-sitekey 属性；Turnstile SPA 用 hook 兜底）
- ``inject_token``：把凭据写入响应字段并派发 input/change 事件
- ``install_turnstile_hook``：导航前注入 render 拦截（SPA 场景抓 sitekey）

供真实采集流程复用：探测到验证码 → 出票 → 注入 → 继续任务。
"""
from __future__ import annotations

import re
from typing import Optional

KIND_FIELDS = {
    "recaptcha_v2": [
        "#g-recaptcha-response",
        "textarea[name='g-recaptcha-response']",
    ],
    "hcaptcha": [
        "textarea[name='h-captcha-response']",
        "input[name='h-captcha-response']",
    ],
    "turnstile": [
        "input[name='cf-turnstile-response']",
        "textarea[name='cf-turnstile-response']",
    ],
}

SITEKEY_EXPR = (
    "() => { const el = document.querySelector('[data-sitekey]');"
    " return el && el.getAttribute('data-sitekey'); }"
)

TURNSTILE_HOOK = """
(() => {
  window.__sitekeys = window.__sitekeys || [];
  const t = setInterval(() => {
    if (window.turnstile && !window.__hooked) {
      window.__hooked = true;
      const orig = window.turnstile.render;
      window.turnstile.render = function (el, params) {
        try { window.__sitekeys.push(params && params.sitekey); } catch (e) {}
        return orig.apply(this, arguments);
      };
      clearInterval(t);
    }
  }, 25);
})();
"""


async def install_turnstile_hook(page) -> None:
    """在导航前注入 Turnstile render 拦截（抓 SPA 场景的 sitekey）。"""
    await page.add_init_script(TURNSTILE_HOOK)


async def detect_sitekey(page, kind: str = "recaptcha_v2") -> Optional[str]:
    """提取 sitekey：data-sitekey 属性优先；turnstile 用 hook/正则兜底。"""
    value = await page.evaluate(SITEKEY_EXPR)
    if value:
        return str(value)
    if kind == "turnstile":
        hooked = await page.evaluate("() => (window.__sitekeys || [])[0] || null")
        if hooked:
            return str(hooked)
        html = await page.content()
        found = re.findall(r'data-sitekey="([^"]+)"', html, re.IGNORECASE)
        if found:
            return found[0]
    return None


async def inject_token(page, kind: str, token: str) -> bool:
    """把凭据写入响应字段（多选择器 + 事件派发）；返回是否写入至少一处。"""
    selectors = KIND_FIELDS.get(kind)
    if not selectors:
        return False
    written = await page.evaluate(
        """([selectors, token]) => {
            let hit = 0;
            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach((el) => {
                    el.value = token;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    hit += 1;
                });
            }
            return hit;
        }""",
        [selectors, token],
    )
    return bool(written)
