# -*- coding: utf-8 -*-
"""验证码自动化链 V1（图片 OCR）/ V2（滑块缺口）· 集成测试

- V1：Pillow 合成验证码图（确定性 seed）→ ddddocr 识别 == 原文本
- V2：Pillow 合成滑块图（噪声背景 + 黑色缺口矩形）→ OpenCV 检测距离 == 真值 ±2px
- 均为离线路径（无 API Key 依赖，验证本地自动化能力）

字符集避开歧义字符（0/o/1/l/i），降低 OCR 测试抖动。
"""
from __future__ import annotations

import asyncio
import io
import random

import pytest
from PIL import Image, ImageDraw, ImageFont

from crawlers.anticrawl.captcha_solver import CaptchaSolver

FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]


def _font(size: int = 30):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _make_image_captcha(text: str, seed: int = 42) -> bytes:
    rng = random.Random(seed)
    img = Image.new("RGB", (120, 44), (250, 250, 250))
    draw = ImageDraw.Draw(img)
    font = _font()
    x = 10
    for ch in text:
        draw.text((x, rng.randint(2, 8)), ch, fill=(15, 15, 15), font=font)
        x += 25
    for _ in range(50):
        draw.point((rng.randint(0, 119), rng.randint(0, 43)), fill=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_slider_gap(gap_x: int = 180, seed: int = 7) -> bytes:
    rng = random.Random(seed)
    img = Image.new("RGB", (300, 150), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    for _ in range(400):
        draw.point((rng.randint(0, 299), rng.randint(0, 149)), fill=(190, 190, 190))
    draw.rectangle([gap_x, 55, gap_x + 40, 95], fill=(8, 8, 8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# V2 · 滑块缺口检测
# --------------------------------------------------------------------------- #
def test_slider_gap_detection():
    solver = CaptchaSolver(api_key=None)
    for truth in (120, 180, 210):
        result = asyncio.run(solver.solve_slider_captcha(_make_slider_gap(truth)))
        assert result["success"] is True, result
        assert result["distance"] is not None, result
        assert abs(result["distance"] - truth) <= 2, (truth, result)


def test_slider_gap_detection_with_background_param():
    """background_data 给定时优先作为背景检测。"""
    solver = CaptchaSolver(api_key=None)
    result = asyncio.run(
        solver.solve_slider_captcha(b"not-used", background_data=_make_slider_gap(160))
    )
    assert result["success"] is True, result
    assert abs(result["distance"] - 160) <= 2, result


def test_slider_no_gap_returns_failure():
    solver = CaptchaSolver(api_key=None)
    rng = random.Random(3)
    img = Image.new("RGB", (300, 150), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    for _ in range(400):
        draw.point((rng.randint(0, 299), rng.randint(0, 149)), fill=(190, 190, 190))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = asyncio.run(solver.solve_slider_captcha(buf.getvalue()))
    assert result["success"] is False, result


# --------------------------------------------------------------------------- #
# V1 · 图片验证码 OCR
# --------------------------------------------------------------------------- #
def test_image_captcha_ocr_single():
    solver = CaptchaSolver(api_key=None)
    result = asyncio.run(solver.solve_image_captcha(_make_image_captcha("a7x2")))
    assert result["success"] is True, result
    assert result["solution"].lower() == "a7x2", result


@pytest.mark.parametrize("text", ["b3k9", "m2p8", "w5d1"])
def test_image_captcha_ocr_batch(text):
    solver = CaptchaSolver(api_key=None)
    result = asyncio.run(
        solver.solve_image_captcha(_make_image_captcha(text, seed=sum(map(ord, text)) % 900))
    )
    assert result["success"] is True, result
    assert result["solution"].lower() == text, result
