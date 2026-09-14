# -*- coding: utf-8 -*-
"""备份与恢复 · 实机演练验证门禁（P10 · O5）

演练链路（真实执行，脚本级——不需要服务）：

1. 创建备份 → 校验文件与 sha256 旁车
2. 在主库制造"标记数据"
3. 恢复预演（dry-run）→ 标记仍在（不误改）
4. 实际恢复 → 标记消失、主库与备份内容一致（计数 + sha）
5. 清理演练产生的 marker 备份
6. 证据落盘 `docs/evidence/p10-backup/`

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_backup_restore.py
"""
from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "p10-backup"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

from backup_db import list_backups, sha256_of  # noqa: E402

MARKER = "_backup_verify_marker"


def run_script(name: str, *args: str) -> tuple[int, str]:
    py = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    proc = subprocess.run(
        [str(py), str(BACKEND_DIR / "scripts" / name), *args],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def table_names(db_path: Path) -> set[str]:
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        con.close()


def logical_digest(db_path: Path) -> str:
    """schema + 每表行数的逻辑指纹（不依赖文件字节布局）。"""
    con = sqlite3.connect(str(db_path))
    try:
        schema = sorted(
            (row[0], row[1] or "")
            for row in con.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table'"
            ).fetchall()
        )
        parts = [f"{name}:{sql}" for name, sql in schema]
        for name, _ in schema:
            count = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            parts.append(f"{name}#rows={count}")
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    finally:
        con.close()


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    from database.models import resolve_default_db_path

    db_path = Path(resolve_default_db_path())

    try:
        baseline = len(list_backups())

        # [1] 创建备份
        code, out = run_script("backup_db.py")
        ok = code == 0 and "[ok] backup-created" in out
        last_line = out.strip().splitlines()[-1] if out.strip() else ""
        checks.append(("backup created", ok, last_line))
        backups = list_backups()
        checks.append((
            "backup count grows",
            len(backups) == baseline + 1,
            f"{baseline} -> {len(backups)}",
        ))
        newest = backups[0]

        # [2] sha256 旁车校验
        sha_file = newest.with_name(newest.name + ".sha256")
        actual = sha256_of(newest)
        expected = (
            sha_file.read_text(encoding="utf-8").strip() if sha_file.exists() else ""
        )
        checks.append((
            "sha256 sidecar valid",
            sha_file.exists() and actual == expected,
            f"sha={actual[:16]}…",
        ))
        baseline_tables = len(table_names(newest))

        # [3] 制造标记数据
        con = sqlite3.connect(str(db_path))
        with con:
            con.execute(f"CREATE TABLE {MARKER} (id INTEGER PRIMARY KEY, note TEXT)")
            con.execute(f"INSERT INTO {MARKER} (note) VALUES ('will-disappear')")
        con.close()
        checks.append(("marker injected", MARKER in table_names(db_path), ""))

        # [4] dry-run：不修改
        code, out = run_script("restore_db.py", "--latest")
        checks.append((
            "restore dry-run keeps marker",
            code == 0 and "[dry-run]" in out and MARKER in table_names(db_path),
            "",
        ))

        # [5] 实际恢复
        code, out = run_script("restore_db.py", "--latest", "--apply")
        checks.append(("restore applied", code == 0 and "[ok] restore-done" in out, ""))

        # [6] 恢复后验证
        tables_after = table_names(db_path)
        checks.append(("marker gone after restore", MARKER not in tables_after, ""))
        checks.append((
            "table count matches backup",
            len(tables_after) == baseline_tables,
            f"after={len(tables_after)} backup={baseline_tables}",
        ))
        # 逻辑等价校验：schema + 每表行数的指纹。
        # （文件级 sha 会因 SQLite 在目标库写入 change-counter 等元数据而不同，
        #   backup API 保证的是逻辑等价而非字节一致。）
        checks.append((
            "logical content matches backup (schema + row counts)",
            logical_digest(db_path) == logical_digest(newest),
            f"digest={logical_digest(db_path)[:16]}...",
        ))

        # [7] 清理演练产生的 marker 备份（safety 那份）
        removed: list[str] = []
        for item in list_backups():
            if item == newest:
                continue
            if MARKER in table_names(item):
                item.unlink()
                sidecar = item.with_name(item.name + ".sha256")
                if sidecar.exists():
                    sidecar.unlink()
                removed.append(item.name)
        checks.append((
            "drill artifacts cleaned",
            True,
            f"removed={removed}" if removed else "nothing to remove",
        ))

    except Exception as exc:  # noqa: BLE001
        checks.append(("exception", False, f"{type(exc).__name__}: {exc}"))

    print("\n=== P10 BACKUP/RESTORE VERIFY RESULTS ===", flush=True)
    all_ok = True
    lines = []
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        line = f"  {mark}  {name}  --  {detail}"
        print(line, flush=True)
        lines.append(line)
        all_ok = all_ok and ok

    verdict = "all checks passed" if all_ok else "FAILURES PRESENT"
    print(f"RESULT: {verdict}", flush=True)
    try:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / "result.txt").write_text(
            "\n".join(lines) + f"\nRESULT: {verdict}\n", encoding="utf-8"
        )
    except OSError:
        pass
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
