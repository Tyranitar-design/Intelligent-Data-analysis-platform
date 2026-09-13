# -*- coding: utf-8 -*-
"""测试 Cookie 加密"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\智能数据分析平台\backend')

from crawlers.auth.cookie_encryptor import CookieEncryptor
from crawlers.auth.cookie_store import CookieStore

print("=== 测试 Cookie 加密 ===\n")

# 测试加密器
encryptor = CookieEncryptor()

# 加密
original = "session_token_12345"
encrypted = encryptor.encrypt(original)
print(f"✅ 加密: {original[:20]}... -> {encrypted[:30]}...")

# 解密
decrypted = encryptor.decrypt(encrypted)
print(f"✅ 解密: {encrypted[:30]}... -> {decrypted}")
print(f"✅ 验证: {'通过' if decrypted == original else '失败'}")

# 测试 CookieStore 加密
print("\n--- 测试 CookieStore 加密 ---")
cookie_store = CookieStore(encrypt=True)

test_cookies = [
    {"name": "session_id", "value": "secret_session_abc123", "domain": ".douban.com"},
    {"name": "user_id", "value": "user_12345", "domain": ".douban.com"},
]

# 保存
cookie_store.save_cookies("test_platform", test_cookies)
print("✅ 保存加密 Cookie")

# 读取
cookies = cookie_store.get_cookies("test_platform")
print(f"✅ 读取解密 Cookie: {len(cookies)} 个")
for c in cookies:
    print(f"   - {c['name']}: {c['value']}")

print("\n=== 测试完成 ===")
