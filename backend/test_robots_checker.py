# -*- coding: utf-8 -*-
"""Robots Checker 测试"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from crawlers.robots_checker import RobotsChecker

async def main():
    checker = RobotsChecker()
    
    # Test 1: 解析逻辑
    print("=" * 40)
    print("Test 1: 本地解析测试")
    rules, meta = checker._parse_robots_txt("""
User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /admin/public/
Crawl-delay: 2

User-agent: GoogleBot
Disallow: /search/
Allow: /search/api/

Sitemap: https://example.com/sitemap.xml
""")
    print(f"  Rules: {len(rules)}")
    for r in rules:
        print(f"    {r.user_agent}: {'Allow' if r.allow else 'Disallow'} {r.path} (pri={r.priority})")
    print(f"  Crawl-delay: {meta.get('crawl_delay')}")
    print(f"  Sitemaps: {meta.get('sitemaps')}")
    
    # Test 2: 路径匹配
    print("\n" + "=" * 40)
    print("Test 2: 路径匹配")
    test_cases = [
        ("/admin/secret", False),
        ("/admin/public/data", True),
        ("/private/file", False),
        ("/normal/page", True),
    ]
    for path, expected in test_cases:
        allowed, rule = checker._is_allowed(rules, path, "*")
        status = "PASS" if allowed == expected else "FAIL"
        print(f"  [{status}] /admin/secret -> {'Allow' if allowed else 'Deny'} (expected {'Allow' if expected else 'Deny'})")
    
    # Test 3: 真实网站检查
    print("\n" + "=" * 40)
    print("Test 3: 真实网站检查")
    urls = [
        "https://httpbin.org/get",
        "https://www.baidu.com/s?wd=test",
    ]
    for url in urls:
        report = await checker.check(url)
        print(f"  {url}: {'Allow' if report.allowed else 'Deny'} (source: {report.source})")
        if report.crawl_delay:
            print(f"    Crawl-delay: {report.crawl_delay}s")
        if report.warnings:
            for w in report.warnings:
                print(f"    Warning: {w}")
    
    print("\nAll tests done!")

if __name__ == "__main__":
    asyncio.run(main())
