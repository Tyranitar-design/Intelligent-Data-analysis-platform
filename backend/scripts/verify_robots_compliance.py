# -*- coding: utf-8 -*-
"""robots.txt 合规探测 · 京东 / 淘宝 / B站（只碰明确合规的目标）

纪律：
- 先用平台 ``RobotsChecker`` 做判定；
- **只对判定 allowed=True 的目标发请求**（HEAD 最小验证）；
- 判定不可采的目标**零请求**（本脚本统计验证该纪律）；
- 判定结果如实记录（不可采 = 正确的合规守门结果）。

证据：docs/evidence/robots-compliance/result.txt

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_robots_compliance.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

EVIDENCE_DIR = BACKEND_DIR.parent / "docs" / "evidence" / "robots-compliance"

CHECKS: list[tuple[str, bool, str]] = []
JUDGMENTS: list[dict] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    mark = "OK  " if ok else "FAIL"
    print(f"  [{mark}] {name} -- {detail}", flush=True)


TARGETS = [
    ("对照·练习站", "https://quotes.toscrape.com/"),
    ("B站·视频页", "https://www.bilibili.com/video/BV1GJ411x7h7"),
    ("京东·首页", "https://www.jd.com/"),
    ("京东·商品页", "https://item.jd.com/100012043978.html"),
    ("淘宝·首页", "https://www.taobao.com/"),
    ("淘宝·商品页", "https://item.taobao.com/item.htm?id=100000"),
]


async def main() -> int:
    import httpx

    from crawlers.robots_checker import RobotsChecker

    checker = RobotsChecker()
    probed = 0
    skipped = 0

    for label, url in TARGETS:
        try:
            report = await checker.check(url)
        except Exception as exc:  # noqa: BLE001
            record(label, False, f"robots 判定异常: {type(exc).__name__}: {str(exc)[:90]}")
            continue

        allowed = bool(report.allowed)
        rule = report.rule
        rule_desc = f"{'Allow' if rule and rule.allow else 'Disallow'} {rule.path}" if rule else "(默认)"
        probe = "skipped(不可采)"
        if allowed:
            # 最小验证：仅对允许的目标发一次 HEAD
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                    resp = await client.head(
                        url,
                        headers={"User-Agent": RobotsChecker.DEFAULT_USER_AGENT},
                    )
                probe = f"HTTP {resp.status_code}"
            except Exception as exc:  # noqa: BLE001
                probe = f"{type(exc).__name__}: {str(exc)[:50]}"
            probed += 1
        else:
            skipped += 1

        JUDGMENTS.append(
            {
                "label": label,
                "url": url,
                "allowed": allowed,
                "source": report.source,
                "rule": rule_desc,
                "crawl_delay": report.crawl_delay,
                "probe": probe,
            }
        )
        status = "允许" if allowed else "阻断"
        record(
            f"{label} → 合规判定：{status}",
            True,
            f"allowed={allowed} source={report.source} rule={rule_desc} "
            f"crawl_delay={report.crawl_delay} probe={probe}",
        )

    # 校准断言：对照组（练习站）必须允许
    control = next((j for j in JUDGMENTS if j["label"].startswith("对照")), None)
    record(
        "校准：练习站对照允许",
        bool(control and control["allowed"] is True),
        f"control={control}",
    )

    # 纪律断言：不可采目标零请求
    record(
        "纪律：不可采目标零请求",
        skipped == len([j for j in JUDGMENTS if not j["allowed"]]),
        f"probed={probed} skipped={skipped}",
    )

    print("\n=== ROBOTS COMPLIANCE RESULTS ===", flush=True)
    lines = [
        f"  [{'OK  ' if ok else 'FAIL'}] {name} -- {detail}"
        for name, ok, detail in CHECKS
    ]
    lines.append("")
    lines.append("--- 判定明细 ---")
    for j in JUDGMENTS:
        lines.append(
            f"  {j['label']}: allowed={j['allowed']} rule={j['rule']} "
            f"delay={j['crawl_delay']} probe={j['probe']}"
        )
    for line in lines:
        print(line, flush=True)
    all_ok = all(ok for _name, ok, _detail in CHECKS)
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
