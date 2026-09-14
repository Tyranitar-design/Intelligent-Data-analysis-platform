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
from sqlalchemy import select

from api.core.database import SessionLocal, init_db
from api.main import app
from api.models import Dataset, CollectItem, CollectJob, CollectTask
from pipeline.storage import DatasetMaterializer

PREFIX = "diff-test"


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
