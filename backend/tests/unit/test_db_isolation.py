# -*- coding: utf-8 -*-
"""数据库隔离哨兵（D1）。

守护两件事：
1. 测试运行时，两条数据库腿都指向隔离测试库（而非主库）——
   ``api.core.config.settings``（SQLAlchemy）与 ``database.models``
   （sqlite3）必须由同一份 ``DATABASE_URL`` 驱动。
2. 主库不得存在 smoke 测试产物 —— 防止任何代码路径回退到主库写脏数据。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
MAIN_DB = BACKEND_DIR / "data_platform.db"


def test_tests_run_against_isolated_database():
    """测试库必须是隔离库；旧 Database 腿也必须跟随同一配置源。"""
    from api.core.config import settings
    from database.models import resolve_default_db_path

    assert "webinsight_pytest" in settings.DATABASE_URL, (
        f"SQLAlchemy 腿未使用隔离库: {settings.DATABASE_URL}；"
        "请检查 tests/conftest.py 是否在 import 前设置了 DATABASE_URL"
    )

    resolved = resolve_default_db_path()
    assert resolved != MAIN_DB, f"旧 Database 腿仍指向主库: {resolved}"
    assert "webinsight_pytest" in str(resolved), (
        f"旧 Database 腿未使用隔离库: {resolved}"
    )


def test_main_database_has_no_smoke_artifacts():
    """哨兵：主库不允许出现 dataset_smoke_* 表。"""
    if not MAIN_DB.exists():
        return  # 全新克隆尚无主库时无需检查

    con = sqlite3.connect(str(MAIN_DB))
    try:
        smoke_tables = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name LIKE 'dataset_smoke%'"
            ).fetchall()
        ]
    finally:
        con.close()

    assert smoke_tables == [], (
        f"主库存在 smoke 测试脏表: {smoke_tables} —— 说明测试隔离失效。"
        "请检查 tests/conftest.py；存量清理用 scripts/clean_smoke_tables.py --apply。"
    )
