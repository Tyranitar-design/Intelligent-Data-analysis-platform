# -*- coding: utf-8 -*-
"""测试豆瓣 Top250 和猫眼电影"""
import sys
import asyncio
sys.path.insert(0, r'D:\智能数据分析平台\backend')

from crawlers.url_crawler import URLCrawler
from crawlers.dynamic_crawler import DynamicCrawler, DynamicCrawlOptions
from crawlers.ranking_extractor import RankingExtractor

async def test_douban():
    print("=== 测试豆瓣 Top250 ===")
    
    # 1. 先测试静态爬取
    print("\n1. 静态爬取:")
    crawler = URLCrawler()
    result = await crawler.crawl_url("https://movie.douban.com/top250")
    print(f"   成功: {result.success}")
    print(f"   消息: {result.message}")
    print(f"   数据条数: {result.count}")
    if result.error:
        print(f"   错误: {result.error}")
    
    # 2. 测试动态爬取
    print("\n2. 动态爬取:")
    dynamic = DynamicCrawler()
    options = DynamicCrawlOptions(
        wait_for=".item",
        wait_time=10,
        auto_scroll=True,
        scroll_count=3,
    )
    result = await dynamic.crawl_dynamic("https://movie.douban.com/top250", options)
    print(f"   成功: {result.success}")
    print(f"   消息: {result.message}")
    if result.data:
        for item in result.data:
            if isinstance(item, dict):
                html = item.get("html", "")[:500]
                print(f"   HTML 前 500 字符: {html}")
    if result.error:
        print(f"   错误: {result.error}")
    
    # 3. 测试榜单抽取器
    print("\n3. 榜单抽取器:")
    extractor = RankingExtractor()
    result = await extractor.extract(
        "https://movie.douban.com/top250",
        "我要排名、电影名、评分、上映时间、导演",
        dynamic=True,
    )
    print(f"   成功: {result['success']}")
    print(f"   消息: {result['message']}")
    print(f"   字段: {[f['name'] for f in result.get('fields', [])]}")
    print(f"   数据条数: {len(result.get('rows', []))}")
    if result.get('rows'):
        print(f"   第一条: {result['rows'][0]}")
    
    await dynamic.close()

async def test_maoyan():
    print("\n\n=== 测试猫眼电影 ===")
    
    # 1. 静态爬取
    print("\n1. 静态爬取:")
    crawler = URLCrawler()
    result = await crawler.crawl_url("https://www.maoyan.com/films")
    print(f"   成功: {result.success}")
    print(f"   消息: {result.message}")
    print(f"   数据条数: {result.count}")
    if result.error:
        print(f"   错误: {result.error}")
    
    # 2. 动态爬取
    print("\n2. 动态爬取:")
    dynamic = DynamicCrawler()
    options = DynamicCrawlOptions(
        wait_for=".movie-item",
        wait_time=10,
        auto_scroll=True,
        scroll_count=3,
    )
    result = await dynamic.crawl_dynamic("https://www.maoyan.com/films", options)
    print(f"   成功: {result.success}")
    print(f"   消息: {result.message}")
    if result.data:
        for item in result.data:
            if isinstance(item, dict):
                html = item.get("html", "")[:500]
                print(f"   HTML 前 500 字符: {html}")
    if result.error:
        print(f"   错误: {result.error}")
    
    # 3. 榜单抽取器
    print("\n3. 榜单抽取器:")
    extractor = RankingExtractor()
    result = await extractor.extract(
        "https://www.maoyan.com/films",
        "我要电影名、评分、上映时间",
        dynamic=True,
    )
    print(f"   成功: {result['success']}")
    print(f"   消息: {result['message']}")
    print(f"   字段: {[f['name'] for f in result.get('fields', [])]}")
    print(f"   数据条数: {len(result.get('rows', []))}")
    if result.get('rows'):
        print(f"   第一条: {result['rows'][0]}")
    
    await dynamic.close()

async def main():
    await test_douban()
    await test_maoyan()
    print("\n\n测试完成")

asyncio.run(main())
