# 智能数据分析平台 - 登录验证与反爬策略开发指南

> 版本: Day 3 完成版
> 日期: 2026-05-09
> 作者: 小彩 + 小宇

---

## 1. 功能概述

本模块为智能数据分析平台提供完整的登录态管理和反爬绕过能力。

### 1.1 核心能力

| 能力 | 说明 |
|------|------|
| **多平台登录** | 支持知乎/微博/豆瓣/B站/小红书等主流平台 |
| **自动登录** | Playwright 自动化填写账号密码 |
| **Cookie 导入** | 支持浏览器 Cookie JSON 导入 |
| **加密存储** | Cookie 值自动 AES 加密 |
| **登录态检测** | 自动检测 Cookie 是否过期 |
| **反爬绕过** | 指纹伪装 + 代理轮换 + Cloudflare 绕过 |

---

## 2. 后端架构

### 2.1 核心类

```
crawlers/auth/
├── auth_manager.py      # AuthManager - 登录态管理器
├── cookie_store.py      # CookieStore - Cookie 持久化存储
├── cookie_encryptor.py  # CookieEncryptor - 加密器
├── login_flows.py       # 预置登录流程配置
└── __init__.py
```

### 2.2 AuthManager API

```python
from crawlers.auth.auth_manager import AuthManager

auth = AuthManager()

# 自动登录
result = await auth.login_with_playwright(
    platform="zhihu",
    username="your_username",
    password="your_password"
)

# Cookie 登录
result = await auth.login_with_cookies("zhihu", cookies_list)

# 检查登录状态
status = await auth.check_login_status("zhihu")

# 获取认证头
headers = await auth.get_auth_headers("zhihu")

# 登出
await auth.logout("zhihu")
```

### 2.3 支持的登录平台

| 平台 | 标识 | 登录方式 |
|------|------|----------|
| 知乎 | `zhihu` | 用户名+密码 |
| 微博 | `weibo` | 用户名+密码 |
| 豆瓣 | `douban` | 用户名+密码 |
| B站 | `bilibili` | 用户名+密码 |
| 小红书 | `xiaohongshu` | 手机号+验证码 |

---

## 3. 前端组件

### 3.1 AuthManager 组件

位置: `frontend/src/components/AuthManager.tsx`

功能:
- 平台选择（图标 + 名称）
- 自动登录表单
- Cookie JSON 导入
- 会话列表管理
- 登录状态检测

### 3.2 登录态配置栏

位置: `frontend/src/pages/Crawl.tsx` (顶部)

使用方式:
1. 勾选"使用登录态采集"
2. 选择已登录平台
3. 执行爬取（自动携带 Cookie）

---

## 4. API 端点

### 4.1 登录管理

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/crawl/auth/platforms` | 列出支持的平台 |
| GET | `/crawl/auth/sessions` | 列出已登录会话 |
| POST | `/crawl/auth/login` | 自动登录 |
| POST | `/crawl/auth/cookie` | Cookie 导入 |
| GET | `/crawl/auth/status/{platform}` | 检查状态 |
| DELETE | `/crawl/auth/logout/{platform}` | 登出 |
| GET | `/crawl/auth/headers/{platform}` | 获取认证头 |

### 4.2 爬取接口（新增参数）

```json
{
  "url": "https://example.com",
  "auth_platform": "zhihu",
  "use_auth": true
}
```

---

## 5. 反爬策略

### 5.1 指纹伪装

```python
from crawlers.anticrawl.fingerprint import FingerprintMasker

fp = FingerprintMasker()
context = fp.get_playwright_context()  # 获取伪装配置
```

### 5.2 代理轮换

```python
from crawlers.anticrawl.anticrawl_engine import AntiCrawlEngine

engine = AntiCrawlEngine()
engine.add_proxies(["http://proxy1:8080", "http://proxy2:8080"])
proxy = await engine.rotate_proxy()
```

### 5.3 Cloudflare 绕过

```python
result = await engine.bypass_cloudflare("https://protected-site.com")
```

---

## 6. 测试

### 6.1 运行测试

```bash
cd D:\智能数据分析平台\backend
venv\Scripts\python.exe test_auth_integration.py
```

### 6.2 测试覆盖

| 测试项 | 说明 |
|--------|------|
| Cookie 存储 | SQLite + 加密 |
| AuthManager | 登录/登出/状态检测 |
| URLCrawler + 登录态 | Cookie 注入验证 |
| 反爬绕过 | 指纹/代理/验证码 |
| URL 探测 | 类型自动识别 |

---

## 7. 后续优化方向

### Day 4 建议

1. **更多平台**: Twitter, Instagram, GitHub 等
2. **验证码集成**: 2captcha / Anti-Captcha
3. **代理池管理**: 动态代理 + 质量检测
4. **自动刷新**: 定时检测 Cookie 过期并重登

### Phase 5 建议

1. **企业级认证**: SSO / OAuth2 / LDAP
2. **审计日志**: 登录/爬取操作记录
3. **权限控制**: 平台访问权限管理

---

## 8. 关键文件清单

### 后端
- `backend/crawlers/auth/auth_manager.py`
- `backend/crawlers/auth/cookie_store.py`
- `backend/crawlers/auth/login_flows.py`
- `backend/crawlers/anticrawl/anticrawl_engine.py`
- `backend/api/routers/crawl.py`
- `backend/test_auth_integration.py`

### 前端
- `frontend/src/components/AuthManager.tsx`
- `frontend/src/api/crawl.ts`
- `frontend/src/pages/Crawl.tsx`

---

*文档版本: Day 3 | 更新: 2026-05-09*
