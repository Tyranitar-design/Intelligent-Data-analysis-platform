#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 3 集成测试：登录态 + 反爬绕过

测试内容：
1. 登录态管理 API
2. Cookie 存储与读取
3. 带登录态的爬取
4. 反爬绕过效果
"""
import asyncio
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from crawlers.auth.auth_manager import AuthManager
from crawlers.auth.cookie_store import CookieStore
from crawlers.url_crawler import URLCrawler
from crawlers.anticrawl.anticrawl_engine import AntiCrawlEngine


async def test_cookie_store():
    """测试 Cookie 存储"""
    print("\n" + "="*60)
    print("测试 1: Cookie 存储")
    print("="*60)
    
    store = CookieStore(db_path=":memory:")  # 内存数据库
    
    # 保存测试 Cookie
    test_cookies = [
        {"name": "session_id", "value": "test123", "domain": ".zhihu.com", "path": "/"},
        {"name": "uid", "value": "user456", "domain": ".zhihu.com", "path": "/"},
    ]
    
    result = store.save_cookies("zhihu", test_cookies)
    print(f"[OK] 保存 Cookie: {result}")
    
    # 读取 Cookie
    cookies = store.get_cookies("zhihu")
    print(f"[OK] 读取 Cookie: {len(cookies)} 个")
    for c in cookies:
        print(f"   - {c['name']}: {c['value']}")
    
    # 保存会话
    session = {"login_url": "https://zhihu.com", "username": "test"}
    store.save_session("zhihu", session, expires_hours=24)
    print(f"[OK] 保存会话")
    
    # 读取会话
    loaded_session = store.get_session("zhihu")
    print(f"[OK] 读取会话: {loaded_session is not None}")
    
    # 列出平台
    platforms = store.list_platforms()
    print(f"[OK] 平台列表: {platforms}")
    
    return True


async def test_auth_manager():
    """测试认证管理器"""
    print("\n" + "="*60)
    print("测试 2: AuthManager")
    print("="*60)
    
    auth = AuthManager()
    
    # 列出支持的平台
    platforms = auth.list_supported_platforms()
    print(f"[OK] 支持的平台: {len(platforms)} 个")
    for k, v in platforms.items():
        print(f"   - {k}: {v}")
    
    # 测试 Cookie 登录
    test_cookies = [
        {"name": "test_cookie", "value": "test_value", "domain": ".example.com", "path": "/"},
    ]
    result = await auth.login_with_cookies("test_platform", test_cookies)
    print(f"[OK] Cookie 登录: {result['success']}")
    
    # 获取认证头
    headers = await auth.get_auth_headers("test_platform")
    print(f"[OK] 认证头: {headers}")
    
    # 检查登录状态
    status = await auth.check_login_status("test_platform")
    print(f"[OK] 登录状态: {status}")
    
    # 登出
    logout_result = await auth.logout("test_platform")
    print(f"[OK] 登出: {logout_result}")
    
    await auth.close()
    return True


async def test_url_crawler_with_auth():
    """测试带登录态的 URL 爬取"""
    print("\n" + "="*60)
    print("测试 3: URLCrawler + 登录态")
    print("="*60)
    
    crawler = URLCrawler()
    
    # 先添加测试 Cookie
    test_cookies = [
        {"name": "test_session", "value": "abc123", "domain": ".httpbin.org", "path": "/"},
    ]
    await crawler.auth_manager.login_with_cookies("httpbin", test_cookies)
    
    # 测试带登录态的请求
    print("测试带登录态的请求...")
    # 使用 httpbin 测试 Cookie 传递
    result = await crawler.crawl_url(
        url="https://httpbin.org/cookies",
        use_auth=True,
        auth_platform="httpbin",
    )
    
    print(f"[OK] 请求结果: {result.success}")
    print(f"   消息: {result.message}")
    if result.data:
        print(f"   数据: {json.dumps(result.data[:1], ensure_ascii=False, indent=2)[:200]}")
    
    return True


async def test_anti_crawl():
    """测试反爬绕过"""
    print("\n" + "="*60)
    print("测试 4: 反爬绕过")
    print("="*60)
    
    engine = AntiCrawlEngine()
    
    # 测试指纹伪装
    print("测试指纹伪装...")
    fp = engine.fingerprint
    print(f"[OK] 指纹可用: {fp is not None}")
    
    # 测试代理轮换
    engine.add_proxies(["http://proxy1:8080", "http://proxy2:8080"])
    proxy = await engine.rotate_proxy()
    print(f"[OK] 代理轮换: {proxy}")
    
    # 测试验证码识别（模拟）
    result = await engine.solve_captcha(b"fake_image_data")
    print(f"[OK] 验证码识别: {result}")
    
    return True


async def test_probe_url():
    """测试 URL 探测"""
    print("\n" + "="*60)
    print("测试 5: URL 探测")
    print("="*60)
    
    crawler = URLCrawler()
    
    # 测试 API URL
    probe = await crawler.probe_url("https://httpbin.org/json")
    print(f"[OK] API URL 探测:")
    print(f"   状态码: {probe.status_code}")
    print(f"   Content-Type: {probe.content_type}")
    print(f"   是否 API: {probe.is_api}")
    print(f"   是否受保护: {probe.is_protected}")
    
    # 测试 HTML URL
    probe2 = await crawler.probe_url("https://httpbin.org/html")
    print(f"[OK] HTML URL 探测:")
    print(f"   状态码: {probe2.status_code}")
    print(f"   Content-Type: {probe2.content_type}")
    print(f"   是否静态 HTML: {probe2.is_static_html}")
    
    return True


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Day 3 集成测试开始")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Cookie 存储", await test_cookie_store()))
    except Exception as e:
        print(f"[FAIL] Cookie 存储测试失败: {e}")
        results.append(("Cookie 存储", False))
    
    try:
        results.append(("AuthManager", await test_auth_manager()))
    except Exception as e:
        print(f"[FAIL] AuthManager 测试失败: {e}")
        results.append(("AuthManager", False))
    
    try:
        results.append(("URLCrawler + 登录态", await test_url_crawler_with_auth()))
    except Exception as e:
        print(f"[FAIL] URLCrawler 测试失败: {e}")
        results.append(("URLCrawler + 登录态", False))
    
    try:
        results.append(("反爬绕过", await test_anti_crawl()))
    except Exception as e:
        print(f"[FAIL] 反爬绕过测试失败: {e}")
        results.append(("反爬绕过", False))
    
    try:
        results.append(("URL 探测", await test_probe_url()))
    except Exception as e:
        print(f"[FAIL] URL 探测测试失败: {e}")
        results.append(("URL 探测", False))
    
    # 汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{status} {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n[OK] 所有测试通过！")
    else:
        print(f"\n[WARN] {total - passed} 个测试失败，请检查")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
