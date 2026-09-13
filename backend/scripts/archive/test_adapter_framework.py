# -*- coding: utf-8 -*-
"""适配器框架测试"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crawlers.adapter_framework import AdapterRegistry
# 导入适配器（触发注册装饰器）
from crawlers.adapters.eastmoney import EastMoneyAdapter
from crawlers.adapters.kr36 import Kr36Adapter
from crawlers.adapters.cls import ClsAdapter


async def main():
    print("=" * 50)
    print("Test 1: AdapterRegistry 注册表")
    print("=" * 50)
    adapters = AdapterRegistry.list_adapters()
    for a in adapters:
        print(f"  {a['name']}: {a['description']} ({a['category']})")
    
    print(f"\n  Total: {len(adapters)} adapters")
    
    print("\n" + "=" * 50)
    print("Test 2: EastMoneyAdapter 实时数据")
    print("=" * 50)
    em = AdapterRegistry.create("eastmoney")
    if em:
        result = await em.fetch(type="stock", stock_code="600519", days=5, market="sh")
        print(f"  Success: {result.success}")
        print(f"  Count: {result.count}")
        if result.data:
            print(f"  Sample: {result.data[0]}")
    
    print("\n" + "=" * 50)
    print("Test 3: Kr36Adapter 实时数据")
    print("=" * 50)
    kr = AdapterRegistry.create("kr36")
    if kr:
        result = await kr.fetch(per_page=5)
        print(f"  Success: {result.success}")
        print(f"  Count: {result.count}")
        if result.data:
            print(f"  Sample: {result.data[0]}")
    
    print("\nAll adapter tests done!")


if __name__ == "__main__":
    asyncio.run(main())
