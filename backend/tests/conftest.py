# -*- coding: utf-8 -*-
"""pytest 全局配置 —— 数据库隔离（D1）

背景
----
修复前：测试直接使用主库 ``backend/data_platform.db`` —— smoke 契约测试
每次运行都会在主库物化 ``dataset_smoke_*`` 表并写入 ``datasets`` 记录，
表只增不减（2026-09-14 实测：每跑一次全量测试 +2 张脏表 +2 条记录）。

策略
----
1. 在任何后端模块 import 之前，把 ``DATABASE_URL`` 指向会话级临时库。
   ``api.core.config.settings``（SQLAlchemy 腿）与
   ``database.models.Database``（sqlite3 腿）都尊重该环境变量，
   一次设置覆盖全部写入路径。
2. 每次会话全新开始：清掉上次残留的测试库文件（含 SQLite 旁路文件）。
3. 会话结束把测试库留在系统 temp 目录 —— 便于失败排查，系统自行清理。
4. ``tests/unit/test_db_isolation.py`` 挂哨兵断言：主库不允许出现
   ``dataset_smoke_*`` 表 —— 防止未来任何路径回退到主库写脏数据。
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TEST_DIR = Path(tempfile.gettempdir()) / "webinsight_pytest"
_TEST_DIR.mkdir(parents=True, exist_ok=True)
_TEST_DB = _TEST_DIR / "test_data_platform.db"

# 每次会话全新开始：清掉上次残留（含 SQLite 旁路文件）
for _p in (
    _TEST_DB,
    Path(str(_TEST_DB) + "-journal"),
    Path(str(_TEST_DB) + "-wal"),
    Path(str(_TEST_DB) + "-shm"),
):
    if _p.exists():
        try:
            _p.unlink()
        except OSError:  # 极端情况下被残留进程持有，交给系统清理
            pass

# ⚠ 必须发生在任何 api.* / smoke.* / crawlers.* / database.* import 之前
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_test_database():
    """建好隔离测试库的全部表。

    SQLAlchemy 侧的表由 ``init_db()`` 创建；旧 ``Database`` 类的表
    （crawl_records / ecom_products 等）在其首次连接时自动创建。
    """
    import api.models  # noqa: F401  注册全部 ORM 模型
    from api.core.database import init_db

    init_db()
    yield
