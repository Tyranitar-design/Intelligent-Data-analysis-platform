# -*- coding: utf-8 -*-
"""
Scrapling 适配器 — 封装 Scrapling 反爬绕过能力

功能:
- StealthySession: 模拟真实浏览器，绕过 Cloudflare/Turnstile
- 智能页面解析: CSS/XPath 选择器
- 自动等待动态内容加载
- 与 BaseCrawler 无缝集成

依赖: scrapling>=0.4.7
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ScraplingConfig:
    """Scrapling 配置"""
    # 是否启用 Scrapling（默认开启）
    enabled: bool = True
    # 网络闲置等待时间（秒），用于判断页面加载完成
    network_idle: bool = True
    # 超时时间（秒）
    timeout: int = 30
    # 是否绕过 Cloudflare
    bypass_cloudflare: bool = True
    # 是否自动等待动态内容
    wait_for_selector: Optional[str] = None
    # 页面滚动加载（适用于无限滚动页面）
    auto_scroll: bool = False
    # 请求头
    custom_headers: Dict[str, str] = field(default_factory=dict)


class ScraplingAdapter:
    """
    Scrapling 适配器

    封装 Scrapling 的核心能力，提供:
    1. 反爬绕过（Cloudflare、Turnstile 等）
    2. 智能页面解析
    3. 动态内容渲染
    """

    def __init__(self, config: ScraplingConfig = None):
        self.config = config or ScraplingConfig()
        self._available = False
        self._check_availability()

    def _check_availability(self):
        """检查 Scrapling 是否可用"""
        self._stealthy_available = False
        try:
            from scrapling import Fetcher
            self._available = True
            logger.info("✅ Scrapling Fetcher 可用")
        except ImportError:
            self._available = False
            logger.warning("⚠️ Scrapling 未安装，反爬绕过功能不可用")
            return

        # 检查 StealthyFetcher（可选，需要额外依赖）
        try:
            from scrapling import StealthyFetcher
            self._stealthy_available = True
            logger.info("✅ Scrapling StealthyFetcher 可用")
        except ImportError:
            logger.info("ℹ️ StealthyFetcher 不可用（需要安装 patchright/camoufox），反爬绕过降级为 Fetcher 模式")

    @property
    def available(self) -> bool:
        """Scrapling 是否可用"""
        return self._available and self.config.enabled

    @property
    def stealthy_available(self) -> bool:
        """StealthyFetcher 是否可用"""
        return self._stealthy_available

    async def fetch_page(
        self,
        url: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        wait_for: str = None,
        auto_scroll: bool = None,
        timeout: int = None,
    ) -> Optional["scrapling.Response"]:
        """
        使用 Scrapling 获取页面

        Args:
            url: 目标 URL
            method: HTTP 方法
            headers: 自定义请求头
            wait_for: CSS 选择器，等待该元素出现
            auto_scroll: 是否自动滚动（覆盖配置）
            timeout: 超时时间（覆盖配置）

        Returns:
            Scrapling Response 对象，失败返回 None
        """
        if not self.available:
            logger.warning("Scrapling 不可用，请先安装")
            return None

        try:
            from scrapling import Fetcher

            # 合并请求头
            request_headers = {**self.config.custom_headers}
            if headers:
                request_headers.update(headers)

            # 使用 Fetcher（轻量级，适合大多数场景）
            fetcher = Fetcher(auto_match=False)

            response = fetcher.get(
                url,
                headers=request_headers or None,
            )

            if response:
                logger.info(f"✅ Scrapling 获取成功: {url} (状态: {response.status})")
                return response
            else:
                logger.warning(f"⚠️ Scrapling 获取失败: {url}")
                return None

        except Exception as e:
            logger.error(f"❌ Scrapling 请求异常: {e}")
            return None

    async def fetch_stealthy(
        self,
        url: str,
        wait_for: str = None,
        auto_scroll: bool = None,
        timeout: int = None,
        headless: bool = True,
    ) -> Optional["scrapling.Response"]:
        """
        使用 StealthyFetcher 获取页面（反爬绕过模式）

        适用于:
        - Cloudflare 保护的网站
        - Turnstile 验证
        - 需要浏览器指纹的网站
        - 动态 JavaScript 渲染的内容

        Args:
            url: 目标 URL
            wait_for: CSS 选择器，等待该元素出现
            auto_scroll: 是否自动滚动
            timeout: 超时时间
            headless: 是否无头模式

        Returns:
            Scrapling Response 对象，失败返回 None
        """
        if not self.available:
            logger.warning("Scrapling 不可用，请先安装")
            return None

        if not self.stealthy_available:
            logger.warning("StealthyFetcher 不可用，回退到 Fetcher 模式")
            return await self.fetch_page(url=url, headers=self.config.custom_headers or None)

        try:
            from scrapling import StealthyFetcher

            # 构建参数
            kwargs = {
                "url": url,
                "headless": headless,
            }

            if wait_for:
                kwargs["wait_selector"] = wait_for
            if auto_scroll is not None:
                kwargs["auto_scroll"] = auto_scroll
            elif self.config.auto_scroll:
                kwargs["auto_scroll"] = True

            # 设置超时
            timeout_val = timeout or self.config.timeout

            response = await StealthyFetcher.async_fetch(**kwargs)

            if response:
                logger.info(f"✅ StealthyFetcher 获取成功: {url} (状态: {response.status})")
                return response
            else:
                logger.warning(f"⚠️ StealthyFetcher 获取失败: {url}")
                return None

        except Exception as e:
            logger.error(f"❌ StealthyFetcher 请求异常: {e}")
            return None

    def parse_elements(
        self,
        response,
        selectors: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        使用 CSS 选择器解析页面元素

        Args:
            response: Scrapling Response 对象
            selectors: {字段名: CSS选择器} 映射

        Returns:
            解析结果字典
        """
        if not response:
            return {}

        result = {}
        for field_name, selector in selectors.items():
            try:
                elements = response.css(selector)
                if elements:
                    # 多元素取文本列表，单元素取文本
                    texts = [el.text.strip() for el in elements if el.text]
                    result[field_name] = texts[0] if len(texts) == 1 else texts
                else:
                    result[field_name] = None
            except Exception as e:
                logger.warning(f"解析字段 '{field_name}' 失败 (选择器: {selector}): {e}")
                result[field_name] = None

        return result

    def parse_list(
        self,
        response,
        container_selector: str,
        item_selectors: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        解析列表数据（如商品列表、新闻列表）

        Args:
            response: Scrapling Response 对象
            container_selector: 列表项容器的 CSS 选择器
            item_selectors: 每个列表项的字段选择器映射

        Returns:
            解析结果列表
        """
        if not response:
            return []

        results = []
        try:
            containers = response.css(container_selector)
            for container in containers:
                item = {}
                for field_name, selector in item_selectors.items():
                    try:
                        el = container.css(selector)
                        if el:
                            if isinstance(el, list):
                                item[field_name] = [e.text.strip() for e in el if e.text]
                            else:
                                # 处理属性提取（如 href, src）
                                if "::attr(" in selector:
                                    attr_name = selector.split("::attr(")[-1].rstrip(")")
                                    item[field_name] = el.attrib.get(attr_name, "").strip()
                                elif "::text" in selector:
                                    item[field_name] = el.text.strip() if el.text else None
                                else:
                                    item[field_name] = el.text.strip() if el.text else None
                        else:
                            item[field_name] = None
                    except Exception as e:
                        logger.warning(f"解析字段 '{field_name}' 失败: {e}")
                        item[field_name] = None
                results.append(item)
        except Exception as e:
            logger.error(f"解析列表失败: {e}")

        return results

    def get_page_text(self, response) -> Optional[str]:
        """获取页面纯文本"""
        if not response:
            return None
        try:
            return response.get_all_text() if hasattr(response, 'get_all_text') else response.text
        except Exception:
            return response.text if hasattr(response, 'text') else None

    def get_page_html(self, response) -> Optional[str]:
        """获取页面 HTML"""
        if not response:
            return None
        try:
            return response.html if hasattr(response, 'html') else str(response)
        except Exception:
            return None
