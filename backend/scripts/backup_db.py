# -*- coding: utf-8 -*-
"""数据库备份（P10 · O5）

用法（backend/ 下）：
    python scripts/backup_db.py                  # 创建一份备份（并执行轮转）
    python scripts/backup_db.py --list           # 列出备份
    python scripts/backup_db.py --keep 5         # 指定保留份数（默认 10）

约定：
- 备份目录：``backend/backups/``
- 命名：``data_platform.db.bak-YYYYmmdd-HHMMSS``
- 每份备份旁写 ``.sha256`` 校验文件（恢复前验真）
- 使用 SQLite 官方 **在线备份 API**（``Connection.backup()``）——服务运行中
  执行也安全，不需要停机复制文件。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

BACKUP_DIR = BACKEND_DIR / "backups"
DEFAULT_KEEP = 10


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_backups() -> list[Path]:
    """按名称倒序返回备份文件（不含 .sha256 旁车文件）。"""
    if not BACKUP_DIR.exists():
        return []
    files = [
        path
        for path in BACKUP_DIR.glob("data_platform.db.bak-*")
        if not path.name.endswith(".sha256")
    ]
    return sorted(files, key=lambda path: path.name, reverse=True)


def create_backup(db_path: Path, keep: int) -> Path:
    """创建一份备份并轮转旧备份。返回备份文件路径。"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = BACKUP_DIR / f"{db_path.name}.bak-{stamp}"
    if target.exists():  # 同一秒内重复执行
        target = BACKUP_DIR / f"{db_path.name}.bak-{stamp}-{os.getpid() % 1000}"

    # SQLite 在线备份 API：一致快照，服务运行中也安全
    source_conn = sqlite3.connect(str(db_path))
    target_conn = sqlite3.connect(str(target))
    try:
        with target_conn:
            source_conn.backup(target_conn)
    finally:
        target_conn.close()
        source_conn.close()

    digest = sha256_of(target)
    target.with_name(target.name + ".sha256").write_text(
        digest + "\n", encoding="utf-8"
    )

    size = target.stat().st_size
    print(f"[ok] backup-created: {target.name} ({size:,} bytes, sha256={digest[:16]}...)")

    for old in list_backups()[max(1, keep):]:
        old.unlink()
        sha_file = old.with_name(old.name + ".sha256")
        if sha_file.exists():
            sha_file.unlink()
        print(f"[rotate] removed old backup: {old.name}")

    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="数据库备份")
    parser.add_argument("--list", action="store_true", help="只列出备份")
    parser.add_argument(
        "--keep", type=int, default=DEFAULT_KEEP, help=f"保留份数（默认 {DEFAULT_KEEP}）"
    )
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

    from database.models import resolve_default_db_path

    db_path = Path(resolve_default_db_path())
    if not db_path.exists():
        print(f"[skip] 主库不存在: {db_path}")
        return 1

    create_backup(db_path, args.keep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
