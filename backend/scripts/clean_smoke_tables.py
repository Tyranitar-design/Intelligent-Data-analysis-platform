# -*- coding: utf-8 -*-
"""清理主库中的 smoke 测试产物（D1 配套工具）。

背景
----
修复前，smoke 契约测试直接在主库物化数据集，留下成批
``dataset_smoke_*`` 物理表与 ``datasets`` 元数据记录。测试隔离
（``tests/conftest.py``）已阻止新的污染，本脚本负责清理历史存量。

用法（在 backend/ 下运行）
--------------------------
    .\\venv\\Scripts\\python.exe scripts\\clean_smoke_tables.py            # 预演：只列出将清理的对象
    .\\venv\\Scripts\\python.exe scripts\\clean_smoke_tables.py --apply    # 执行清理（自动备份主库）

幂等：可安全重复运行。
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

TABLE_PATTERN = "dataset_smoke%"
DATASET_CONDITION = "source_type = 'smoke_local' OR name LIKE 'smoke_local%'"


def _collect_targets(cur: sqlite3.Cursor) -> tuple[list[str], list[tuple]]:
    tables = [
        r[0]
        for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?",
            (TABLE_PATTERN,),
        ).fetchall()
    ]
    datasets_rows: list[tuple] = []
    has_datasets = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='datasets'"
    ).fetchone()
    if has_datasets:
        datasets_rows = cur.execute(
            f"SELECT id, name, table_name FROM datasets WHERE {DATASET_CONDITION}"
        ).fetchall()
    return tables, datasets_rows


def _count_tables(cur: sqlite3.Cursor) -> int:
    return cur.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
    ).fetchone()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="清理主库 smoke 测试产物")
    parser.add_argument("--apply", action="store_true", help="实际执行清理（默认仅预演）")
    parser.add_argument("--db", default=None, help="主库路径（默认按统一配置源解析）")
    args = parser.parse_args()

    if args.db:
        db_path = Path(args.db)
    else:
        from database.models import resolve_default_db_path

        db_path = resolve_default_db_path()

    if not db_path.exists():
        print(f"[skip] 主库不存在: {db_path}")
        return 0

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    tables, datasets_rows = _collect_targets(cur)

    print(f"主库: {db_path}")
    print(f"清理前: 共 {_count_tables(cur)} 张表 / datasets {len(datasets_rows)} 条待清理记录")
    print(f"\n待清理物理表 ({len(tables)}):")
    for t in tables:
        print(f"  - {t}")
    print(f"待清理 datasets 记录 ({len(datasets_rows)}):")
    for r in datasets_rows:
        print(f"  - id={r[0]} name={r[1]} table={r[2]}")

    if not args.apply:
        print("\n预演模式（未修改任何数据）。确认后加 --apply 执行。")
        con.close()
        return 0

    if not tables and not datasets_rows:
        print("\n无需清理。")
        con.close()
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = db_path.with_name(f"{db_path.name}.bak-{stamp}")
    shutil.copy2(db_path, backup)
    print(f"\n已备份主库: {backup.name}")

    for t in tables:
        cur.execute(f'DROP TABLE IF EXISTS "{t}"')
    if datasets_rows:
        cur.execute(f"DELETE FROM datasets WHERE {DATASET_CONDITION}")
    con.commit()

    left, _ = _collect_targets(cur)
    print(
        f"清理完成: 剩余 smoke 表 {len(left)}，"
        f"主库现有 {_count_tables(cur)} 张表。"
    )
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
