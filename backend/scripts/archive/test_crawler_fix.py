# -*- coding: utf-8 -*-
"""
爬虫功能测试脚本
测试数据获取和存储功能
"""
import asyncio
import sys
import os
import io

# 设置标准输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加路径
sys.path.insert(0, r"D:\智能数据分析平台\backend")

async def test_jd_crawler():
    """测试京东爬虫"""
    from crawlers.ecommerce.crawler import JDCrawler
    
    print("=" * 50)
    print("[JD] Testing JD crawler")
    print("=" * 50)
    
    crawler = JDCrawler()
    
    # 测试爬取手机数据
    result = await crawler.crawl(keywords=["手机"], pages=1, save_to_db=True)
    
    print(f"\nSuccess: {result.success}")
    print(f"Message: {result.message}")
    print(f"Data count: {result.count}")
    
    if result.data:
        print("\nFirst 3 items:")
        for i, item in enumerate(result.data[:3]):
            title = item.get('title', 'N/A')[:50]
            print(f"\n[{i+1}] {title}")
            print(f"    Price: {item.get('price', 'N/A')}")
            print(f"    Platform: {item.get('platform', 'N/A')}")
            print(f"    is_mock: {item.get('is_mock', 'N/A')}")
    
    return result

async def test_taobao_crawler():
    """测试淘宝爬虫"""
    from crawlers.ecommerce.crawler import TaobaoCrawler
    
    print("\n" + "=" * 50)
    print("[TB] Testing Taobao crawler")
    print("=" * 50)
    
    crawler = TaobaoCrawler()
    
    # 测试爬取耳机数据
    result = await crawler.crawl(keywords=["耳机"], pages=1, save_to_db=True)
    
    print(f"\nSuccess: {result.success}")
    print(f"Message: {result.message}")
    print(f"Data count: {result.count}")
    
    if result.data:
        print("\nFirst 3 items:")
        for i, item in enumerate(result.data[:3]):
            title = item.get('title', 'N/A')[:50]
            print(f"\n[{i+1}] {title}")
            print(f"    Price: {item.get('price', 'N/A')}")
            print(f"    Platform: {item.get('platform', 'N/A')}")
            print(f"    is_mock: {item.get('is_mock', 'N/A')}")
    
    return result

async def test_eastmoney_crawler():
    """测试东方财富爬虫（真实数据）"""
    from crawlers.finance.eastmoney import EastMoneyCrawler
    
    print("\n" + "=" * 50)
    print("[EM] Testing EastMoney crawler (Real Data)")
    print("=" * 50)
    
    crawler = EastMoneyCrawler()
    
    # 测试爬取股票K线
    result = await crawler.crawl_stock_kline("600519", days=10, market="sh")
    
    print(f"\nSuccess: {result.success}")
    print(f"Message: {result.message}")
    print(f"Data count: {result.count}")
    
    if result.data:
        print("\nFirst 5 K-line data:")
        for i, item in enumerate(result.data[:5]):
            date = item.get('date', 'N/A')
            close = item.get('close', 'N/A')
            print(f"[{i+1}] Date: {date}, Close: {close}")
    
    return result

async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("=== Starting Crawler Test ===")
    print("=" * 60)
    
    results = []
    
    # 测试京东
    try:
        r1 = await test_jd_crawler()
        results.append(("JD", r1.success, r1.count))
    except Exception as e:
        print(f"\n[ERROR] JD test failed: {e}")
        results.append(("JD", False, 0))
    
    # 等待一下，避免并发太高
    await asyncio.sleep(2)
    
    # 测试淘宝
    try:
        r2 = await test_taobao_crawler()
        results.append(("Taobao", r2.success, r2.count))
    except Exception as e:
        print(f"\n[ERROR] Taobao test failed: {e}")
        results.append(("Taobao", False, 0))
    
    await asyncio.sleep(2)
    
    # 测试东方财富
    try:
        r3 = await test_eastmoney_crawler()
        results.append(("EastMoney", r3.success, r3.count))
    except Exception as e:
        print(f"\n[ERROR] EastMoney test failed: {e}")
        results.append(("EastMoney", False, 0))
    
    # 汇总
    print("\n" + "=" * 60)
    print("=== Test Summary ===")
    print("=" * 60)
    
    print("\n| Crawler | Status | Count |")
    print("|---------|--------|-------|")
    for name, success, count in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"| {name} | {status} | {count} |")
    
    total = sum(c for _, _, c in results)
    print(f"\nTotal: {total} records")
    
    print("\n=== Test Complete! ===")

if __name__ == "__main__":
    asyncio.run(main())