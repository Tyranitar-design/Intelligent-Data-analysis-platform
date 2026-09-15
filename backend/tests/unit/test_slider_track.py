# -*- coding: utf-8 -*-
"""滑块拟人轨迹生成 · 单元测试（纯函数，不依赖浏览器）

断言：
- 净位移 == 目标距离（含过冲回退）±2
- 轨迹足够细腻（>= 15 点）
- 存在回退段（末端过冲修正）
- 非匀速（存在明显快慢变化）
- seed 确定性
"""
from __future__ import annotations

import random

from crawlers.anticrawl.slider_drag import generate_human_track


def test_track_net_displacement():
    for distance in (80, 180, 260):
        track = generate_human_track(distance, rng=random.Random(42))
        net = sum(dx for dx, _dy, _dt in track)
        assert abs(net - distance) <= 2, (distance, net)


def test_track_density():
    track = generate_human_track(180, rng=random.Random(1))
    assert len(track) >= 15, len(track)


def test_track_has_backoff():
    track = generate_human_track(180, rng=random.Random(2))
    # 末端存在回退（dx < 0）
    assert any(dx < -0.5 for dx, _dy, _dt in track), track[-3:]


def test_track_non_uniform_speed():
    track = generate_human_track(180, rng=random.Random(3))
    dxs = [dx for dx, _dy, _dt in track if dx > 0]
    assert len(dxs) >= 10
    assert (max(dxs) - min(dxs)) > 2.0, (min(dxs), max(dxs))


def test_track_seed_deterministic():
    a = generate_human_track(180, rng=random.Random(7))
    b = generate_human_track(180, rng=random.Random(7))
    assert a == b


def test_track_has_vertical_jitter():
    track = generate_human_track(180, rng=random.Random(4))
    dys = [dy for _dx, dy, _dt in track]
    assert any(abs(dy) > 0.2 for dy in dys), dys[:8]
