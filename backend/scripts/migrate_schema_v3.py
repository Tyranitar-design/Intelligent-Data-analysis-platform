"""
P0.2 数据库 schema 重建脚本
============================

背景
----
数据库文件（data_platform.db）是按**旧模型定义**建立的，代码库已完成
refactor 到 api/models/ 包（新 schema）。结果是：后端能启动、106 个路由
能注册，但任何涉及 ORM 查询的操作都会抛 OperationalError：

    no such column: data_sources.is_active
    no such column: crawl_tasks.name
    no such column: datasets.source_type
    no such column: ml_models.task_type
    no such column: reports.name
    no such table:  users
    no such table:  analysis_tasks

这是本项目"能启动但一用就崩"的根因。

策略
----
1. 备份旧库到 data_platform.db.bak-<timestamp>
2. 记录非 ORM 业务表（采集产生的数据表）的 DDL 与数据
3. 删除旧库，用当前 ORM 定义重建全部表
4. 回填业务表数据（这些表的 schema 未变，原样搬运）
5. 逐模型验证查询可用

用法
----
    cd backend
    ./venv/Scripts/python.exe scripts/migrate_schema_v3.py

回滚
----
    mv data_platform.db.bak-<timestamp> data_platform.db
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "data_platform.db"

# 非 ORM 管理的业务数据表：采集流程产出的数据表。
# 它们由运行时动态创建，不在 Base.metadata 中，重建时需原样搬运。
BUSINESS_TABLES = [
    "crawl_records",
    "ecom_products",
    "energy_data",
    "news_data",
    "stock_data",
]


def fail(msg: str) -> None:
    print(f"[ERROR] {msg}")
    sys.exit(1)


def main() -> int:
    if not DB_PATH.exists():
        fail(f"database not found: {DB_PATH}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = DB_PATH.with_name(f"data_platform.db.bak-{stamp}")

    # ---------- 1. 备份 ----------
    shutil.copy2(DB_PATH, backup_path)
    print(f"[1] backup created: {backup_path.name}")

    # ---------- 2. 采集业务表 ----------
    old_con = sqlite3.connect(backup_path)
    old_cur = old_con.cursor()
    preserved: dict[str, dict] = {}

    for table in BUSINESS_TABLES:
        try:
            old_cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            row = old_cur.fetchone()
            if not row or not row[0]:
                print(f"[2] skip {table}: no DDL")
                continue

            old_cur.execute(f"SELECT * FROM {table}")  # noqa: S608 - local fixture
            columns = [d[0] for d in old_cur.description]
            rows = old_cur.fetchall()
            preserved[table] = {"ddl": row[0], "columns": columns, "rows": rows}
            print(f"[2] preserved {table}: {len(rows)} rows, {len(columns)} cols")
        except sqlite3.Error as exc:
            print(f"[2] skip {table}: {exc}")

    old_con.close()

    # ---------- 3. 重建 ----------
    DB_PATH.unlink()
    print("[3] old database removed")

    sys.path.insert(0, str(BACKEND_DIR))
    from api.core.database import SessionLocal, init_db  # noqa: E402
    import api.models  # noqa: F401,E402 - 导入以注册全部模型到 Base.metadata

    init_db()
    print("[4] new schema created from current ORM models")

    # ---------- 4. 回填业务表 ----------
    if preserved:
        new_con = sqlite3.connect(DB_PATH)
        new_cur = new_con.cursor()
        for table, payload in preserved.items():
            try:
                new_cur.execute(payload["ddl"])
                placeholders = ",".join("?" * len(payload["columns"]))
                column_list = ",".join(payload["columns"])
                new_cur.executemany(
                    f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})",  # noqa: S608
                    payload["rows"],
                )
                new_con.commit()
                print(f"[5] restored {table}: {len(payload['rows'])} rows")
            except sqlite3.Error as exc:
                print(f"[5] FAILED {table}: {str(exc)[:90]}")
        new_con.close()

    # ---------- 5. 验证 ----------
    from api.models import (  # noqa: E402
        AnalysisTask,
        CrawlTask,
        DataSource,
        Dataset,
        MLModel,
        Report,
        User,
    )

    models = [DataSource, CrawlTask, Dataset, MLModel, Report, User, AnalysisTask]
    session = SessionLocal()
    failures = 0
    print("[6] verification:")
    for model in models:
        try:
            count = session.query(model).count()
            print(f"    OK   {model.__name__:14s} rows={count}")
        except Exception as exc:  # noqa: BLE001 - 诊断脚本需捕获全部
            failures += 1
            print(f"    FAIL {model.__name__:14s} {str(exc)[:80]}")
    session.close()

    print()
    if failures:
        print(f"RESULT: {failures} model(s) still failing. Rollback with:")
        print(f"    mv {backup_path.name} data_platform.db")
        return 1

    print("RESULT: all models queryable. Schema migration complete.")
    print(f"Rollback point kept at: {backup_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
