# -*- coding: utf-8 -*-
"""登录表单自动探测：无选择器配置时的通用定位。

策略：
- password 输入框（必有，排除 hidden）
- username：密码框所在 form 内、DOM 顺序在密码框**之前**的最后一个 text/email/tel 输入
- submit：form 内 ``button[type=submit]`` / ``input[type=submit]``，
  或文本含 login/sign in/登录 的按钮

返回可用的 CSS 选择器（优先 ``#id``，其次 ``[name=...]``）。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DETECT_SCRIPT = r"""
() => {
    const pw = document.querySelector('input[type="password"]');
    if (!pw) return null;
    const form = pw.closest('form') || document;

    const candidates = Array.from(
        form.querySelectorAll(
            'input[type="text"], input[type="email"], input[type="tel"], input:not([type])'
        )
    ).filter((el) => el.type !== 'hidden');

    let username = null;
    for (const el of candidates) {
        // pw 在 el 之后 => el 位于密码框之前（用户名框的典型位置）
        if (el.compareDocumentPosition(pw) & Node.DOCUMENT_POSITION_FOLLOWING) {
            username = el;
        }
    }
    if (!username && candidates.length) username = candidates[0];

    let submit = form.querySelector('button[type="submit"], input[type="submit"]');
    if (!submit) {
        submit = Array.from(form.querySelectorAll('button')).find((b) =>
            /log\s?in|sign\s?in|submit|登录/.test((b.textContent || '').toLowerCase())
        ) || null;
    }

    function sel(el) {
        if (!el) return null;
        if (el.id) return '#' + (window.CSS && CSS.escape ? CSS.escape(el.id) : el.id);
        if (el.name) return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
        return `${el.tagName.toLowerCase()}[type='${el.getAttribute('type') || 'text'}']`;
    }

    return {
        username: sel(username),
        password: sel(pw),
        submit: sel(submit),
    };
}
"""


async def detect_login_form(page) -> Optional[Dict[str, Any]]:
    """探测登录表单，返回 ``{"username","password","submit"}``（缺 password 时返回 None）。"""
    try:
        result = await page.evaluate(DETECT_SCRIPT)
    except Exception as exc:  # noqa: BLE001
        logger.warning("表单探测失败: %s", exc)
        return None
    if not result or not result.get("password"):
        return None
    return result
