# -*- coding: utf-8 -*-
"""JustOneAPI Token 测试"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))
os.environ["JUSTONE_API_TOKEN"] = "vcPFRkOp9ZvzMLVQ"

from crawlers.adapters.justoneapi import JustOneAPIAdapter

async def main():
    adapter = JustOneAPIAdapter(token="vcPFRkOp9ZvzMLVQ")
    print(f"Token configured: {adapter.validate_config()}")
    
    # Test weibo hot search
    print("\n[weibo_hot]")
    r = await adapter.fetch(type="weibo_hot")
    print(f"  success={r.success}, count={r.count}, msg={r.message}")
    if r.data and isinstance(r.data, list):
        for item in r.data[:5]:
            if isinstance(item, dict):
                title = item.get("word") or item.get("title") or item.get("word_label") or str(item)[:80]
                print(f"  - {title}")
    
    # Test xiaohongshu search
    print("\n[xiaohongshu_search]")
    r = await adapter.fetch(type="xiaohongshu_search", keyword="数据分析")
    print(f"  success={r.success}, count={r.count}, msg={r.message}")
    if r.data and isinstance(r.data, list):
        for item in r.data[:3]:
            if isinstance(item, dict):
                title = item.get("title") or item.get("note_card", {}).get("title") or str(item)[:80]
                print(f"  - {title}")
    
    # Test douyin search
    print("\n[douyin_search]")
    r = await adapter.fetch(type="douyin_search", keyword="AI")
    print(f"  success={r.success}, count={r.count}, msg={r.message}")
    if r.data and isinstance(r.data, list):
        for item in r.data[:3]:
            if isinstance(item, dict):
                title = item.get("desc") or item.get("title") or str(item)[:80]
                print(f"  - {title[:50]}")

if __name__ == "__main__":
    asyncio.run(main())
