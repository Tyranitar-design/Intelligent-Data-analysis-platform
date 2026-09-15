# -*- coding: utf-8 -*-
"""滑块拖拽闭环 · 集成测试（Playwright + 本地合成页，端到端）

流程：本地 HTML 滑块（记录拖动最终位置）→ drag_slider 拟人轨迹拖动 → 断言最终 x ≈ 目标。
"""
from __future__ import annotations

import asyncio

from crawlers.anticrawl.slider_drag import drag_slider

SLIDER_PAGE = """<!doctype html>
<html><body style="margin:0">
<div id="track" style="position:relative;width:500px;height:60px;background:#eeeeee">
  <div id="handle" style="position:absolute;left:0;top:10px;width:40px;height:40px;background:#3388aa;cursor:pointer"></div>
</div>
<script>
let cur = 0, dragging = false, startX = 0;
const handle = document.getElementById('handle');
window.finalX = null;
handle.addEventListener('mousedown', (e) => { dragging = true; startX = e.clientX; });
document.addEventListener('mousemove', (e) => {
  if (!dragging) return;
  cur = Math.max(0, e.clientX - startX);
  handle.style.left = cur + 'px';
});
document.addEventListener('mouseup', () => {
  if (!dragging) return;
  dragging = false;
  window.finalX = cur;
});
</script>
</body></html>
"""


def test_drag_slider_end_to_end(tmp_path):
    html_file = tmp_path / "slider.html"
    html_file.write_text(SLIDER_PAGE, encoding="utf-8")

    async def body():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 800, "height": 300})
            await page.goto(html_file.as_uri())
            result = await drag_slider(page, "#handle", 180)
            final_x = await page.evaluate("window.finalX")
            await browser.close()
            return result, final_x

    result, final_x = asyncio.run(body())
    assert result["success"] is True, result
    assert final_x is not None, "拖拽事件未触发"
    assert abs(final_x - 180) <= 3, (final_x, result)
