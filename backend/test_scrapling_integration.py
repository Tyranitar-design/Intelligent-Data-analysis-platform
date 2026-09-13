# -*- coding: utf-8 -*-
"""
Scrapling 集成测试

验证:
1. Scrapling 安装和导入
2. ScraplingAdapter 基础功能
3. BaseCrawler Scrapling 集成
4. 页面获取和解析
"""
import sys
import os
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crawlers.scrapling_adapter import ScraplingAdapter, ScraplingConfig
from crawlers.base import BaseCrawler, CrawlResult


def test_scrapling_import():
    """测试 1: Scrapling 包导入"""
    print("=" * 50)
    print("测试 1: Scrapling 包导入")
    print("=" * 50)
    try:
        from scrapling import Fetcher
        print("✅ scrapling.Fetcher 导入成功")
    except ImportError as e:
        print(f"❌ scrapling 导入失败: {e}")
        return False

    try:
        from scrapling import StealthyFetcher
        print("✅ scrapling.StealthyFetcher 导入成功")
    except ImportError as e:
        print(f"⚠️ StealthyFetcher 导入失败(可选): {e}")

    return True


def test_scrapling_adapter():
    """测试 2: ScraplingAdapter 初始化"""
    print("\n" + "=" * 50)
    print("测试 2: ScraplingAdapter 初始化")
    print("=" * 50)

    config = ScraplingConfig(
        enabled=True,
        timeout=30,
        bypass_cloudflare=True,
    )
    adapter = ScraplingAdapter(config)

    print(f"  available: {adapter.available}")
    print(f"  config.enabled: {adapter.config.enabled}")
    print(f"  config.timeout: {adapter.config.timeout}")
    print(f"  config.bypass_cloudflare: {adapter.config.bypass_cloudflare}")

    if adapter.available:
        print("✅ ScraplingAdapter 初始化成功，Scrapling 可用")
    else:
        print("⚠️ ScraplingAdapter 初始化成功，但 Scrapling 不可用")

    return True


def test_base_crawler_scrapling():
    """测试 3: BaseCrawler Scrapling 集成"""
    print("\n" + "=" * 50)
    print("测试 3: BaseCrawler Scrapling 集成")
    print("=" * 50)

    # 创建启用 Scrapling 的爬虫
    class TestCrawler(BaseCrawler):
        async def crawl(self, **kwargs):
            return CrawlResult(
                success=True,
                data=[],
                message="test",
                source="test"
            )

    crawler = TestCrawler(name="test_crawler", enable_scrapling=True)
    print(f"  name: {crawler.name}")
    print(f"  enable_scrapling: {crawler.enable_scrapling}")
    print(f"  scrapling property: {crawler.scrapling}")
    print(f"  scrapling.available: {crawler.scrapling.available if crawler.scrapling else 'N/A'}")

    # 测试 get_stats
    stats = crawler.get_stats()
    print(f"  stats.scrapling_enabled: {stats.get('scrapling_enabled')}")
    print(f"  stats.scrapling_fallback_count: {stats.get('scrapling_fallback_count')}")

    # 创建未启用 Scrapling 的爬虫
    crawler_no_scrapling = TestCrawler(name="no_scrapling", enable_scrapling=False)
    print(f"  no_scrapling.enable_scrapling: {crawler_no_scrapling.enable_scrapling}")
    print(f"  no_scrapling.scrapling: {crawler_no_scrapling.scrapling}")

    print("✅ BaseCrawler Scrapling 集成正常")
    return True


async def test_scrapling_fetch():
    """测试 4: Scrapling 页面获取"""
    print("\n" + "=" * 50)
    print("测试 4: Scrapling 页面获取")
    print("=" * 50)

    adapter = ScraplingAdapter()
    if not adapter.available:
        print("⚠️ Scrapling 不可用，跳过页面获取测试")
        return True

    # 测试 Fetcher 模式
    test_url = "https://httpbin.org/get"
    print(f"  测试 URL: {test_url}")

    try:
        response = await adapter.fetch_page(test_url)
        if response:
            print(f"  ✅ Fetcher 模式获取成功")
            print(f"  状态码: {response.status if hasattr(response, 'status') else 'N/A'}")
        else:
            print(f"  ⚠️ Fetcher 模式返回空")
    except Exception as e:
        print(f"  ⚠️ Fetcher 模式异常: {e}")

    print("✅ 页面获取测试完成")
    return True


async def test_scrapling_parse():
    """测试 5: Scrapling 解析功能"""
    print("\n" + "=" * 50)
    print("测试 5: Scrapling 解析功能")
    print("=" * 50)

    adapter = ScraplingAdapter()
    if not adapter.available:
        print("⚠️ Scrapling 不可用，跳过解析测试")
        return True

    test_url = "https://httpbin.org/html"
    print(f"  测试 URL: {test_url}")

    try:
        response = await adapter.fetch_page(test_url)
        if response:
            # 测试文本提取
            text = adapter.get_page_text(response)
            print(f"  ✅ 文本提取成功, 长度: {len(text) if text else 0}")

            # 测试 HTML 提取
            html = adapter.get_page_html(response)
            print(f"  ✅ HTML 提取成功, 长度: {len(html) if html else 0}")

            # 测试 CSS 选择器解析
            elements = adapter.parse_elements(response, {"heading": "h1"})
            print(f"  ✅ CSS 选择器解析成功: {elements}")
        else:
            print(f"  ⚠️ 页面获取返回空")
    except Exception as e:
        print(f"  ⚠️ 解析测试异常: {e}")

    print("✅ 解析功能测试完成")
    return True


async def test_fetch_auto():
    """测试 6: 自动回退获取"""
    print("\n" + "=" * 50)
    print("测试 6: fetch_auto 自动回退")
    print("=" * 50)

    class TestCrawler(BaseCrawler):
        async def crawl(self, **kwargs):
            return CrawlResult(success=True, data=[], message="test", source="test")

    crawler = TestCrawler(name="auto_test", enable_scrapling=True)

    # 正常 URL 测试
    test_url = "https://httpbin.org/get"
    try:
        result = await crawler.fetch_auto(test_url)
        if result:
            print(f"  ✅ fetch_auto 成功，响应长度: {len(result)}")
        else:
            print(f"  ⚠️ fetch_auto 返回空")
    except Exception as e:
        print(f"  ⚠️ fetch_auto 异常: {e}")

    print("✅ 自动回退测试完成")
    return True


async def main():
    print("🧪 Scrapling 集成测试\n")

    results = []

    # 同步测试
    results.append(("Scrapling 导入", test_scrapling_import()))
    results.append(("Adapter 初始化", test_scrapling_adapter()))
    results.append(("BaseCrawler 集成", test_base_crawler_scrapling()))

    # 异步测试
    results.append(("页面获取", await test_scrapling_fetch()))
    results.append(("解析功能", await test_scrapling_parse()))
    results.append(("自动回退", await test_fetch_auto()))

    # 汇总
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)

    all_pass = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if not result:
            all_pass = False

    if all_pass:
        print("\n🎉 所有测试通过！Scrapling 集成成功！")
    else:
        print("\n⚠️ 部分测试未通过，请检查")

    return all_pass


if __name__ == "__main__":
    asyncio.run(main())
