# -*- coding: utf-8 -*-
"""
智能爬虫系统 v2.0 - 自适应爬虫引擎

提供智能、自适应、可观测的爬取能力。

主要组件:
- AdaptiveScraper: 核心引擎
- Intent Engine: 意图识别
- Quality Assessor: 质量评估
- Adapt Manager: 自适应管理
- Observ Logger: 可观测性日志

使用示例:
    from crawlers.intelligent import AdaptiveScraper, ScraperConfig

    config = ScraperConfig(min_quality_score=0.7)
    scraper = AdaptiveScraper(config)

    async with scraper:
        result = await scraper.crawl("https://example.com")
        print(f"Quality: {result.quality_score}")
"""

from .adaptive_scraper import AdaptiveScraper
from .adapt_manager import AdaptManager, BackoffStrategy, CircuitBreaker, RetryConfig
from .intent_engine import IntentEngine, IntentRule, IntentRuleStats
from .quality_assessor import QualityAssessor, QualityRule
from .exceptions import (
    AdaptError,
    CircuitBreakerOpenError,
    ProbeError,
    QualityError,
    ScraperError,
    StrategyError,
    StrategyNotAvailable,
    StrategyTimeout,
    StrategyValidationError,
)
from .models import (
    CircuitBreakerConfig,
    CircuitBreakerState,
    CrawlIntent,
    CrawlResult,
    IntentType,
    ProbeResult,
    QualityIssue,
    QualityReport,
    QualityScore,
    ScraperConfig,
    StrategyName,
    StrategyResult,
)
from .observ_logger import ObservLogger, create_span

__all__ = [
    # 核心引擎
    "AdaptiveScraper",
    # Adapt Manager
    "AdaptManager",
    "CircuitBreaker",
    "RetryConfig",
    "BackoffStrategy",
    # Intent Engine
    "IntentEngine",
    "IntentRule",
    "IntentRuleStats",
    # Quality Assessor
    "QualityAssessor",
    "QualityRule",
    # 异常
    "ScraperError",
    "ProbeError",
    "StrategyError",
    "StrategyNotAvailable",
    "StrategyTimeout",
    "StrategyValidationError",
    "QualityError",
    "AdaptError",
    "CircuitBreakerOpenError",
    # 数据模型
    "ScraperConfig",
    "CrawlIntent",
    "CrawlResult",
    "ProbeResult",
    "IntentType",
    "StrategyName",
    "StrategyResult",
    "QualityScore",
    "QualityIssue",
    "QualityReport",
    "CircuitBreakerConfig",
    "CircuitBreakerState",
    # 可观测性
    "ObservLogger",
    "create_span",
]

__version__ = "2.0.0"
