# -*- coding: utf-8 -*-
"""检查 HTML 结构"""
import sys
sys.path.insert(0, r'D:\智能数据分析平台\backend')

import httpx
from bs4 import BeautifulSoup

async def test():
    print("=== 获取豆瓣 HTML ===")
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get("https://movie.douban.com/top250", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        resp.raise_for_status()
        html = resp.text
        
        print(f"HTML 长度: {len(html)}")
        
        soup = BeautifulSoup(html, "lxml")
        
        # 检查关键元素
        print(f"\n.grid-view 数量: {len(soup.select('.grid-view'))}")
        print(f".grid-view .item 数量: {len(soup.select('.grid-view .item'))}")
        print(f".item 数量: {len(soup.select('.item'))}")
        print(f"li 数量: {len(soup.select('li'))}")
        
        # 保存 HTML
        with open(r'D:\douban.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("\nHTML 已保存到 D:\douban.html")

import asyncio
asyncio.run(test())
