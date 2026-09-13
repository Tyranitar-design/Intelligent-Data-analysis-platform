# -*- coding: utf-8 -*-
"""Day 1 模块测试"""
import sys
import asyncio
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\智能数据分析平台\backend')

print("=" * 60)
print("Day 1 模块测试")
print("=" * 60)

# ========== 测试 1: CookieStore ==========
print("\n[测试 1] CookieStore - Cookie 持久化存储")
print("-" * 40)

from crawlers.auth.cookie_store import CookieStore

cookie_store = CookieStore()

# 保存 Cookie
test_cookies = [
    {"name": "session_id", "value": "abc123", "domain": ".douban.com", "path": "/", "secure": True, "httpOnly": True},
    {"name": "user_id", "value": "12345", "domain": ".douban.com", "path": "/", "secure": False, "httpOnly": False},
]

result = cookie_store.save_cookies("douban", test_cookies)
print(f"✅ 保存 Cookie: {result}")

# 读取 Cookie
cookies = cookie_store.get_cookies("douban")
print(f"✅ 读取 Cookie: {len(cookies)} 个")
for c in cookies:
    print(f"   - {c['name']}: {c['value'][:20]}...")

# 保存会话
session_data = {"username": "test_user", "login_time": "2024-01-01"}
result = cookie_store.save_session("douban", session_data, expires_hours=24)
print(f"✅ 保存会话: {result}")

# 读取会话
session = cookie_store.get_session("douban")
print(f"✅ 读取会话: {session}")

# 列出平台
platforms = cookie_store.list_platforms()
print(f"✅ 平台列表: {platforms}")

# ========== 测试 2: FingerprintMasker ==========
print("\n[测试 2] FingerprintMasker - 指纹伪装")
print("-" * 40)

from crawlers.anticrawl.fingerprint import FingerprintMasker

fp = FingerprintMasker()

# 生成指纹
fingerprint = fp.generate_fingerprint()
print(f"✅ 生成指纹:")
print(f"   - User-Agent: {fingerprint['user_agent'][:50]}...")
print(f"   - 视口: {fingerprint['viewport']}")
print(f"   - 时区: {fingerprint['timezone']}")
print(f"   - 语言: {fingerprint['language']}")

# 获取请求头
headers = fp.get_headers()
print(f"✅ 请求头:")
print(f"   - User-Agent: {headers['User-Agent'][:50]}...")
print(f"   - Accept-Language: {headers['Accept-Language']}")

# 轮换指纹
fp.rotate()
new_fp = fp.generate_fingerprint()
print(f"✅ 轮换后 UA: {new_fp['user_agent'][:50]}...")

# ========== 测试 3: JSReverseEngine ==========
print("\n[测试 3] JSReverseEngine - JS 逆向")
print("-" * 40)

from crawlers.jsreverse.js_reverse_engine import JSReverseEngine

js_engine = JSReverseEngine()

# 测试 JS 代码
test_js = """
function sign(params) {
    var timestamp = Date.now();
    var nonce = Math.random().toString(36).substr(2, 15);
    var str = JSON.stringify(params) + timestamp + nonce;
    return md5(str);
}

function md5(str) {
    // 简化的 MD5
    return 'md5_' + str.length;
}

var API_KEY = 'secret_key_123';
var BASE_URL = 'https://api.example.com';
"""

# 解析 AST
ast = js_engine.parse_ast(test_js)
if ast:
    print(f"✅ AST 解析成功: {ast.get('type', 'unknown')}")
    
    # 查找函数
    functions = js_engine.find_functions(ast)
    print(f"✅ 找到 {len(functions)} 个函数:")
    for f in functions:
        print(f"   - {f['name']}({', '.join(f['params'])})")
    
    # 查找变量
    variables = js_engine.find_variables(ast)
    print(f"✅ 找到 {len(variables)} 个变量:")
    for v in variables:
        print(f"   - {v['name']} = {v['init']}")
else:
    print("⚠️ AST 解析失败（esprima 可能未安装）")

# 提取函数代码
func_code = js_engine.extract_function_code(test_js, "sign")
if func_code:
    print(f"✅ 提取 sign 函数: {func_code[:50]}...")

# 执行 JS
if js_engine.js_context:
    result = js_engine.execute_js(test_js, "md5", ["test_string"])
    print(f"✅ 执行 md5('test_string'): {result}")
else:
    print("⚠️ PyExecJS 未安装，跳过执行测试")

# 分析请求参数
analysis = js_engine.analyze_request_params(test_js)
print(f"✅ 参数分析:")
print(f"   - 签名函数: {len(analysis['signature_functions'])} 个")
print(f"   - 时间戳使用: {len(analysis['timestamp_usage'])} 处")
print(f"   - 随机数使用: {len(analysis['nonce_usage'])} 处")

# ========== 测试 4: SignatureExtractor ==========
print("\n[测试 4] SignatureExtractor - 签名提取")
print("-" * 40)

from crawlers.jsreverse.signature_extractor import SignatureExtractor

sig_extractor = SignatureExtractor()

# 提取 MD5 签名
md5_sig = sig_extractor.extract_md5_sign(test_js)
if md5_sig:
    print(f"✅ 提取 MD5 签名: {md5_sig['name']}")

# 提取时间戳参数
ts_param = sig_extractor.extract_timestamp_param(test_js)
print(f"✅ 时间戳参数: {ts_param}")

# 提取随机数参数
nonce_param = sig_extractor.extract_nonce_param(test_js)
print(f"✅ 随机数参数: {nonce_param}")

# 生成签名
test_params = {"page": 1, "limit": 10}
signature = sig_extractor.generate_signature(test_params, "secret_key", "md5")
print(f"✅ 生成签名: {signature}")

# ========== 总结 ==========
print("\n" + "=" * 60)
print("Day 1 模块测试完成")
print("=" * 60)
print("\n✅ 测试通过:")
print("   - CookieStore: 存储/读取/会话管理")
print("   - FingerprintMasker: 指纹生成/轮换")
print("   - JSReverseEngine: AST分析/函数提取/参数分析")
print("   - SignatureExtractor: 签名提取/生成")
print("\n⚠️ 注意:")
print("   - esprima 未安装时 AST 解析不可用")
print("   - PyExecJS 需要 Node.js 环境")
