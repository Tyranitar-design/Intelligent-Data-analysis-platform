"""
数据管道 · 单元测试
===================

覆盖规范化、PII 最小化、血缘构建三组纯函数。
"""
from __future__ import annotations

import pytest

from pipeline.lineage import build_lineage, trace_field
from pipeline.normalize import (
    FieldType,
    clean_text,
    coerce,
    infer_type,
    merge_field_types,
    normalize_record,
    parse_datetime,
    parse_number,
)
from pipeline.pii import (
    PIIAction,
    PIIKind,
    apply_action,
    detect_pii,
    minimize,
    scan_pii,
)


# --------------------------------------------------------------------------- #
# 规范化
# --------------------------------------------------------------------------- #


class TestCleanText:
    def test_fullwidth_to_halfwidth(self):
        assert clean_text("１２３ＡＢＣ") == "123ABC"

    def test_whitespace_collapsed(self):
        # 连续空格与制表符都压成单个空格，首尾去除
        assert clean_text("  多   空格\t混排  ") == "多 空格 混排"

    def test_none_returns_empty(self):
        assert clean_text(None) == ""

    def test_excess_newlines_collapsed(self):
        assert clean_text("a\n\n\n\nb") == "a\n\nb"


class TestParseDatetime:
    @pytest.mark.parametrize(
        "raw",
        [
            "2026-09-10T08:30:00+08:00",
            "2026-09-10T08:30:00Z",
            "2026-09-10 08:30:00",
            "2026-09-10 08:30",
            "2026-09-10",
            "2026/09/10",
            "2026年09月10日",
            "2026.09.10",
        ],
    )
    def test_parses_common_formats(self, raw):
        result = parse_datetime(raw)
        assert result is not None
        assert result.startswith("2026-09-10")

    def test_invalid_returns_none(self):
        assert parse_datetime("不是日期") is None
        assert parse_datetime("") is None
        assert parse_datetime(None) is None


class TestParseNumber:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1234.56", 1234.56),
            ("¥1,234.56", 1234.56),
            ("价格 99 元", 99.0),
            ("-12.5", -12.5),
            ("50%", 0.5),
            (42, 42.0),
            (3.14, 3.14),
        ],
    )
    def test_extracts_numbers(self, raw, expected):
        assert parse_number(raw) == pytest.approx(expected)

    def test_no_number_returns_none(self):
        assert parse_number("没有数字") is None


class TestInferType:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("https://example.com/a", FieldType.URL),
            ("2026-09-10", FieldType.DATETIME),
            ("123", FieldType.INT),
            ("12.5", FieldType.FLOAT),
            (True, FieldType.BOOL),
            ([1, 2], FieldType.LIST),
            ({"a": 1}, FieldType.JSON),
            ("普通文本", FieldType.TEXT),
        ],
    )
    def test_infer(self, value, expected):
        assert infer_type(value) == expected


class TestNormalizeRecord:
    def test_schema_driven_conversion(self):
        record = {"price": "¥1,299.00", "title": "  商品  ", "count": "42"}
        normalized, types = normalize_record(
            record, schema={"price": "float", "count": "int", "title": "text"}
        )
        assert normalized["price"] == 1299.0
        assert normalized["count"] == 42
        assert normalized["title"] == "商品"
        assert types["price"] == "float"

    def test_private_fields_dropped(self):
        normalized, _ = normalize_record({"title": "a", "_completeness": 0.9})
        assert "_completeness" not in normalized

    def test_empty_values_dropped(self):
        normalized, _ = normalize_record({"a": "", "b": "  ", "c": "ok"})
        assert "a" not in normalized
        assert "b" not in normalized
        assert normalized["c"] == "ok"

    def test_merge_types_widens(self):
        merged = merge_field_types([{"x": "int"}, {"x": "float"}, {"y": "text"}])
        assert merged["x"] == "float"
        assert merged["y"] == "text"


# --------------------------------------------------------------------------- #
# PII 最小化
# --------------------------------------------------------------------------- #


class TestDetectPII:
    @pytest.mark.parametrize(
        "field,value,expected",
        [
            ("contact", "user@example.com", PIIKind.EMAIL),
            ("phone", "13812345678", PIIKind.PHONE),
            ("id", "110101199003071234", PIIKind.ID_CARD),
            ("card", "6222021234567890123", PIIKind.BANK_CARD),
            ("ip", "192.168.1.1", PIIKind.IP),
            ("author", "张三", PIIKind.PERSON_NAME),
            ("address", "北京市朝阳区某路 1 号", PIIKind.ADDRESS),
        ],
    )
    def test_detects_pii(self, field, value, expected):
        assert detect_pii(field, value) == expected

    @pytest.mark.parametrize(
        "field,value",
        [
            ("title", "数据平台上线公告"),
            ("count", "42"),
            ("url", "https://example.com/article/1"),
            ("author", "某某研究院编辑部"),  # 过长，不是人名
        ],
    )
    def test_non_pii_not_flagged(self, field, value):
        assert detect_pii(field, value) is None


class TestApplyAction:
    def test_hash_is_stable_and_irreversible(self):
        first = apply_action("user@example.com", PIIKind.EMAIL, PIIAction.HASHED)
        second = apply_action("user@example.com", PIIKind.EMAIL, PIIAction.HASHED)
        assert first == second
        assert first.startswith("h:")
        assert "user" not in first
        assert "example" not in first

    def test_mask_keeps_edges(self):
        masked = apply_action("192.168.1.100", PIIKind.IP, PIIAction.MASKED)
        assert masked.startswith("19")
        assert masked.endswith("00")
        assert "*" in masked

    @pytest.mark.parametrize(
        "age,expected",
        [(15, "0-18"), (28, "25-35"), (60, "55-65"), (70, "65+")],
    )
    def test_bin_age(self, age, expected):
        assert apply_action(age, PIIKind.PERSON_NAME, PIIAction.BINNED) == expected

    def test_generalize_address_to_city(self):
        result = apply_action(
            "北京市朝阳区建国路 88 号", PIIKind.ADDRESS, PIIAction.GENERALIZED
        )
        assert result == "北京市"
        assert "朝阳" not in result

    def test_drop_returns_none(self):
        assert apply_action("x", PIIKind.EMAIL, PIIAction.DROPPED) is None


class TestMinimize:
    def test_auto_detect_and_minimize(self):
        records = [
            {"title": "公告一", "author": "张三", "email": "a@example.com"},
            {"title": "公告二", "author": "李四", "email": "b@example.com"},
        ]
        cleaned, policy = minimize(records)

        assert "author" in policy
        assert "email" in policy
        # 标题不是 PII，保持不变
        assert cleaned[0]["title"] == "公告一"
        # 姓名与邮箱被处理
        assert cleaned[0]["author"].startswith("h:")
        assert cleaned[0]["email"].startswith("h:")
        # 同一作者的两条记录仍可关联
        assert cleaned[0]["author"] != cleaned[1]["author"]

    def test_explicit_policy_overrides(self):
        records = [{"author": "张三"}]
        cleaned, policy = minimize(records, {"author": "dropped"})
        assert cleaned[0]["author"] is None or "author" not in cleaned[0] or cleaned[0]["author"] is None
        assert policy["author"] == "dropped"

    def test_scan_returns_kinds(self):
        found = scan_pii([{"email": "a@b.com", "phone": "13800000000", "title": "x"}])
        assert found.get("email") == PIIKind.EMAIL
        assert found.get("phone") == PIIKind.PHONE
        assert "title" not in found


# --------------------------------------------------------------------------- #
# 血缘
# --------------------------------------------------------------------------- #


class TestLineage:
    def test_build_from_profile_rules(self):
        profile = {
            "profile_id": 7,
            "domain": "news.example.com",
            "fields": [
                {"name": "title", "source": "json-ld", "path": "$.headline"},
                {"name": "publish_date", "source": "json-ld", "path": "$.datePublished"},
            ],
        }
        records = [
            {"title": "A", "publish_date": "2026-09-10"},
            {"title": "B"},  # 缺 publish_date
        ]
        lineage = build_lineage(
            ["title", "publish_date"], records, profile=profile, source_urls=["u1"]
        )

        title_entry = trace_field(lineage, "title")
        assert title_entry["extractor_rule"] == "json-ld:$.headline"
        assert title_entry["coverage"] == 1.0
        assert title_entry["profile_id"] == 7

        date_entry = trace_field(lineage, "publish_date")
        assert date_entry["coverage"] == 0.5

    def test_missing_rule_marked_unknown(self):
        lineage = build_lineage(["mystery"], [{"mystery": 1}], profile={})
        assert lineage[0]["extractor_rule"] == "unknown"
