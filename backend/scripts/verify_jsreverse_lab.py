# -*- coding: utf-8 -*-
"""JS 逆向实战实验室 · 实机门禁（端到端 + 证据落盘）

链路：仿真站 → 抓 sign.js → AST 函数发现 → 依赖链提取（函数 + 全局变量）
      → execjs 复现签名 → 带签请求 200
对照组：错签 403 · 过期时间戳 403（防重放）

证据：docs/evidence/jsrev-lab/result.txt

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_jsreverse_lab.py
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

EVIDENCE_DIR = BACKEND_DIR.parent / "docs" / "evidence" / "jsrev-lab"

CHECKS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    mark = "OK  " if ok else "FAIL"
    print(f"  [{mark}] {name} -- {detail}", flush=True)


def main() -> int:
    import httpx

    from crawlers.jsreverse.js_reverse_engine import JSReverseEngine
    from crawlers.jsreverse.jsrev_lab import (
        SIGN_JS,
        expected_sign,
        reversed_signed_fetch,
        start_lab_server,
    )

    # 1) 静态：AST 函数发现
    engine = JSReverseEngine()
    ast = engine.parse_ast(SIGN_JS)
    funcs = sorted(f["name"] for f in engine.find_functions(ast or {}))
    record(
        "AST 函数发现（sign/_0xa1/buildQuery）",
        {"sign", "_0xa1", "buildQuery"} <= set(funcs),
        f"funcs={funcs}",
    )

    # 2) 起仿真站并跑完整逆向链
    server, base = start_lab_server()
    print(f"[lab] 仿真站已启动: {base}", flush=True)
    try:
        result = asyncio.run(reversed_signed_fetch(base, "lab-user"))
        record(
            "逆向链自动签名 → 200",
            result.get("status") == 200,
            f"status={result.get('status')} sign={str(result.get('sign'))[:12]} err={result.get('error', '')}",
        )
        record(
            "复现值 == 服务端参照实现",
            result.get("sign") == result.get("expected"),
            "",
        )
        record(
            "响应数据完整（items）",
            isinstance(result.get("body"), dict)
            and result["body"].get("items") == [1, 2, 3],
            f"body={str(result.get('body'))[:80]}",
        )

        # 对照组
        bad = httpx.get(
            f"{base}/api/data",
            params={"uid": "lab-user", "ts": int(time.time()), "sign": "deadbeef"},
            timeout=10,
        )
        record("对照组：错签 → 403", bad.status_code == 403, f"status={bad.status_code}")

        stale_ts = int(time.time()) - 3600
        expired = httpx.get(
            f"{base}/api/data",
            params={
                "uid": "lab-user",
                "ts": stale_ts,
                "sign": expected_sign("lab-user", stale_ts),
            },
            timeout=10,
        )
        record(
            "对照组：过期时间戳 → 403（防重放）",
            expired.status_code == 403,
            f"status={expired.status_code}",
        )
    finally:
        server.shutdown()

    print("\n=== JSREV LAB RESULTS ===", flush=True)
    all_ok = all(ok for _name, ok, _detail in CHECKS)
    lines = [
        f"  [{'OK  ' if ok else 'FAIL'}] {name} -- {detail}"
        for name, ok, detail in CHECKS
    ]
    for line in lines:
        print(line, flush=True)
    verdict = "all checks passed" if all_ok else "failures present"
    print(f"RESULT: {verdict}", flush=True)
    try:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / "result.txt").write_text(
            "\n".join(lines) + f"\nRESULT: {verdict}\n", encoding="utf-8"
        )
    except OSError:
        pass
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
