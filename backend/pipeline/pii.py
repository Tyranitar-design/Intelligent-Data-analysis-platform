"""
PII 字段级最小化
================

默认动作是**字段级处理**，不是整体弃采。

这条原则决定了平台的实际可用性：真实数据集里个人数据往往只占少数字段，
因为一个作者名就整包丢弃，损失的是整条数据链的价值。

处理策略：

| 策略 | 适用 | 做法 |
|---|---|---|
| hashed | 直接标识符（邮箱、手机、身份证、银行卡） | SHA-256 前 16 位，保留可关联性且不可逆 |
| masked | 需要保留格式线索的字段（IP、部分账号） | 保留首尾，中间打码 |
| binned | 准标识符中的数值（年龄） | 区间分箱 |
| generalized | 准标识符中的位置（精确地址） | 抽取到城市粒度 |
| dropped | 明确不应留存 | 直接不落库 |
"""
from __future__ import annotations

import hashlib
import logging
import re
from enum import StrEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PIIKind(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    ID_CARD = "id_card"
    BANK_CARD = "bank_card"
    PERSON_NAME = "person_name"
    ADDRESS = "address"
    IP = "ip"


class PIIAction(StrEnum):
    HASHED = "hashed"
    MASKED = "masked"
    BINNED = "binned"
    GENERALIZED = "generalized"
    DROPPED = "dropped"


_RE_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
_RE_PHONE_CN = re.compile(r"^1[3-9]\d{9}$")
_RE_ID_CARD = re.compile(r"^\d{17}[\dXx]$")
_RE_BANK_CARD = re.compile(r"^\d{16,19}$")
_RE_IPV4 = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
_RE_CN_NAME = re.compile(r"^[\u4e00-\u9fff]{2,4}$")

# 字段名提示（用于在没有明显格式时辅助判断）
_FIELD_HINTS: dict[str, PIIKind] = {
    "email": PIIKind.EMAIL,
    "mail": PIIKind.EMAIL,
    "邮箱": PIIKind.EMAIL,
    "phone": PIIKind.PHONE,
    "mobile": PIIKind.PHONE,
    "tel": PIIKind.PHONE,
    "手机": PIIKind.PHONE,
    "电话": PIIKind.PHONE,
    "id_card": PIIKind.ID_CARD,
    "idcard": PIIKind.ID_CARD,
    "身份证": PIIKind.ID_CARD,
    "bank": PIIKind.BANK_CARD,
    "card_no": PIIKind.BANK_CARD,
    "银行卡": PIIKind.BANK_CARD,
    "name": PIIKind.PERSON_NAME,
    "author": PIIKind.PERSON_NAME,
    "姓名": PIIKind.PERSON_NAME,
    "作者": PIIKind.PERSON_NAME,
    "address": PIIKind.ADDRESS,
    "addr": PIIKind.ADDRESS,
    "地址": PIIKind.ADDRESS,
    "ip": PIIKind.IP,
    "ip_addr": PIIKind.IP,
}

# 默认策略
DEFAULT_POLICY: dict[PIIKind, PIIAction] = {
    PIIKind.EMAIL: PIIAction.HASHED,
    PIIKind.PHONE: PIIAction.HASHED,
    PIIKind.ID_CARD: PIIAction.HASHED,
    PIIKind.BANK_CARD: PIIAction.HASHED,
    PIIKind.PERSON_NAME: PIIAction.HASHED,
    PIIKind.ADDRESS: PIIAction.GENERALIZED,
    PIIKind.IP: PIIAction.MASKED,
}


def hash_value(value: str, salt: str = "webinsight") -> str:
    """不可逆哈希（保留跨记录关联能力）。"""
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()
    return f"h:{digest[:16]}"


def detect_pii(field_name: str, value: Any) -> Optional[PIIKind]:
    """判断某个字段值是否属于个人数据。

    先看格式（强证据），再看字段名（弱证据）。两者都没有则判定为非个人数据
    —— 不做过度推断，把一切当个人数据会让平台失去可用性。
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if _RE_EMAIL.match(text):
        return PIIKind.EMAIL
    if _RE_PHONE_CN.match(text):
        return PIIKind.PHONE
    if _RE_ID_CARD.match(text):
        return PIIKind.ID_CARD
    if _RE_BANK_CARD.match(text):
        return PIIKind.BANK_CARD
    if _RE_IPV4.match(text):
        return PIIKind.IP

    lowered = (field_name or "").lower()
    for hint, kind in _FIELD_HINTS.items():
        if hint not in lowered:
            continue
        if kind is PIIKind.PERSON_NAME:
            # 姓名要求"短且全中文"，避免把标题误判为姓名
            if len(text) <= 4 and _RE_CN_NAME.match(text):
                return PIIKind.PERSON_NAME
            continue
        if kind is PIIKind.ADDRESS and len(text) >= 6:
            return PIIKind.ADDRESS
        if kind in (PIIKind.EMAIL, PIIKind.PHONE, PIIKind.ID_CARD, PIIKind.BANK_CARD):
            continue  # 这些类型必须有格式证据
        return kind

    return None


def apply_action(value: Any, kind: PIIKind, action: PIIAction) -> Any:
    """对单个值执行最小化处理。"""
    if value is None:
        return None

    text = str(value)

    if action is PIIAction.DROPPED:
        return None

    if action is PIIAction.HASHED:
        return hash_value(text)

    if action is PIIAction.MASKED:
        if len(text) <= 4:
            return "*" * len(text)
        return f"{text[:2]}{'*' * (len(text) - 4)}{text[-2:]}"

    if action is PIIAction.BINNED:
        try:
            age = int(float(text))
        except (TypeError, ValueError):
            return "unknown"
        for low, high in ((0, 18), (18, 25), (25, 35), (35, 45), (45, 55), (55, 65)):
            if low <= age < high:
                return f"{low}-{high}"
        return "65+"

    if action is PIIAction.GENERALIZED:
        # 地址泛化到城市粒度：截取到"市"或前 6 个字符
        for marker in ("市", "省", "区", "县"):
            index = text.find(marker)
            if 0 <= index:
                return text[: index + 1]
        return text[:6]

    return text


def scan_pii(records: list[dict]) -> dict[str, PIIKind]:
    """扫描一批记录，找出含个人数据的字段。

    返回 ``{field_name: PIIKind}``；命中任一记录即认定该字段需要处理。
    """
    found: dict[str, PIIKind] = {}
    for record in records[:200]:  # 采样上限，避免大集扫描过慢
        if not isinstance(record, dict):
            continue
        for field, value in record.items():
            if field in found:
                continue
            kind = detect_pii(field, value)
            if kind is not None:
                found[field] = kind
    return found


def minimize(
    records: list[dict],
    policy: Optional[dict[str, str]] = None,
    *,
    auto_detect: bool = True,
) -> tuple[list[dict], dict[str, str]]:
    """对一批记录执行 PII 最小化。

    ``policy`` 形如 ``{"email": "hashed", "age": "binned"}``；
    未指定的字段在 ``auto_detect`` 为真时按默认策略处理。

    返回 ``(处理后记录, 实际应用的策略表)``。
    """
    policy = policy or {}
    applied: dict[str, str] = {}

    if not records:
        return records, applied

    detected = scan_pii(records) if auto_detect else {}
    # 显式声明的字段也要纳入处理范围
    targets: dict[str, PIIKind] = dict(detected)
    for field in policy:
        targets.setdefault(field, detected.get(field) or PIIKind.PERSON_NAME)

    if not targets:
        return records, applied

    out: list[dict] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        cleaned = dict(record)
        for field, kind in targets.items():
            if field not in cleaned:
                continue
            action_name = policy.get(field)
            try:
                action = (
                    PIIAction(action_name) if action_name else DEFAULT_POLICY[kind]
                )
            except (ValueError, KeyError):
                action = PIIAction.HASHED
            cleaned[field] = apply_action(cleaned[field], kind, action)
            applied[field] = str(action)
        out.append(cleaned)

    logger.info("PII 最小化应用于 %d 个字段: %s", len(applied), list(applied))
    return out, applied
