# -*- coding: utf-8 -*-
"""
反爬策略增强模块 - 智能数据采集反反爬系统

提供完整的反反爬能力：
1. 代理池管理 - 代理轮换、可用性检测
2. Cookie管理 - 自动维护会话状态
3. 浏览器指纹 - 生成真实浏览器特征
4. 请求策略 - 智能调度和降级
5. IP轮换 - 多IP分布式采集

作者: Claude Code
日期: 2026-04-24
"""
import asyncio
import hashlib
import json
import random
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ==================== 数据类定义 ====================

@dataclass
class Proxy:
    """代理配置"""
    ip: str
    port: int
    protocol: str = "http"  # http, https, socks5
    username: Optional[str] = None
    password: Optional[str] = None
    score: float = 100.0  # 可用性评分
    fail_count: int = 0  # 失败次数
    success_count: int = 0  # 成功次数
    last_check: Optional[datetime] = None  # 最后检测时间
    region: Optional[str] = None  # 地区
    anonymous: bool = True  # 是否高匿

    @property
    def url(self) -> str:
        """生成代理URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.ip}:{self.port}"
        return f"{self.protocol}://{self.ip}:{self.port}"

    @property
    def is_available(self) -> bool:
        """是否可用"""
        return self.fail_count < 5 and self.score > 30


@dataclass
class Cookie:
    """Cookie配置"""
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[datetime] = None
    http_only: bool = False
    secure: bool = False
    same_site: str = "Lax"


@dataclass
class RequestContext:
    """请求上下文"""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    proxy: Optional[Proxy] = None
    fingerprint: Optional[Dict] = None
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


# ==================== 浏览器指纹生成器 ====================

class BrowserFingerprint:
    """浏览器指纹生成器"""

    # 真实浏览器 User-Agent 列表
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",

        # Chrome on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",

        # Firefox on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",

        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",

        # Safari on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]

    # Accept-Language 列表
    ACCEPT_LANGUAGES = [
        "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "zh-CN,zh;q=0.9,en;q=0.8",
        "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7",
        "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
        "en-US,en;q=0.9,zh-CN;q=0.8",
        "en-GB,en;q=0.9,zh-CN;q=0.8",
    ]

    # Accept 列表
    ACCEPTS = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    ]

    # 平台信息
    PLATFORMS = [
        "Win32",
        "MacIntel",
        "Linux x86_64",
        "Windows NT 10.0; Win64; x64",
        "Windows NT 10.0; Win64; x64; rv:123.0",
    ]

    @classmethod
    def generate_headers(cls, referer: Optional[str] = None, domain: Optional[str] = None) -> Dict[str, str]:
        """生成随机但真实的请求头"""
        headers = {
            "User-Agent": random.choice(cls.USER_AGENTS),
            "Accept": random.choice(cls.ACCEPTS),
            "Accept-Language": random.choice(cls.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        # 添加 Referer（如果提供）
        if referer:
            headers["Referer"] = referer
        elif domain:
            headers["Referer"] = f"https://{domain}/"

        # 随机添加一些可选头
        if random.random() > 0.5:
            headers["DNT"] = str(random.randint(1, 2))

        if random.random() > 0.3:
            headers["Sec-Ch-Ua"] = '"Chromium";v="123", "Not:A_Brand";v="8", "Google Chrome";v="123"'
            headers["Sec-Ch-Ua-Mobile"] = "?0"
            headers["Sec-Ch-Ua-Platform"] = '"Windows"'

        return headers

    @classmethod
    def generate_fingerprint(cls) -> Dict[str, Any]:
        """生成浏览器指纹信息"""
        return {
            "screen_resolution": random.choice(["1920x1080", "1366x768", "2560x1440", "3840x2160"]),
            "color_depth": random.choice([24, 32]),
            "timezone": random.choice(["Asia/Shanghai", "Asia/Hong_Kong", "America/New_York", "Europe/London"]),
            "timezone_offset": random.choice([-480, -420, -360, 0, 480, 540]),
            "language": random.choice(["zh-CN", "en-US", "zh-TW", "ja-JP"]),
            "platform": random.choice(cls.PLATFORMS),
            "cookies_enabled": True,
            "do_not_track": random.choice([True, False, None]),
            "plugins": ["Chrome PDF Plugin", "Chrome PDF Viewer", "Native Client"],
            "webgl_vendor": random.choice(["Google Inc. (NVIDIA)", "Google Inc. (Intel)", "Google Inc. (AMD)"]),
            "webgl_renderer": random.choice(["ANGLE (NVIDIA GeForce GTX 1060)", "ANGLE (Intel UHD Graphics 620)", "ANGLE (AMD Radeon RX 580)"]),
        }


# ==================== 代理池管理器 ====================

class ProxyPool:
    """代理池管理器"""

    def __init__(
        self,
        initial_proxies: List[Dict] = None,
        max_pool_size: int = 100,
        check_interval: int = 300,
        min_score: float = 30.0
    ):
        """
        初始化代理池

        Args:
            initial_proxies: 初始代理列表
            max_pool_size: 最大代理池大小
            check_interval: 检测间隔（秒）
            min_score: 最低可用评分
        """
        self.proxies: Dict[str, Proxy] = {}
        self.max_pool_size = max_pool_size
        self.check_interval = check_interval
        self.min_score = min_score
        self._lock = asyncio.Lock()
        self._use_history = deque(maxlen=1000)  # 使用历史记录

        # 添加初始代理
        if initial_proxies:
            for p in initial_proxies:
                self.add_proxy(p)

    def add_proxy(self, proxy_info: Dict) -> bool:
        """添加代理"""
        try:
            proxy = Proxy(
                ip=proxy_info["ip"],
                port=proxy_info["port"],
                protocol=proxy_info.get("protocol", "http"),
                username=proxy_info.get("username"),
                password=proxy_info.get("password"),
                region=proxy_info.get("region"),
                anonymous=proxy_info.get("anonymous", True),
            )
            key = proxy.url
            self.proxies[key] = proxy
            logger.info(f"添加代理: {key}")
            return True
        except Exception as e:
            logger.error(f"添加代理失败: {e}")
            return False

    async def get_proxy(self, strategy: str = "random") -> Optional[Proxy]:
        """
        获取可用代理

        Args:
            strategy: 获取策略 (random, score, least_used, region)

        Returns:
            可用代理或None
        """
        async with self._lock:
            available = [p for p in self.proxies.values() if p.is_available]

            if not available:
                return None

            if strategy == "random":
                return random.choice(available)
            elif strategy == "score":
                return max(available, key=lambda p: p.score)
            elif strategy == "least_used":
                return min(available, key=lambda p: p.success_count)
            else:
                return random.choice(available)

    async def report_proxy_result(self, proxy: Proxy, success: bool, response_time: float = None):
        """汇报代理使用结果"""
        async with self._lock:
            if success:
                proxy.success_count += 1
                proxy.fail_count = 0
                proxy.score = min(100, proxy.score + 2)
            else:
                proxy.fail_count += 1
                proxy.score = max(0, proxy.score - 10)

            proxy.last_check = datetime.now()

            self._use_history.append({
                "proxy": proxy.url,
                "success": success,
                "time": datetime.now()
            })

    async def remove_proxy(self, proxy: Proxy):
        """移除代理"""
        async with self._lock:
            key = proxy.url
            if key in self.proxies:
                del self.proxies[key]
                logger.info(f"移除代理: {key}")

    async def check_proxies(self, test_url: str = "https://www.baidu.com"):
        """检测所有代理可用性"""
        import httpx

        async with self._lock:
            tasks = []
            for proxy in self.proxies.values():
                tasks.append(self._check_single_proxy(proxy, test_url))

            await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_single_proxy(self, proxy: Proxy, test_url: str) -> bool:
        """检测单个代理"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(test_url, proxies={"http": proxy.url, "https": proxy.url})
                if response.status_code == 200:
                    await self.report_proxy_result(proxy, True)
                    return True
        except Exception:
            await self.report_proxy_result(proxy, False)
        return False

    def get_stats(self) -> Dict:
        """获取代理池统计"""
        total = len(self.proxies)
        available = sum(1 for p in self.proxies.values() if p.is_available)
        avg_score = sum(p.score for p in self.proxies.values()) / max(total, 1)

        return {
            "total": total,
            "available": available,
            "unavailable": total - available,
            "avg_score": avg_score,
        }


# ==================== Cookie管理器 ====================

class CookieManager:
    """Cookie管理器"""

    def __init__(self, storage_path: str = None):
        """
        初始化Cookie管理器

        Args:
            storage_path: Cookie持久化路径
        """
        self.storage_path = storage_path
        self.cookies: Dict[str, List[Cookie]] = {}  # domain -> cookies
        self._lock = asyncio.Lock()
        self._load_cookies()

    def add_cookie(
        self,
        domain: str,
        name: str,
        value: str,
        **kwargs
    ):
        """添加Cookie"""
        cookie = Cookie(name=name, value=value, domain=domain, **kwargs)

        if domain not in self.cookies:
            self.cookies[domain] = []

        # 检查是否已存在
        for i, c in enumerate(self.cookies[domain]):
            if c.name == name:
                self.cookies[domain][i] = cookie
                return

        self.cookies[domain].append(cookie)
        self._save_cookies()

    def get_cookies(self, domain: str) -> Dict[str, str]:
        """获取域名的所有Cookie（字典格式）"""
        if domain not in self.cookies:
            return {}

        result = {}
        for cookie in self.cookies[domain]:
            # 检查过期
            if cookie.expires and cookie.expires < datetime.now():
                continue
            result[cookie.name] = cookie.value

        return result

    def update_from_response(self, domain: str, set_cookie_header: str):
        """从响应头更新Cookie"""
        # 解析Set-Cookie头
        parts = set_cookie_header.split(";")
        if not parts:
            return

        first_part = parts[0].strip()
        if "=" not in first_part:
            return

        name, value = first_part.split("=", 1)

        cookie_kwargs = {"domain": domain}
        for part in parts[1:]:
            part = part.strip().lower()
            if part.startswith("expires="):
                try:
                    cookie_kwargs["expires"] = datetime.fromisoformat(part[8:])
                except:
                    pass
            elif part == "httponly":
                cookie_kwargs["http_only"] = True
            elif part == "secure":
                cookie_kwargs["secure"] = True
            elif part.startswith("path="):
                cookie_kwargs["path"] = part[5:]

        self.add_cookie(domain, name.strip(), value.strip(), **cookie_kwargs)

    def _save_cookies(self):
        """保存Cookie到文件"""
        if not self.storage_path:
            return

        try:
            data = {}
            for domain, cookies in self.cookies.items():
                data[domain] = [
                    {
                        "name": c.name,
                        "value": c.value,
                        "path": c.path,
                        "expires": c.expires.isoformat() if c.expires else None,
                        "http_only": c.http_only,
                        "secure": c.secure,
                    }
                    for c in cookies
                ]

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")

    def _load_cookies(self):
        """从文件加载Cookie"""
        if not self.storage_path:
            return

        try:
            if not os.path.exists(self.storage_path):
                return

            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for domain, cookies_data in data.items():
                self.cookies[domain] = []
                for cd in cookies_data:
                    cookie = Cookie(
                        name=cd["name"],
                        value=cd["value"],
                        domain=domain,
                        path=cd.get("path", "/"),
                        expires=datetime.fromisoformat(cd["expires"]) if cd.get("expires") else None,
                        http_only=cd.get("http_only", False),
                        secure=cd.get("secure", False),
                    )
                    self.cookies[domain].append(cookie)
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")


# ==================== 请求策略调度器 ====================

class RequestStrategy:
    """请求策略调度器"""

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 1.5,
        jitter: float = 0.3
    ):
        """
        初始化请求策略

        Args:
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            backoff_factor: 退避因子
            jitter: 随机抖动因子
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self._request_times: Dict[str, deque] = {}  # 每个域名的请求时间记录
        self._lock = asyncio.Lock()

    async def wait_before_request(self, domain: str):
        """请求前等待"""
        async with self._lock:
            if domain not in self._request_times:
                self._request_times[domain] = deque(maxlen=100)

            now = time.time()
            times = self._request_times[domain]

            if times:
                last_time = times[-1]
                elapsed = now - last_time

                if elapsed < self.base_delay:
                    wait_time = self.base_delay - elapsed
                    # 添加随机抖动
                    wait_time *= (1 + random.uniform(-self.jitter, self.jitter))
                    await asyncio.sleep(max(0, wait_time))

            times.append(time.time())

    async def get_delay_after_failure(self, retry_count: int) -> float:
        """获取失败后的延迟时间（指数退避）"""
        delay = min(
            self.base_delay * (self.backoff_factor ** retry_count),
            self.max_delay
        )
        # 添加随机抖动
        delay *= (1 + random.uniform(-self.jitter, self.jitter))
        return delay

    async def record_success(self, domain: str):
        """记录成功请求"""
        async with self._lock:
            if domain in self._request_times:
                # 成功时稍微减少延迟
                pass

    async def record_failure(self, domain: str):
        """记录失败请求"""
        async with self._lock:
            # 可以在这里增加失败计数，后续降低请求频率
            pass


# ==================== IP轮换管理器 ====================

class IPRotation:
    """IP轮换管理器"""

    def __init__(
        self,
        proxy_pool: ProxyPool = None,
        local_ips: List[str] = None,
        rotation_interval: int = 60
    ):
        """
        初始化IP轮换器

        Args:
            proxy_pool: 代理池
            local_ips: 本地IP列表（多网卡）
            rotation_interval: 轮换间隔（秒）
        """
        self.proxy_pool = proxy_pool
        self.local_ips = local_ips or []
        self.rotation_interval = rotation_interval
        self._current_index = 0
        self._last_rotation = time.time()
        self._lock = asyncio.Lock()

    async def get_next_ip(self) -> Optional[Dict]:
        """
        获取下一个IP

        Returns:
            {"type": "proxy", "url": "..."} 或 {"type": "direct"}
        """
        async with self._lock:
            now = time.time()

            # 检查是否需要轮换
            if now - self._last_rotation > self.rotation_interval:
                self._current_index = (self._current_index + 1) % max(1, len(self.local_ips))
                self._last_rotation = now

            # 如果有代理池，使用代理
            if self.proxy_pool:
                proxy = await self.proxy_pool.get_proxy()
                if proxy:
                    return {
                        "type": "proxy",
                        "url": proxy.url,
                        "proxy_obj": proxy
                    }

            # 否则使用本地IP
            if self.local_ips:
                return {
                    "type": "direct",
                    "local_ip": self.local_ips[self._current_index]
                }

            return {"type": "direct"}


# ==================== 反爬策略增强类 ====================

class AntiCrawlerEnhancer:
    """
    反爬策略增强器

    提供完整的反反爬能力集成
    """

    def __init__(
        self,
        config: Dict[str, Any] = None
    ):
        """
        初始化反爬策略增强器

        Args:
            config: 配置字典
        """
        config = config or {}

        # 初始化各个组件
        self.fingerprint = BrowserFingerprint()
        self.proxy_pool = ProxyPool(
            initial_proxies=config.get("proxies", []),
            max_pool_size=config.get("max_pool_size", 100)
        )
        self.cookie_manager = CookieManager(
            storage_path=config.get("cookie_storage")
        )
        self.request_strategy = RequestStrategy(
            base_delay=config.get("base_delay", 1.0),
            max_delay=config.get("max_delay", 60.0)
        )
        self.ip_rotation = IPRotation(
            proxy_pool=self.proxy_pool if config.get("use_proxy") else None,
            rotation_interval=config.get("rotation_interval", 60)
        )

        # 配置
        self.config = config
        self._domains: Dict[str, int] = {}  # 域名请求计数

    def generate_headers(
        self,
        url: str,
        referer: Optional[str] = None
    ) -> Dict[str, str]:
        """生成请求头"""
        domain = urlparse(url).netloc
        return self.fingerprint.generate_headers(referer=referer, domain=domain)

    async def prepare_request(self, url: str, context: RequestContext = None) -> RequestContext:
        """
        准备请求上下文

        Args:
            url: 请求URL
            context: 已有上下文

        Returns:
            更新后的请求上下文
        """
        if context is None:
            context = RequestContext(url=url)

        domain = urlparse(url).netloc

        # 生成请求头
        context.headers = self.generate_headers(url, referer=context.headers.get("Referer"))

        # 添加Cookie
        cookies = self.cookie_manager.get_cookies(domain)
        context.cookies.update(cookies)

        # 获取代理
        ip_info = await self.ip_rotation.get_next_ip()
        if ip_info.get("type") == "proxy":
            context.proxy = ip_info.get("proxy_obj")

        # 生成指纹
        context.fingerprint = self.fingerprint.generate_fingerprint()

        # 更新域名计数
        self._domains[domain] = self._domains.get(domain, 0) + 1

        return context

    async def on_request_success(self, url: str, response_time: float = None):
        """请求成功回调"""
        domain = urlparse(url).netloc
        await self.request_strategy.record_success(domain)

        # 如果使用了代理，汇报结果
        if self.ip_rotation.proxy_pool:
            proxy = self.ip_rotation.proxy_pool.proxies.get(url)
            if proxy:
                await self.proxy_pool.report_proxy_result(proxy, True, response_time)

    async def on_request_failure(
        self,
        url: str,
        status_code: int = None,
        error: Exception = None
    ):
        """请求失败回调"""
        domain = urlparse(url).netloc

        # 更新请求策略
        self._domains[domain] = self._domains.get(domain, 0) + 1

        # 如果使用了代理，汇报结果
        if self.ip_rotation.proxy_pool:
            proxy = self.ip_rotation.proxy_pool.proxies.get(url)
            if proxy:
                await self.proxy_pool.report_proxy_result(proxy, False)

        # 根据状态码调整策略
        if status_code:
            if status_code == 403:
                logger.warning(f"403 禁止访问: {url}")
            elif status_code == 418:
                logger.warning(f"418 我是机器人: {url}")
            elif status_code == 429:
                logger.warning(f"429 请求过多: {url}")

    async def wait_before_request(self, url: str):
        """请求前等待"""
        domain = urlparse(url).netloc
        await self.request_strategy.wait_before_request(domain)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "proxy_pool": self.proxy_pool.get_stats() if self.proxy_pool else {},
            "domains": self._domains.copy(),
            "config": {
                "use_proxy": bool(self.proxy_pool.proxies) if self.proxy_pool else False,
                "base_delay": self.request_strategy.base_delay,
            }
        }


# ==================== 便捷函数 ====================

# 默认增强器实例
_default_enhancer: Optional[AntiCrawlerEnhancer] = None


def get_enhancer(config: Dict = None) -> AntiCrawlerEnhancer:
    """获取默认增强器实例"""
    global _default_enhancer
    if _default_enhancer is None or config:
        _default_enhancer = AntiCrawlerEnhancer(config)
    return _default_enhancer


def enhance_headers(url: str, referer: str = None) -> Dict[str, str]:
    """便捷函数：生成增强的请求头"""
    enhancer = get_enhancer()
    return enhancer.generate_headers(url, referer)


# ==================== 导入缺失的模块 ====================
import os
