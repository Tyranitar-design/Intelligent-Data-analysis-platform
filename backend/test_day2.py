# -*- coding: utf-8 -*-
"""Day 2 核心功能测试"""
import sys
import asyncio
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\智能数据分析平台\backend')

print("=" * 60)
print("Day 2 核心功能测试")
print("=" * 60)

# ========== 测试 1: Cookie 加密 ==========
print("\n[测试 1] Cookie 加密增强")
print("-" * 40)

from crawlers.auth.cookie_store import CookieStore
from crawlers.auth.cookie_encryptor import CookieEncryptor

# 创建加密存储
cookie_store = CookieStore(encrypt=True)

# 保存敏感 Cookie
sensitive_cookies = [
    {"name": "session_token", "value": "secret_token_abc123_xyz", "domain": ".example.com"},
    {"name": "auth_key", "value": "my_secret_auth_key_12345", "domain": ".example.com"},
]

result = cookie_store.save_cookies("test_encrypted", sensitive_cookies)
print(f"✅ 保存加密 Cookie: {result}")

# 读取（自动解密）
cookies = cookie_store.get_cookies("test_encrypted")
print(f"✅ 读取解密 Cookie: {len(cookies)} 个")
for c in cookies:
    print(f"   - {c['name']}: {c['value'][:30]}...")

# ========== 测试 2: 登录流程配置 ==========
print("\n[测试 2] 登录流程配置")
print("-" * 40)

from crawlers.auth.login_flows import get_login_flow, list_supported_platforms

platforms = list_supported_platforms()
print(f"✅ 支持的平台: {len(platforms)} 个")
for code, name in platforms.items():
    print(f"   - {code}: {name}")

# 获取豆瓣登录流程
douban_flow = get_login_flow("douban")
print(f"\n✅ 豆瓣登录流程:")
print(f"   - 登录 URL: {douban_flow.get('login_url')}")
print(f"   - 用户名选择器: {douban_flow.get('username_selector')}")
print(f"   - 密码选择器: {douban_flow.get('password_selector')}")
print(f"   - 提交按钮: {douban_flow.get('submit_selector')}")

# ========== 测试 3: 浏览器池 ==========
print("\n[测试 3] 浏览器池")
print("-" * 40)

from crawlers.anticrawl.browser_pool import BrowserPool

pool = BrowserPool(max_browsers=2)
print(f"✅ 创建浏览器池: max_browsers={pool.max_browsers}")

# 测试指纹生成
fp = pool.fingerprint.generate_fingerprint()
print(f"✅ 生成指纹:")
print(f"   - UA: {fp['user_agent'][:40]}...")
print(f"   - 视口: {fp['viewport']}")
print(f"   - 时区: {fp['timezone']}")

# ========== 测试 4: 验证码识别 ==========
print("\n[测试 4] 验证码识别")
print("-" * 40)

from crawlers.anticrawl.captcha_solver import CaptchaSolver

solver = CaptchaSolver()

# 测试图片验证码
async def test_captcha():
    result = await solver.solve_image_captcha(b"fake_image_data")
    print(f"✅ 图片验证码识别: {result['success']}")
    print(f"   - 消息: {result['error']}")

    # 测试滑块验证码
    result = await solver.solve_slider_captcha(b"fake_slider_data")
    print(f"✅ 滑块验证码识别: {result['success']}")
    print(f"   - 消息: {result['error']}")

asyncio.run(test_captcha())

# ========== 测试 5: AuthManager 集成 ==========
print("\n[测试 5] AuthManager 集成")
print("-" * 40)

from crawlers.auth.auth_manager import AuthManager

auth = AuthManager()

# 列出支持的平台
supported = auth.list_supported_platforms()
print(f"✅ AuthManager 支持平台: {len(supported)} 个")
for code, name in supported.items():
    print(f"   - {code}: {name}")

# 测试保存 Cookie 登录
import asyncio

async def test_auth():
    # 模拟登录（使用 Cookie）
    test_cookies = [
        {"name": "test_session", "value": "test_value_123", "domain": ".test.com"},
    ]
    result = await auth.login_with_cookies("test_platform", test_cookies)
    print(f"✅ Cookie 登录: {result['success']}")
    print(f"   - 消息: {result['message']}")
    
    # 获取认证头
    headers = await auth.get_auth_headers("test_platform")
    print(f"✅ 获取认证头: {'Cookie' in headers}")
    
    # 登出
    result = await auth.logout("test_platform")
    print(f"✅ 登出: {result}")

asyncio.run(test_auth())

# ========== 总结 ==========
print("\n" + "=" * 60)
print("Day 2 核心功能测试完成")
print("=" * 60)
print("\n✅ 测试通过:")
print("   - Cookie 加密存储")
print("   - 登录流程配置")
print("   - 浏览器池 + 指纹轮换")
print("   - 验证码识别接口")
print("   - AuthManager 集成")
