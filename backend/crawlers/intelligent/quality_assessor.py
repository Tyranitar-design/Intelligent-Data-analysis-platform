# -*- coding: utf-8 -*-
"""
质量评估器 - 智能爬虫系统 v2.0

负责评估爬取结果的数据质量。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from .models import QualityIssue, QualityReport, QualityScore, StrategyResult
from .observ_logger import ObservLogger


class Dimension(Enum):
    """质量维度"""

    COMPLETENESS = "completeness"
    VALIDITY = "validity"
    FRESHNESS = "freshness"
    CONSISTENCY = "consistency"


@dataclass
class QualityRule:
    """质量规则"""

    name: str
    dimension: Dimension
    severity: str
    check: Callable[[Dict[str, Any]], bool]
    description: str
    weight: float = 1.0
    enabled: bool = True


class QualityAssessor:
    """质量评估器

    对爬取结果进行多维度质量评估。
    """

    DEFAULT_RULES: List[QualityRule] = []

    def __init__(
        self,
        rules: Optional[List[QualityRule]] = None,
        logger: Optional[ObservLogger] = None,
    ) -> None:
        self.rules = rules or self._get_default_rules()
        self.logger = logger or ObservLogger(name="intelligent.quality_assessor")
        self._assessment_cache: Dict[str, QualityReport] = {}

    def _get_default_rules(self) -> List[QualityRule]:
        """获取默认规则"""
        return [
            QualityRule(
                name="min_content_length",
                dimension=Dimension.COMPLETENESS,
                severity="warning",
                check=lambda d: len(d.get("content", "")) >= 100,
                description="Content should be at least 100 characters",
                weight=0.5,
            ),
            QualityRule(
                name="has_html_structure",
                dimension=Dimension.COMPLETENESS,
                severity="error",
                check=lambda d: "<html" in d.get("content", "").lower() or d.get("data"),
                description="Should contain valid HTML structure or structured data",
                weight=1.0,
            ),
            QualityRule(
                name="valid_url",
                dimension=Dimension.VALIDITY,
                severity="error",
                check=lambda d: bool(d.get("url")),
                description="URL must be present",
                weight=1.0,
            ),
            QualityRule(
                name="valid_status_code",
                dimension=Dimension.VALIDITY,
                severity="error",
                check=lambda d: d.get("status_code", 0) == 200,
                description="Status code should be 200",
                weight=1.0,
            ),
            QualityRule(
                name="no_error_content",
                dimension=Dimension.VALIDITY,
                severity="error",
                check=lambda d: not any(x in d.get("content", "").lower() for x in ["error", "exception", "traceback"]),
                description="Should not contain error messages",
                weight=0.8,
            ),
            QualityRule(
                name="has_title",
                dimension=Dimension.COMPLETENESS,
                severity="warning",
                check=lambda d: bool(d.get("data", {}).get("title")) or "<title" in d.get("content", "").lower(),
                description="Should have a page title",
                weight=0.3,
            ),
            QualityRule(
                name="has_links",
                dimension=Dimension.COMPLETENESS,
                severity="info",
                check=lambda d: bool(d.get("data", {}).get("links")),
                description="Should contain links",
                weight=0.2,
            ),
        ]

    def add_rule(self, rule: QualityRule) -> None:
        """添加质量规则"""
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> None:
        """移除质量规则"""
        self.rules = [r for r in self.rules if r.name != rule_name]

    def assess(self, result: StrategyResult) -> QualityReport:
        """评估爬取结果质量

        Args:
            result: 策略执行结果

        Returns:
            质量报告
        """
        data = {
            "url": result.strategy_name,
            "content": result.content or "",
            "data": result.data or {},
            "status_code": result.status_code,
            "success": result.success,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "metadata": result.metadata,
        }

        issues: List[QualityIssue] = []
        dimension_scores: Dict[Dimension, List[float]] = {
            Dimension.COMPLETENESS: [],
            Dimension.VALIDITY: [],
            Dimension.FRESHNESS: [],
            Dimension.CONSISTENCY: [],
        }

        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                passed = rule.check(data)
                if not passed:
                    issue = QualityIssue(
                        dimension=rule.dimension.value,
                        severity=rule.severity,
                        description=rule.description,
                        field=rule.name,
                    )
                    issues.append(issue)

                    score = 0.5 if rule.severity == "warning" else 0.0
                    dimension_scores[rule.dimension].append(score)
                else:
                    dimension_scores[rule.dimension].append(1.0)

            except Exception as e:
                self.logger.warning(f"Rule check failed: {rule.name}", error=str(e))

        completeness = self._calculate_dimension_score(dimension_scores[Dimension.COMPLETENESS])
        validity = self._calculate_dimension_score(dimension_scores[Dimension.VALIDITY])
        freshness = self._calculate_freshness_score(result)
        consistency = self._calculate_consistency_score(result)

        score = QualityScore(
            completeness=completeness,
            validity=validity,
            freshness=freshness,
            consistency=consistency,
        )

        suggestions = self._generate_suggestions(issues)

        report = QualityReport(
            score=score,
            issues=issues,
            suggestions=suggestions,
            metadata={
                "strategy": result.strategy_name,
                "duration_ms": result.duration_ms,
                "content_length": len(result.content or ""),
            },
            timestamp=datetime.now(),
        )

        self.logger.log_quality_assessment(
            url=result.strategy_name,
            score=score.overall,
            issues_count=len(issues),
        )

        return report

    def _calculate_dimension_score(self, scores: List[float]) -> float:
        """计算维度得分"""
        if not scores:
            return 1.0
        return sum(scores) / len(scores)

    def _calculate_freshness_score(self, result: StrategyResult) -> float:
        """计算新鲜度得分

        基于内容特征判断数据新鲜度。
        """
        if not result.success:
            return 0.0

        score = 1.0

        content = result.content or ""
        content_lower = content.lower()

        if any(word in content_lower for word in ["yesterday", "today", "latest", "recent"]):
            score = max(score, 0.9)

        if result.metadata.get("timestamp"):
            score = 0.95

        return min(score, 1.0)

    def _calculate_consistency_score(self, result: StrategyResult) -> float:
        """计算一致性得分

        基于数据结构和格式一致性评估。
        """
        if not result.success:
            return 0.0

        score = 1.0

        if result.data:
            if isinstance(result.data, dict):
                if not result.data:
                    score = 0.7
            elif isinstance(result.data, list):
                if not result.data:
                    score = 0.7

        content = result.content or ""
        if content:
            html_tags = len(re.findall(r"<[^>]+>", content))
            if html_tags > 0:
                text_ratio = len(re.sub(r"<[^>]+>", "", content)) / len(content)
                if text_ratio < 0.1:
                    score *= 0.8

        return min(score, 1.0)

    def _generate_suggestions(self, issues: List[QualityIssue]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        error_issues = [i for i in issues if i.severity == "error"]
        warning_issues = [i for i in issues if i.severity == "warning"]

        if error_issues:
            suggestions.append(f"Fix {len(error_issues)} critical issue(s) first")

        if any(i.dimension == "completeness" for i in issues):
            suggestions.append("Consider using a more powerful extraction strategy")

        if any(i.dimension == "validity" for i in issues):
            suggestions.append("Check if the target website has anti-bot protection")

        if warning_issues:
            suggestions.append(f"Review {len(warning_issues)} warning(s) for potential improvements")

        return suggestions

    def get_dimension_weights(self) -> Dict[str, float]:
        """获取维度权重"""
        return {
            "completeness": 0.25,
            "validity": 0.30,
            "freshness": 0.20,
            "consistency": 0.25,
        }

    def set_dimension_weights(self, weights: Dict[str, float]) -> None:
        """设置维度权重"""
        self.logger.warning("Dimension weights override is not yet implemented")

    def clear_cache(self) -> None:
        """清除评估缓存"""
        self._assessment_cache.clear()
