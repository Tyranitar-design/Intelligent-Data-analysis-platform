# -*- coding: utf-8 -*-
"""Prometheus 指标导出 · 集成测试

覆盖：
- 200 + text/plain
- 关键指标名存在
- 每行样本格式合法（``metric[{labels}] value``）
- 指标值与表计数一致（抽查 audit_logs）
"""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from api.core.database import init_db
from api.main import app

SAMPLE_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\{[^}]*\})? -?[0-9]+(\.[0-9]+)?$")

REQUIRED_METRICS = [
    "webinsight_jobs",
    "webinsight_schedules",
    "webinsight_rate_current_per_second",
    "webinsight_storage_bytes",
    "webinsight_storage_tables",
    "webinsight_datasets",
    "webinsight_items",
    "webinsight_profiles",
    "webinsight_audit_logs",
    "webinsight_verdicts",
]


def test_metrics_endpoint_format():
    init_db()
    client = TestClient(app)
    resp = client.get("/api/v1/monitor/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")

    text = resp.text
    for name in REQUIRED_METRICS:
        assert name in text, f"missing metric: {name}"

    sample_count = 0
    for line in text.strip().splitlines():
        if not line or line.startswith("#"):
            continue
        assert SAMPLE_RE.match(line), f"bad sample line: {line!r}"
        sample_count += 1
    assert sample_count >= 8


def test_metrics_reflects_counts():
    """抽查：webinsight_audit_logs 与审计表计数一致。"""
    from sqlalchemy import func, select

    init_db()
    from api.core.database import SessionLocal
    from api.models import AuditLog

    db = SessionLocal()
    try:
        expected = db.execute(select(func.count()).select_from(AuditLog)).scalar_one()
    finally:
        db.close()

    client = TestClient(app)
    text = client.get("/api/v1/monitor/metrics").text
    match = re.search(r"^webinsight_audit_logs ([0-9.]+)$", text, re.MULTILINE)
    assert match, "webinsight_audit_logs sample missing"
    assert float(match.group(1)) == expected
