# -*- coding: utf-8 -*-
"""代理池：配置加载 + 轮换策略 + 失败剔除

调研依据（多源）：IP 轮换是规模化采集的基本实践（zenrows《Web Scraping Best
Practices》· dave's corner 等）。代理来源：环境变量 ``PROXY_POOL``（逗号分隔）
或构造参数；格式 ``http://user:pass@host:port`` / ``socks5://host:port``。

用法::

    from crawlers.anticrawl.proxy_pool import get_global_pool

    pool = get_global_pool()
    proxy = pool.next()            # 无池时 None（请求走直连）
    ... 发起请求 ...
    pool.record_success(proxy)     # 或 pool.record_failure(proxy)
"""
from __future__ import annotations

import logging
import os
import random
from typing import List, Optional

logger = logging.getLogger(__name__)


def load_proxies_from_env() -> List[str]:
    """从 ``PROXY_POOL`` 环境变量加载（逗号分隔）。"""
    raw = os.environ.get("PROXY_POOL", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


class ProxyPool:
    """代理池：round_robin / random 轮换 + 连续失败剔除。"""

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        strategy: str = "round_robin",
        max_failures: int = 3,
        enabled: bool = True,
    ) -> None:
        self._proxies = list(proxies if proxies is not None else load_proxies_from_env())
        self.strategy = strategy
        self.max_failures = max_failures
        self.enabled = enabled
        self._index = 0
        self._failures: dict[str, int] = {}

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def available_proxies(self) -> List[str]:
        """未达失败阈值的代理列表。"""
        return [
            proxy
            for proxy in self._proxies
            if self._failures.get(proxy, 0) < self.max_failures
        ]

    @property
    def available_count(self) -> int:
        return len(self.available_proxies())

    def has_proxies(self) -> bool:
        return self.available_count > 0

    # ------------------------------------------------------------------ #
    # 取用与反馈
    # ------------------------------------------------------------------ #
    def next(self) -> Optional[str]:
        """取下一个可用代理；池为空 / 关闭时返回 None（走直连）。"""
        if not self.enabled:
            return None
        pool = self.available_proxies()
        if not pool:
            return None
        if self.strategy == "random":
            return random.choice(pool)
        proxy = pool[self._index % len(pool)]
        self._index += 1
        return proxy

    def record_success(self, proxy: Optional[str]) -> None:
        """成功：重置该代理的连续失败计数。"""
        if proxy:
            self._failures.pop(proxy, None)

    def record_failure(self, proxy: Optional[str]) -> None:
        """失败：累计连续失败；达到阈值剔除（不再返回）。"""
        if not proxy:
            return
        self._failures[proxy] = self._failures.get(proxy, 0) + 1
        if self._failures[proxy] >= self.max_failures:
            logger.warning("代理连续失败已剔除: %s", proxy)


_global_pool: Optional[ProxyPool] = None


def get_global_pool() -> ProxyPool:
    """进程级共享代理池（懒加载，环境变量配置）。"""
    global _global_pool
    if _global_pool is None:
        _global_pool = ProxyPool()
    return _global_pool
