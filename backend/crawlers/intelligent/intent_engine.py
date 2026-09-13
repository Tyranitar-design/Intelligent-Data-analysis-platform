# -*- coding: utf-8 -*-
"""
意图引擎 - 智能爬虫系统 v2.0

负责 URL 探测和意图识别，动态选择最佳爬取策略。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .models import IntentType, ProbeResult
from .observ_logger import ObservLogger


class RuleType(Enum):
    """规则类型"""

    CONTENT_TYPE = "content_type"
    URL_PATTERN = "url_pattern"
    RESPONSE_HEADER = "response_header"
    HTML_FEATURE = "html_feature"
    RESPONSE_STATUS = "response_status"


@dataclass
class IntentRule:
    """意图规则"""

    name: str
    rule_type: RuleType
    intent: IntentType
    pattern: str
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches(self, probe: ProbeResult) -> bool:
        """检查规则是否匹配"""
        if not self.enabled:
            return False

        try:
            if self.rule_type == RuleType.CONTENT_TYPE:
                return self._match_content_type(probe)
            elif self.rule_type == RuleType.URL_PATTERN:
                return self._match_url_pattern(probe)
            elif self.rule_type == RuleType.RESPONSE_HEADER:
                return self._match_response_header(probe)
            elif self.rule_type == RuleType.HTML_FEATURE:
                return self._match_html_feature(probe)
            elif self.rule_type == RuleType.RESPONSE_STATUS:
                return self._match_response_status(probe)
        except Exception:
            return False
        return False

    def _match_content_type(self, probe: ProbeResult) -> bool:
        """匹配内容类型"""
        pattern = re.compile(self.pattern, re.IGNORECASE)
        return bool(pattern.search(probe.content_type))

    def _match_url_pattern(self, probe: ProbeResult) -> bool:
        """匹配 URL 模式"""
        pattern = re.compile(self.pattern, re.IGNORECASE)
        return bool(pattern.search(probe.url))

    def _match_response_header(self, probe: ProbeResult) -> bool:
        """匹配响应头"""
        header_name = self.metadata.get("header_name", "")
        pattern = re.compile(self.pattern, re.IGNORECASE)
        header_value = probe.headers.get(header_name, "")
        return bool(pattern.search(header_value))

    def _match_html_feature(self, probe: ProbeResult) -> bool:
        """匹配 HTML 特征"""
        if not probe.is_html:
            return False
        pattern = re.compile(self.pattern, re.IGNORECASE)
        return bool(pattern.search(probe.content_type))

    def _match_response_status(self, probe: ProbeResult) -> bool:
        """匹配响应状态"""
        return str(probe.status_code) == self.pattern


@dataclass
class IntentRuleStats:
    """规则统计"""

    rule_name: str
    hit_count: int = 0
    miss_count: int = 0

    @property
    def total(self) -> int:
        return self.hit_count + self.miss_count

    @property
    def hit_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.hit_count / self.total


class IntentEngine:
    """意图引擎

    负责 URL 探测和意图识别。
    """

    DEFAULT_RULES: List[IntentRule] = [
        IntentRule(
            name="api_json",
            rule_type=RuleType.CONTENT_TYPE,
            intent=IntentType.API_DATA,
            pattern=r"application/json",
            priority=100,
        ),
        IntentRule(
            name="api_xml",
            rule_type=RuleType.CONTENT_TYPE,
            intent=IntentType.API_DATA,
            pattern=r"application/xml|text/xml",
            priority=90,
        ),
        IntentRule(
            name="static_html",
            rule_type=RuleType.CONTENT_TYPE,
            intent=IntentType.STATIC_CONTENT,
            pattern=r"text/html",
            priority=50,
        ),
        IntentRule(
            name="protected_cloudflare",
            rule_type=RuleType.RESPONSE_HEADER,
            intent=IntentType.PROTECTED_CONTENT,
            pattern=r"cloudflare|cf-ray",
            priority=80,
            metadata={"header_name": "server"},
        ),
        IntentRule(
            name="protected_turnstile",
            rule_type=RuleType.HTML_FEATURE,
            intent=IntentType.PROTECTED_CONTENT,
            pattern=r"turnstile|challenge",
            priority=85,
        ),
        IntentRule(
            name="auth_cookie",
            rule_type=RuleType.RESPONSE_HEADER,
            intent=IntentType.AUTHENTICATED,
            pattern=r"login|signin|auth",
            priority=70,
            metadata={"header_name": "set-cookie"},
        ),
        IntentRule(
            name="pagination_pattern",
            rule_type=RuleType.URL_PATTERN,
            intent=IntentType.PAGINATED,
            pattern=r"page=\d+|p=\d+|offset=\d+",
            priority=60,
        ),
        IntentRule(
            name="stream_chunked",
            rule_type=RuleType.RESPONSE_HEADER,
            intent=IntentType.STREAMING,
            pattern=r"chunked",
            priority=75,
            metadata={"header_name": "transfer-encoding"},
        ),
    ]

    def __init__(
        self,
        rules: Optional[List[IntentRule]] = None,
        logger: Optional[ObservLogger] = None,
    ) -> None:
        self.rules = rules or self.DEFAULT_RULES.copy()
        self.logger = logger or ObservLogger(name="intelligent.intent_engine")
        self._stats: Dict[str, IntentRuleStats] = {
            rule.name: IntentRuleStats(rule_name=rule.name)
            for rule in self.rules
        }

    def add_rule(self, rule: IntentRule) -> None:
        """添加规则"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        self._stats[rule.name] = IntentRuleStats(rule_name=rule.name)

    def remove_rule(self, rule_name: str) -> None:
        """移除规则"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        if rule_name in self._stats:
            del self._stats[rule_name]

    def classify(self, probe: ProbeResult) -> IntentType:
        """对探测结果进行意图分类

        Args:
            probe: URL 探测结果

        Returns:
            识别的意图类型
        """
        matched_rules: List[Tuple[IntentRule, bool]] = []

        for rule in self.rules:
            if rule.matches(probe):
                matched_rules.append((rule, True))
                self._stats[rule.name].hit_count += 1
            else:
                self._stats[rule.name].miss_count += 1

        if matched_rules:
            best_rule = max(matched_rules, key=lambda x: x[0].priority)[0]
            self.logger.debug(
                f"Intent classified: {best_rule.intent.value}",
                rule=best_rule.name,
                priority=best_rule.priority,
            )
            return best_rule.intent

        return IntentType.STATIC_CONTENT

    def load_rules_from_yaml(self, yaml_path: str) -> None:
        """从 YAML 文件加载规则

        Args:
            yaml_path: YAML 文件路径
        """
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        rules_data = data.get("intent_rules", [])
        for rule_data in rules_data:
            rule = IntentRule(
                name=rule_data["name"],
                rule_type=RuleType(rule_data["type"]),
                intent=IntentType(rule_data["intent"]),
                pattern=rule_data["pattern"],
                priority=rule_data.get("priority", 0),
                enabled=rule_data.get("enabled", True),
                metadata=rule_data.get("metadata", {}),
            )
            self.add_rule(rule)

        self.logger.info(f"Loaded {len(rules_data)} rules from YAML")

    def get_stats(self) -> Dict[str, Any]:
        """获取规则统计"""
        return {
            "total_rules": len(self.rules),
            "rules": [
                {
                    "name": stats.rule_name,
                    "hit_count": stats.hit_count,
                    "miss_count": stats.miss_count,
                    "hit_rate": stats.hit_rate,
                }
                for stats in self._stats.values()
            ],
        }

    def reset_stats(self) -> None:
        """重置统计"""
        for stats in self._stats.values():
            stats.hit_count = 0
            stats.miss_count = 0
