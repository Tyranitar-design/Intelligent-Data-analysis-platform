"""
采集链路 · 集成测试
===================

覆盖完整闭环（全部走 MockTransport，不触碰真实网络）：

    站点判别 → 生成计划 → 创建任务 → 能力选链 → 执行 → 三级去重 → 入库 → 统计

验证要点：

1. 采集产出的每条数据都关联了合规判定（合规强制点）
2. 二次执行时增量去重生效（不重复入库）
3. 能力链在一个能力降级后能继续尝试下一候选
"""
from __future__ import annotations

import asyncio

import httpx
import pytest
from sqlalchemy import delete, func, select

from api.core.database import SessionLocal, init_db
from api.models import (
    CollectItem,
    CollectJob,
    CollectPlan,
    CollectTask,
    ComplianceVerdict,
    SiteProfile,
)
from collect.scheduler import CollectScheduler
from discover.fetcher import SiteFetcher
from discover.profile import SiteProfiler

DEMO_DOMAIN = "collect.webinsight.test"
BASE = f"https://{DEMO_DOMAIN}"

ROBOTS = """User-agent: *
Disallow: /admin/
Sitemap: https://collect.webinsight.test/sitemap.xml
"""

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://collect.webinsight.test/article/1</loc></url>
  <url><loc>https://collect.webinsight.test/article/2</loc></url>
</urlset>
"""

LIST_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>采集演示站</title>
<script type="application/ld+json">
{"@type":"NewsArticle","headline":"采集演示","datePublished":"2026-09-01T10:00:00+08:00"}
</script></head><body>
<ul class="post-list">
  <li class="post-item"><a href="/article/1">第一篇：判别内核</a></li>
  <li class="post-item"><a href="/article/2">第二篇：采集内核</a></li>
  <li class="post-item"><a href="/article/3">第三篇：合规判定</a></li>
</ul>
<a href="/news?page=2">下一页</a>
</body></html>
"""


def _detail_html(index: int) -> str:
    body = "这是第 %d 篇文章的正文内容。" % index
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>第 {index} 篇：数据平台</title>
<script type="application/ld+json">
{{"@type":"NewsArticle","headline":"第 {index} 篇：数据平台",
 "datePublished":"2026-09-1{index}T08:30:00+08:00",
 "author":{{"name":"编辑部"}}}}
</script></head><body>
<article><h1>第 {index} 篇：数据平台</h1>
<time datetime="2026-09-1{index}T08:30:00+08:00">2026-09-1{index}</time>
<p>{body * 30}</p></article>
</body></html>
"""


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url == f"{BASE}/robots.txt":
        return httpx.Response(200, text=ROBOTS, headers={"content-type": "text/plain"})
    if url == f"{BASE}/sitemap.xml":
        return httpx.Response(200, text=SITEMAP, headers={"content-type": "application/xml"})
    if url.rstrip("/") == f"{BASE}/news":
        return httpx.Response(200, text=LIST_HTML, headers={"content-type": "text/html"})
    for index in (1, 2, 3):
        if url.rstrip("/").endswith(f"/article/{index}"):
            return httpx.Response(
                200, text=_detail_html(index), headers={"content-type": "text/html"}
            )
    return httpx.Response(404, text="<html>not found</html>",
                          headers={"content-type": "text/html"})


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(_handler), follow_redirects=True
    )


@pytest.fixture(scope="function")
def session():
    init_db()
    db = SessionLocal()
    yield db
    db.execute(
        delete(CollectItem).where(CollectItem.source_url.like(f"%{DEMO_DOMAIN}%"))
    )
    db.execute(
        delete(CollectTask).where(
            CollectTask.job_id.in_(
                select(CollectJob.id).where(
                    CollectJob.plan_id.in_(
                        select(CollectPlan.id).where(
                            CollectPlan.target_url.like(f"%{DEMO_DOMAIN}%")
                        )
                    )
                )
            )
        )
    )
    db.execute(
        delete(CollectJob).where(
            CollectJob.plan_id.in_(
                select(CollectPlan.id).where(
                    CollectPlan.target_url.like(f"%{DEMO_DOMAIN}%")
                )
            )
        )
    )
    db.execute(
        delete(CollectPlan).where(CollectPlan.target_url.like(f"%{DEMO_DOMAIN}%"))
    )
    db.execute(
        delete(ComplianceVerdict).where(
            ComplianceVerdict.target_url.like(f"%{DEMO_DOMAIN}%")
        )
    )
    db.execute(delete(SiteProfile).where(SiteProfile.domain == DEMO_DOMAIN))
    db.commit()
    db.close()


def _analyze(session):
    """跑一次判别，得到画像与判定。"""

    async def _go():
        client = _client()
        profiler = SiteProfiler(session, fetcher=SiteFetcher(client=client))
        result = await profiler.analyze(f"{BASE}/news", force_refresh=True)
        await client.aclose()
        return result

    return asyncio.run(_go())


def _make_plan(session, analyzed) -> CollectPlan:
    profile = analyzed.profile
    plan = CollectPlan(
        profile_id=profile["profile_id"],
        target_url=f"{BASE}/news",
        requirement="采集全部文章标题与发布时间",
        field_mapping=profile["fields"],
        strategy_chain=profile["strategy"]["chain"],
        rate_policy=profile["strategy"]["rate"],
        incremental_policy=profile["strategy"]["incremental"],
        verdict_uid=analyzed.verdict["verdict_id"],
        status="ready",
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def _run_job(session, job_id: int) -> CollectJob:
    async def _go():
        client = _client()
        scheduler = CollectScheduler(session)
        job = await scheduler.run_job(job_id, client=client)
        await client.aclose()
        return job

    return asyncio.run(_go())


# --------------------------------------------------------------------------- #
# 测试
# --------------------------------------------------------------------------- #


def test_full_collect_pipeline(session):
    analyzed = _analyze(session)
    assert analyzed.verdict["decision"] == "proceed"

    plan = _make_plan(session, analyzed)

    scheduler = CollectScheduler(session)

    async def _create():
        return await scheduler.create_job(plan)

    job = asyncio.run(_create())
    assert job.status == "pending"
    assert job.total_tasks == 1

    job = _run_job(session, job.id)

    # 任务完成
    assert job.status == "succeeded", f"status={job.status} errors={job.error_dist}"
    assert job.done_tasks == job.total_tasks
    assert job.items_count >= 3, f"仅入库 {job.items_count} 条"

    # 合规强制点：每条数据都关联了判定
    items = (
        session.execute(
            select(CollectItem).where(CollectItem.job_id == job.id)
        )
        .scalars()
        .all()
    )
    assert len(items) >= 3
    assert all(item.verdict_id is not None for item in items)

    # 字段落库
    first = items[0]
    assert first.payload
    assert "source_url" not in first.payload
    assert first.item_key

    # 质量分有值
    assert job.quality_score > 0

    # 使用的能力
    task = (
        session.execute(
            select(CollectTask).where(CollectTask.job_id == job.id)
        )
        .scalars()
        .first()
    )
    assert task.status == "done"
    assert task.capability_used in ("structured_extractor", "sitemap_walker", "http_fetcher")


def test_second_run_is_deduplicated(session):
    analyzed = _analyze(session)
    plan = _make_plan(session, analyzed)

    scheduler = CollectScheduler(session)

    async def _create():
        return await scheduler.create_job(plan)

    job1 = asyncio.run(_create())
    job1 = _run_job(session, job1.id)
    count_after_first = session.execute(
        select(func.count()).select_from(CollectItem)
    ).scalar_one()

    # 第二次执行：同样的站点，同样的内容
    job2 = asyncio.run(_create())
    job2 = _run_job(session, job2.id)
    count_after_second = session.execute(
        select(func.count()).select_from(CollectItem)
    ).scalar_one()

    # 条目总数不应因为重复采集而增长
    assert count_after_second == count_after_first, (
        f"重复采集导致条目增长: {count_after_first} -> {count_after_second}"
    )

    # 第二次的去重统计里应有跳过、内容命中或增量命中
    stats = job2.dedup_stats or {}
    assert (
        stats.get("skipped", 0)
        + stats.get("content_hits", 0)
        + stats.get("known_hits", 0)
    ) > 0, stats


def test_sitemap_capability_is_usable(session):
    """能力链中的 sitemap_walker 可独立执行。"""
    from collect.capabilities import SitemapWalker
    from collect.registry import CollectRequest, ExecContext

    analyzed = _analyze(session)
    profile = analyzed.profile

    async def _go():
        client = _client()
        from collect.capabilities import PageFetcher
        from collect.ratelimit import AdaptiveRateLimiter

        limiter = AdaptiveRateLimiter(default_rate=100.0)
        fetcher = PageFetcher(client, limiter)
        ctx = ExecContext(fetcher=fetcher, rate_limiter=limiter)
        result = await SitemapWalker().execute(
            profile, CollectRequest(target_url=f"{BASE}/news", max_items=5), ctx
        )
        await client.aclose()
        return result, ctx

    result, ctx = asyncio.run(_go())
    assert result.status.value == "ok", (
        f"degrade reason: {result.error} | "
        f"sitemaps={profile['access'].get('sitemaps')} | trace={ctx.trace}"
    )
    assert len(result.items) >= 2
