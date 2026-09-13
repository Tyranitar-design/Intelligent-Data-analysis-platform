# -*- coding: utf-8 -*-
"""
分布式采集引擎 - 支持大规模并发采集

特性:
- asyncio 并发控制 (Semaphore)
- 任务队列 + Worker 模式
- 自动重试 + 指数退避
- 结果自动入库
- 速率限制 (per-domain)
- 进度追踪
- 统计报告
"""
import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional
from urllib.parse import urlparse

from .base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)


@dataclass(order=False)
class CrawlTask:
    """采集任务"""
    task_id: str
    source: str
    func: str  # 爬虫方法名
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: int = 0  # 0=普通, 1=高, -1=低
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    _seq: int = 0

    # 用于优先级队列排序
    def __lt__(self, other):
        return (self.priority, self._seq) < (other.priority, other._seq)


@dataclass
class CrawlStats:
    """采集统计"""
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    total_records: int = 0
    total_bytes: int = 0
    start_time: float = 0
    end_time: float = 0
    errors: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_source: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def elapsed(self) -> float:
        return (self.end_time or time.time()) - (self.start_time or time.time())

    @property
    def success_rate(self) -> float:
        return self.completed / max(self.total_tasks, 1) * 100

    @property
    def throughput(self) -> float:
        """每秒处理任务数"""
        elapsed = self.elapsed
        return self.total_tasks / max(elapsed, 0.001)

    def to_dict(self) -> Dict:
        return {
            "total_tasks": self.total_tasks,
            "completed": self.completed,
            "failed": self.failed,
            "success_rate": round(self.success_rate, 2),
            "total_records": self.total_records,
            "elapsed_seconds": round(self.elapsed, 2),
            "throughput_tps": round(self.throughput, 2),
            "by_source": dict(self.by_source),
            "top_errors": dict(sorted(self.errors.items(), key=lambda x: x[1], reverse=True)[:10]),
        }


class DistributedCrawler:
    """
    分布式采集引擎

    支持大规模并发采集，自动入库，统计追踪
    """

    def __init__(
        self,
        max_concurrency: int = 2,  # 大幅降低并发，避免被封
        per_domain_delay: float = 5.0,  # 增加同域名最小间隔到 5 秒
        max_per_domain_rps: float = 0.2,  # 同域名最大每秒请求数
        auto_save_db: bool = True,
    ):
        """
        Args:
            max_concurrency: 最大并发数（已降低避免封号）
            per_domain_delay: 同域名最小间隔（已增加）
            max_per_domain_rps: 同域名最大每秒请求数
            auto_save_db: 是否自动保存到数据库
        """
        self.max_concurrency = max_concurrency
        self.per_domain_delay = per_domain_delay
        self.auto_save_db = auto_save_db

        # 并发控制
        self._semaphore = asyncio.Semaphore(max_concurrency)

        # 域名级别速率限制
        self._domain_locks: Dict[str, asyncio.Lock] = {}
        self._domain_last_request: Dict[str, float] = {}

        # 任务队列
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._results: List[CrawlResult] = []
        self._stats = CrawlStats()
        self._task_seq = 0

        # 爬虫实例缓存
        self._crawlers: Dict[str, BaseCrawler] = {}

    def register_crawler(self, name: str, crawler: BaseCrawler):
        """注册爬虫实例"""
        self._crawlers[name] = crawler

    def add_task(
        self,
        source: str,
        func: str,
        args: tuple = (),
        kwargs: dict = None,
        priority: int = 0,
    ):
        """添加采集任务"""
        kwargs = kwargs or {}
        task_id = f"{source}_{func}_{len(self._results)}"
        task = CrawlTask(
            task_id=task_id,
            source=source,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            _seq=self._task_seq,
        )
        self._task_seq += 1
        self._task_queue.put_nowait((priority, self._task_seq, task))

    async def _get_domain_lock(self, url: str) -> asyncio.Lock:
        """获取域名级别的锁"""
        domain = urlparse(url).netloc
        if domain not in self._domain_locks:
            self._domain_locks[domain] = asyncio.Lock()
        return self._domain_locks[domain]

    async def _wait_for_domain(self, url: str):
        """等待域名速率限制"""
        domain = urlparse(url).netloc
        lock = await self._get_domain_lock(url)

        async with lock:
            last = self._domain_last_request.get(domain, 0)
            now = time.time()
            wait = self.per_domain_delay - (now - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._domain_last_request[domain] = time.time()

    async def _execute_task(self, task: CrawlTask) -> CrawlResult:
        """执行单个任务"""
        crawler = self._crawlers.get(task.source)
        if not crawler:
            return CrawlResult(
                success=False, data=[], message=f"Unknown source: {task.source}",
                source=task.source, error=f"crawler '{task.source}' not registered"
            )

        method = getattr(crawler, task.func, None)
        if not method or not callable(method):
            return CrawlResult(
                success=False, data=[], message=f"Unknown method: {task.func}",
                source=task.source, error=f"method '{task.func}' not found"
            )

        try:
            # 并发控制
            async with self._semaphore:
                result = await method(*task.args, **task.kwargs)

                if isinstance(result, CrawlResult):
                    # 自动入库
                    if self.auto_save_db and result.success and result.data:
                        try:
                            result.save_to_db(platform=task.source)
                        except Exception as e:
                            logger.warning(f"Auto save to DB failed: {e}")

                    return result
                else:
                    return CrawlResult(
                        success=False, data=[], message="Unexpected return type",
                        source=task.source
                    )

        except Exception as e:
            return CrawlResult(
                success=False, data=[], message=str(e),
                source=task.source, error=str(e)
            )

    async def run(self, task_count: int = 0) -> CrawlStats:
        """
        运行采集引擎

        Args:
            task_count: 预期任务数 (0=自动检测)
        """
        self._stats = CrawlStats(start_time=time.time())

        workers = []
        for _ in range(min(self.max_concurrency, 5)):
            workers.append(asyncio.create_task(self._worker()))

        # 等待所有任务完成
        # 如果 task_count 已知，等待对应数量的结果
        if task_count > 0:
            while len(self._results) < task_count:
                await asyncio.sleep(0.5)
        else:
            # 等待队列清空 + 所有 worker 空闲
            while not self._task_queue.empty():
                await asyncio.sleep(0.5)
            await asyncio.sleep(2)  # 等待最后几个

        # 停止 workers
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

        self._stats.end_time = time.time()
        return self._stats

    async def _worker(self):
        """工作线程"""
        while True:
            try:
                priority, seq, task = await asyncio.wait_for(
                    self._task_queue.get(), timeout=5.0
                )
            except asyncio.TimeoutError:
                continue

            self._stats.total_tasks += 1

            try:
                result = await self._execute_task(task)

                self._results.append(result)

                if result.success:
                    self._stats.completed += 1
                    self._stats.total_records += result.count
                    self._stats.by_source[result.source] += result.count
                else:
                    self._stats.failed += 1
                    error_msg = result.error or result.message
                    self._stats.errors[str(error_msg)[:50]] += 1

                    # 自动重试
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        self._task_seq += 1
                        self._task_queue.put_nowait((priority - 1, self._task_seq, task))

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._stats.failed += 1
                self._stats.errors[str(e)[:50]] += 1


# ==================== 便捷函数 ====================

async def crawl_all_stocks(
    stocks: List[Dict],
    days: int = 30,
    concurrency: int = 5,
    auto_save: bool = True,
) -> CrawlStats:
    """
    一键爬取多只股票

    Args:
        stocks: [{"code": "600519", "name": "贵州茅台", "market": "sh"}, ...]
        days: K线天数
        concurrency: 并发数
        auto_save: 自动入库

    Returns:
        统计结果
    """
    from .finance.eastmoney import EastMoneyCrawler

    crawler = EastMoneyCrawler()
    engine = DistributedCrawler(
        max_concurrency=concurrency,
        auto_save_db=auto_save
    )
    engine.register_crawler("eastmoney", crawler)

    for stock in stocks:
        code = stock.get("code", "")
        market = stock.get("market", "sh" if code.startswith("6") else "sz")
        engine.add_task("eastmoney", "crawl_stock_kline", args=(code, days, market))

    stats = await engine.run(task_count=len(stocks))
    return stats


async def crawl_all_news(
    pages: int = 3,
    concurrency: int = 3,
    auto_save: bool = True,
) -> CrawlStats:
    """
    一键爬取多页新闻

    Args:
        pages: 页数
        concurrency: 并发数
        auto_save: 自动入库

    Returns:
        统计结果
    """
    from .news.netease import News36KRCrawler, CLSCrawler

    kr_crawler = News36KRCrawler()
    cls_crawler = CLSCrawler()

    engine = DistributedCrawler(
        max_concurrency=concurrency,
        auto_save_db=auto_save
    )
    engine.register_crawler("36kr", kr_crawler)
    engine.register_crawler("cls", cls_crawler)

    for p in range(1, pages + 1):
        engine.add_task("36kr", "crawl_newsflash", kwargs={"per_page": 30, "page": p})
        engine.add_task("cls", "crawl_telegraph", kwargs={"page": p, "per_page": 30})

    stats = await engine.run(task_count=pages * 2)
    return stats
