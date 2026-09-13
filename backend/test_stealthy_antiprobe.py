# -*- coding: utf-8 -*-
"""
StealthyFetcher 反爬能力测试
===========================

测试:
1. StealthyFetcher 导入和可用性
2. 抓取普通页面
3. 抓取有反爬保护的网站
4. 与 Fetcher + httpx 对比
"""
import sys, os, asyncio, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))


async def test_stealthy_availability():
    """测试 1: StealthyFetcher 可用性"""
    print("=" * 50)
    print("Test 1: StealthyFetcher 可用性")
    print("=" * 50)
    
    from crawlers.scrapling_adapter import ScraplingAdapter, ScraplingConfig
    adapter = ScraplingAdapter()
    
    print(f"  Fetcher available: {adapter.available}")
    print(f"  Stealthy available: {adapter.stealthy_available}")
    
    if not adapter.stealthy_available:
        print("  >>> StealthyFetcher 不可用，后续测试跳过")
        return False
    
    return True


async def test_fetcher_vs_stealthy():
    """测试 2: Fetcher vs StealthyFetcher 对比"""
    print("\n" + "=" * 50)
    print("Test 2: Fetcher vs StealthyFetcher")
    print("=" * 50)
    
    from crawlers.scrapling_adapter import ScraplingAdapter, ScraplingConfig
    adapter = ScraplingAdapter()
    
    # 使用 httpbin 测试
    test_url = "https://httpbin.org/headers"
    
    # Fetcher 模式
    print(f"\n  [Fetcher] {test_url}")
    start = time.time()
    response = await adapter.fetch_page(test_url)
    elapsed_fetcher = time.time() - start
    print(f"    Result: {'OK' if response else 'FAIL'} ({elapsed_fetcher:.2f}s)")
    
    # StealthyFetcher 模式
    print(f"\n  [StealthyFetcher] {test_url}")
    start = time.time()
    try:
        response = await adapter.fetch_stealthy(test_url, headless=True)
        elapsed_stealthy = time.time() - start
        print(f"    Result: {'OK' if response else 'FAIL'} ({elapsed_stealthy:.2f}s)")
    except Exception as e:
        print(f"    Error: {e}")
    
    return True


async def test_base_crawler_scrapling():
    """测试 3: BaseCrawler Scrapling 集成"""
    print("\n" + "=" * 50)
    print("Test 3: BaseCrawler + Scrapling 集成")
    print("=" * 50)
    
    from crawlers.base import BaseCrawler, CrawlResult
    
    class TestCrawler(BaseCrawler):
        async def crawl(self, **kwargs):
            return CrawlResult(success=True, data=[], message="test", source="test")
    
    # 启用 Scrapling 的爬虫
    crawler = TestCrawler(name="stealthy_test", enable_scrapling=True)
    print(f"  scrapling available: {crawler.scrapling.available}")
    print(f"  stealthy available: {crawler.scrapling.stealthy_available}")
    
    # 测试 fetch_with_scrapling
    print(f"\n  fetch_with_scrapling test...")
    result = await crawler.fetch_with_scrapling(
        url="https://httpbin.org/get",
        selectors={"origin": "pre"},
    )
    print(f"    Result: {result}")
    
    return True


async def test_real_website():
    """测试 4: 真实网站抓取"""
    print("\n" + "=" * 50)
    print("Test 4: 真实网站抓取能力")
    print("=" * 50)
    
    from crawlers.scrapling_adapter import ScraplingAdapter
    adapter = ScraplingAdapter()
    
    # 测试多个网站
    sites = [
        ("httpbin.org", "https://httpbin.org/html"),
    ]
    
    for name, url in sites:
        print(f"\n  [{name}] {url}")
        
        # Fetcher 模式
        try:
            start = time.time()
            response = await adapter.fetch_page(url)
            elapsed = time.time() - start
            if response:
                text = adapter.get_page_text(response)
                print(f"    Fetcher: OK ({elapsed:.2f}s, text_len={len(text) if text else 0})")
            else:
                print(f"    Fetcher: FAIL ({elapsed:.2f}s)")
        except Exception as e:
            print(f"    Fetcher: ERROR - {e}")
        
        # StealthyFetcher 模式
        if adapter.stealthy_available:
            try:
                start = time.time()
                response = await adapter.fetch_stealthy(url, headless=True)
                elapsed = time.time() - start
                if response:
                    text = adapter.get_page_text(response)
                    print(f"    Stealthy: OK ({elapsed:.2f}s, text_len={len(text) if text else 0})")
                else:
                    print(f"    Stealthy: FAIL ({elapsed:.2f}s)")
            except Exception as e:
                print(f"    Stealthy: ERROR - {e}")
    
    return True


async def test_fetch_auto_fallback():
    """测试 5: 自动回退机制"""
    print("\n" + "=" * 50)
    print("Test 5: fetch_auto 自动回退")
    print("=" * 50)
    
    from crawlers.base import BaseCrawler, CrawlResult
    
    class TestCrawler(BaseCrawler):
        async def crawl(self, **kwargs):
            return CrawlResult(success=True, data=[], message="test", source="test")
    
    crawler = TestCrawler(name="auto_test", enable_scrapling=True)
    
    # 正常 URL
    url = "https://httpbin.org/get"
    print(f"  URL: {url}")
    result = await crawler.fetch_auto(url)
    if result:
        print(f"  Result: OK (len={len(result)})")
    else:
        print(f"  Result: FAIL")
    
    stats = crawler.get_stats()
    print(f"  Stats: requests={stats['request_count']}, scrapling_fallbacks={stats['scrapling_fallback_count']}")
    
    return True


async def main():
    print("StealthyFetcher 反爬能力测试\n")
    
    available = await test_stealthy_availability()
    
    if available:
        await test_fetcher_vs_stealthy()
        await test_base_crawler_scrapling()
        await test_real_website()
        await test_fetch_auto_fallback()
    else:
        print("\nStealthyFetcher 不可用，仅测试 Fetcher 模式")
        await test_fetch_auto_fallback()
    
    print("\n" + "=" * 50)
    print("反爬能力测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
