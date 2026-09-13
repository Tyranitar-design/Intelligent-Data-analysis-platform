# -*- coding: utf-8 -*-
"""调试测试"""
import sys
import asyncio
sys.path.insert(0, r'D:\智能数据分析平台\backend')

from crawlers.url_crawler import URLCrawler

async def test():
    print("=== 调试豆瓣 Top250 ===")
    crawler = URLCrawler()
    
    result = await crawler.crawl_url("https://movie.douban.com/top250")
    print(f"成功: {result.success}")
    print(f"消息: {result.message}")
    print(f"数据条数: {result.count}")
    print(f"数据类型: {type(result.data)}")
    
    if result.data:
        print(f"\n数据内容:")
        for i, item in enumerate(result.data[:3]):
            print(f"\n  项目 {i}:")
            if isinstance(item, dict):
                for k, v in item.items():
                    v_str = str(v)[:200]
                    print(f"    {k}: {v_str}")
            else:
                print(f"    {type(item)}: {str(item)[:200]}")

asyncio.run(test())
