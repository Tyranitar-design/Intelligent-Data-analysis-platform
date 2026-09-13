# -*- coding: utf-8 -*-
"""
Prometheus 指标导出 - 智能爬虫系统 v2.0

提供 Prometheus 指标收集和导出功能。
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    start_http_server = None


class PrometheusExporter:
    """Prometheus 指标导出器

    导出爬虫系统运行指标供 Prometheus 收集。
    """

    def __init__(self, port: int = 9090) -> None:
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("prometheus_client is required for metrics export")

        self.port = port
        self._thread: Optional[threading.Thread] = None
        self._running = False

        self._init_metrics()

    def _init_metrics(self) -> None:
        """初始化指标"""
        self.requests_total = Counter(
            "scraper_requests_total",
            "Total number of scrape requests",
            ["strategy", "status"],
        )

        self.requests_success = Counter(
            "scraper_requests_success_total",
            "Total number of successful scrape requests",
            ["strategy"],
        )

        self.requests_failed = Counter(
            "scraper_requests_failed_total",
            "Total number of failed scrape requests",
            ["strategy"],
        )

        self.request_duration = Histogram(
            "scraper_request_duration_seconds",
            "Scrape request duration in seconds",
            ["strategy"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
        )

        self.quality_score = Gauge(
            "scraper_quality_score",
            "Quality score of last scrape",
            ["strategy"],
        )

        self.circuit_breaker_state = Gauge(
            "scraper_circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half_open)",
            ["strategy"],
        )

        self.active_requests = Gauge(
            "scraper_active_requests",
            "Number of active scrape requests",
        )

        self.strategy_fallbacks = Counter(
            "scraper_strategy_fallbacks_total",
            "Total number of strategy fallbacks",
            ["from_strategy", "to_strategy"],
        )

        self.bytes_scraped = Counter(
            "scraper_bytes_scraped_total",
            "Total bytes scraped",
            ["strategy"],
        )

    def start(self) -> None:
        """启动指标服务器"""
        if self._running:
            return

        start_http_server(self.port)
        self._running = True

    def stop(self) -> None:
        """停止指标服务器"""
        self._running = False
        if self._thread:
            self._thread.join()
            self._thread = None

    def record_crawl(
        self,
        strategy: str,
        success: bool,
        duration_ms: float,
        bytes_scraped: int = 0,
        quality_score: Optional[float] = None,
    ) -> None:
        """记录爬取结果

        Args:
            strategy: 策略名称
            success: 是否成功
            duration_ms: 耗时（毫秒）
            bytes_scraped: 爬取字节数
            quality_score: 质量分数
        """
        status = "success" if success else "failed"

        self.requests_total.labels(strategy=strategy, status=status).inc()

        if success:
            self.requests_success.labels(strategy=strategy).inc()
        else:
            self.requests_failed.labels(strategy=strategy).inc()

        self.request_duration.labels(strategy=strategy).observe(duration_ms / 1000)

        if bytes_scraped > 0:
            self.bytes_scraped.labels(strategy=strategy).inc(bytes_scraped)

        if quality_score is not None:
            self.quality_score.labels(strategy=strategy).set(quality_score)

    def record_fallback(
        self,
        from_strategy: str,
        to_strategy: str,
    ) -> None:
        """记录策略降级

        Args:
            from_strategy: 原策略
            to_strategy: 目标策略
        """
        self.strategy_fallbacks.labels(
            from_strategy=from_strategy,
            to_strategy=to_strategy,
        ).inc()

    def update_circuit_breaker_state(
        self,
        strategy: str,
        state: str,
    ) -> None:
        """更新熔断器状态

        Args:
            strategy: 策略名称
            state: 状态 (closed, open, half_open)
        """
        state_map = {"closed": 0, "open": 1, "half_open": 2}
        value = state_map.get(state, 0)
        self.circuit_breaker_state.labels(strategy=strategy).set(value)

    def set_active_requests(self, count: int) -> None:
        """设置活跃请求数

        Args:
            count: 活跃请求数量
        """
        self.active_requests.set(count)

    def increment_active_requests(self) -> None:
        """增加活跃请求数"""
        self.active_requests.inc()

    def decrement_active_requests(self) -> None:
        """减少活跃请求数"""
        self.active_requests.dec()


class MetricsCollector:
    """指标收集器

    收集和聚合爬虫运行指标。
    """

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, list] = {}

    def increment(self, name: str, value: int = 1) -> None:
        """增加计数器"""
        self._counters[name] = self._counters.get(name, 0) + value

    def record_value(self, name: str, value: float) -> None:
        """记录值"""
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)

    def get_counter(self, name: str) -> int:
        """获取计数器值"""
        return self._counters.get(name, 0)

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """获取直方图统计"""
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}

        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def reset(self) -> None:
        """重置所有指标"""
        self._counters.clear()
        self._histograms.clear()
