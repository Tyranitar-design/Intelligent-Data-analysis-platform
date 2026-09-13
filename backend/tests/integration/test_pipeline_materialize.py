"""
数据管道 · 物化集成测试
=======================

完整闭环（全走 MockTransport）：

    采集入库 → 规范化 → PII 最小化 → 物化成数据集 → 读取 → 血缘追溯 → 清理
"""
from __future__ import annotations

import asyncio

import httpx
import pytest
from sqlalchemy import delete, select, text

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

DEMO_DOMAIN = "pipeline.webinsight.test"
BASE = f"https://{DEMO_DOMAIN}"

ROBOTS = "User-agent: *\nAllow: /\n"

LIST_HTML = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>管道演示站</title></head><body>
<ul class="entry-list">
  <li class="entry"><a href="/post/1">第一篇</a></li>
  <li class="entry"><a href="/post/2">第二篇</a></li>
  <li class="entry"><a href="/post/3">第三篇</a></li>
</ul></body></html>
"""


def _post_html(index: int) -> str:
    # 注意：JSON-LD 里的花括号在 f-string 中需转义，这里单独拼装避免歧义
    ld_json = (
        '{"@type":"NewsArticle",'
        f'"headline":"第 {index} 篇文章",'
        f'"datePublished":"2026-09-1{index}T10:00:00+08:00",'
        '"author":{"name":"编辑部"}}'
    )
    body = "这是正文内容，用于验证物化链路的字段提取与类型归一。" * 8
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>第 {index} 篇</title>
<script type="application/ld+json">{ld_json}</script></head><body>
<article><h1>第 {index} 篇文章</h1>
<time datetime="2026-09-1{index}T10:00:00+08:00">2026-09-1{index}</time>
<p>{body}</p>
</article></body></html>
"""


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/robots.txt"):
        return httpx.Response(200, text=ROBOTS, headers={"content-type": "text/plain"})
    if url.rstrip("/").endswith("/news"):
        return httpx.Response(200, text=LIST_HTML, headers={"content-type": "text/html"})
    for index in (1, 2, 3):
        if url.rstrip("/").endswith(f"/post/{index}"):
            return httpx.Response(
                200, text=_post_html(index), headers={"content-type": "text/html"}
            )
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
        # teardown 必须在任何异常下都释放连接，否则后续测试会撞上 database is locked
        try:
            _cleanup(db)
        except Exception:  # noqa: BLE001
            db.rollback()
        finally:
            db.close()


def _cleanup(db) -> None:
    """清理本测试文件产生的全部数据（含物化出来的物理表）。

    删除顺序必须遵循外键依赖，从叶到根：

        collect_items → datasets → collect_tasks → collect_jobs
        → collect_plans → compliance_verdicts → site_profiles

    顺序错误会让整条事务因外键约束回滚，结果是"看似清理了，其实一条没删"，
    残留数据会让后续测试全部误判为已采集。
    """
    # 清理前先结束任何悬挂事务：若上一个测试以 IntegrityError 结束，
    # session 处于不可用状态，此时任何清理都会失败。
    try:
        db.rollback()
    except Exception:  # noqa: BLE001
        pass

    datasets = (
        db.execute(select(Dataset).where(Dataset.name.like("pipe_test_%"))).scalars().all()
    )
    dataset_snapshots = [(d.id, d.table_name) for d in datasets]

    for dataset_id, table_name in dataset_snapshots:
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
            select(CollectPlan).where(CollectPlan.target_url.like(f"%{DEMO_DOMAIN}%"))
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
    db.execute(
        delete(CollectItem).where(CollectItem.source_url.like(f"%{DEMO_DOMAIN}%"))
    )
    db.execute(delete(Dataset).where(Dataset.collect_job_id.in_(jid)))
    db.execute(delete(Dataset).where(Dataset.name.like("pipe_test_%")))
    db.execute(delete(CollectTask).where(CollectTask.job_id.in_(jid)))
    db.execute(delete(CollectJob).where(CollectJob.id.in_(jid)))
    if plan_ids:
        db.execute(delete(CollectPlan).where(CollectPlan.id.in_(plan_ids)))
    db.execute(
        delete(ComplianceVerdict).where(
            ComplianceVerdict.target_url.like(f"%{DEMO_DOMAIN}%")
        )
    )
    db.execute(delete(SiteProfile).where(SiteProfile.domain == DEMO_DOMAIN))
    db.commit()


def _collect(session) -> int:
    """跑完一条采集链，返回 job_id。"""

    async def _go():
        client = _client()
        profiler = SiteProfiler(session, fetcher=SiteFetcher(client=client))
        analyzed = await profiler.analyze(f"{BASE}/news", force_refresh=True)

        profile = analyzed.profile
        plan = CollectPlan(
            profile_id=profile["profile_id"],
            target_url=f"{BASE}/news",
            requirement="采集标题与时间",
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
        print(
            f"[DIAG] job={job.id} status={job.status} items={job.items_count} "
            f"tasks={job.done_tasks}/{job.total_tasks} "
            f"errors={job.error_dist} dedup={job.dedup_stats}"
        )
        task_rows = (
            session.execute(
                select(CollectTask).where(CollectTask.job_id == job.id)
            )
            .scalars()
            .all()
        )
        for row in task_rows:
            print(
                f"[DIAG]   task={row.id} status={row.status} "
                f"cap={row.capability_used} attempts={row.attempts} "
                f"err={(row.last_error or '')[:160]}"
            )
        await client.aclose()
        return job.id

    return asyncio.run(_go())


# --------------------------------------------------------------------------- #


def test_materialize_creates_dataset_and_table(session):
    job_id = _collect(session)

    materializer = DatasetMaterializer(session)
    dataset = materializer.materialize_job(
        job_id, name=f"pipe_test_{job_id}", pii_policy={"author": "hashed"}
    )

    # Dataset 记录
    assert dataset.id is not None
    assert dataset.row_count >= 3
    assert dataset.column_count >= 2
    assert dataset.table_name == table_name_for(dataset.id)

    # 物理表可读
    content = materializer.read_dataset(dataset.id, limit=10)
    assert content["total"] >= 3
    assert len(content["rows"]) >= 3
    assert "title" in content["columns"]
    assert content["rows"][0]["source_url"].startswith(BASE)

    # 字段类型已归一（publish_date 为 datetime 类型声明）
    schema = dataset.schema or {}
    assert "title" in schema
    assert schema["title"]["type"] in ("text", "json")


def test_pii_is_minimized_on_materialize(session):
    job_id = _collect(session)

    materializer = DatasetMaterializer(session)
    dataset = materializer.materialize_job(job_id, name=f"pipe_test_pii_{job_id}")

    # author 被自动识别为个人数据并哈希化
    pii_policy = dataset.pii_policy or {}
    assert "author" in pii_policy, f"未识别到 PII 字段: {pii_policy}"

    content = materializer.read_dataset(dataset.id, limit=5)
    if "author" in content["columns"]:
        authors = [row.get("author") for row in content["rows"]]
        assert all(
            (a is None) or str(a).startswith("h:") for a in authors
        ), f"author 未被最小化: {authors}"


def test_lineage_traces_back_to_extractor_rule(session):
    job_id = _collect(session)

    materializer = DatasetMaterializer(session)
    dataset = materializer.materialize_job(job_id, name=f"pipe_test_lin_{job_id}")

    lineage = dataset.lineage or []
    assert lineage, "缺少血缘记录"

    by_field = {entry["field"]: entry for entry in lineage}
    assert "title" in by_field
    entry = by_field["title"]
    assert entry["profile_id"] is not None
    assert entry["domain"] == DEMO_DOMAIN
    assert entry["extractor_rule"] != "unknown"
    assert 0.0 < entry["coverage"] <= 1.0


def test_drop_dataset_removes_table(session):
    job_id = _collect(session)

    materializer = DatasetMaterializer(session)
    dataset = materializer.materialize_job(job_id, name=f"pipe_test_drop_{job_id}")
    dataset_id = dataset.id
    table_name = dataset.table_name

    assert materializer.drop_dataset(dataset_id) is True
    assert session.get(Dataset, dataset_id) is None

    from sqlalchemy import inspect as sa_inspect

    assert not sa_inspect(session.connection()).has_table(table_name)
