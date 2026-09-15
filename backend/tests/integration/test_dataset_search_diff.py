# -*- coding: utf-8 -*-
"""数据集检索与对比 API · 集成测试

覆盖：
- `/datasets/{id}/search`：关键字命中 / 字段限域 / 非法字段 400 / 不存在 404
- `/datasets/diff`：两数据集 schema 差异（新增/缺失字段 + 行数差） / 不存在 404

数据用 ``DatasetMaterializer.materialize_records`` 直接物化（不联网），
teardown 用 ``drop_dataset`` 逐条清理（含物理表）。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from api.core.database import SessionLocal, init_db
from api.main import app
from api.models import CollectItem, CollectJob, CollectPlan, CollectTask, Dataset
from pipeline.storage import DatasetMaterializer

PREFIX = "diff-test"
VERSIONS_TARGET = "https://versions-test/list"


@pytest.fixture(scope="function")
def session():
    init_db()
    db = SessionLocal()
    yield db
    db.rollback()
    materializer = DatasetMaterializer(db)
    rows = (
        db.execute(select(Dataset).where(Dataset.name.like(f"{PREFIX}%")))
        .scalars()
        .all()
    )
    for row in rows:
        materializer.drop_dataset(row.id)
    # 版本链测试的采集链（plan → jobs → tasks/items）
    plan_ids = select(CollectPlan.id).where(
        CollectPlan.target_url.like("%versions-test%")
    )
    job_ids = select(CollectJob.id).where(CollectJob.plan_id.in_(plan_ids))
    db.execute(delete(CollectItem).where(CollectItem.job_id.in_(job_ids)))
    db.execute(delete(CollectTask).where(CollectTask.job_id.in_(job_ids)))
    db.execute(delete(CollectJob).where(CollectJob.plan_id.in_(plan_ids)))
    db.execute(
        delete(CollectPlan).where(CollectPlan.target_url.like("%versions-test%"))
    )
    db.commit()
    db.close()


def _make_dataset(session, records, name, **kw):
    materializer = DatasetMaterializer(session)
    return materializer.materialize_records(
        records,
        name=name,
        source_type="test",
        apply_pii=False,
        **kw,
    )


def test_search_by_keyword_across_fields(session):
    dataset = _make_dataset(
        session,
        [
            {"title": "alpha 新闻", "score": 1},
            {"title": "beta 报道", "score": 2},
            {"title": "gamma 特稿", "score": 3},
        ],
        f"{PREFIX}-a",
    )
    client = TestClient(app)

    resp = client.get(f"/api/v1/collect/datasets/{dataset.id}/search", params={"q": "alpha"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 1
    assert payload["rows"][0]["title"] == "alpha 新闻"
    assert payload["query"]["q"] == "alpha"

    # 无关键字 = 全量分页
    resp = client.get(f"/api/v1/collect/datasets/{dataset.id}/search", params={"limit": 2})
    assert resp.json()["total"] == 3
    assert len(resp.json()["rows"]) == 2


def test_search_scoped_to_field(session):
    dataset = _make_dataset(
        session,
        [
            {"title": "alpha", "note": "contains alpha too"},
            {"title": "beta", "note": "alpha"},
        ],
        f"{PREFIX}-b",
    )
    client = TestClient(app)

    # 限定 title：只有第一条命中
    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search",
        params={"q": "alpha", "field": "title"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # 全字段：两条命中
    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search", params={"q": "alpha"}
    )
    assert resp.json()["total"] == 2


def test_search_invalid_field_rejected(session):
    dataset = _make_dataset(session, [{"title": "x"}], f"{PREFIX}-c")
    client = TestClient(app)

    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search",
        params={"q": "x", "field": "not_a_field"},
    )
    assert resp.status_code == 400


def test_search_missing_dataset_404(session):
    client = TestClient(app)
    resp = client.get("/api/v1/collect/datasets/999999/search", params={"q": "x"})
    assert resp.status_code == 404


def test_diff_two_datasets(session):
    dataset_a = _make_dataset(
        session,
        [{"title": "t1", "author": "a"}, {"title": "t2", "author": "b"}],
        f"{PREFIX}-diff-a",
    )
    dataset_b = _make_dataset(
        session,
        [
            {"title": "t1", "author": "a", "publish_date": "2026-09-01"},
        ],
        f"{PREFIX}-diff-b",
    )

    client = TestClient(app)
    resp = client.get(
        "/api/v1/collect/datasets/diff",
        params={"a": dataset_a.id, "b": dataset_b.id},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["a"]["dataset_id"] == dataset_a.id
    assert payload["b"]["dataset_id"] == dataset_b.id
    assert payload["row_delta"] == (dataset_b.row_count or 0) - (
        dataset_a.row_count or 0
    )
    assert "title" in payload["common_fields"]
    assert "author" in payload["common_fields"]
    assert "publish_date" in payload["only_b"]
    assert payload["only_a"] == []


def test_diff_missing_dataset_404(session):
    dataset = _make_dataset(session, [{"title": "x"}], f"{PREFIX}-diff-c")
    client = TestClient(app)

    resp = client.get(
        "/api/v1/collect/datasets/diff", params={"a": dataset.id, "b": 999999}
    )
    assert resp.status_code == 404


def test_list_datasets_contract(session):
    dataset = _make_dataset(session, [{"title": "x"}], f"{PREFIX}-list")
    client = TestClient(app)

    resp = client.get("/api/v1/collect/datasets")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(item["dataset_id"] == dataset.id for item in items)
    assert all(
        "row_count" in item and "name" in item and "created_at" in item
        for item in items
    )


def test_versions_chain_within_plan(session):
    """同一计划的两次物化 → 版本链按顺序、current 标记正确。"""
    plan = CollectPlan(target_url=VERSIONS_TARGET, status="ready")
    session.add(plan)
    session.commit()
    session.refresh(plan)

    job1 = CollectJob(
        plan_id=plan.id, status="succeeded", total_tasks=1, done_tasks=1,
        items_count=1, dedup_stats={},
    )
    job2 = CollectJob(
        plan_id=plan.id, status="succeeded", total_tasks=1, done_tasks=1,
        items_count=2, dedup_stats={},
    )
    session.add_all([job1, job2])
    session.commit()
    session.refresh(job1)
    session.refresh(job2)

    ds1 = _make_dataset(session, [{"title": "v1"}], f"{PREFIX}-v1")
    ds1.collect_job_id = job1.id
    ds2 = _make_dataset(
        session, [{"title": "v1"}, {"title": "v2"}], f"{PREFIX}-v2"
    )
    ds2.collect_job_id = job2.id
    session.commit()

    client = TestClient(app)
    resp = client.get(f"/api/v1/collect/datasets/{ds2.id}/versions")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["plan_id"] == plan.id
    assert [v["id"] for v in payload["versions"]] == [ds1.id, ds2.id]
    assert payload["current_index"] == 1
    assert payload["versions"][1]["is_current"] is True
    assert payload["versions"][0]["is_current"] is False
    assert payload["versions"][1]["row_count"] == 2

    # 从 v1 进入：当前位是链中的首条
    resp = client.get(f"/api/v1/collect/datasets/{ds1.id}/versions")
    assert resp.json()["current_index"] == 0


def test_versions_single_for_standalone_dataset(session):
    """无采集来源的数据集：单元素链 + plan_id 为空。"""
    dataset = _make_dataset(session, [{"title": "solo"}], f"{PREFIX}-solo")
    client = TestClient(app)

    resp = client.get(f"/api/v1/collect/datasets/{dataset.id}/versions")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["plan_id"] is None
    assert len(payload["versions"]) == 1
    assert payload["versions"][0]["is_current"] is True


def test_versions_missing_dataset_404(session):
    client = TestClient(app)
    resp = client.get("/api/v1/collect/datasets/999999/versions")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# D4 检索深化：多关键字（AND 分词）+ 时间范围过滤
# --------------------------------------------------------------------------- #


def test_search_multi_keyword_and(session):
    dataset = _make_dataset(
        session,
        [
            # 两词都有但非连续 —— 整串 LIKE 不命中、分词 AND 应命中
            {"title": "beta 在前 alpha 在后", "note": "x"},
            {"title": "alpha only", "note": "x"},
            {"title": "beta only", "note": "x"},
        ],
        f"{PREFIX}-multi",
    )
    client = TestClient(app)

    # 多词 = AND：只有同时含两词的行命中
    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search", params={"q": "alpha beta"}
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert "alpha" in resp.json()["rows"][0]["title"]

    # 单词仍为 OR 语义（向后兼容）：alpha 命中 2 条
    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search", params={"q": "alpha"}
    )
    assert resp.json()["total"] == 2


def test_search_multi_keyword_scoped_field(session):
    dataset = _make_dataset(
        session,
        [
            # title 同时含两词（逆序 + 连字符分隔）
            {"title": "beta-alpha 逆序", "note": "gamma"},
            {"title": "alpha", "note": "beta"},
        ],
        f"{PREFIX}-multi-field",
    )
    client = TestClient(app)

    # 限定 title：只有第一条 title 同时含 alpha + beta
    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search",
        params={"q": "alpha beta", "field": "title"},
    )
    assert resp.json()["total"] == 1
    assert resp.json()["rows"][0]["title"] == "beta-alpha 逆序"


def test_search_date_range(session):
    dataset = _make_dataset(
        session,
        [
            {"title": "a", "publish_date": "2026-08-31"},
            {"title": "b", "publish_date": "2026-09-01"},
            {"title": "c", "publish_date": "2026-09-15"},
            {"title": "d", "publish_date": "2026-10-01"},
            {"title": "e"},
        ],
        f"{PREFIX}-dates",
    )
    client = TestClient(app)

    # 含当天边界：09-01 ~ 09-15 => b, c
    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search",
        params={
            "date_field": "publish_date",
            "date_from": "2026-09-01",
            "date_to": "2026-09-15",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 2
    assert {r["title"] for r in payload["rows"]} == {"b", "c"}

    # 单侧下界
    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search",
        params={"date_field": "publish_date", "date_from": "2026-10-01"},
    )
    assert resp.json()["total"] == 1


def test_search_date_range_with_timestamps(session):
    """带时间部分的值按日期截断比较。"""
    dataset = _make_dataset(
        session,
        [
            {"title": "morning", "publish_date": "2026-09-01T08:30:00"},
            {"title": "night", "publish_date": "2026-09-01T23:59:00"},
            {"title": "next", "publish_date": "2026-09-02T00:00:01"},
        ],
        f"{PREFIX}-ts",
    )
    client = TestClient(app)

    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search",
        params={
            "date_field": "publish_date",
            "date_from": "2026-09-01",
            "date_to": "2026-09-01",
        },
    )
    assert resp.json()["total"] == 2  # morning + night


def test_search_date_with_keyword_combined(session):
    dataset = _make_dataset(
        session,
        [
            {"title": "alpha", "publish_date": "2026-09-01"},
            {"title": "alpha", "publish_date": "2026-08-01"},
            {"title": "beta", "publish_date": "2026-09-02"},
        ],
        f"{PREFIX}-date-kw",
    )
    client = TestClient(app)

    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search",
        params={
            "q": "alpha",
            "date_field": "publish_date",
            "date_from": "2026-09-01",
        },
    )
    assert resp.json()["total"] == 1


def test_search_date_param_validation(session):
    dataset = _make_dataset(session, [{"title": "x"}], f"{PREFIX}-date-val")
    client = TestClient(app)

    # 日期字段不在 schema
    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search",
        params={"date_field": "nope", "date_from": "2026-01-01"},
    )
    assert resp.status_code == 400

    # 有 date_from 但无 date_field
    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search",
        params={"date_from": "2026-01-01"},
    )
    assert resp.status_code == 400

    # date_field 但无任何范围
    resp = client.get(
        f"/api/v1/collect/datasets/{dataset.id}/search",
        params={"date_field": "title"},
    )
    assert resp.status_code == 400
