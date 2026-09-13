"""
三级去重
========

| 级 | 手段 | 用途 |
|---|---|---|
| 1 主键级 | URL 归一化指纹（``item_key``） | 这条采过没 |
| 2 内容级 | 正文 SimHash（64 位，汉明距离 ≤ 阈值视为同内容） | 这条内容变过没 |
| 3 语义级 | 向量相似度 | 跨源是不是同一条（接口预留，后期启用） |

第 1 级决定"要不要写"，第 2 级决定"要不要更新内容"，第 3 级决定"要不要合并"。
三者职责不重叠，混用会导致既漏又重。
"""
from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import CollectItem

logger = logging.getLogger(__name__)

# 归一化时剔除的跟踪参数
TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "spm",
        "from",
        "share_token",
        "ref",
        "fbclid",
        "gclid",
    }
)

DEFAULT_HAMMING_THRESHOLD = 3
SIMHASH_CANDIDATE_LIMIT = 200


# --------------------------------------------------------------------------- #
# 纯函数
# --------------------------------------------------------------------------- #


def normalize_url(url: str) -> str:
    """URL 归一化：去 fragment、剔跟踪参数、统一小写主机、去尾斜杠。"""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return url.strip()

    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    query_pairs.sort()

    path = parsed.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    return urlunparse(
        (
            parsed.scheme.lower() or "https",
            parsed.netloc.lower(),
            path,
            "",
            urlencode(query_pairs),
            "",
        )
    )


def make_item_key(url: str) -> str:
    """第 1 级主键：归一化 URL 的 sha1 前 32 位。"""
    return hashlib.sha1(normalize_url(url).encode("utf-8")).hexdigest()[:32]


def to_signed64(value: int) -> int:
    """把无符号 64 位整数转成 SQLite 可存的有符号形式。"""
    value &= (1 << 64) - 1
    if value >= (1 << 63):
        value -= 1 << 64
    return value


def to_unsigned64(value: int) -> int:
    """还原为无符号 64 位。"""
    return value & ((1 << 64) - 1)


def _hash64(token: str) -> int:
    digest = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def tokenize(text: str) -> dict[str, int]:
    """中英混排的轻量分词：英文按词、中文按 bigram。

    不引入分词依赖，对 SimHash 这类"近似指纹"场景足够。
    """
    tokens: Counter[str] = Counter()
    lowered = text.lower()

    for word in re.findall(r"[a-z]{2,}", lowered):
        tokens[word] += 1

    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(run) == 1:
            tokens[run] += 1
            continue
        for i in range(len(run) - 1):
            tokens[run[i : i + 2]] += 1

    return dict(tokens)


def simhash64(text: str) -> int:
    """计算正文的 64 位 SimHash。空文本返回 0。"""
    tokens = tokenize(text or "")
    if not tokens:
        return 0

    vector = [0] * 64
    for token, weight in tokens.items():
        hashed = _hash64(token)
        for bit in range(64):
            vector[bit] += weight if (hashed >> bit) & 1 else -weight

    signature = 0
    for bit in range(64):
        if vector[bit] > 0:
            signature |= 1 << bit
    return signature


def hamming_distance(a: int, b: int) -> int:
    """两个 SimHash 的汉明距离。"""
    return bin((a ^ b) & ((1 << 64) - 1)).count("1")


@dataclass
class DedupVerdict:
    """一次去重判定的结果。"""

    is_duplicate: bool
    reason: str
    existing: Optional[CollectItem] = None
    content_changed: bool = False

    def to_dict(self) -> dict:
        return {
            "is_duplicate": self.is_duplicate,
            "reason": self.reason,
            "existing_id": self.existing.id if self.existing else None,
            "content_changed": self.content_changed,
        }


class DedupStore:
    """基于数据库的三级去重。"""

    def __init__(
        self,
        session: Session,
        hamming_threshold: int = DEFAULT_HAMMING_THRESHOLD,
    ) -> None:
        self.session = session
        self.hamming_threshold = hamming_threshold

    # ------------------------------------------------------------------ #
    # 第 1 级：主键
    # ------------------------------------------------------------------ #

    def find_by_key(self, item_key: str) -> Optional[CollectItem]:
        stmt = select(CollectItem).where(CollectItem.item_key == item_key).limit(1)
        return self.session.execute(stmt).scalars().first()

    # ------------------------------------------------------------------ #
    # 第 2 级：内容指纹
    # ------------------------------------------------------------------ #

    def find_by_content(
        self, simhash: int, limit: int = SIMHASH_CANDIDATE_LIMIT
    ) -> Optional[CollectItem]:
        """按内容指纹查找已存条目。

        当前实现取最近 N 条候选逐一比对汉明距离。这是**近似**做法：
        SimHash 的精确近邻查询需要 LSH 分桶索引（按指纹分块建索引），
        待条目规模上到十万级再补，现在做属于过早优化。
        """
        if not simhash:
            return None

        stmt = (
            select(CollectItem)
            .where(CollectItem.content_simhash.isnot(None))
            .order_by(CollectItem.id.desc())
            .limit(limit)
        )
        target = to_unsigned64(simhash)
        for candidate in self.session.execute(stmt).scalars():
            if (
                hamming_distance(target, to_unsigned64(candidate.content_simhash))
                <= self.hamming_threshold
            ):
                return candidate
        return None

    # ------------------------------------------------------------------ #
    # 综合判定
    # ------------------------------------------------------------------ #

    def check(
        self, url: str, text: str = "", *, check_content: bool = True
    ) -> DedupVerdict:
        """对一条待写入的数据做去重判定。"""
        item_key = make_item_key(url)
        existing = self.find_by_key(item_key)

        if existing is None:
            return DedupVerdict(is_duplicate=False, reason="new_item")

        if not check_content or not text:
            return DedupVerdict(
                is_duplicate=True, reason="key_hit", existing=existing
            )

        new_hash = simhash64(text)
        old_hash = to_unsigned64(existing.content_simhash or 0)
        distance = hamming_distance(new_hash, old_hash)

        if distance <= self.hamming_threshold:
            return DedupVerdict(
                is_duplicate=True, reason="content_unchanged", existing=existing
            )

        return DedupVerdict(
            is_duplicate=False,
            reason="content_changed",
            existing=existing,
            content_changed=True,
        )

    # ------------------------------------------------------------------ #
    # 观测
    # ------------------------------------------------------------------ #

    def stats(self, job_id: Optional[int] = None) -> dict:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(CollectItem)
        if job_id is not None:
            stmt = stmt.where(CollectItem.job_id == job_id)
        total = self.session.execute(stmt).scalar_one()
        return {"total_items": total, "hamming_threshold": self.hamming_threshold}
