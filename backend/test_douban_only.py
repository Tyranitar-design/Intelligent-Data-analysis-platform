# -*- coding: utf-8 -*-
"""单独测试豆瓣 Top250"""
import sys
import asyncio
sys.path.insert(0, r'D:\智能数据分析平台\backend')

from crawlers.ranking_extractor import RankingExtractor

async def test():
    print("=== 测试豆瓣 Top250 ===")
    extractor = RankingExtractor()
    
    # 测试静态抽取
    print("\n1. 静态抽取:")
    result = await extractor.extract(
        "https://movie.douban.com/top250",
        "我要排名、电影名、评分、上映时间、导演",
        dynamic=False,
    )
    print(f"   成功: {result['success']}")
    print(f"   消息: {result['message']}")
    print(f"   字段: {[f['name'] for f in result.get('fields', [])]}")
    print(f"   数据条数: {len(result.get('rows', []))}")
    if result.get('rows'):
        print(f"   第一条:")
        for k, v in result['rows'][0].items():
            print(f"      {k}: {v[:80] if len(str(v)) > 80 else v}")
    
    # 测试动态抽取
    print("\n2. 动态抽取:")
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
        print(f"   第一条:")
        for k, v in result['rows'][0].items():
            print(f"      {k}: {v[:80] if len(str(v)) > 80 else v}")
    
    print("\n测试完成")

asyncio.run(test())
