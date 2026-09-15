# -*- coding: utf-8 -*-
"""滑块拟人拖拽（V2b：缺口检测 → 拖拽闭环）

- ``generate_human_track``：拟人轨迹（加速-减速 + 垂直抖动 + 末端过冲回退），纯函数可单测
- ``drag_slider``：Playwright 页面拖拽（按下 → 逐点移动 → 松开）
"""
from __future__ import annotations

import logging
import random
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

TrackPoint = Tuple[float, float, int]  # (dx, dy, dt_ms)


def generate_human_track(
    distance: int, rng: Optional[random.Random] = None
) -> List[TrackPoint]:
    """生成拟人滑动轨迹。

    结构：加速-减速主段（两端慢中间快，抛物线速度分布）+ 垂直抖动
    + 末端过冲回退；净位移 ≈ distance（轻微欠冲由回退段决定）。
    """
    r = rng or random.Random()
    overshoot = r.uniform(3.0, 8.0)
    total = distance + overshoot
    n = r.randint(18, 26)

    # 主段速度形状：6t(1-t) 抛物线（中段快、两端慢）
    weights: List[float] = []
    for i in range(n):
        t = i / (n - 1)
        weights.append(6 * t * (1 - t) + 0.4)
    w_sum = sum(weights)

    track: List[TrackPoint] = []
    for w in weights:
        dx = w / w_sum * total
        dy = r.uniform(-1.2, 1.2)
        dt = r.randint(12, 32)
        track.append((dx, dy, dt))

    # 过冲回退（含轻微回抖）
    track.append(
        (-overshoot - r.uniform(0.0, 1.5), r.uniform(-0.8, 0.8), r.randint(30, 60))
    )
    return track


async def drag_slider(
    page,
    selector: str,
    distance: int,
    rng: Optional[random.Random] = None,
) -> dict:
    """在 Playwright 页面上按拟人轨迹拖动滑块。

    Args:
        page: Playwright Page（async API）
        selector: 滑块手柄选择器
        distance: 目标滑动距离（px，来自缺口检测）
        rng: 可注入随机源（测试确定性）

    Returns:
        {"success": bool, "distance": int|None, "points": int, "error": str|None}
    """
    try:
        handle = page.locator(selector).first
        box = await handle.bounding_box()
        if not box:
            return {
                "success": False,
                "distance": None,
                "points": 0,
                "error": "滑块元素不可见",
            }

        start_x = box["x"] + box["width"] / 2
        start_y = box["y"] + box["height"] / 2
        track = generate_human_track(distance, rng)

        await page.mouse.move(start_x, start_y)
        await page.mouse.down()
        pause = rng.randint(80, 160) if rng else 120
        await page.wait_for_timeout(pause)

        cur_x, cur_y = start_x, start_y
        for dx, dy, dt in track:
            cur_x += dx
            cur_y += dy
            await page.mouse.move(cur_x, cur_y)
            await page.wait_for_timeout(dt)

        await page.wait_for_timeout(60)
        await page.mouse.up()
        return {
            "success": True,
            "distance": distance,
            "points": len(track),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("滑块拖拽失败: %s", exc)
        return {
            "success": False,
            "distance": None,
            "points": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }
