# -*- coding: utf-8 -*-
"""最终测试豆瓣 Top250"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import asyncio
sys.path.insert(0, r'D:\智能数据分析平台\backend')

from crawlers.ranking_extractor import RankingExtractor

async def test():
    print("=== 测试豆瓣 Top250 ===")
    extractor = RankingExtractor()
    
    result = await extractor.extract(
        "https://movie.douban.com/top250",
        "我要排名、电影名、评分、上映时间、导演",
        dynamic=False,
    )
    
    print(f"成功: {result['success']}")
    print(f"消息: {result['message']}")
    print(f"字段: {[f['name'] for f in result.get('fields', [])]}")
    print(f"数据条数: {len(result.get('rows', []))}")
    
    if result.get('rows'):
        print(f"\n前 3 条数据:")
        for i, row in enumerate(result['rows'][:3]):
            print(f"\n  [{i+1}]")
            for k, v in row.items():
                v_str = str(v).replace('\xa0', ' ')
                if len(v_str) > 80:
                    v_str = v_str[:80] + "..."
                print(f"    {k}: {v_str}")

asyncio.run(test())
print("\n测试完成")
