"""
自适应限速器
============

按域名维护请求节奏。规则：

- 基准速率来自站点画像（robots 的 crawl-delay 优先，否则保守默认值）
- 遇 429 / 503 立即降至 50%，并遵守 ``Retry-After``
- 连续成功 10 次后按 20% 递进恢复，上限不超过基准速率
- 每域名并发上限固定，避免突发流量

设计取向是"宁可慢，不可被封"：目标不是压榨目标站点，而是在可持续的节奏下
长期稳定地把数据取回来。
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

THROTTLE_STATUS = frozenset({429, 503})

RECOVER_AFTER_SUCCESSES = 10
RECOVER_FACTOR = 1.2
THROTTLE_FACTOR = 0.5


@dataclass
class DomainState:
    """单个域名的限速状态。"""

    base_rate: float
    current_rate: float
    min_rate: float
    max_concurrency: int
    success_streak: int = 0
    next_allowed_at: float = 0.0
    total_requests: int = 0
    throttle_events: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    semaphore: Optional[asyncio.Semaphore] = None

    def ensure_semaphore(self) -> asyncio.Semaphore:
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(self.max_concurrency)
        return self.semaphore

    def snapshot(self) -> dict:
        return {
            "base_per_second": round(self.base_rate, 4),
            "current_per_second": round(self.current_rate, 4),
            "min_per_second": round(self.min_rate, 4),
            "max_concurrency": self.max_concurrency,
            "success_streak": self.success_streak,
            "total_requests": self.total_requests,
            "throttle_events": self.throttle_events,
            "throttled": self.current_rate < self.base_rate,
        }


class AdaptiveRateLimiter:
    """按域名自适应的请求限速器。"""

    def __init__(
        self,
        default_rate: float = 1.0,
        min_rate: float = 0.1,
        max_concurrency_per_domain: int = 2,
    ) -> None:
        self.default_rate = default_rate
        self.min_rate = min_rate
        self.max_concurrency = max_concurrency_per_domain
        self._states: dict[str, DomainState] = {}

    # ------------------------------------------------------------------ #
    # 状态管理
    # ------------------------------------------------------------------ #

    def state_for(self, domain: str, base_rate: Optional[float] = None) -> DomainState:
        """取得（或初始化）域名状态。"""
        state = self._states.get(domain)
        if state is None:
            rate = base_rate if base_rate and base_rate > 0 else self.default_rate
            state = DomainState(
                base_rate=rate,
                current_rate=rate,
                min_rate=min(self.min_rate, rate),
                max_concurrency=self.max_concurrency,
            )
            self._states[domain] = state
        elif base_rate and base_rate > 0:
            # 画像给了更精确的基准速率时更新
            state.base_rate = base_rate
            state.current_rate = min(state.current_rate, base_rate)
        return state

    # ------------------------------------------------------------------ #
    # 请求闸门
    # ------------------------------------------------------------------ #

    async def acquire(self, domain: str, base_rate: Optional[float] = None) -> None:
        """取得一次请求许可。必要时等待，直到满足当前速率。"""
        state = self.state_for(domain, base_rate)

        async with state.lock:
            now = time.monotonic()
            wait = state.next_allowed_at - now
            if wait > 0:
                await asyncio.sleep(wait)
            interval = 1.0 / max(state.current_rate, state.min_rate)
            state.next_allowed_at = time.monotonic() + interval
            state.total_requests += 1

    async def concurrency_slot(self, domain: str) -> asyncio.Semaphore:
        """取得域名级并发信号量（调用方自行 ``async with``）。"""
        return self.state_for(domain).ensure_semaphore()

    # ------------------------------------------------------------------ #
    # 反馈
    # ------------------------------------------------------------------ #

    def on_response(
        self,
        domain: str,
        status: int,
        retry_after: Optional[float] = None,
    ) -> None:
        """根据响应码调整速率。"""
        state = self.state_for(domain)

        if status in THROTTLE_STATUS:
            state.current_rate = max(state.min_rate, state.current_rate * THROTTLE_FACTOR)
            state.success_streak = 0
            state.throttle_events += 1
            if retry_after and retry_after > 0:
                state.next_allowed_at = max(
                    state.next_allowed_at, time.monotonic() + retry_after
                )
            logger.info(
                "域名 %s 触发限速（HTTP %s），速率降至 %.3f/s",
                domain,
                status,
                state.current_rate,
            )
            return

        if 200 <= status < 400:
            state.success_streak += 1
            if (
                state.success_streak >= RECOVER_AFTER_SUCCESSES
                and state.current_rate < state.base_rate
            ):
                state.current_rate = min(
                    state.base_rate, state.current_rate * RECOVER_FACTOR
                )
                state.success_streak = 0
                logger.debug(
                    "域名 %s 恢复速率至 %.3f/s", domain, state.current_rate
                )
            return

        # 4xx（非 429）不计成功也不降速，避免因目标站点自身错误误伤节奏
        state.success_streak = 0

    # ------------------------------------------------------------------ #
    # 观测
    # ------------------------------------------------------------------ #

    def stats(self) -> dict:
        return {domain: s.snapshot() for domain, s in self._states.items()}

    def domain_stats(self, domain: str) -> dict:
        state = self._states.get(domain)
        return state.snapshot() if state else {}

    def reset(self, domain: Optional[str] = None) -> None:
        if domain:
            self._states.pop(domain, None)
        else:
            self._states.clear()
