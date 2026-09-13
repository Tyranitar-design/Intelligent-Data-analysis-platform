"""
合规判定引擎 · 四维矩阵
=======================

判定不是一个标签，是四个维度的组合。每一维都输出**取证依据**，
调用方据此可复核判定是否成立。

组合规则（与 docs/REBUILD-SPEC-v3.md 第 4 章 D3 一致）：

    A1~A3 + B1/B2/B3 + C1~C5 + D1        → proceed
    A1~A3 + B4 + C1~C5                   → confirm_required（走授权确认流程）
    A2/A3 + D2                           → proceed，附用途限制条件
    任意 A + D3                          → proceed，附字段级最小化条件
    A4 + 任意 B                          → blocked（技术措施边界）
    B5                                   → blocked（凭证来源）
    D4                                   → blocked（数据属性）

blocked 一律附带替代数据源清单与覆盖率估算，不让任务空转。
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_TTL_HOURS = 72


class VerdictDecision(StrEnum):
    PROCEED = "proceed"
    CONFIRM_REQUIRED = "confirm_required"
    BLOCKED = "blocked"


class AccessDimension(StrEnum):
    A1 = "A1"  # 完全公开
    A2 = "A2"  # 公开但需凭证
    A3 = "A3"  # 部分公开
    A4 = "A4"  # 技术隔离


class AuthorizationDimension(StrEnum):
    B1 = "B1"  # 官方开放
    B2 = "B2"  # 用户自有凭证
    B3 = "B3"  # 用户书面授权
    B4 = "B4"  # 未声明
    B5 = "B5"  # 来源不明


class BehaviorDimension(StrEnum):
    C1 = "C1"  # 遵守 robots
    C2 = "C2"  # 频率自适应
    C3 = "C3"  # 标识身份
    C4 = "C4"  # 尊重退避
    C5 = "C5"  # 缓存与增量


class DataDimension(StrEnum):
    D1 = "D1"  # 公开信息
    D2 = "D2"  # 公开但受版权保护
    D3 = "D3"  # 个人数据
    D4 = "D4"  # 法定禁止


@dataclass
class AlternativeSource:
    """blocked 时的替代数据源。"""

    kind: str
    detail: str
    coverage: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Verdict:
    """判定结果。"""

    decision: VerdictDecision
    dim_access: AccessDimension
    dim_authorization: AuthorizationDimension
    dim_behavior: BehaviorDimension
    dim_data: DataDimension
    reasons: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    alternatives: list[AlternativeSource] = field(default_factory=list)
    coverage_estimate: float = 0.0
    authorization_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    @property
    def proceed(self) -> bool:
        return self.decision is VerdictDecision.PROCEED

    def to_dict(self) -> dict:
        return {
            "decision": str(self.decision),
            "dimensions": {
                "access": str(self.dim_access),
                "authorization": str(self.dim_authorization),
                "behavior": str(self.dim_behavior),
                "data": str(self.dim_data),
            },
            "reasons": list(self.reasons),
            "conditions": list(self.conditions),
            "alternatives": [a.to_dict() for a in self.alternatives],
            "coverage_estimate": self.coverage_estimate,
            "authorization_token": self.authorization_token,
            "token_expires_at": (
                self.token_expires_at.isoformat() if self.token_expires_at else None
            ),
        }


# 从保护状态到可访问性维度的映射
_PROTECTION_TO_ACCESS = {
    "none": AccessDimension.A1,
    "login_wall": AccessDimension.A2,
    "paywall": AccessDimension.A4,
    "captcha": AccessDimension.A4,
    "cloudflare": AccessDimension.A4,
    "forbidden": AccessDimension.A4,
}


class ComplianceEngine:
    """四维矩阵判定引擎。"""

    def __init__(self, token_ttl_hours: int = DEFAULT_TOKEN_TTL_HOURS) -> None:
        self.token_ttl_hours = token_ttl_hours

    # ------------------------------------------------------------------ #
    # 维度判定
    # ------------------------------------------------------------------ #

    def judge_access(self, access_state: dict) -> tuple[AccessDimension, list[str]]:
        """判定可访问性维度。"""
        reasons: list[str] = []
        protection = access_state.get("protection", "none")
        dimension = _PROTECTION_TO_ACCESS.get(protection, AccessDimension.A1)
        reasons.append(f"保护状态 '{protection}' → {dimension}")

        http_status = access_state.get("http_status")
        if http_status:
            reasons.append(f"HTTP {http_status}")

        robots_allowed = access_state.get("robots_allowed")
        if robots_allowed is False:
            reasons.append("robots 规则明确不允许抓取目标路径")

        if dimension is AccessDimension.A1 and access_state.get("requires_credentials"):
            dimension = AccessDimension.A2
            reasons.append("页面要求凭证 → 调整为 A2")

        return dimension, reasons

    def judge_authorization(
        self, declared: Optional[str], has_official_channel: bool
    ) -> tuple[AuthorizationDimension, list[str]]:
        """判定授权基础维度。

        ``declared`` 由调用方提供，取值 ``official`` / ``own_credentials`` /
        ``written_authorization`` / ``unknown``；未提供则视为未声明。
        """
        reasons: list[str] = []

        if declared == "third_party_credentials":
            return AuthorizationDimension.B5, ["凭证来源为第三方获取"]

        if declared == "official" or (declared is None and has_official_channel):
            if has_official_channel:
                reasons.append("站点提供官方开放通道（API / RSS / Sitemap）")
            return AuthorizationDimension.B1, reasons or ["声明为官方开放数据"]

        if declared == "own_credentials":
            return AuthorizationDimension.B2, ["调用方声明持自有有效凭证"]

        if declared == "written_authorization":
            return AuthorizationDimension.B3, ["调用方声明持有书面授权"]

        reasons.append("未声明授权基础 → 走授权确认流程")
        return AuthorizationDimension.B4, reasons

    def judge_behavior(self, behavior_flags: Optional[dict] = None) -> tuple[BehaviorDimension, list[str]]:
        """判定行为合规维度。

        本平台实现固定满足 C1-C5，此处返回其中最弱的一项用于记录，
        并列出实际满足项作为证据。
        """
        flags = behavior_flags or {}
        satisfied: list[str] = []
        mapping = (
            ("c1_robots", BehaviorDimension.C1, "遵守 robots 路径级约束"),
            ("c2_adaptive_rate", BehaviorDimension.C2, "频率自适应与熔断"),
            ("c3_identified", BehaviorDimension.C3, "请求标识自身身份"),
            ("c4_backoff", BehaviorDimension.C4, "尊重 429/503 与 Retry-After"),
            ("c5_cache", BehaviorDimension.C5, "缓存复用与增量优先"),
        )
        weakest = BehaviorDimension.C1
        for key, dimension, text in mapping:
            if flags.get(key, True):
                satisfied.append(text)
            else:
                weakest = dimension
        return weakest, satisfied

    def judge_data(self, signals: Optional[dict] = None) -> tuple[DataDimension, list[str]]:
        """判定数据属性维度。"""
        signals = signals or {}
        reasons: list[str] = []

        if signals.get("prohibited"):
            return DataDimension.D4, ["数据属于法定禁止公开流转范围"]

        if signals.get("personal_data"):
            reasons.append("检测到个人数据特征 → 需字段级最小化")
            return DataDimension.D3, reasons

        if signals.get("copyrighted_content"):
            reasons.append("正文/图片属公开但受版权保护内容")
            return DataDimension.D2, reasons

        reasons.append("公开信息（事实性/统计性/公开披露内容）")
        return DataDimension.D1, reasons

    # ------------------------------------------------------------------ #
    # 组合判定
    # ------------------------------------------------------------------ #

    def evaluate(
        self,
        target_url: str,
        access_state: Optional[dict] = None,
        declared_authorization: Optional[str] = None,
        data_signals: Optional[dict] = None,
        behavior_flags: Optional[dict] = None,
        issue_token: bool = True,
    ) -> Verdict:
        """执行四维判定并给出决策。"""
        access_state = access_state or {}
        has_official = bool(
            access_state.get("sitemaps")
            or access_state.get("feeds")
            or access_state.get("public_api")
        )

        dim_a, reasons_a = self.judge_access(access_state)
        dim_b, reasons_b = self.judge_authorization(declared_authorization, has_official)
        dim_c, reasons_c = self.judge_behavior(behavior_flags)
        dim_d, reasons_d = self.judge_data(data_signals)

        reasons = [*reasons_a, *reasons_b, *reasons_c, *reasons_d]

        verdict = Verdict(
            decision=VerdictDecision.PROCEED,
            dim_access=dim_a,
            dim_authorization=dim_b,
            dim_behavior=dim_c,
            dim_data=dim_d,
            reasons=reasons,
        )

        # --- 硬边界：技术措施 ---
        if dim_a is AccessDimension.A4:
            verdict.decision = VerdictDecision.BLOCKED
            verdict.reasons.append(
                "目标处于技术隔离（验证码/付费墙/访问控制/WAF），"
                "不实现绕过路径"
            )
            verdict.alternatives = self._alternatives_for(target_url, dim_a)
            verdict.coverage_estimate = self._estimate_coverage(verdict.alternatives)
            return verdict

        # --- 硬边界：凭证来源 ---
        if dim_b is AuthorizationDimension.B5:
            verdict.decision = VerdictDecision.BLOCKED
            verdict.reasons.append("凭证来源不明或由第三方获取，不使用该凭证")
            verdict.alternatives = self._alternatives_for(target_url, dim_a)
            verdict.coverage_estimate = self._estimate_coverage(verdict.alternatives)
            return verdict

        # --- 硬边界：数据属性 ---
        if dim_d is DataDimension.D4:
            verdict.decision = VerdictDecision.BLOCKED
            verdict.reasons.append("数据属性处于法定禁止流转范围")
            verdict.alternatives = self._alternatives_for(target_url, dim_a)
            verdict.coverage_estimate = self._estimate_coverage(verdict.alternatives)
            return verdict

        # --- 授权未声明：不阻断任务，走确认流程 ---
        if dim_b is AuthorizationDimension.B4:
            verdict.decision = VerdictDecision.CONFIRM_REQUIRED
            verdict.conditions = self._conditions_for(dim_a, dim_d)
            if issue_token:
                verdict.authorization_token = self._mint_token(target_url)
                verdict.token_expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=self.token_ttl_hours
                )
            return verdict

        # --- 通过，但按数据属性附加条件 ---
        if dim_d is DataDimension.D3:
            verdict.conditions.append(
                "对个人数据字段做最小化处理：直接标识符哈希化，准标识符分箱泛化"
            )
        if dim_d is DataDimension.D2:
            verdict.conditions.append(
                "受版权保护内容限定内部检索与不公开分析用途，控制全文留存范围"
            )
        if dim_a is AccessDimension.A2:
            verdict.conditions.append("仅使用调用方自有凭证，凭证不入日志、不入版本库")

        return verdict

    # ------------------------------------------------------------------ #
    # 辅助
    # ------------------------------------------------------------------ #

    def _conditions_for(
        self, dim_a: AccessDimension, dim_d: DataDimension
    ) -> list[str]:
        """confirm_required 时的解锁条件。"""
        conditions = [
            "声明授权基础：official / own_credentials / written_authorization 之一",
            "提供 operator 标识与授权依据说明，用于审计留痕",
        ]
        if dim_a is AccessDimension.A2:
            conditions.append("如使用账号或 API Key，须为该账号的合法持有者")
        if dim_a is AccessDimension.A3:
            conditions.append("受限部分仅采集公开可见字段，不触碰需更高权限的内容")
        if dim_d is DataDimension.D3:
            conditions.append("涉及个人数据时声明用途与保留期限")
        conditions.append("补齐声明后携带 authorization_token 重放采集请求")
        return conditions

    def _alternatives_for(
        self, target_url: str, dim_a: AccessDimension
    ) -> list[AlternativeSource]:
        """blocked 时的替代数据源。"""
        return [
            AlternativeSource(
                kind="official_api",
                detail="查询目标站点是否提供官方 API / 开放数据接口",
                coverage=0.6,
            ),
            AlternativeSource(
                kind="feeds_and_sitemap",
                detail="使用 RSS / Atom / Sitemap 等站点主动公开的结构化通道",
                coverage=0.4,
            ),
            AlternativeSource(
                kind="open_dataset",
                detail="检索政府开放数据平台、学术数据集、行业公开统计",
                coverage=0.3,
            ),
            AlternativeSource(
                kind="web_archive",
                detail="通过公开网络存档（Wayback Machine / Common Crawl）回溯历史内容",
                coverage=0.35,
            ),
            AlternativeSource(
                kind="authorized_partner",
                detail="与站点方建立授权合作或采购商用数据服务",
                coverage=0.9,
            ),
        ]

    def _estimate_coverage(self, alternatives: list[AlternativeSource]) -> float:
        """替代路径的覆盖率估算（去重后的乐观上界）。"""
        if not alternatives:
            return 0.0
        remaining = 1.0
        for alt in alternatives:
            remaining *= 1.0 - max(0.0, min(1.0, alt.coverage))
        return round(1.0 - remaining, 3)

    def _mint_token(self, target_url: str) -> str:
        """签发解锁令牌。"""
        raw = f"{target_url}|{datetime.now(timezone.utc).isoformat()}|{secrets.token_hex(8)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:48]

    def verify_token(
        self,
        token: str,
        expected_token: Optional[str],
        expires_at: Optional[datetime],
    ) -> tuple[bool, str]:
        """校验解锁令牌是否有效。"""
        if not expected_token:
            return False, "该判定无需令牌"
        if token != expected_token:
            return False, "令牌不匹配"
        if expires_at is not None:
            now = datetime.now(timezone.utc)
            exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
            if now > exp:
                return False, "令牌已过期"
        return True, "ok"
