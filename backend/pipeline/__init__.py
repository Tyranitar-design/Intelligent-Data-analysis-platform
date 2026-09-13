"""
数据管道层
==========

把采集结果变成可分析资产：

    collect_items (原始 payload)
        → normalize    统一八种类型（text/int/float/bool/datetime/url/json/list）
        → pii          PII 字段级最小化（哈希 / 打码 / 分箱 / 泛化 / 丢弃）
        → storage      物化成真实表 + Dataset 记录
        → lineage      字段级血缘（可回溯到提取规则与站点画像）

模块划分：

- ``normalize``  类型推断、清洗、转换
- ``pii``        PII 检测与最小化策略
- ``lineage``    字段级血缘构建与回溯
- ``storage``    数据集物化、读取、清理
"""

from pipeline.lineage import build_lineage, format_lineage, trace_field
from pipeline.normalize import (
    FieldType,
    coerce,
    infer_type,
    merge_field_types,
    normalize_record,
    parse_datetime,
    parse_number,
)
from pipeline.pii import (
    DEFAULT_POLICY,
    PIIAction,
    PIIKind,
    apply_action,
    detect_pii,
    minimize,
    scan_pii,
)
from pipeline.storage import DatasetMaterializer, table_name_for

__all__ = [
    "FieldType",
    "coerce",
    "infer_type",
    "merge_field_types",
    "normalize_record",
    "parse_datetime",
    "parse_number",
    "DEFAULT_POLICY",
    "PIIAction",
    "PIIKind",
    "apply_action",
    "detect_pii",
    "minimize",
    "scan_pii",
    "build_lineage",
    "format_lineage",
    "trace_field",
    "DatasetMaterializer",
    "table_name_for",
]
