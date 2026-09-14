"""
数据存储与物化
==============

把采集条目汇总成可分析的数据集。

    collect_items (payload)
        → normalize  统一类型系统
        → pii        字段级最小化
        → materialize 落成真实表 + Dataset 记录
        → lineage    字段级血缘

落成**真实表**而非仅存 JSON，是为了让分析层（EDA / 统计 / 建模）能直接用
SQL 读取，不必为了兼容而引入中间层。表名由数据集 ID 派生，删除数据集时一并清理。
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from api.models import CollectItem, CollectJob, Dataset, SiteProfile
from pipeline.lineage import build_lineage
from pipeline.normalize import FieldType, merge_field_types, normalize_record
from pipeline.pii import minimize

logger = logging.getLogger(__name__)

TABLE_PREFIX = "ds_"
MAX_PAYLOAD_CHARS = 60000

# 统一类型 → SQLite 列类型
_SQL_TYPE = {
    str(FieldType.TEXT): "TEXT",
    str(FieldType.INT): "INTEGER",
    str(FieldType.FLOAT): "REAL",
    str(FieldType.BOOL): "INTEGER",
    str(FieldType.DATETIME): "TEXT",
    str(FieldType.URL): "TEXT",
    str(FieldType.JSON): "TEXT",
    str(FieldType.LIST): "TEXT",
}

_RE_UNSAFE_IDENT = re.compile(r"[^0-9a-zA-Z_\u4e00-\u9fff]")


def _quote(identifier: str) -> str:
    """SQLite 标识符引用。保留中文列名以便直接阅读查询结果。"""
    return '"' + identifier.replace('"', '""') + '"'


def safe_column_name(name: str, used: set[str]) -> str:
    """把字段名规范成合法且唯一的列名。"""
    ident = _RE_UNSAFE_IDENT.sub("_", str(name)).strip("_") or "field"
    if ident[0].isdigit():
        ident = "f_" + ident
    ident = ident[:60]

    base = ident
    index = 1
    while ident.lower() in used:
        ident = f"{base}_{index}"
        index += 1
    used.add(ident.lower())
    return ident


def table_name_for(dataset_id: int) -> str:
    return f"{TABLE_PREFIX}{dataset_id}"


class DatasetMaterializer:
    """把采集结果物化成数据集。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ #
    # 物化
    # ------------------------------------------------------------------ #

    def materialize_job(
        self,
        job_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        pii_policy: Optional[dict[str, str]] = None,
        apply_pii: bool = True,
    ) -> Dataset:
        """把一个采集任务的全部条目物化成数据集。"""
        job = self.session.get(CollectJob, job_id)
        if job is None:
            raise ValueError(f"采集任务不存在: {job_id}")

        items = (
            self.session.execute(
                select(CollectItem)
                .where(CollectItem.job_id == job_id)
                .order_by(CollectItem.id)
            )
            .scalars()
            .all()
        )
        if not items:
            raise ValueError(f"采集任务没有可物化的条目: {job_id}")

        records = [dict(i.payload or {}) for i in items]
        source_urls = [i.source_url for i in items if i.source_url]

        dataset_name = name or self._default_name(job)
        return self.materialize_records(
            records,
            name=dataset_name,
            description=description or f"来自采集任务 #{job_id}",
            source_type="crawl",
            source_id=job_id,
            collect_job_id=job_id,
            profile_id=self._profile_id_for_plan(job.plan_id),
            source_urls=source_urls,
            pii_policy=pii_policy,
            apply_pii=apply_pii,
        )

    def materialize_records(
        self,
        records: list[dict],
        *,
        name: str,
        description: str = "",
        source_type: str = "crawl",
        source_id: Optional[int] = None,
        collect_job_id: Optional[int] = None,
        profile_id: Optional[int] = None,
        source_urls: Optional[list[str]] = None,
        pii_policy: Optional[dict[str, str]] = None,
        apply_pii: bool = True,
    ) -> Dataset:
        """把一批记录物化成数据集。

        ``apply_pii`` 默认为真：平台的基本原则是"默认做字段级最小化"，
        而不是等调用方想起来才处理。
        """
        if not records:
            raise ValueError("没有可物化的记录")

        # 1. 规范化
        normalized: list[dict] = []
        type_maps: list[dict[str, str]] = []
        for record in records:
            clean, types = normalize_record(record)
            if not clean:
                continue
            normalized.append(clean)
            type_maps.append(types)

        if not normalized:
            raise ValueError("规范化后没有有效记录")

        schema_types = merge_field_types(type_maps)

        # 2. PII 最小化（默认执行）
        if apply_pii:
            policy = dict(pii_policy or {})
            normalized, applied_policy = minimize(normalized, policy)
        else:
            applied_policy = {}

        # 3. 列名映射
        used: set[str] = {"id", "source_url"}
        column_map: dict[str, str] = {}
        for field in schema_types:
            column_map[field] = safe_column_name(field, used)

        # 4. Dataset 记录
        dataset = Dataset(
            name=name,
            description=description,
            source_type=source_type,
            source_id=source_id,
            collect_job_id=collect_job_id,
            profile_id=profile_id,
            row_count=len(normalized),
            column_count=len(column_map),
            size_bytes=0,
            file_format="table",
            pii_policy=applied_policy,
        )
        self.session.add(dataset)
        self.session.commit()
        self.session.refresh(dataset)

        # 5. 建表 + 写入
        table_name = table_name_for(dataset.id)
        self._create_and_fill_table(
            table_name, column_map, schema_types, normalized, source_urls or []
        )

        dataset.table_name = table_name
        dataset.size_bytes = self._table_size(table_name)
        dataset.schema = {
            field: {
                "column": column_map[field],
                "type": schema_types[field],
            }
            for field in schema_types
        }
        dataset.statistics = self._compute_statistics(normalized, schema_types, applied_policy)
        dataset.sample_data = normalized[:5]

        # 6. 血缘
        profile = self._load_profile(profile_id)
        dataset.lineage = build_lineage(
            list(schema_types.keys()),
            normalized,
            profile=profile or {},
            source_urls=source_urls or [],
        )

        self.session.commit()
        self.session.refresh(dataset)

        logger.info(
            "数据集物化完成 id=%s rows=%s cols=%s",
            dataset.id,
            dataset.row_count,
            dataset.column_count,
        )
        return dataset

    # ------------------------------------------------------------------ #
    # 表操作
    # ------------------------------------------------------------------ #

    def _create_and_fill_table(
        self,
        table_name: str,
        column_map: dict[str, str],
        schema_types: dict[str, str],
        rows: list[dict],
        source_urls: list[str],
    ) -> None:
        """创建物理表并写入数据。已存在则先删除（重建语义）。"""
        columns_ddl = ", ".join(
            f"{_quote(column_map[field])} {_SQL_TYPE.get(schema_types[field], 'TEXT')}"
            for field in column_map
        )
        ddl = (
            f"CREATE TABLE {_quote(table_name)} ("
            f'"id" INTEGER PRIMARY KEY AUTOINCREMENT, '
            f'"source_url" TEXT, '
            f"{columns_ddl})"
        )

        conn = self.session.connection()
        conn.execute(text(f"DROP TABLE IF EXISTS {_quote(table_name)}"))
        conn.execute(text(ddl))

        field_list = list(column_map.keys())
        insert_columns = [_quote("source_url")] + [
            _quote(column_map[f]) for f in field_list
        ]
        placeholders = ", ".join(f":p{i}" for i in range(len(insert_columns)))
        insert_sql = (
            f"INSERT INTO {_quote(table_name)} "
            f"({', '.join(insert_columns)}) "
            f"VALUES ({placeholders})"
        )

        payloads = []
        for index, row in enumerate(rows):
            params: dict[str, Any] = {
                "p0": source_urls[index] if index < len(source_urls) else None
            }
            for position, field in enumerate(field_list, start=1):
                params[f"p{position}"] = self._to_sql_value(row.get(field))
            payloads.append(params)

        if payloads:
            conn.execute(text(insert_sql), payloads)
        self.session.commit()

    def _to_sql_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, (int, float, str)):
            text_value = str(value) if isinstance(value, str) else value
            if isinstance(text_value, str) and len(text_value) > MAX_PAYLOAD_CHARS:
                return text_value[:MAX_PAYLOAD_CHARS]
            return text_value
        try:
            return json.dumps(value, ensure_ascii=False)[:MAX_PAYLOAD_CHARS]
        except (TypeError, ValueError):
            return str(value)[:MAX_PAYLOAD_CHARS]

    def _table_size(self, table_name: str) -> int:
        try:
            conn = self.session.connection()
            result = conn.execute(
                text("SELECT SUM(pgsize) FROM dbstat WHERE name = :name"),
                {"name": table_name},
            ).scalar()
            if result:
                return int(result)
        except Exception:  # noqa: BLE001 - dbstat 扩展未必可用，退化为近似估算
            pass
        return 0

    # ------------------------------------------------------------------ #
    # 读取与清理
    # ------------------------------------------------------------------ #

    def read_dataset(
        self, dataset_id: int, limit: int = 50, offset: int = 0
    ) -> dict:
        """读取数据集内容。"""
        dataset = self.session.get(Dataset, dataset_id)
        if dataset is None:
            raise ValueError(f"数据集不存在: {dataset_id}")

        table_name = dataset.table_name or table_name_for(dataset_id)
        inspector = inspect(self.session.connection())
        if not inspector.has_table(table_name):
            return {
                "dataset_id": dataset_id,
                "columns": [],
                "rows": [],
                "total": 0,
                "missing_table": True,
            }

        conn = self.session.connection()
        columns = [c["name"] for c in inspector.get_columns(table_name)]
        rows = conn.execute(
            text(
                f"SELECT * FROM {_quote(table_name)} "
                f"ORDER BY id LIMIT :limit OFFSET :offset"
            ),
            {"limit": limit, "offset": offset},
        ).mappings().all()

        return {
            "dataset": dataset.to_dict(),
            "dataset_id": dataset_id,
            "name": dataset.name,
            "columns": columns,
            "rows": [dict(r) for r in rows],
            "total": dataset.row_count,
            "limit": limit,
            "offset": offset,
        }

    def drop_dataset(self, dataset_id: int) -> bool:
        """删除数据集及其物理表。"""
        dataset = self.session.get(Dataset, dataset_id)
        if dataset is None:
            return False

        table_name = dataset.table_name or table_name_for(dataset_id)
        try:
            conn = self.session.connection()
            conn.execute(text(f"DROP TABLE IF EXISTS {_quote(table_name)}"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("删除物理表失败 %s: %s", table_name, exc)

        self.session.delete(dataset)
        self.session.commit()
        return True

    # ------------------------------------------------------------------ #
    # 辅助
    # ------------------------------------------------------------------ #

    @staticmethod
    def _default_name(job: CollectJob) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"collect_job_{job.id}_{stamp}"

    def _profile_id_for_plan(self, plan_id: int) -> Optional[int]:
        from api.models import CollectPlan

        plan = self.session.get(CollectPlan, plan_id)
        return plan.profile_id if plan else None

    def _load_profile(self, profile_id: Optional[int]) -> Optional[dict]:
        if not profile_id:
            return None
        profile = self.session.get(SiteProfile, profile_id)
        return profile.to_dict() if profile else None

    @staticmethod
    def _compute_statistics(
        rows: list[dict], schema_types: dict[str, str], pii_policy: dict[str, str]
    ) -> dict:
        total = max(1, len(rows))
        fields: dict[str, dict] = {}
        for field, field_type in schema_types.items():
            values = [r.get(field) for r in rows]
            present = [v for v in values if v not in (None, "")]
            entry: dict[str, Any] = {
                "type": field_type,
                "coverage": round(len(present) / total, 4),
                "null_count": total - len(present),
            }
            if field in pii_policy:
                entry["pii_action"] = pii_policy[field]
            numeric = [
                float(v)
                for v in present
                if isinstance(v, (int, float)) or _is_numeric(v)
            ]
            if numeric:
                entry["min"] = min(numeric)
                entry["max"] = max(numeric)
            fields[field] = entry

        return {
            "row_count": len(rows),
            "field_count": len(schema_types),
            "fields": fields,
            "pii_fields": sorted(pii_policy),
        }


def _is_numeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
