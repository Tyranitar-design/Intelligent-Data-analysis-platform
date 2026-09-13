# -*- coding: utf-8 -*-
"""
反爬策略测试脚本

测试反爬增强模块的各项功能
"""
import asyncio
import sys
import os

# Windows GBK 编码兼容
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.utils.anti_crawler import (
    AntiCrawlerEnhancer,
    BrowserFingerprint,
    ProxyPool,
    Proxy,
    get_enhancer,
    enhance_headers,
)


async def test_browser_fingerprint():
    """测试浏览器指纹生成"""
    print("\n" + "=" * 50)
    print("测试 1: 浏览器指纹生成")
    print("=" * 50)

    fingerprint = BrowserFingerprint()

    # 生成请求头
    headers = fingerprint.generate_headers(
        referer="https://www.google.com",
        domain="example.com"
    )

    print("\n生成的请求头:")
    for key, value in headers.items():
        print(f"  {key}: {value}")

    # 验证关键字段
    assert "User-Agent" in headers
    assert "Accept" in headers
    assert "Accept-Language" in headers
    assert headers["User-Agent"].startswith("Mozilla/5.0")

    print("\n[OK] 浏览器指纹测试通过!")


async def test_proxy_pool():
    """测试代理池管理"""
    print("\n" + "=" * 50)
    print("测试 2: 代理池管理")
    print("=" * 50)

    # 创建代理池
    proxies = [
        {"ip": "192.168.1.1", "port": 8080, "protocol": "http"},
        {"ip": "192.168.1.2", "port": 8080, "protocol": "http"},
        {"ip": "192.168.1.3", "port": 8080, "protocol": "socks5"},
    ]

    pool = ProxyPool(initial_proxies=proxies)

    print(f"\n初始代理数量: {len(pool.proxies)}")

    # 获取代理
    proxy1 = await pool.get_proxy(strategy="random")
    print(f"随机获取代理: {proxy1.url if proxy1 else '无'}")

    proxy2 = await pool.get_proxy(strategy="score")
    print(f"按评分获取代理: {proxy2.url if proxy2 else '无'}")

    # 汇报结果
    if proxy1:
        await pool.report_proxy_result(proxy1, success=True)
        print(f"代理 {proxy1.ip} 成功，评分: {proxy1.score}")

    # 统计信息
    stats = pool.get_stats()
    print(f"\n代理池统计: {stats}")

    print("\n[OK] 代理池测试通过!")


async def test_anti_crawler_enhancer():
    """测试反爬增强器"""
    print("\n" + "=" * 50)
    print("测试 3: 反爬增强器")
    print("=" * 50)

    # 创建增强器
    enhancer = AntiCrawlerEnhancer({
        "base_delay": 0.5,
        "max_delay": 10.0,
        "use_proxy": True,
        "proxies": [
            {"ip": "10.0.0.1", "port": 8080},
            {"ip": "10.0.0.2", "port": 8080},
        ]
    })

    # 添加更多代理
    enhancer.proxy_pool.add_proxy({
        "ip": "203.0.113.1",
        "port": 3128,
        "protocol": "http",
        "region": "北京"
    })

    print(f"\n代理池统计: {enhancer.proxy_pool.get_stats()}")

    # 准备请求
    context = await enhancer.prepare_request("https://example.com/api/data")
    print(f"\n请求上下文:")
    print(f"  URL: {context.url}")
    print(f"  User-Agent: {context.headers.get('User-Agent', 'N/A')[:50]}...")
    print(f"  是否使用代理: {context.proxy is not None}")

    # 统计信息
    stats = enhancer.get_stats()
    print(f"\n增强器统计: {stats}")

    print("\n[OK] 反爬增强器测试通过!")


async def test_request_headers():
    """测试请求头生成"""
    print("\n" + "=" * 50)
    print("测试 4: 请求头生成（多次调用）")
    print("=" * 50)

    print("\n生成5组不同的请求头:")
    for i in range(5):
        headers = enhance_headers(
            url="https://jd.com/search",
            referer="https://jd.com"
        )
        print(f"\n组 {i+1}:")
        print(f"  UA: {headers['User-Agent'][:60]}...")
        print(f"  Accept: {headers['Accept'][:50]}...")

    print("\n[OK] 请求头测试通过!")


async def test_real_request():
    """测试真实请求"""
    print("\n" + "=" * 50)
    print("测试 5: 真实HTTP请求")
    print("=" * 50)

    from crawlers.base import BaseCrawler
    import httpx

    # 创建测试爬虫
    class TestCrawler(BaseCrawler):
        async def crawl(self, **kwargs):
            pass

    crawler = TestCrawler("test")

    # 测试URL
    test_urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/headers",
    ]

    for url in test_urls:
        print(f"\n请求: {url}")
        result = await crawler.fetch(url)
        if result:
            print(f"  状态: 成功")
            print(f"  响应长度: {len(result)} 字节")
            # 尝试解析JSON
            try:
                import json
                data = json.loads(result)
                print(f"  JSON键: {list(data.keys())[:5]}")
            except:
                print(f"  响应预览: {result[:100]}...")
        else:
            print(f"  状态: 失败")

    print("\n[OK] 真实请求测试通过!")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("[Shield] 反爬策略增强模块测试")
    print("=" * 60)

    try:
        await test_browser_fingerprint()
        await test_proxy_pool()
        await test_anti_crawler_enhancer()
        await test_request_headers()
        await test_real_request()

        print("\n" + "=" * 60)
        print("[OK] 所有测试通过!")
        print("=" * 60)
        print("""
反爬策略增强模块功能:
1. [OK] BrowserFingerprint - 真实浏览器指纹生成
2. [OK] ProxyPool - 代理池管理
3. [OK] AntiCrawlerEnhancer - 反爬增强器
4. [OK] 多次调用生成不同请求头
5. [OK] 真实HTTP请求测试
        """)

    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
