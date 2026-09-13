# Phase 4.6.4 — 登录态 + 反爬能力增强

**日期**: 2026-05-09
**状态**: 提案阶段
**目标**: 构建企业级反爬绕过与登录态采集能力

---

## 🎯 核心目标

让平台具备处理以下场景的能力：

1. **登录态页面采集** — 需要登录后才能访问的数据
2. **强反爬页面采集** — Cloudflare、验证码、指纹检测
3. **JS 逆向采集** — 逆向加密参数、签名算法
4. **浏览器会话复用** — Cookie/Token 持久化
5. **智能策略选择** — 自动判断页面类型并选择最优策略

---

## 📊 现状分析

### 已有能力
| 能力 | 状态 | 技术 |
|------|------|------|
| 静态页面爬取 | ✅ | httpx + BeautifulSoup |
| 动态页面爬取 | ✅ | Playwright |
| 反爬绕过 | ✅ | Scrapling StealthyFetcher |
| 智能提取 | ✅ | crawl4ai |
| 参数表单化 | ✅ | JSON Schema → 动态表单 |
| 数据保存 | ✅ | 一键保存数据集 |

### 缺失能力
| 能力 | 优先级 | 技术方案 |
|------|--------|----------|
| 登录态采集 | 🔴 P0 | CDP Bridge MCP / Playwright 会话 |
| 验证码处理 | 🔴 P0 | 2captcha / 打码平台 / 视觉模型 |
| JS 逆向 | 🟡 P1 | AST 分析 / 断点调试 / 参数还原 |
| 指纹伪装 | 🟡 P1 | Camofox / Scrapling FP |
| 代理池轮换 | 🟡 P1 | 代理池 + 智能轮换 |
| 请求签名还原 | 🟢 P2 | JS 逆向 + 本地执行 |

---

## 🏗️ 架构设计

### 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    采集策略调度层                         │
│         (自动判断页面类型 → 选择最优策略)                  │
├─────────────────────────────────────────────────────────┤
│  静态策略  │  动态策略  │  登录态策略  │  反爬策略        │
│  httpx    │ Playwright │ CDP Bridge  │ Camofox          │
│           │ Scrapling  │ 会话复用     │ 指纹伪装         │
│           │ crawl4ai   │ Cookie 注入  │ 代理轮换         │
├─────────────────────────────────────────────────────────┤
│                    数据提取层                             │
│         (智能字段抽取 / 榜单抽取 / 表格识别)               │
├─────────────────────────────────────────────────────────┤
│                    数据存储层                             │
│         (数据集保存 / 数据库 / 文件导出)                   │
└─────────────────────────────────────────────────────────┘
```

### 核心模块

#### 1. 登录态管理器 (AuthManager)
```python
class AuthManager:
    """登录态管理器"""
    
    # 功能：
    # - Cookie 持久化存储
    # - Token 自动刷新
    # - 多账号管理
    # - 登录状态检测
    
    async def login_with_cdp(self, url: str, credentials: dict):
        """使用 CDP Bridge 登录"""
        pass
    
    async def inject_cookies(self, page, cookies: list):
        """注入 Cookie"""
        pass
    
    async def save_session(self, platform: str, session_data: dict):
        """保存会话"""
        pass
```

#### 2. 反爬策略引擎 (AntiCrawlEngine)
```python
class AntiCrawlEngine:
    """反爬策略引擎"""
    
    # 功能：
    # - 指纹伪装
    # - 行为模拟
    # - 验证码处理
    # - 代理轮换
    
    async def bypass_cloudflare(self, url: str):
        """绕过 Cloudflare"""
        pass
    
    async def solve_captcha(self, image: bytes):
        """验证码识别"""
        pass
    
    async def rotate_proxy(self):
        """代理轮换"""
        pass
```

#### 3. JS 逆向引擎 (JSReverseEngine)
```python
class JSReverseEngine:
    """JS 逆向引擎"""
    
    # 功能：
    # - AST 分析
    # - 参数还原
    # - 签名计算
    # - 本地执行
    
    async def analyze_js(self, js_url: str):
        """分析 JS 文件"""
        pass
    
    async def extract_signature(self, js_code: str):
        """提取签名算法"""
        pass
    
    async def execute_locally(self, js_code: str, params: dict):
        """本地执行 JS"""
        pass
```

---

## 🔧 技术选型

### CDP Bridge MCP
- **用途**: 浏览器远程控制、登录态接管
- **优势**: 可复用已有登录态、支持复杂交互
- **集成**: 通过 MCP 协议与主系统通信

### Scrapling
- **用途**: 反爬绕过、指纹伪装
- **优势**: 成熟稳定、支持多种绕过策略
- **集成**: 已有基础设施，扩展即可

### crawl4ai
- **用途**: 智能提取、Markdown 输出
- **优势**: 专为 LLM 设计、提取准确率高
- **集成**: 已有基础设施

### Camofox Browser
- **用途**: 高级指纹伪装
- **优势**: 模拟真实浏览器指纹
- **集成**: 作为 Playwright 的替代/增强

### JS 逆向
- **工具**: PyExecJS / Node.js / AST 分析
- **用途**: 逆向加密参数、签名算法
- **场景**: 需要还原请求参数的计算逻辑

---

## 📅 实施计划

### Day 1: 基础设施
| 任务 | 时间 | 内容 |
|------|------|------|
| 1.1 | 30min | 安装 Camofox / CDP Bridge 依赖 |
| 1.2 | 30min | 创建 AuthManager 模块 |
| 1.3 | 30min | 创建 AntiCrawlEngine 模块 |
| 1.4 | 30min | 创建 JSReverseEngine 模块 |

### Day 2: 核心功能
| 任务 | 时间 | 内容 |
|------|------|------|
| 2.1 | 45min | 实现 Cookie 持久化存储 |
| 2.2 | 45min | 实现 CDP Bridge 登录流程 |
| 2.3 | 45min | 实现指纹伪装增强 |
| 2.4 | 45min | 实现验证码识别接口 |

### Day 3: 集成与测试
| 任务 | 时间 | 内容 |
|------|------|------|
| 3.1 | 45min | 集成到智能采集流程 |
| 3.2 | 45min | 前端新增登录态配置 |
| 3.3 | 45min | 测试真实登录场景 |
| 3.4 | 45min | 测试反爬绕过效果 |

---

## 🧪 测试场景

### 场景 1: 豆瓣登录采集
```
URL: https://movie.douban.com/top250
状态: 未登录可访问（已测试通过）
扩展: 登录后采集用户评分、收藏列表
```

### 场景 2: 微博登录采集
```
URL: https://weibo.com
状态: 需要登录
测试: CDP Bridge 登录 → 采集热搜/用户动态
```

### 场景 3: 反爬测试
```
URL: https://www.cloudflare.com/
状态: 有 Cloudflare 保护
测试: 指纹伪装 + 行为模拟 → 绕过验证
```

---

## 📁 文件结构

```
crawlers/
├── auth/
│   ├── __init__.py
│   ├── auth_manager.py       # 登录态管理器
│   ├── cookie_store.py       # Cookie 持久化
│   └── cdp_bridge.py         # CDP Bridge 客户端
├── anticrawl/
│   ├── __init__.py
│   ├── anticrawl_engine.py   # 反爬策略引擎
│   ├── fingerprint.py        # 指纹伪装
│   ├── captcha_solver.py     # 验证码处理
│   └── proxy_rotator.py      # 代理轮换
├── jsreverse/
│   ├── __init__.py
│   ├── js_reverse_engine.py  # JS 逆向引擎
│   ├── ast_analyzer.py       # AST 分析器
│   └── signature_extractor.py # 签名提取器
└── ...
```

---

## 🔑 关键技术点

### 1. CDP Bridge MCP 集成
```python
# 通过 MCP 协议控制浏览器
async def cdp_login(url: str, username: str, password: str):
    cdp = CDPBridgeClient()
    page = await cdp.connect()
    await page.goto(url)
    await page.fill("#username", username)
    await page.fill("#password", password)
    await page.click("#login")
    cookies = await page.cookies()
    await cdp.disconnect()
    return cookies
```

### 2. 指纹伪装
```python
# Camofox 指纹伪装
async def stealth_fetch(url: str):
    browser = await camofox.launch()
    page = await browser.new_page()
    await page.set_viewport({"width": 1920, "height": 1080})
    await page.set_user_agent("Mozilla/5.0 ...")
    await page.goto(url)
    html = await page.content()
    await browser.close()
    return html
```

### 3. JS 逆向
```python
# 逆向签名算法
async def reverse_signature(js_url: str):
    js_code = await fetch_js(js_url)
    ast = parse_ast(js_code)
    signature_func = find_signature_function(ast)
    return signature_func
```

---

## ✅ 验收标准

### Completeness
- [ ] 所有 12 个任务完成
- [ ] 登录态采集可用
- [ ] 反爬绕过可用
- [ ] JS 逆向可用

### Correctness
- [ ] 豆瓣登录采集测试通过
- [ ] 微博登录采集测试通过
- [ ] Cloudflare 绕过测试通过
- [ ] 验证码识别准确率 > 80%

### Coherence
- [ ] 架构与提案一致
- [ ] 命名规范统一
- [ ] 与现有模块集成良好

---

*提案设计: 小彩 | 2026-05-09 12:30*
