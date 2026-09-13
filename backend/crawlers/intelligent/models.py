# -*- coding: utf-8 -*-
"""
Pydantic 数据模型 - 智能爬虫系统 v2.0

定义所有核心数据结构和配置模型。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator


class IntentType(Enum):
    """爬取意图类型"""

    STATIC_CONTENT = "static_content"
    DYNAMIC_CONTENT = "dynamic_content"
    API_DATA = "api_data"
    PROTECTED_CONTENT = "protected"
    AUTHENTICATED = "authenticated"
    PAGINATED = "paginated"
    STREAMING = "streaming"


class StrategyName(Enum):
    """策略名称枚举"""

    HTTPX = "httpx"
    SCRAPLING = "scrapling"
    CRAWL4AI = "crawl4ai"
    PLAYWRIGHT = "playwright"


class CrawlIntent(BaseModel):
    """爬取意图定义"""

    intent_type: IntentType = IntentType.STATIC_CONTENT
    require_auth: bool = False
    auth_platform: Optional[str] = None
    pagination: bool = False
    stream: bool = False
    headers: Dict[str, str] = Field(default_factory=dict)
    cookies: Dict[str, str] = Field(default_factory=dict)

    @field_validator("headers", mode="before")
    @classmethod
    def validate_headers(cls, v: Any) -> Dict[str, str]:
        if isinstance(v, dict):
            return v
        return {}


@dataclass
class ScraperConfig:
    """爬虫配置"""

    request_timeout: int = 30
    browser_timeout: int = 60
    max_concurrent: int = 10
    rate_limit: float = 1.0
    max_retries: int = 3
    retry_backoff: float = 2.0
    preferred_strategies: List[str] = field(
        default_factory=lambda: ["httpx", "scrapling", "crawl4ai", "playwright"]
    )
    min_quality_score: float = 0.6
    enable_tracing: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScraperConfig":
        """从字典创建配置"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ProbeResult:
    """URL 探测结果"""

    url: str
    status_code: int
    content_type: str
    headers: Dict[str, str]
    is_html: bool
    is_json: bool
    is_protected: bool = False
    requires_auth: bool = False
    has_pagination: bool = False
    detected_intent: Optional[IntentType] = None
    response_time: float = 0.0
    error: Optional[str] = None


@dataclass
class QualityScore:
    """质量评分"""

    completeness: float = 0.0
    validity: float = 0.0
    freshness: float = 0.0
    consistency: float = 0.0
    overall: float = 0.0

    def __post_init__(self) -> None:
        """计算综合评分"""
        if self.overall == 0.0:
            self.overall = (
                self.completeness * 0.25
                + self.validity * 0.30
                + self.freshness * 0.20
                + self.consistency * 0.25
            )


@dataclass
class QualityIssue:
    """质量问题"""

    dimension: str
    severity: str
    description: str
    field: Optional[str] = None
    value: Any = None


@dataclass
class QualityReport:
    """质量报告"""

    score: QualityScore
    issues: List[QualityIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StrategyResult:
    """策略执行结果"""

    strategy_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    status_code: Optional[int] = None
    quality_report: Optional[QualityReport] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrawlResult:
    """爬取结果"""

    url: str
    success: bool
    strategy_used: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    quality_score: Optional[float] = None
    quality_report: Optional[QualityReport] = None
    probe_result: Optional[ProbeResult] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    strategies_tried: List[str] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerState:
    """熔断器状态"""

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    recovery_deadline: Optional[datetime] = None

    def should_allow_request(self) -> bool:
        """是否允许请求"""
        if self.state == "CLOSED":
            return True
        if self.state == "HALF_OPEN":
            return True
        return False


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_max_calls: int = 3
