# -*- coding: utf-8 -*-
"""调试测试2"""
import sys
import asyncio
sys.path.insert(0, r'D:\智能数据分析平台\backend')

from crawlers.url_crawler import URLCrawler

async def test():
    print("=== 调试豆瓣 Top250 HTML ===")
    crawler = URLCrawler()
    
    result = await crawler.crawl_url("https://movie.douban.com/top250")
    
    # 获取原始 HTML
    html = None
    for item in result.data:
        if isinstance(item, dict):
            if "html" in item and item["html"]:
                html = item["html"]
                break
            if "content" in item and item["content"]:
                html = item["content"]
                break
    
    if html:
        # 检查是否包含电影列表
        print(f"HTML 长度: {len(html)}")
        print(f"包含 .grid-view: {'.grid-view' in html}")
        print(f"包含 .item: {'.item' in html}")
        print(f"包含 movie: {'movie' in html.lower()}")
        
        # 保存 HTML 到文件查看
        with open(r'D:\douban.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("HTML 已保存到 D:\douban.html")
    else:
        print("未找到 HTML")
        # 打印所有数据
        for i, item in enumerate(result.data):
            print(f"\n项目 {i}: {type(item)}")
            if isinstance(item, dict):
                for k in item.keys():
                    print(f"  键: {k}")

asyncio.run(test())
