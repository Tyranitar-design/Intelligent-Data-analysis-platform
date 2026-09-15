# -*- coding: utf-8 -*-
"""API 嗅探器 · 集成测试（本地 SPA 仿真站）

场景：页面 JS 通过 fetch('/api/items?page=1') 拉 JSON 渲染列表。
验证：
1. Playwright 网络嗅探捕获 XHR/JSON 接口（url/method/status/item_count）
2. best_api() 选出数据接口
3. fetch_via_api() 直连取数 == 页面渲染数据（API 直连免渲染）
"""
from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from crawlers.intelligent.api_sniffer import ApiSniffer

ITEMS = [{"id": i, "name": f"item-{i}"} for i in range(1, 6)]

SPA_HTML = """<!doctype html>
<html><body>
<h1>SPA Lab</h1>
<ul id="list"></ul>
<script>
fetch('/api/items?page=1')
  .then((r) => r.json())
  .then((data) => {
    document.getElementById('list').innerHTML =
      data.items.map((it) => '<li>' + it.name + '</li>').join('');
    document.title = 'SPA-Loaded-' + data.items.length;
  });
</script>
</body></html>"""


class SpaHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, body, content_type):
        payload = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802
        if self.path == "/":
            return self._send(200, SPA_HTML, "text/html; charset=utf-8")
        if self.path.startswith("/api/items"):
            return self._send(
                200, json.dumps({"items": ITEMS, "total": len(ITEMS)}), "application/json"
            )
        return self._send(404, "not found", "text/plain")


def _start_spa() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), SpaHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_sniff_and_direct_fetch():
    server, base = _start_spa()

    async def body():
        from playwright.async_api import async_playwright

        sniffer = ApiSniffer()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            sniffer.attach(page)
            await page.goto(base + "/", wait_until="networkidle")
            # 等 JS 渲染完成
            await page.wait_for_function("document.title.startsWith('SPA-Loaded')", timeout=10000)
            await sniffer.drain(timeout=1.5)
            rendered = await page.evaluate(
                "() => Array.from(document.querySelectorAll('#list li')).map(li => li.textContent)"
            )
            await browser.close()

        best = sniffer.best_api()
        direct = await sniffer.fetch_via_api(best, page=base)
        return sniffer.captured, best, direct, rendered

    captured, best, direct, rendered = asyncio.run(body())
    server.shutdown()

    # 1) 捕获到 JSON 接口
    api_hits = [c for c in captured if "/api/items" in c["url"]]
    assert api_hits, f"未捕获 /api/items：{captured}"
    assert api_hits[0]["method"] == "GET"
    assert api_hits[0]["status"] == 200

    # 2) best_api 选出该接口
    assert best is not None
    assert "/api/items" in best["url"]

    # 3) 直连取数 == 渲染数据
    assert direct is not None
    assert [it["name"] for it in direct] == rendered == [f"item-{i}" for i in range(1, 6)]
