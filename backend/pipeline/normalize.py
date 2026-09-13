"""
数据规范化
==========

把采集到的原始 payload 归一成统一类型系统的记录。

统一类型系统：

    text / int / float / bool / datetime / url / json / list

规范化的价值在于"后续不用再猜"——分析层、导出层、检索层都只面对这八种类型，
不必各自处理"价格是 ¥1,234.56 还是 1234.56"这类差异。
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class FieldType(StrEnum):
    """统一字段类型。"""

    TEXT = "text"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    DATETIME = "datetime"
    URL = "url"
    JSON = "json"
    LIST = "list"


# 全角 ASCII（U+FF01–U+FF5E）→ 半角 ASCII（U+0021–U+007E），涵盖数字、字母与标点
_FULLWIDTH_MAP = str.maketrans(
    "".join(chr(0xFF01 + i) for i in range(94)),
    "".join(chr(0x21 + i) for i in range(94)),
)

_RE_NUMERIC = re.compile(r"-?\d+(?:\.\d+)?")
_RE_URL = re.compile(r"^https?://\S+$")
_RE_SPACE = re.compile(r"[ \t\u3000]+")
_RE_MULTI_NEWLINE = re.compile(r"\n{3,}")

_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
    "%Y年%m月%d日 %H:%M",
    "%Y年%m月%d日",
    "%Y.%m.%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
)

_BOOL_TRUE = frozenset({"true", "1", "yes", "y", "是", "有", "真"})
_BOOL_FALSE = frozenset({"false", "0", "no", "n", "否", "无", "假"})


# --------------------------------------------------------------------------- #
# 清洗
# --------------------------------------------------------------------------- #


def clean_text(value: Any) -> str:
    """文本清洗：全角归一、压缩空白、去首尾。"""
    if value is None:
        return ""
    text = str(value).translate(_FULLWIDTH_MAP)
    text = _RE_SPACE.sub(" ", text)
    text = _RE_MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def parse_datetime(value: Any) -> Optional[str]:
    """尽力解析日期时间，返回 ISO 8601（UTC 感知）或 None。

    不猜测无时区的本地时间语义——解析成功即保留，失败就返回 None，
    由调用方决定是丢弃还是保留原文。
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    text = clean_text(value)
    if not text:
        return None

    # 标准库 fromisoformat 覆盖大部分 ISO 变体（含 Z 后缀）
    candidate = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(candidate)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        pass

    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(text, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue

    return None


def parse_number(value: Any) -> Optional[float]:
    """从文本中抽取数值，兼容货币符号、千分位、百分号。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)

    text = clean_text(value)
    if not text:
        return None

    # 千分位逗号会把数字截断（"1,234.56" 只能匹配到 1），先移除
    text = text.replace(",", "")

    match = _RE_NUMERIC.search(text)
    if not match:
        return None

    try:
        number = float(match.group())
    except ValueError:
        return None

    if "%" in text:
        number /= 100.0
    return number


def parse_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = clean_text(value).lower()
    if text in _BOOL_TRUE:
        return True
    if text in _BOOL_FALSE:
        return False
    return None


# --------------------------------------------------------------------------- #
# 类型推断与转换
# --------------------------------------------------------------------------- #


def infer_type(value: Any) -> FieldType:
    """推断值的类型。"""
    if value is None:
        return FieldType.TEXT
    if isinstance(value, bool):
        return FieldType.BOOL
    if isinstance(value, int):
        return FieldType.INT
    if isinstance(value, float):
        return FieldType.FLOAT
    if isinstance(value, (list, tuple, set)):
        return FieldType.LIST
    if isinstance(value, dict):
        return FieldType.JSON

    text = clean_text(value)
    if not text:
        return FieldType.TEXT
    if _RE_URL.match(text):
        return FieldType.URL
    if parse_datetime(text) is not None and re.search(r"\d{4}[-/年.]\d{1,2}", text):
        return FieldType.DATETIME
    if re.fullmatch(r"-?\d+", text):
        return FieldType.INT
    if re.fullmatch(r"-?\d+\.\d+", text):
        return FieldType.FLOAT
    return FieldType.TEXT


def coerce(value: Any, target: FieldType) -> Any:
    """把值转换成目标类型；转换失败时退回清洗后的文本。"""
    if value is None:
        return None

    if target is FieldType.TEXT:
        result = clean_text(value)
        return result or None
    if target is FieldType.INT:
        number = parse_number(value)
        return int(number) if number is not None else clean_text(value)
    if target is FieldType.FLOAT:
        number = parse_number(value)
        return number if number is not None else clean_text(value)
    if target is FieldType.BOOL:
        parsed = parse_bool(value)
        return parsed if parsed is not None else clean_text(value)
    if target is FieldType.DATETIME:
        parsed = parse_datetime(value)
        return parsed if parsed else clean_text(value)
    if target is FieldType.URL:
        text = clean_text(value)
        return text if _RE_URL.match(text) else text
    if target is FieldType.LIST:
        if isinstance(value, (list, tuple, set)):
            return [clean_text(v) for v in value]
        return [clean_text(value)]
    if target is FieldType.JSON:
        return value if isinstance(value, (dict, list)) else {"value": clean_text(value)}
    return clean_text(value)


def normalize_record(
    payload: dict, schema: Optional[dict] = None
) -> tuple[dict, dict[str, str]]:
    """规范化一条记录。

    返回 ``(规范化后的记录, 字段类型表)``。

    传入 ``schema`` 时按声明的类型转换；未传则逐字段推断。
    """
    if not isinstance(payload, dict):
        return {}, {}

    normalized: dict[str, Any] = {}
    types: dict[str, str] = {}
    declared = schema or {}

    for key, value in payload.items():
        if key.startswith("_"):
            continue

        declared_type = declared.get(key)
        if declared_type:
            try:
                field_type = FieldType(declared_type)
            except ValueError:
                field_type = infer_type(value)
        else:
            field_type = infer_type(value)

        converted = coerce(value, field_type)
        if converted is None or converted == "":
            continue

        normalized[key] = converted
        types[key] = str(field_type)

    return normalized, types


def merge_field_types(type_maps: list[dict[str, str]]) -> dict[str, str]:
    """合并多条记录的类型表，冲突时按"更宽"的类型取胜。"""
    width = {
        str(FieldType.TEXT): 5,
        str(FieldType.JSON): 4,
        str(FieldType.LIST): 4,
        str(FieldType.URL): 3,
        str(FieldType.DATETIME): 3,
        str(FieldType.FLOAT): 2,
        str(FieldType.INT): 1,
        str(FieldType.BOOL): 0,
    }
    merged: dict[str, str] = {}
    for mapping in type_maps:
        for key, value in mapping.items():
            current = merged.get(key)
            if current is None or width.get(value, 5) > width.get(current, 0):
                merged[key] = value
    return merged
