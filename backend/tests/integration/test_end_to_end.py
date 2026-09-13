"""
端到端验收测试
==============

完整链路（全部走 MockTransport，不触碰真实网络）：

    输入 URL → 站点画像 → 合规判定 → 采集计划 → 执行采集
    → 三级去重入库 → 物化成数据集 → 分析 → 报告 → 导出

这是本项目"能不能真正用起来"的最终判据。任一环断裂都会在这里暴露。
"""
from __future__ import annotations

import asyncio

import httpx
import pytest
from sqlalchemy import delete, select, text

from analysis.facade import AnalysisFacade
from api.core.database import SessionLocal, init_db
from api.models import (
    CollectItem,
    CollectJob,
    CollectPlan,
    CollectTask,
    ComplianceVerdict,
    Dataset,
    SiteProfile,
)
from collect.scheduler import CollectScheduler
from discover.fetcher import SiteFetcher
from discover.profile import SiteProfiler
from pipeline.storage import DatasetMaterializer, table_name_for

DOMAIN = "e2e.webinsight.test"
BASE = f"https://{DOMAIN}"

ROBOTS = "User-agent: *\nCrawl-delay: 0\nSitemap: https://e2e.webinsight.test/sitemap.xml\n"

SITEMAP = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{BASE}/story/1</loc></url>
  <url><loc>{BASE}/story/2</loc></url>
  <url><loc>{BASE}/story/3</loc></url>
</urlset>
"""

LIST_HTML = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>端到端演示站</title>
<meta name="description" content="用于端到端验收的演示站点">
</head><body>
<ul class="story-list">
  <li class="story"><a href="/story/1">第一篇报道</a></li>
  <li class="story"><a href="/story/2">第二篇报道</a></li>
  <li class="story"><a href="/story/3">第三篇报道</a></li>
</ul>
<a href="/news?page=2">下一页</a>
</body></html>
"""


def _story_html(index: int, word_count: int, comments: int) -> str:
    ld = (
        '{"@type":"NewsArticle",'
        f'"headline":"第 {index} 篇报道",'
        f'"datePublished":"2026-09-1{index}T09:00:00+08:00",'
        '"author":{"name":"编辑部"},'
        f'"wordCount":{word_count},"commentCount":{comments}}}'
    )
    body = f"这是第 {index} 篇报道的正文内容，用于端到端验收测试。" * 12
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>第 {index} 篇报道</title>
<script type="application/ld+json">{ld}</script></head><body>
<article><h1>第 {index} 篇报道</h1>
<time datetime="2026-09-1{index}T09:00:00+08:00">2026-09-1{index}</time>
<p>{body}</p></article></body></html>
"""


_STORIES = {
    1: _story_html(1, 1200, 15),
    2: _story_html(2, 1800, 32),
    3: _story_html(3, 950, 8),
}


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/robots.txt"):
        return httpx.Response(200, text=ROBOTS, headers={"content-type": "text/plain"})
    if url.endswith("/sitemap.xml"):
        return httpx.Response(
            200, text=SITEMAP, headers={"content-type": "application/xml"}
        )
    if "/story/" in url:
        try:
            index = int(url.rstrip("/").rsplit("/", 1)[-1])
        except ValueError:
            index = 0
        html = _STORIES.get(index)
        if html:
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})
    if url.rstrip("/").endswith("/news"):
        return httpx.Response(200, text=LIST_HTML, headers={"content-type": "text/html"})
    return httpx.Response(404, text="<html>nf</html>", headers={"content-type": "text/html"})


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(_handler), follow_redirects=True
    )


@pytest.fixture()
def session():
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            _cleanup(db)
        except Exception:  # noqa: BLE001
            db.rollback()
        finally:
            db.close()


def _cleanup(db) -> None:
    """按外键依赖从叶到根清理。"""
    # 先结束悬挂事务，否则上一个测试留下的异常状态会让清理静默失败
    try:
        db.rollback()
    except Exception:  # noqa: BLE001
        pass

    datasets = (
        db.execute(select(Dataset).where(Dataset.name.like("e2e_%"))).scalars().all()
    )
    snapshots = [(d.id, d.table_name) for d in datasets]
    for dataset_id, table_name in snapshots:
        try:
            db.execute(
                text(f'DROP TABLE IF EXISTS "{table_name or table_name_for(dataset_id)}"')
            )
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()

    plan_ids = [
        p.id
        for p in db.execute(
            select(CollectPlan).where(CollectPlan.target_url.like(f"%{DOMAIN}%"))
        ).scalars()
    ]
    job_ids = (
        [
            j.id
            for j in db.execute(
                select(CollectJob).where(CollectJob.plan_id.in_(plan_ids))
            ).scalars()
        ]
        if plan_ids
        else []
    )
    jid = job_ids or [0]

    db.execute(delete(CollectItem).where(CollectItem.job_id.in_(jid)))
    db.execute(delete(Dataset).where(Dataset.collect_job_id.in_(jid)))
    db.execute(delete(Dataset).where(Dataset.name.like("e2e_%")))
    db.execute(delete(CollectTask).where(CollectTask.job_id.in_(jid)))
    db.execute(delete(CollectJob).where(CollectJob.id.in_(jid)))
    if plan_ids:
        db.execute(delete(CollectPlan).where(CollectPlan.id.in_(plan_ids)))
    db.execute(
        delete(ComplianceVerdict).where(ComplianceVerdict.target_url.like(f"%{DOMAIN}%"))
    )
    db.execute(delete(SiteProfile).where(SiteProfile.domain == DOMAIN))
    db.commit()


# --------------------------------------------------------------------------- #
# 端到端
# --------------------------------------------------------------------------- #


def test_full_pipeline_url_to_report(session):
    """输入 URL → 报告导出的完整验收。"""

    async def _pipeline():
        client = _client()

        # 1. 站点判别
        profiler = SiteProfiler(session, fetcher=SiteFetcher(client=client))
        analyzed = await profiler.analyze(f"{BASE}/news", force_refresh=True)
        profile = analyzed.profile
        verdict = analyzed.verdict

        # 2. 采集计划
        plan = CollectPlan(
            profile_id=profile["profile_id"],
            target_url=f"{BASE}/news",
            requirement="采集全部报道的标题与时间",
            field_mapping=profile["fields"],
            strategy_chain=profile["strategy"]["chain"],
            rate_policy=profile["strategy"]["rate"],
            incremental_policy=profile["strategy"]["incremental"],
            verdict_uid=verdict["verdict_id"],
            status="ready",
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)

        # 3. 执行采集
        scheduler = CollectScheduler(session)
        job = await scheduler.create_job(plan)
        job = await scheduler.run_job(job.id, client=client)
        await client.aclose()

        return profile, verdict, plan, job

    profile, verdict, plan, job = asyncio.run(_pipeline())

    # --- 环节 1：画像 ---
    assert profile["domain"] == DOMAIN
    assert profile["site"]["type"] == "news"
    assert profile["confidence"] > 0.5
    assert profile["structure"]["has_sitemap"] is True
    assert any(f["name"] == "title" for f in profile["fields"])

    # --- 环节 2：判定 ---
    assert verdict["decision"] == "proceed"
    assert verdict["dimensions"]["access"] == "A1"

    # --- 环节 3：采集 ---
    assert job.status == "succeeded", f"status={job.status} err={job.error_dist}"
    assert job.items_count >= 3, f"仅入库 {job.items_count} 条"

    items = (
        session.execute(select(CollectItem).where(CollectItem.job_id == job.id))
        .scalars()
        .all()
    )
    assert len(items) >= 3
    # 合规强制点：每条数据都能追溯到判定
    assert all(item.verdict_id is not None for item in items)
    # 字段确实落库
    sample_payloads = [i.payload or {} for i in items]
    assert any("title" in p for p in sample_payloads)

    # --- 环节 4：物化 ---
    materializer = DatasetMaterializer(session)
    dataset = materializer.materialize_job(job.id, name=f"e2e_dataset_{job.id}")

    assert dataset.row_count >= 3
    assert dataset.table_name == table_name_for(dataset.id)
    assert dataset.lineage, "缺少血缘"
    assert dataset.pii_policy, "未执行 PII 最小化"

    # --- 环节 5：分析 ---
    facade = AnalysisFacade(session)

    eda = facade.run(dataset.id, "eda")
    assert eda["summary"]
    assert eda["result"], "EDA 无结果"

    stats = facade.run(dataset.id, "stats")
    numeric = stats["result"].get("numeric") or {}
    assert numeric, f"未识别到数值字段: {list(stats['result'].keys())}"
    # wordCount 应被识别为数值并给出统计量
    assert any("mean" in v for v in numeric.values())

    corr = facade.run(dataset.id, "correlation")
    assert "columns" in corr["result"]

    outliers = facade.run(dataset.id, "outliers")
    assert "total_outliers" in outliers["result"]

    # 图表
    assert eda["charts"], "未生成任何图表"
    assert all("option" in c for c in eda["charts"])
    assert all("series" in c["option"] for c in eda["charts"])

    # --- 环节 6：报告 ---
    report = facade.build_report(dataset.id, "eda", fmt="markdown")
    assert report["title"].startswith("数据集分析报告")
    assert "数据集概况" in report["content"]
    assert "数据血缘" in report["content"]
    assert report["sections"]

    html_report = facade.build_report(dataset.id, "eda", fmt="html")
    assert html_report["content"].startswith("<!DOCTYPE html>")
    assert "<table>" in html_report["content"]

    # --- 环节 7：导出 ---
    for fmt, expected_media in (
        ("csv", "text/csv"),
        ("json", "application/json"),
        ("excel", "spreadsheetml"),
    ):
        content, filename, media_type = facade.export(dataset.id, fmt)
        assert content, f"{fmt} 导出为空"
        assert expected_media in media_type, f"{fmt} media_type={media_type}"
        assert filename.endswith({"csv": ".csv", "json": ".json", "excel": ".xlsx"}[fmt])

    csv_bytes, _, _ = facade.export(dataset.id, "csv")
    csv_text = csv_bytes.decode("utf-8-sig")
    assert "source_url" in csv_text.splitlines()[0]


def test_pipeline_is_idempotent(session):
    """二次执行整条链路：增量去重生效，不重复入库。"""

    async def _collect_once():
        client = _client()
        profiler = SiteProfiler(session, fetcher=SiteFetcher(client=client))
        analyzed = await profiler.analyze(f"{BASE}/news", force_refresh=True)
        profile = analyzed.profile

        plan = CollectPlan(
            profile_id=profile["profile_id"],
            target_url=f"{BASE}/news",
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

        scheduler = CollectScheduler(session)
        job = await scheduler.create_job(plan)
        job = await scheduler.run_job(job.id, client=client)
        await client.aclose()
        return job

    from sqlalchemy import func

    first = asyncio.run(_collect_once())
    count_first = session.execute(
        select(func.count()).select_from(CollectItem)
    ).scalar_one()

    second = asyncio.run(_collect_once())
    count_second = session.execute(
        select(func.count()).select_from(CollectItem)
    ).scalar_one()

    assert count_second == count_first, f"重复采集导致增长 {count_first} → {count_second}"
    stats = second.dedup_stats or {}
    assert (
        stats.get("known_hits", 0)
        + stats.get("skipped", 0)
        + stats.get("content_hits", 0)
    ) > 0, stats
