# -*- coding: utf-8 -*-
"""数据库恢复（P10 · O5）

用法（backend/ 下）：
    python scripts/restore_db.py --list            # 列出可用备份
    python scripts/restore_db.py --latest          # 预演（默认 dry-run，不改动）
    python scripts/restore_db.py --latest --apply  # 实际恢复
    python scripts/restore_db.py --file data_platform.db.bak-20260914-160000 --apply

安全设计：
- 默认 **dry-run**；
- 恢复前校验备份 sha256（不匹配则拒绝）；
- 实际恢复前把当前库再另存一份（防手滑）；
- 使用 SQLite 在线备份 API 写入主库；**建议先停止后端服务**再执行恢复。
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backup_db import BACKUP_DIR, create_backup, list_backups, sha256_of  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="数据库恢复")
    parser.add_argument("--list", action="store_true", help="列出可用备份")
    parser.add_argument("--latest", action="store_true", help="使用最新一份备份")
    parser.add_argument("--file", type=str, default=None, help="指定备份文件名")
    parser.add_argument("--apply", action="store_true", help="实际执行恢复（默认预演）")
    args = parser.parse_args()

    if args.list:
        backups = list_backups()
        if not backups:
            print("(无备份)")
            return 0
        print(f"备份目录: {BACKUP_DIR}")
        for item in backups:
            print(f"  {item.name}  {item.stat().st_size:,} bytes")
        return 0

    if args.file:
        source = BACKUP_DIR / args.file
    elif args.latest:
        backups = list_backups()
        if not backups:
            print("[fail] 无备份可用")
            return 1
        source = backups[0]
    else:
        parser.error("需要 --file 或 --latest")

    if not source.exists():
        print(f"[fail] 备份不存在: {source}")
        return 1

    # ---- 验真 ----
    sha_file = source.with_name(source.name + ".sha256")
    if sha_file.exists():
        expected = sha_file.read_text(encoding="utf-8").strip()
        actual = sha256_of(source)
        if actual != expected:
            print("[fail] sha256 校验不匹配——备份可能损坏，拒绝恢复")
            return 1
        print(f"[ok] 校验通过 sha256={actual[:16]}…")
    else:
        print("[warn] 无 .sha256 校验文件——跳过验真")

    from database.models import resolve_default_db_path

    db_path = Path(resolve_default_db_path())
    print(f"目标主库: {db_path}")
    print(f"来源备份: {source.name}")

    if not args.apply:
        print("\n[dry-run] no changes made. add --apply to execute.")
        return 0

    # ---- 防手滑：先把当前库另存一份 ----
    if db_path.exists():
        safety = create_backup(db_path, keep=10_000)  # 大 keep：不触发轮转
        print(f"[safety] 当前库已另存: {safety.name}")

    # ---- 恢复（在线备份 API 反向写入）----
    source_conn = sqlite3.connect(str(source))
    target_conn = sqlite3.connect(str(db_path))
    try:
        with target_conn:
            source_conn.backup(target_conn)
    finally:
        target_conn.close()
        source_conn.close()

    print("[ok] restore-done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
