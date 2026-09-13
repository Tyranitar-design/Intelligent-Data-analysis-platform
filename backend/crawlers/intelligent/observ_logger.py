# -*- coding: utf-8 -*-
"""
可观测性日志 - 智能爬虫系统 v2.0

提供结构化日志、性能指标收集、调用链路追踪功能。
"""

from __future__ import annotations

import json
import logging
import re
import time
from contextvars import ContextVar
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

TRACE_ID: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
SPAN_ID: ContextVar[Optional[str]] = ContextVar("span_id", default=None)

SENSITIVE_PATTERNS = [
    (re.compile(r"(?i)(cookie|authorization|token|passwd|password)[:=]\s*[\w\-]+"), "[REDACTED]"),
]


class CrawlLogLevel(Enum):
    """爬虫日志级别"""

    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class ObservLogger:
    """可观测性日志器"""

    def __init__(
        self,
        name: str = "intelligent.scraper",
        log_level: str = "INFO",
        log_format: str = "json",
    ) -> None:
        self.logger = logging.getLogger(name)
        self.log_format = log_format
        self._set_level(log_level)
        self._metrics: Dict[str, int] = {}
        self._histograms: Dict[str, List[float]] = {}

    def _set_level(self, level: str) -> None:
        """设置日志级别"""
        level_map = {
            "TRACE": 5,
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50,
        }
        numeric_level = level_map.get(level.upper(), 20)
        self.logger.setLevel(numeric_level)

    def _redact_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏敏感信息"""
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self._redact_sensitive(value)
            elif isinstance(value, str):
                redacted = value
                for pattern, replacement in SENSITIVE_PATTERNS:
                    redacted = pattern.sub(replacement, redacted)
                result[key] = redacted
            else:
                result[key] = value
        return result

    def _format_log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """格式化日志"""
        log_data = {
            "timestamp": datetime.now().isoformat() + "Z",
            "level": level,
            "logger": self.logger.name,
            "message": message,
            "trace_id": TRACE_ID.get(),
            "span_id": SPAN_ID.get(),
        }

        if extra:
            log_data.update(self._redact_sensitive(extra))

        if self.log_format == "json":
            return json.dumps(log_data, ensure_ascii=False)
        else:
            return f"[{log_data['timestamp']}] {level} - {message}"

    def trace(self, message: str, **kwargs: Any) -> None:
        """TRACE 级别日志"""
        self.logger.debug(self._format_log("TRACE", message, kwargs))

    def debug(self, message: str, **kwargs: Any) -> None:
        """DEBUG 级别日志"""
        self.logger.debug(self._format_log("DEBUG", message, kwargs))

    def info(self, message: str, **kwargs: Any) -> None:
        """INFO 级别日志"""
        self.logger.info(self._format_log("INFO", message, kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        """WARNING 级别日志"""
        self.logger.warning(self._format_log("WARNING", message, kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        """ERROR 级别日志"""
        self.logger.error(self._format_log("ERROR", message, kwargs))

    def critical(self, message: str, **kwargs: Any) -> None:
        """CRITICAL 级别日志"""
        self.logger.critical(self._format_log("CRITICAL", message, kwargs))

    def log_request(
        self,
        url: str,
        strategy: str,
        status_code: Optional[int] = None,
        duration_ms: float = 0.0,
        response_size: int = 0,
    ) -> None:
        """记录请求日志"""
        self.info(
            "Request completed",
            url=url,
            strategy=strategy,
            status_code=status_code,
            duration_ms=duration_ms,
            response_size=response_size,
        )

    def log_strategy_switch(
        self,
        from_strategy: str,
        to_strategy: str,
        reason: str,
    ) -> None:
        """记录策略切换日志"""
        self.warning(
            "Strategy switched",
            from_strategy=from_strategy,
            to_strategy=to_strategy,
            reason=reason,
        )

    def log_quality_assessment(
        self,
        url: str,
        score: float,
        issues_count: int,
    ) -> None:
        """记录质量评估日志"""
        self.info(
            "Quality assessed",
            url=url,
            quality_score=score,
            issues_count=issues_count,
        )

    def increment_counter(self, name: str, value: int = 1) -> None:
        """递增计数器"""
        self._metrics[name] = self._metrics.get(name, 0) + value

    def record_histogram(self, name: str, value: float) -> None:
        """记录直方图数据"""
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "counters": self._metrics.copy(),
            "histograms": {
                k: {
                    "count": len(v),
                    "sum": sum(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                }
                for k, v in self._histograms.items()
            },
        }

    def export_prometheus(self) -> str:
        """导出 Prometheus 格式指标"""
        lines = []
        for name, value in self._metrics.items():
            metric_name = name.replace(".", "_")
            lines.append(f"# TYPE {metric_name} counter")
            lines.append(f"{metric_name} {value}")
        for name, stats in self._histograms.items():
            metric_name = name.replace(".", "_")
            lines.append(f"# TYPE {metric_name} histogram")
            if stats:
                lines.append(f"{metric_name}_sum {sum(stats)}")
                lines.append(f"{metric_name}_count {len(stats)}")
        return "\n".join(lines)


class Span:
    """调用链路追踪跨度"""

    def __init__(
        self,
        logger: ObservLogger,
        name: str,
        parent_id: Optional[str] = None,
    ) -> None:
        self.logger = logger
        self.name = name
        self.parent_id = parent_id
        self.span_id = f"{id(self):016x}"
        self.start_time = time.time()
        self.attributes: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []
        self.ended = False

    def set_attribute(self, key: str, value: Any) -> "Span":
        """设置属性"""
        self.attributes[key] = value
        return self

    def add_event(self, name: str, **kwargs: Any) -> "Span":
        """添加事件"""
        self.events.append({
            "name": name,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        })
        return self

    def end(self) -> None:
        """结束跨度"""
        if self.ended:
            return
        self.ended = True
        duration_ms = (time.time() - self.start_time) * 1000
        self.logger.debug(
            f"Span ended: {self.name}",
            span_id=self.span_id,
            parent_id=self.parent_id,
            duration_ms=duration_ms,
            attributes=self.attributes,
        )
        self.logger.record_histogram(f"span.{self.name}.duration_ms", duration_ms)

    def __enter__(self) -> "Span":
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """上下文管理器出口"""
        self.end()


def create_span(logger: ObservLogger, name: str) -> Span:
    """创建追踪跨度"""
    return Span(logger, name, SPAN_ID.get())
