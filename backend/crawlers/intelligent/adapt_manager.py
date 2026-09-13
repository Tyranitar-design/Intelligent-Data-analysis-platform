# -*- coding: utf-8 -*-
"""
自适应管理器 - 智能爬虫系统 v2.0

负责熔断、错误分类、策略切换和重试逻辑。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from .exceptions import (
    AdaptiveScraperError,
    AuthRequiredError,
    NetworkError,
    ProtectedContentError,
    RateLimitError,
    StrategyExhaustedError,
)
from .models import StrategyResult
from .observ_logger import ObservLogger


class ErrorCategory(Enum):
    """错误分类"""

    NETWORK = "network"
    AUTH = "auth"
    PROTECTED = "protected"
    RATE_LIMIT = "rate_limit"
    PARSE = "parse"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 60.0
    half_open_max_calls: int = 3


class CircuitState(Enum):
    """熔断状态"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """熔断器

    防止连续失败导致系统崩溃。
    """

    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _half_open_calls: int = field(default=0, init=False)

    def record_success(self) -> None:
        """记录成功"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._half_open_calls = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """记录失败"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._half_open_calls = 0
            self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """检查是否可以执行"""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.config.timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._failure_count = 0
                return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls

        return False

    def get_state(self) -> CircuitState:
        """获取当前状态"""
        return self._state

    def reset(self) -> None:
        """重置熔断器"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = 0.0


@dataclass
class RetryConfig:
    """重试配置"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class BackoffStrategy:
    """退避策略"""

    @staticmethod
    def exponential(
        attempt: int,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = True,
    ) -> float:
        """指数退避

        Args:
            attempt: 当前尝试次数
            base_delay: 基础延迟
            max_delay: 最大延迟
            jitter: 是否添加抖动

        Returns:
            延迟时间（秒）
        """
        delay = min(base_delay * (2 ** attempt), max_delay)

        if jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    @staticmethod
    def linear(
        attempt: int,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> float:
        """线性退避

        Args:
            attempt: 当前尝试次数
            base_delay: 基础延迟
            max_delay: 最大延迟

        Returns:
            延迟时间（秒）
        """
        return min(base_delay * (attempt + 1), max_delay)

    @staticmethod
    def constant(
        attempt: int,
        delay: float = 1.0,
    ) -> float:
        """固定延迟

        Args:
            attempt: 当前尝试次数
            delay: 固定延迟

        Returns:
            延迟时间（秒）
        """
        return delay


class AdaptManager:
    """自适应管理器

    负责:
    - 熔断器管理
    - 错误分类
    - 策略切换决策
    - 重试逻辑
    """

    STRATEGY_TRANSITIONS: Dict[str, List[str]] = {
        "httpx": ["scrapling", "crawl4ai", "playwright"],
        "scrapling": ["crawl4ai", "playwright", "httpx"],
        "crawl4ai": ["playwright", "scrapling", "httpx"],
        "playwright": ["crawl4ai", "scrapling", "httpx"],
    }

    ERROR_TO_STRATEGY: Dict[ErrorCategory, List[str]] = {
        ErrorCategory.NETWORK: ["playwright"],
        ErrorCategory.AUTH: ["playwright"],
        ErrorCategory.PROTECTED: ["playwright"],
        ErrorCategory.RATE_LIMIT: ["httpx"],
        ErrorCategory.PARSE: ["scrapling", "crawl4ai"],
        ErrorCategory.TIMEOUT: ["crawl4ai", "playwright"],
        ErrorCategory.UNKNOWN: ["playwright"],
    }

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        logger: Optional[ObservLogger] = None,
    ) -> None:
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.logger = logger or ObservLogger(name="intelligent.adapt_manager")

        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._strategy_history: Dict[str, List[StrategyResult]] = {}

    def get_circuit_breaker(self, strategy_name: str) -> CircuitBreaker:
        """获取熔断器

        Args:
            strategy_name: 策略名称

        Returns:
            熔断器实例
        """
        if strategy_name not in self._circuit_breakers:
            self._circuit_breakers[strategy_name] = CircuitBreaker(
                name=strategy_name,
                config=self.circuit_breaker_config,
            )
        return self._circuit_breakers[strategy_name]

    def classify_error(self, error: Exception) -> ErrorCategory:
        """分类错误

        Args:
            error: 异常对象

        Returns:
            错误分类
        """
        error_mapping: Dict[Type[Exception], ErrorCategory] = {
            NetworkError: ErrorCategory.NETWORK,
            AuthRequiredError: ErrorCategory.AUTH,
            ProtectedContentError: ErrorCategory.PROTECTED,
            RateLimitError: ErrorCategory.RATE_LIMIT,
            StrategyExhaustedError: ErrorCategory.PARSE,
            TimeoutError: ErrorCategory.TIMEOUT,
            asyncio.TimeoutError: ErrorCategory.TIMEOUT,
        }

        for exc_type, category in error_mapping.items():
            if isinstance(error, exc_type):
                return category

        error_msg = str(error).lower()

        if any(x in error_msg for x in ["network", "connection", "dns", "refused"]):
            return ErrorCategory.NETWORK
        if any(x in error_msg for x in ["auth", "login", "unauthorized", "403", "401"]):
            return ErrorCategory.AUTH
        if any(x in error_msg for x in ["protected", "cloudflare", "captcha", "challenge"]):
            return ErrorCategory.PROTECTED
        if any(x in error_msg for x in ["rate", "limit", "429", "throttle"]):
            return ErrorCategory.RATE_LIMIT
        if any(x in error_msg for x in ["timeout", "timed out"]):
            return ErrorCategory.TIMEOUT

        return ErrorCategory.UNKNOWN

    def get_next_strategy(
        self,
        current_strategy: str,
        error: Optional[Exception] = None,
        result: Optional[StrategyResult] = None,
    ) -> Optional[str]:
        """获取下一个策略

        Args:
            current_strategy: 当前策略名称
            error: 当前错误（可选）
            result: 当前结果（可选）

        Returns:
            下一个策略名称，如果无可用策略则返回 None
        """
        transitions = self.STRATEGY_TRANSITIONS.get(current_strategy, [])

        if error:
            error_category = self.classify_error(error)
            preferred = self.ERROR_TO_STRATEGY.get(error_category, [])
            for strategy in preferred:
                if strategy in transitions:
                    cb = self.get_circuit_breaker(strategy)
                    if cb.can_execute():
                        self.logger.info(
                            f"Strategy transition due to {error_category.value}: {current_strategy} → {strategy}"
                        )
                        return strategy

        for strategy in transitions:
            cb = self.get_circuit_breaker(strategy)
            if cb.can_execute():
                return strategy

        return None

    def record_result(self, strategy_name: str, result: StrategyResult) -> None:
        """记录策略结果

        Args:
            strategy_name: 策略名称
            result: 执行结果
        """
        if strategy_name not in self._strategy_history:
            self._strategy_history[strategy_name] = []

        self._strategy_history[strategy_name].append(result)

        if len(self._strategy_history[strategy_name]) > 100:
            self._strategy_history[strategy_name] = self._strategy_history[strategy_name][-100:]

        cb = self.get_circuit_breaker(strategy_name)

        if result.success:
            cb.record_success()
        else:
            cb.record_failure()

    async def execute_with_retry(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> StrategyResult:
        """带重试的执行

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            执行结果
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.retry_config.max_attempts):
            try:
                result = await func(*args, **kwargs)

                if isinstance(result, StrategyResult) and result.success:
                    return result

                if isinstance(result, StrategyResult) and result.error:
                    last_error = Exception(result.error)
                else:
                    last_error = None

            except Exception as e:
                last_error = e

            if attempt < self.retry_config.max_attempts - 1:
                delay = BackoffStrategy.exponential(
                    attempt=attempt,
                    base_delay=self.retry_config.base_delay,
                    max_delay=self.retry_config.max_delay,
                    jitter=self.retry_config.jitter,
                )

                self.logger.info(
                    f"Retry attempt {attempt + 1}/{self.retry_config.max_attempts} after {delay:.2f}s",
                    error=str(last_error),
                )

                await asyncio.sleep(delay)

        if last_error:
            raise last_error

        raise AdaptiveScraperError("Max retries exceeded")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "circuit_breakers": {
                name: {
                    "state": cb.get_state().value,
                    "failure_count": cb._failure_count,
                    "success_count": cb._success_count,
                }
                for name, cb in self._circuit_breakers.items()
            },
            "retry_config": {
                "max_attempts": self.retry_config.max_attempts,
                "base_delay": self.retry_config.base_delay,
                "exponential_base": self.retry_config.exponential_base,
            },
        }

    def reset_all_circuit_breakers(self) -> None:
        """重置所有熔断器"""
        for cb in self._circuit_breakers.values():
            cb.reset()
        self.logger.info("All circuit breakers reset")
