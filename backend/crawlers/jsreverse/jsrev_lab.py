# -*- coding: utf-8 -*-
"""JS 逆向实战实验室：签名仿真站 + 逆向客户端

组成：
- ``SIGN_JS``：带混淆元素的签名 JS（FNV-1a 哈希 + 全局 key 变量 + 时间戳构建）
- ``expected_sign``：服务端参照实现（验签用）
- ``LabHandler`` / ``start_lab_server``：仿真站（``/sign.js`` 与 ``/api/data``，含 **ts 窗口防重放**）
- ``reversed_signed_fetch``：**逆向客户端**——引擎链自动还原签名并发起带签请求：
  fetch_js → parse_ast → 提取依赖（函数 + 全局变量）→ execjs 复现 → 请求 200

用途：ts 正确 + sign 复现正确 → 服务端 200；错签 → 403（对照组）。
"""
from __future__ import annotations

import asyncio
import hmac
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple
from urllib.parse import parse_qs, urlparse

SIGN_JS = """// sign.js —— 参数签名（lab）
var _0xn = ["l", "a", "b", "s", "e", "c", "r", "e", "t"].join("") + "2026";

function _0xa1(s) {
  var h = 0x811c9dc5;
  for (var i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16);
}

function sign(uid, ts) {
  var raw = "uid=" + uid + "&ts=" + ts + "&key=" + _0xn;
  return _0xa1(raw);
}

function buildQuery(uid) {
  var ts = Math.floor(Date.now() / 1000);
  return "uid=" + uid + "&ts=" + ts + "&sign=" + sign(uid, ts);
}
"""

TS_WINDOW_SECONDS = 300


def fnv1a_32(text: str) -> str:
    """FNV-1a 32bit（与 JS ``Math.imul`` 版等价的 Python 参照）。"""
    h = 0x811C9DC5
    for ch in text:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return format(h, "x")


def expected_sign(uid: str, ts: int) -> str:
    raw = f"uid={uid}&ts={ts}&key=labsecret2026"
    return fnv1a_32(raw)


class LabHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D102 - silence
        pass

    def _send(self, status: int, body: str, content_type: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/sign.js":
            return self._send(200, SIGN_JS, "application/javascript; charset=utf-8")
        if parsed.path == "/":
            html = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<title>Sign Lab</title></head><body>"
                "<h1>JS 逆向实验室</h1>"
                "<script src='/sign.js'></script>"
                "<p>受保护接口：<code>/api/data?uid=&ts=&sign=</code></p>"
                "</body></html>"
            )
            return self._send(200, html, "text/html; charset=utf-8")
        if parsed.path == "/api/data":
            query = parse_qs(parsed.query)
            uid = (query.get("uid") or [""])[0]
            ts_raw = (query.get("ts") or [""])[0]
            signature = (query.get("sign") or [""])[0]
            try:
                ts = int(ts_raw)
            except ValueError:
                return self._send(403, json.dumps({"error": "bad ts"}), "application/json")
            if abs(int(time.time()) - ts) > TS_WINDOW_SECONDS:
                return self._send(403, json.dumps({"error": "ts expired"}), "application/json")
            if not hmac.compare_digest(signature, expected_sign(uid, ts)):
                return self._send(403, json.dumps({"error": "bad sign"}), "application/json")
            return self._send(
                200,
                json.dumps({"ok": True, "uid": uid, "items": [1, 2, 3]}),
                "application/json",
            )
        return self._send(404, "not found", "text/plain")


def start_lab_server(
    host: str = "127.0.0.1", port: int = 0
) -> Tuple[ThreadingHTTPServer, str]:
    """启动仿真站（daemon 线程），返回 (server, base_url)。port=0 自动分配。"""
    server = ThreadingHTTPServer((host, port), LabHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://{host}:{server.server_address[1]}"
    return server, base


async def reversed_signed_fetch(base_url: str, uid: str) -> Dict[str, Any]:
    """逆向客户端：引擎链还原签名 → 带签请求（返回结果与还原细节）。"""
    import httpx

    from .js_reverse_engine import JSReverseEngine

    engine = JSReverseEngine()

    # 1) 抓取签名 JS
    js = await engine.fetch_js(f"{base_url}/sign.js")
    if not js:
        return {"status": 0, "error": "fetch_js 失败"}

    # 2) AST 函数发现
    ast = engine.parse_ast(js)
    funcs = sorted(f["name"] for f in engine.find_functions(ast or {}))
    if "sign" not in funcs:
        return {"status": 0, "error": f"sign 未找到（funcs={funcs}）"}

    # 3) 依赖链提取：哈希函数 + 全局 key 变量 + 签名函数
    dep_hash = await asyncio.to_thread(engine.extract_function_code, js, "_0xa1") or ""
    dep_var = ""
    var_match = re.search(r"var\s+_0xn\s*=\s*.*?;", js)
    if var_match:
        dep_var = var_match.group(0)
    sign_code = await asyncio.to_thread(engine.extract_function_code, js, "sign") or ""
    if not (dep_hash and sign_code):
        return {"status": 0, "error": "依赖链提取失败"}

    # 4) execjs 复现签名
    combined = "\n".join([dep_var, dep_hash, sign_code])
    ts = int(time.time())
    signature = await asyncio.to_thread(engine.execute_js, combined, "sign", [uid, ts])
    if not signature:
        return {"status": 0, "error": "签名复现失败"}

    # 5) 带签请求
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{base_url}/api/data",
            params={"uid": uid, "ts": ts, "sign": signature},
        )
    body: Any
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = resp.text[:200]
    return {
        "status": resp.status_code,
        "body": body,
        "sign": signature,
        "ts": ts,
        "funcs": funcs,
        "expected": expected_sign(uid, ts),
    }
