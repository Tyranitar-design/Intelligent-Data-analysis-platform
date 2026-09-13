# -*- coding: utf-8 -*-
"""新增适配器验证测试"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from crawlers.adapter_framework import AdapterRegistry
# 触发注册
from crawlers.adapters.eastmoney import EastMoneyAdapter
from crawlers.adapters.kr36 import Kr36Adapter
from crawlers.adapters.cls import ClsAdapter
from crawlers.adapters.justoneapi import JustOneAPIAdapter
from crawlers.adapters.public_apis import OpenWeatherAdapter, ExchangeRateAdapter, WikipediaAdapter


async def main():
    print("=" * 60)
    print("适配器注册表 - 全量验证")
    print("=" * 60)
    
    adapters = AdapterRegistry.list_adapters()
    print(f"\n  Total: {len(adapters)} adapters\n")
    
    categories = {}
    for a in adapters:
        cat = a['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(a)
    
    for cat, items in sorted(categories.items()):
        print(f"  [{cat}]")
        for item in items:
            print(f"    - {item['name']}: {item['description']}")
    
    # 实时数据测试
    print("\n" + "=" * 60)
    print("实时数据验证")
    print("=" * 60)
    
    # 1. 东方财富 (已有)
    print("\n  [finance/eastmoney]")
    em = AdapterRegistry.create("eastmoney")
    r = await em.fetch(type="stock", stock_code="000001", days=3, market="sz")
    print(f"    success={r.success}, count={r.count}")
    if r.data:
        print(f"    sample: {r.data[0]}")
    
    # 2. 汇率
    print("\n  [finance/exchangerate]")
    er = AdapterRegistry.create("exchangerate")
    r = await er.fetch(base="USD")
    print(f"    success={r.success}, count={r.count}")
    if r.data:
        print(f"    rates: {r.data[0].get('rates', {})}")
    
    # 3. Wikipedia
    print("\n  [research/wikipedia]")
    wiki = AdapterRegistry.create("wikipedia")
    r = await wiki.fetch(keyword="机器学习", language="zh", limit=3)
    print(f"    success={r.success}, count={r.count}")
    if r.data:
        for item in r.data:
            print(f"    - {item['title']}")
    
    # 4. 天气 (wttr.in 免费)
    print("\n  [weather/openweather]")
    weather = AdapterRegistry.create("openweather")
    r = await weather.fetch(city="Beijing")
    print(f"    success={r.success}, count={r.count}")
    if r.data:
        print(f"    temp: {r.data[0].get('temp_C')}C, desc: {r.data[0].get('description')}")
    
    # 5. JustOneAPI (需要 Token)
    print("\n  [social/justoneapi]")
    joa = AdapterRegistry.create("justoneapi")
    print(f"    token configured: {joa.validate_config()}")
    if not joa.validate_config():
        print("    (需要配置 JUSTONE_API_TOKEN 才能使用)")
    
    print("\n" + "=" * 60)
    print(f"SUMMARY: {len(adapters)} adapters registered, {len(categories)} categories")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
