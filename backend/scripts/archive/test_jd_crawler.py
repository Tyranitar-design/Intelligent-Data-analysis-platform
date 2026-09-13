# -*- coding: utf-8 -*-
"""测试京东爬虫"""
import asyncio
import sys
sys.path.insert(0, '.')
from crawlers.ecommerce.crawler import JDCrawler, TaobaoCrawler

async def test_jd():
    """测试京东爬虫"""
    print("=" * 50)
    print("测试京东爬虫")
    print("=" * 50)
    
    crawler = JDCrawler()
    print("开始爬取京东「手机」...")
    
    result = await crawler.crawl(keywords=['手机'], pages=1, save_to_db=False)
    
    print(f"\n成功: {result.success}")
    print(f"数据条数: {result.count}")
    print(f"消息: {result.message}")
    
    if result.data:
        print(f"\n真实数据 vs 模拟数据: is_mock = {result.data[0].get('is_mock', True)}")
        print(f"\n前 3 条数据:")
        for i, item in enumerate(result.data[:3]):
            print(f"  {i+1}. {item.get('title', 'N/A')[:50]}... - ¥{item.get('price', 0)}")

async def test_taobao():
    """测试淘宝爬虫"""
    print("\n" + "=" * 50)
    print("测试淘宝爬虫")
    print("=" * 50)
    
    crawler = TaobaoCrawler()
    print("开始爬取淘宝「耳机」...")
    
    result = await crawler.crawl(keywords=['耳机'], pages=1, save_to_db=False)
    
    print(f"\n成功: {result.success}")
    print(f"数据条数: {result.count}")
    print(f"消息: {result.message}")
    
    if result.data:
        print(f"\n真实数据 vs 模拟数据: is_mock = {result.data[0].get('is_mock', True)}")

if __name__ == "__main__":
    asyncio.run(test_jd())
    asyncio.run(test_taobao())
