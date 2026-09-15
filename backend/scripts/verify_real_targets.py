# -*- coding: utf-8 -*-
"""真实目标站实测 · 四方向（公开合法目标 + 实时数据）

A · 公开 API 直连          Hacker News Algolia API（实时故事数据）
B · 金融数据适配器          东方财富（公开行情 K线）
C · 真实站 API 嗅探         scrapethissite AJAX 站（点击触发 XHR → 嗅探 → 直连复现）
D · 反爬挑战               nowsecure.nl（Cloudflare，StealthyFetcher 升级链）

证据：docs/evidence/real-targets/result.txt

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_real_targets.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

EVIDENCE_DIR = BACKEND_DIR.parent / "docs" / "evidence" / "real-targets"

CHECKS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    mark = "OK  " if ok else "FAIL"
    print(f"  [{mark}] {name} -- {detail}", flush=True)


# --------------------------------------------------------------------------- #
# A · 公开 API 直连（HN Algolia，实时数据）
# --------------------------------------------------------------------------- #
async def direction_a() -> None:
    import httpx

    resp = httpx.get(
        "https://hn.algolia.com/api/v1/search",
        params={"query": "python", "tags": "story", "hitsPerPage": 5},
        timeout=25,
    )
    payload = resp.json()
    hits = payload.get("hits") or []
    first_title = str((hits[0] or {}).get("title", ""))[:50] if hits else ""
    record(
        "A 公开 API 直连（HN Algolia 实时数据）",
        resp.status_code == 200 and len(hits) >= 3,
        f"status={resp.status_code} hits={len(hits)} first={first_title}",
    )


# --------------------------------------------------------------------------- #
# B · 金融数据适配器（东方财富 K线）
# --------------------------------------------------------------------------- #
async def direction_b() -> None:
    from crawlers.adapters.eastmoney import EastMoneyAdapter

    adapter = EastMoneyAdapter()
    result = await adapter.fetch_stock_kline(stock_code="600519", days=5, market="sh")
    data = getattr(result, "data", None)
    success = getattr(result, "success", None)
    if success is None:
        success = bool(data)
    record(
        "B 金融数据（东方财富 · 贵州茅台 K线）",
        bool(success) and bool(data),
        f"success={success} data={str(data)[:90]}",
    )


# --------------------------------------------------------------------------- #
# C · 真实站 API 嗅探（scrapethissite AJAX → 点击 → 嗅探 → 直连）
# --------------------------------------------------------------------------- #
async def direction_c() -> None:
    from playwright.async_api import async_playwright

    from crawlers.intelligent.api_sniffer import ApiSniffer

    url = "https://www.scrapethissite.com/pages/ajax-javascript/"
    sniffer = ApiSniffer()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        sniffer.attach(page)
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1500)
        clicked = False
        for selector in ("text=2015", "a:has-text('2015')"):
            try:
                await page.click(selector, timeout=4000)
                clicked = True
                break
            except Exception:  # noqa: BLE001
                continue
        await page.wait_for_timeout(3500)
        await sniffer.drain(timeout=2.0)
        films = await page.evaluate(
            "() => document.querySelectorAll('#films tbody tr, #films tr').length"
        )
        await browser.close()

    api_hits = [c for c in sniffer.captured if "ajax" in c["url"] or "year=" in c["url"]]
    best = sniffer.best_api()
    direct = None
    if best is not None:
        direct = await sniffer.fetch_via_api(best, page=url)

    record(
        "C 真实站 API 嗅探（scrapethissite AJAX）",
        bool(api_hits) or films > 0,
        f"clicked={clicked} captured={len(sniffer.captured)} "
        f"api_hits={len(api_hits)} films_rendered={films}",
    )
    if best is not None and direct is not None:
        record(
            "C2 直连复现（免渲染取数）",
            len(direct) > 0,
            f"best={best['url'][-60:]} rows={len(direct)}",
        )
    elif api_hits:
        record(
            "C2 直连复现（免渲染取数）",
            False,
            f"捕获 {len(api_hits)} 条 XHR 但无 JSON 直连候选（响应可能为 HTML 片段）",
        )


# --------------------------------------------------------------------------- #
# D · 反爬挑战（Cloudflare）
# --------------------------------------------------------------------------- #
async def direction_d() -> None:
    from crawlers.intelligent.adaptive_scraper import AdaptiveScraper

    scraper = AdaptiveScraper()
    result = await asyncio.wait_for(scraper.crawl("https://nowsecure.nl/"), timeout=180)
    record(
        "D 反爬挑战（CF nowsecure.nl · StealthyFetcher 链）",
        bool(result.success),
        f"strategy={result.strategy_used} quality={result.quality_score} "
        f"err={str(result.error)[:70]}",
    )


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
async def main() -> int:
    print("=== REAL TARGETS VERIFY ===", flush=True)
    for label, fn in (
        ("A", direction_a),
        ("B", direction_b),
        ("C", direction_c),
        ("D", direction_d),
    ):
        print(f"== {label} ==", flush=True)
        try:
            await fn()
        except Exception as exc:  # noqa: BLE001
            record(f"{label} 方向异常", False, f"{type(exc).__name__}: {str(exc)[:120]}")

    all_ok = all(ok for _name, ok, _detail in CHECKS)
    lines = [
        f"  [{'OK  ' if ok else 'FAIL'}] {name} -- {detail}"
        for name, ok, detail in CHECKS
    ]
    print("\n=== RESULTS ===", flush=True)
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
    raise SystemExit(asyncio.run(main()))
