# -*- coding: utf-8 -*-
"""
统一异常体系 - 智能爬虫系统 v2.0

遵循 harness-engineering 规范定义的标准异常层级。
"""

from typing import Optional, Any, Dict


class ScraperError(Exception):
    """爬虫基类异常"""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.url = url
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "url": self.url,
            "details": self.details,
        }


class AdaptiveScraperError(ScraperError):
    """自适应爬虫通用异常"""

    pass


class ProbeError(ScraperError):
    """探测失败异常"""

    pass


class StrategyError(ScraperError):
    """策略执行失败基类"""

    pass


class StrategyNotAvailable(StrategyError):
    """策略不可用异常"""

    def __init__(
        self,
        strategy_name: str,
        reason: str,
        url: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=f"Strategy '{strategy_name}' is not available: {reason}",
            url=url,
            details={"strategy": strategy_name, "reason": reason},
        )
        self.strategy_name = strategy_name
        self.reason = reason


class StrategyTimeout(StrategyError):
    """策略超时异常"""

    def __init__(
        self,
        strategy_name: str,
        timeout: float,
        url: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=f"Strategy '{strategy_name}' timed out after {timeout}s",
            url=url,
            details={"strategy": strategy_name, "timeout": timeout},
        )
        self.strategy_name = strategy_name
        self.timeout = timeout


class StrategyValidationError(StrategyError):
    """策略结果验证失败异常"""

    def __init__(
        self,
        strategy_name: str,
        reason: str,
        url: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=f"Strategy '{strategy_name}' validation failed: {reason}",
            url=url,
            details={"strategy": strategy_name, "reason": reason},
        )
        self.strategy_name = strategy_name
        self.reason = reason


class QualityError(ScraperError):
    """质量评估失败异常"""

    pass


class AdaptError(ScraperError):
    """适配管理错误异常"""

    pass


class CircuitBreakerOpenError(AdaptError):
    """熔断器开启异常"""

    def __init__(
        self,
        strategy_name: str,
        failure_count: int,
        url: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=f"Circuit breaker is OPEN for '{strategy_name}' after {failure_count} failures",
            url=url,
            details={"strategy": strategy_name, "failure_count": failure_count},
        )
        self.strategy_name = strategy_name
        self.failure_count = failure_count


class ObservabilityError(ScraperError):
    """可观测性错误异常"""

    pass


class NetworkError(AdaptiveScraperError):
    """网络相关异常"""

    pass


class AuthRequiredError(AdaptiveScraperError):
    """需要认证异常"""

    pass


class ProtectedContentError(AdaptiveScraperError):
    """受保护内容异常"""

    pass


class RateLimitError(AdaptiveScraperError):
    """限流异常"""

    pass


class StrategyExhaustedError(AdaptiveScraperError):
    """所有策略耗尽异常"""

    pass
