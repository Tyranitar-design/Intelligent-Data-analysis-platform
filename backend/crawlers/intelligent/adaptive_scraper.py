# -*- coding: utf-8 -*-
"""
自适应爬虫引擎 - 智能爬虫系统 v2.0

核心引擎，提供智能、自适应、可观测的爬取能力。
集成 Intent Engine、Quality Assessor、Adapt Manager。
"""

from __future__ import annotations

import asyncio
import time
from abc import abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from .adapt_manager import AdaptManager, RetryConfig
from .exceptions import (
    ProbeError,
    ScraperError,
    StrategyError,
    StrategyNotAvailable,
)
from .intent_engine import IntentEngine
from .models import (
    CircuitBreakerConfig,
    CircuitBreakerState,
    CrawlIntent,
    CrawlResult,
    IntentType,
    ProbeResult,
    ScraperConfig,
    StrategyResult,
)
from .observ_logger import ObservLogger, create_span
from .quality_assessor import QualityAssessor
from .strategies.base import BaseStrategy
from .strategies.crawl4ai_strategy import Crawl4AIStrategy
from .strategies.httpx_strategy import HttpxStrategy
from .strategies.playwright_strategy import PlaywrightStrategy
from .strategies.scrapling_strategy import ScraplingStrategy


class AdaptiveScraper:
    """自适应爬虫引擎

    提供智能策略选择、数据质量评估、自适应降级的爬取能力。

    集成模块:
    - IntentEngine: 意图识别和策略选择
    - QualityAssessor: 数据质量评估
    - AdaptManager: 自适应管理和熔断

    支持上下文管理器用法:
        async with AdaptiveScraper(config) as scraper:
            result = await scraper.crawl("https://example.com")
    """

    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        strategies: Optional[List[BaseStrategy]] = None,
        logger: Optional[ObservLogger] = None,
        intent_engine: Optional[IntentEngine] = None,
        quality_assessor: Optional[QualityAssessor] = None,
        adapt_manager: Optional[AdaptManager] = None,
    ) -> None:
        self.config = config or ScraperConfig()
        self.strategies: List[BaseStrategy] = strategies or []
        self.logger = logger or ObservLogger(
            name=f"intelligent.scraper",
            log_level=self.config.log_level,
        )

        self.intent_engine = intent_engine or IntentEngine(logger=self.logger)
        self.quality_assessor = quality_assessor or QualityAssessor(logger=self.logger)
        self.adapt_manager = adapt_manager or AdaptManager(logger=self.logger)

        self._circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self._cb_config = CircuitBreakerConfig()
        self._lifecycle_hooks: Dict[str, List[Callable]] = {
            "on_start": [],
            "on_success": [],
            "on_error": [],
            "on_retry": [],
            "on_fallback": [],
        }
        self._initialized = False
        self._prometheus_exporter: Optional["PrometheusExporter"] = None
        self._otel_tracer: Optional[Any] = None

        if not self.strategies:
            self._load_default_strategies()

    def _load_default_strategies(self) -> None:
        """加载默认策略集合。"""
        self.strategies = [
            HttpxStrategy(timeout=self.config.request_timeout),
            ScraplingStrategy(timeout=self.config.request_timeout),
            Crawl4AIStrategy(timeout=self.config.browser_timeout),
            PlaywrightStrategy(timeout=self.config.browser_timeout),
        ]
        self.strategies.sort(key=lambda s: s.get_priority(), reverse=True)

    def add_strategy(self, strategy: BaseStrategy) -> None:
        """添加爬取策略"""
        self.strategies.append(strategy)
        self.strategies.sort(key=lambda s: s.get_priority(), reverse=True)
        self.logger.info(f"Strategy added: {strategy.name}", priority=strategy.priority)

    def add_lifecycle_hook(
        self,
        event: str,
        hook: Callable[..., Any],
    ) -> None:
        """添加生命周期钩子

        Args:
            event: 事件名称 (on_start, on_success, on_error, on_retry, on_fallback)
            hook: 钩子函数
        """
        if event in self._lifecycle_hooks:
            self._lifecycle_hooks[event].append(hook)

    def setup_prometheus(self, port: int = 9090) -> None:
        """设置 Prometheus 指标导出

        Args:
            port: Prometheus 端口
        """
        try:
            from .metrics import PrometheusExporter
            self._prometheus_exporter = PrometheusExporter(port=port)
            self._prometheus_exporter.start()
            self.logger.info(f"Prometheus exporter started on port {port}")
        except ImportError:
            self.logger.warning("prometheus_client not installed, skipping Prometheus setup")

    def setup_opentelemetry(
        self,
        service_name: str = "intelligent-scraper",
        endpoint: Optional[str] = None,
    ) -> None:
        """设置 OpenTelemetry 链路追踪

        Args:
            service_name: 服务名称
            endpoint: OTLP 接收端点
        """
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import SERVICE_NAME, Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource(attributes={
                SERVICE_NAME: service_name,
            })

            provider = TracerProvider(resource=resource)

            if endpoint:
                exporter = OTLPSpanExporter(endpoint=endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))

            trace.set_tracer_provider(provider)
            self._otel_tracer = trace.get_tracer(service_name)

            self.logger.info(f"OpenTelemetry initialized for {service_name}")
        except ImportError:
            self.logger.warning("opentelemetry not installed, skipping OpenTelemetry setup")

    async def probe(self, url: str) -> ProbeResult:
        """探测 URL 并识别意图

        Args:
            url: 目标 URL

        Returns:
            探测结果
        """
        with create_span(self.logger, "probe") as span:
            span.set_attribute("url", url)
            start_time = time.time()

            try:
                result = await self._do_probe(url)
                result.response_time = (time.time() - start_time) * 1000
                span.set_attribute("status_code", result.status_code)
                span.set_attribute("intent", result.detected_intent.value if result.detected_intent else "unknown")
                self.logger.info(
                    "Probe completed",
                    url=url,
                    status_code=result.status_code,
                    intent=result.detected_intent.value if result.detected_intent else "unknown",
                )
                return result
            except Exception as e:
                self.logger.error(f"Probe failed: {e}", url=url)
                raise ProbeError(message=str(e), url=url)

    async def _do_probe(self, url: str) -> ProbeResult:
        """执行实际的探测逻辑

        Args:
            url: 目标 URL

        Returns:
            探测结果
        """
        import httpx

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.request_timeout),
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = await client.get(url)

        content_type = response.headers.get("content-type", "").lower()
        text = response.text[:4096]
        protected_signals = [
            "cloudflare",
            "captcha",
            "turnstile",
            "access denied",
            "blocked",
            "challenge",
        ]
        is_protected = response.status_code in {401, 403, 418, 429, 503} or any(
            signal in text.lower() for signal in protected_signals
        )
        requires_auth = response.status_code in {401, 403} or "login" in str(response.url).lower()

        probe = ProbeResult(
            url=url,
            status_code=response.status_code,
            content_type=content_type,
            headers=dict(response.headers),
            is_html="text/html" in content_type,
            is_json="application/json" in content_type,
            is_protected=is_protected,
            requires_auth=requires_auth,
            has_pagination=("page=" in url.lower() or "offset=" in url.lower()),
        )
        probe.detected_intent = self.intent_engine.classify(probe)
        return probe

    async def crawl(
        self,
        url: str,
        intent: Optional[CrawlIntent] = None,
        **kwargs: Any,
    ) -> CrawlResult:
        """智能爬取

        自动选择最佳策略，支持自动降级和质量评估。

        Args:
            url: 目标 URL
            intent: 爬取意图 (可选)
            **kwargs: 其他参数

        Returns:
            爬取结果
        """
        with create_span(self.logger, "crawl") as span:
            span.set_attribute("url", url)
            start_time = time.time()

            await self._run_lifecycle_hooks("on_start", url)
            self.logger.increment_counter("scraper.requests.total")

            result = CrawlResult(
                url=url,
                success=False,
                timestamp=span.start_time,  # type: ignore
            )

            try:
                probe_result = await self.probe(url)
                result.probe_result = probe_result

                intent = intent or self._infer_intent(probe_result)

                strategy_result = await self._execute_with_fallback(
                    url, intent, **kwargs
                )

                result.success = strategy_result.success
                result.strategy_used = strategy_result.strategy_name
                result.data = strategy_result.data
                result.content = strategy_result.content
                result.duration_ms = (time.time() - start_time) * 1000
                result.quality_report = strategy_result.quality_report
                result.quality_score = (
                    strategy_result.quality_report.score.overall
                    if strategy_result.quality_report
                    else None
                )
                result.metadata = strategy_result.metadata

                if result.success:
                    self.logger.increment_counter("scraper.requests.success")
                    await self._run_lifecycle_hooks("on_success", url, result)
                else:
                    self.logger.increment_counter("scraper.requests.failed")
                    result.error = strategy_result.error

                span.set_attribute("success", result.success)
                span.set_attribute("strategy", result.strategy_used or "none")
                span.set_attribute("quality_score", result.quality_score or 0)

                return result

            except Exception as e:
                self.logger.increment_counter("scraper.requests.error")
                self.logger.error(f"Crawl failed: {e}", url=url)
                result.error = str(e)
                await self._run_lifecycle_hooks("on_error", url, e)
                raise

    async def _execute_with_fallback(
        self,
        url: str,
        intent: CrawlIntent,
        **kwargs: Any,
    ) -> StrategyResult:
        """使用降级策略执行

        尝试多个策略直到成功或全部失败。
        集成 AdaptManager 进行自适应管理。

        Args:
            url: 目标 URL
            intent: 爬取意图
            **kwargs: 其他参数

        Returns:
            策略执行结果
        """
        last_error: Optional[Exception] = None
        attempted_strategies: List[str] = []

        for strategy in self.strategies:
            if strategy.name not in self.config.preferred_strategies:
                continue

            cb_state = self._get_circuit_breaker(strategy.name)
            if not cb_state.should_allow_request():
                self.logger.warning(
                    f"Circuit breaker open, skipping strategy: {strategy.name}",
                    url=url,
                )
                continue

            attempted_strategies.append(strategy.name)

            self.logger.info(
                f"Trying strategy: {strategy.name}",
                url=url,
                priority=strategy.priority,
            )

            try:
                result = await self._execute_strategy(strategy, url, intent, **kwargs)

                if result.success:
                    self._record_success(strategy.name)

                    quality_report = self.quality_assessor.assess(result)
                    result.quality_report = quality_report

                    self.adapt_manager.record_result(strategy.name, result)

                    if self._prometheus_exporter:
                        self._prometheus_exporter.record_crawl(
                            strategy=strategy.name,
                            success=True,
                            duration_ms=result.duration_ms,
                        )

                    return result

                last_error = StrategyError(message=result.error or "Unknown error", url=url)
                self._record_failure(strategy.name)

                await self._run_lifecycle_hooks(
                    "on_fallback",
                    url,
                    strategy.name,
                    result.error,
                )

                next_strategy = self.adapt_manager.get_next_strategy(
                    strategy.name,
                    error=last_error,
                    result=result,
                )

                if next_strategy:
                    self.logger.info(
                        f"Falling back from {strategy.name} to {next_strategy}",
                        url=url,
                    )

            except Exception as e:
                last_error = e
                self._record_failure(strategy.name)

                self.adapt_manager.record_result(
                    strategy.name,
                    StrategyResult(
                        strategy_name=strategy.name,
                        success=False,
                        error=str(e),
                        duration_ms=0,
                    ),
                )

                self.logger.error(
                    f"Strategy failed: {strategy.name}",
                    error=str(e),
                    url=url,
                )

        raise StrategyNotAvailable(
            strategy_name="all",
            reason=f"All strategies failed. Last error: {last_error}",
            url=url,
        )

    async def _execute_strategy(
        self,
        strategy: BaseStrategy,
        url: str,
        intent: CrawlIntent,
        **kwargs: Any,
    ) -> StrategyResult:
        """执行单个策略

        Args:
            strategy: 策略实例
            url: 目标 URL
            intent: 爬取意图
            **kwargs: 其他参数

        Returns:
            策略执行结果
        """
        with create_span(self.logger, f"strategy.{strategy.name}") as span:
            span.set_attribute("strategy", strategy.name)

            timeout = strategy.get_timeout()
            try:
                result = await asyncio.wait_for(
                    strategy.execute(url, intent, **kwargs),
                    timeout=timeout,
                )

                if not await strategy.validate(result):
                    result.success = False
                    result.error = "Validation failed"

                self.logger.log_request(
                    url=url,
                    strategy=strategy.name,
                    status_code=result.status_code,
                    duration_ms=result.duration_ms,
                    response_size=len(result.content or ""),
                )

                return result

            except asyncio.TimeoutError:
                raise StrategyError(
                    message=f"Strategy timed out after {timeout}s",
                    url=url,
                )
            except Exception as e:
                raise StrategyError(
                    message=f"Strategy execution failed: {e}",
                    url=url,
                )

    def _infer_intent(self, probe_result: ProbeResult) -> CrawlIntent:
        """从探测结果推断意图

        Args:
            probe_result: 探测结果

        Returns:
            推断的爬取意图
        """
        if probe_result.detected_intent:
            intent_type = probe_result.detected_intent
        elif probe_result.is_json:
            intent_type = IntentType.API_DATA
        elif probe_result.is_protected:
            intent_type = IntentType.PROTECTED_CONTENT
        elif probe_result.requires_auth:
            intent_type = IntentType.AUTHENTICATED
        elif probe_result.has_pagination:
            intent_type = IntentType.PAGINATED
        elif probe_result.is_html:
            intent_type = IntentType.DYNAMIC_CONTENT
        else:
            intent_type = IntentType.STATIC_CONTENT

        return CrawlIntent(
            intent_type=intent_type,
            require_auth=probe_result.requires_auth,
            pagination=probe_result.has_pagination,
        )

    def _get_circuit_breaker(self, strategy_name: str) -> CircuitBreakerState:
        """获取策略的熔断器状态"""
        if strategy_name not in self._circuit_breakers:
            self._circuit_breakers[strategy_name] = CircuitBreakerState()
        return self._circuit_breakers[strategy_name]

    def _record_success(self, strategy_name: str) -> None:
        """记录成功"""
        cb = self._get_circuit_breaker(strategy_name)
        cb.success_count += 1
        cb.failure_count = 0
        if cb.state == "HALF_OPEN":
            cb.state = "CLOSED"

    def _record_failure(self, strategy_name: str) -> None:
        """记录失败"""
        cb = self._get_circuit_breaker(strategy_name)
        cb.failure_count += 1
        cb.last_failure_time = None

        if cb.failure_count >= self._cb_config.failure_threshold:
            cb.state = "OPEN"
            self.logger.warning(
                f"Circuit breaker opened for: {strategy_name}",
                failure_count=cb.failure_count,
            )

    async def _run_lifecycle_hooks(
        self,
        event: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """运行生命周期钩子"""
        for hook in self._lifecycle_hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(*args, **kwargs)
                else:
                    hook(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Lifecycle hook failed: {e}", event=event)

    async def initialize(self) -> None:
        """初始化爬虫引擎"""
        if self._initialized:
            return
        self.logger.info("Initializing AdaptiveScraper")
        self._initialized = True

    async def cleanup(self) -> None:
        """清理资源"""
        self.logger.info("Cleaning up AdaptiveScraper")
        self._initialized = False

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        """生命周期上下文管理器"""
        try:
            await self.initialize()
            yield
        finally:
            await self.cleanup()

    async def __aenter__(self) -> "AdaptiveScraper":
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """异步上下文管理器出口"""
        await self.cleanup()

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        base_metrics = self.logger.get_metrics()
        base_metrics["circuit_breakers"] = {
            name: {
                "state": cb.state,
                "failure_count": cb.failure_count,
                "success_count": cb.success_count,
            }
            for name, cb in self._circuit_breakers.items()
        }
        base_metrics["adapt_manager"] = self.adapt_manager.get_stats()
        return base_metrics
