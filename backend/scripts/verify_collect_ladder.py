# -*- coding: utf-8 -*-
"""采集能力阶梯验证（部署前，从简单到复杂）

L0 静态直采 / L1 指纹伪装 / L2 JS 渲染 / L3 反爬挑战 / L4 分页链路 / L6 逆向协同
（L5 登录态由 Smoke assisted 覆盖——见 docs/evidence/smoke-*，本脚本不重复。）

判定：PASS / DEGRADED（可达但降级）/ FAIL（进修复队列）
证据：docs/evidence/collect-ladder/{result.txt,ladder.json}

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_collect_ladder.py               # 默认 L0,L1,L2,L4,L6
    .\\venv\\Scripts\\python.exe scripts\\verify_collect_ladder.py -Layer L3     # 单独跑反爬挑战层
    .\\venv\\Scripts\\python.exe scripts\\verify_collect_ladder.py -Layer L0,L1  # 快速冒烟
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

EVIDENCE_DIR = BACKEND_DIR.parent / "docs" / "evidence" / "collect-ladder"

CHECKS: list[dict] = []


def record(layer: str, name: str, status: str, detail: str = "") -> None:
    CHECKS.append({"layer": layer, "name": name, "status": status, "detail": detail})
    print(f"  [{status:8s}] {layer} {name} -- {detail}", flush=True)


def _blob_of(result) -> str:
    """汇总 crawl 结果的可搜索文本（data + content）。"""
    parts = []
    if getattr(result, "content", None):
        parts.append(str(result.content))
    if getattr(result, "data", None):
        try:
            parts.append(json.dumps(result.data, ensure_ascii=False, default=str))
        except Exception:
            parts.append(str(result.data))
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# L0 · 静态直采
# --------------------------------------------------------------------------- #
async def run_l0() -> None:
    from crawlers.intelligent.adaptive_scraper import AdaptiveScraper

    scraper = AdaptiveScraper()
    cases = [
        ("https://books.toscrape.com/", "Light in the Attic"),
        ("https://example.com/", "Example Domain"),
    ]
    for url, probe_text in cases:
        t0 = time.time()
        try:
            r = await asyncio.wait_for(scraper.crawl(url), timeout=120)
            blob = _blob_of(r)
            ok = bool(r.success) and probe_text in blob
            record(
                "L0",
                f"crawl {url.split('//')[1].split('/')[0]}",
                "PASS" if ok else "FAIL",
                f"success={r.success} strategy={r.strategy_used} "
                f"probe_text={'Y' if probe_text in blob else 'N'} "
                f"{len(blob)}B {time.time() - t0:.1f}s",
            )
        except Exception as exc:  # noqa: BLE001
            record("L0", f"crawl {url}", "FAIL", f"{type(exc).__name__}: {str(exc)[:140]}")


# --------------------------------------------------------------------------- #
# L1 · 指纹伪装（UA 回显 + TLS 指纹对比）
# --------------------------------------------------------------------------- #
async def run_l1() -> None:
    import httpx

    from crawlers.anticrawl.fingerprint import FingerprintMasker

    fp = FingerprintMasker().generate_fingerprint()
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        # ① UA 伪装回显
        try:
            h = (await client.get("https://httpbin.org/headers", headers={"User-Agent": fp["user_agent"]})).json()
            ua = (h.get("headers") or {}).get("User-Agent", "")
            record(
                "L1",
                "UA 伪装回显（httpbin）",
                "PASS" if "Mozilla" in ua else "FAIL",
                f"UA={ua[:70]}",
            )
        except Exception as exc:  # noqa: BLE001
            record("L1", "UA 伪装回显（httpbin）", "FAIL", f"{type(exc).__name__}: {str(exc)[:120]}")

        # ② 裸 httpx TLS 指纹（基线）
        bare_ja3 = ""
        try:
            bare = (await client.get("https://tls.browserleaks.com/json")).json()
            bare_ja3 = str(bare.get("ja3_hash") or "")
            record(
                "L1",
                "裸 httpx TLS 基线",
                "PASS" if bare_ja3 else "FAIL",
                f"ja3={bare_ja3[:16]} user_agent={str(bare.get('user_agent'))[:40]}",
            )
        except Exception as exc:  # noqa: BLE001
            record("L1", "裸 httpx TLS 基线", "FAIL", f"{type(exc).__name__}: {str(exc)[:120]}")

    # ③ Scrapling Fetcher 的 TLS 指纹（平台能力）
    try:
        try:
            from scrapling.fetchers import Fetcher  # scrapling >= 0.3
        except Exception:
            from scrapling import Fetcher  # 旧版兜底
        resp = Fetcher.get("https://tls.browserleaks.com/json", stealthy_headers=True)
        text = getattr(resp, "text", None) or ""
        if not text:
            body = getattr(resp, "body", None)
            if isinstance(body, bytes):
                text = body.decode("utf-8", errors="ignore")
        sc = json.loads(text)
        sc_ja3 = str(sc.get("ja3_hash") or "")
        same = bool(bare_ja3) and sc_ja3 == bare_ja3
        record(
            "L1",
            "Scrapling TLS 指纹",
            "DEGRADED" if same else ("PASS" if sc_ja3 else "FAIL"),
            f"ja3={sc_ja3[:16]} 与裸 httpx {'相同（同为 httpx 栈）' if same else '不同'}",
        )
    except Exception as exc:  # noqa: BLE001
        record("L1", "Scrapling TLS 指纹", "FAIL", f"{type(exc).__name__}: {str(exc)[:140]}")


# --------------------------------------------------------------------------- #
# L2 · JS 渲染
# --------------------------------------------------------------------------- #
async def run_l2() -> None:
    from crawlers.intelligent.adaptive_scraper import AdaptiveScraper

    scraper = AdaptiveScraper()
    try:
        r = await asyncio.wait_for(scraper.crawl("https://quotes.toscrape.com/js/"), timeout=180)
        blob = _blob_of(r)
        has_quote = "Einstein" in blob
        ok = bool(r.success) and has_quote
        record(
            "L2",
            "JS 渲染站 quotes/js",
            "PASS" if ok else "FAIL",
            f"success={r.success} strategy={r.strategy_used} "
            f"quality={r.quality_score} einstein={'Y' if has_quote else 'N'}",
        )
    except Exception as exc:  # noqa: BLE001
        record("L2", "JS 渲染站 quotes/js", "FAIL", f"{type(exc).__name__}: {str(exc)[:140]}")


# --------------------------------------------------------------------------- #
# L3 · 反爬挑战（Cloudflare 经典测试靶）
# --------------------------------------------------------------------------- #
async def run_l3() -> None:
    from crawlers.intelligent.adaptive_scraper import AdaptiveScraper

    scraper = AdaptiveScraper()
    try:
        r = await asyncio.wait_for(scraper.crawl("https://nowsecure.nl/"), timeout=240)
        ok = bool(r.success)
        record(
            "L3",
            "CF 挑战 nowsecure.nl",
            "PASS" if ok else "DEGRADED",
            f"success={r.success} strategy={r.strategy_used} "
            f"quality={r.quality_score} err={str(r.error)[:90]}",
        )
    except asyncio.TimeoutError:
        record("L3", "CF 挑战 nowsecure.nl", "FAIL", "timeout 240s")
    except Exception as exc:  # noqa: BLE001
        record("L3", "CF 挑战 nowsecure.nl", "FAIL", f"{type(exc).__name__}: {str(exc)[:140]}")


# --------------------------------------------------------------------------- #
# L4 · 分页链路
# --------------------------------------------------------------------------- #
async def run_l4() -> None:
    from crawlers.intelligent.adaptive_scraper import AdaptiveScraper

    scraper = AdaptiveScraper()
    total = 0
    for page in (1, 2, 3):
        url = f"https://quotes.toscrape.com/page/{page}/"
        try:
            r = await asyncio.wait_for(scraper.crawl(url), timeout=120)
            blob = _blob_of(r)
            n = blob.count('class="quote"')
            total += n
            record(
                "L4",
                f"page/{page} 引文计数",
                "PASS" if r.success and n >= 10 else "FAIL",
                f"quotes={n} strategy={r.strategy_used}",
            )
        except Exception as exc:  # noqa: BLE001
            record("L4", f"page/{page} 引文计数", "FAIL", f"{type(exc).__name__}: {str(exc)[:120]}")
    record("L4", "三页合计", "PASS" if total == 30 else "FAIL", f"total={total}（期望 30）")


# --------------------------------------------------------------------------- #
# L6 · 逆向协同（合成签名 fixture）
# --------------------------------------------------------------------------- #
FIXTURE_JS = """
var SIGN_KEY = "wb_secret_2024";

function sign(params) {
  var ts = params.ts || Date.now();
  var nonce = Math.random().toString(36).slice(2, 8);
  return SIGN_KEY + "_" + params.id + "_" + ts + "_" + nonce;
}

function buildQuery(params) {
  var parts = [];
  for (var k in params) { parts.push(k + "=" + params[k]); }
  return parts.join("&") + "&sign=" + sign(params);
}
"""


async def run_l6() -> None:
    from crawlers.jsreverse.js_reverse_engine import JSReverseEngine

    engine = JSReverseEngine()

    ast = engine.parse_ast(FIXTURE_JS)
    funcs = engine.find_functions(ast or {})
    names = sorted(f["name"] for f in funcs)
    record(
        "L6",
        "AST 函数发现",
        "PASS" if {"sign", "buildQuery"} <= set(names) else "FAIL",
        f"funcs={names}",
    )

    code = engine.extract_function_code(FIXTURE_JS, "sign") or ""
    record(
        "L6",
        "sign 函数提取",
        "PASS" if "SIGN_KEY" in code else "FAIL",
        f"{len(code)}B",
    )

    val = engine.execute_js(FIXTURE_JS, "sign", [{"id": 42, "ts": 1700000000}])
    expected_prefix = "wb_secret_2024_42_1700000000_"
    record(
        "L6",
        "execjs 求值（签名复现）",
        "PASS" if isinstance(val, str) and val.startswith(expected_prefix) else "FAIL",
        f"value={str(val)[:60]}",
    )

    analysis = engine.analyze_request_params(FIXTURE_JS)
    ok = bool(
        analysis["timestamp_usage"]
        and analysis["nonce_usage"]
        and analysis["signature_functions"]
    )
    record(
        "L6",
        "参数分析（时间戳/nonce/签名）",
        "PASS" if ok else "FAIL",
        f"ts={len(analysis['timestamp_usage'])} "
        f"nonce={len(analysis['nonce_usage'])} "
        f"sig={len(analysis['signature_functions'])}",
    )


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
LAYER_FUNCS = {
    "L0": run_l0,
    "L1": run_l1,
    "L2": run_l2,
    "L3": run_l3,
    "L4": run_l4,
    "L6": run_l6,
}


async def main() -> int:
    parser = argparse.ArgumentParser(description="采集能力阶梯验证")
    parser.add_argument("-Layer", default="L0,L1,L2,L4,L6", help="逗号分隔层列表")
    args = parser.parse_args()
    layers = [x.strip().upper() for x in args.Layer.split(",") if x.strip()]

    for layer in layers:
        fn = LAYER_FUNCS.get(layer)
        if fn is None:
            record(layer, "unknown layer", "FAIL", "支持的层：L0/L1/L2/L3/L4/L6")
            continue
        print(f"== {layer} ==", flush=True)
        t0 = time.time()
        try:
            await fn()
        except Exception as exc:  # noqa: BLE001
            record(layer, "exception", "FAIL", f"{type(exc).__name__}: {str(exc)[:180]}")
        print(f"   ({layer} done in {time.time() - t0:.1f}s)", flush=True)

    print("\n=== COLLECT LADDER RESULTS ===", flush=True)
    counts = {"PASS": 0, "DEGRADED": 0, "FAIL": 0}
    lines = []
    for c in CHECKS:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
        line = f"  [{c['status']:8s}] {c['layer']} {c['name']} -- {c['detail']}"
        lines.append(line)
        print(line, flush=True)
    verdict = (
        "all checks passed"
        if counts["FAIL"] == 0 and counts["DEGRADED"] == 0
        else ("degraded present" if counts["FAIL"] == 0 else "failures present")
    )
    summary = (
        f"PASS={counts['PASS']} DEGRADED={counts['DEGRADED']} FAIL={counts['FAIL']}"
    )
    print(f"RESULT: {verdict} ({summary})", flush=True)

    try:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / "result.txt").write_text(
            "\n".join(lines) + f"\nRESULT: {verdict} ({summary})\n", encoding="utf-8"
        )
        (EVIDENCE_DIR / "ladder.json").write_text(
            json.dumps(CHECKS, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass
    return 0 if counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
