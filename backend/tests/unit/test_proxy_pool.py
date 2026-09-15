# -*- coding: utf-8 -*-
"""代理池 · 单元测试（纯逻辑，无网络）

覆盖：轮换顺序 / 失败剔除 / 成功重置 / 空池降级 / env 加载。
"""
from __future__ import annotations

import pytest

from crawlers.anticrawl.proxy_pool import ProxyPool, load_proxies_from_env

P1 = "http://user:pass@proxy1.example:8080"
P2 = "http://proxy2.example:8080"
P3 = "socks5://proxy3.example:1080"


def test_round_robin_order():
    pool = ProxyPool([P1, P2, P3], strategy="round_robin")
    picks = [pool.next() for _ in range(4)]
    assert picks == [P1, P2, P3, P1]


def test_random_strategy_stays_in_pool():
    pool = ProxyPool([P1, P2], strategy="random")
    picks = {pool.next() for _ in range(20)}
    assert picks <= {P1, P2}
    assert len(picks) >= 2  # 20 次里两个都出现（概率上）


def test_failure_eviction():
    pool = ProxyPool([P1], max_failures=3, strategy="round_robin")
    for _ in range(3):
        assert pool.next() == P1
        pool.record_failure(P1)
    # P1 被剔除后无可用代理
    assert pool.next() is None
    assert pool.available_count == 0


def test_success_resets_failures():
    pool = ProxyPool([P1], max_failures=3, strategy="round_robin")
    pool.record_failure(P1)
    pool.record_failure(P1)
    pool.record_success(P1)  # 重置计数
    pool.record_failure(P1)
    pool.record_failure(P1)
    # 仍可用（未达连续 3 次）
    assert pool.available_count == 1
    assert pool.next() == P1


def test_empty_pool_returns_none():
    pool = ProxyPool([])
    assert pool.has_proxies() is False
    assert pool.next() is None
    assert pool.available_count == 0


def test_load_from_env(monkeypatch):
    monkeypatch.setenv("PROXY_POOL", f"{P1},{P2}")
    assert load_proxies_from_env() == [P1, P2]
    monkeypatch.delenv("PROXY_POOL")
    assert load_proxies_from_env() == []


def test_disabled_pool(monkeypatch):
    """enabled=False 时不取代理（显式关闭）。"""
    pool = ProxyPool([P1], enabled=False)
    assert pool.next() is None
