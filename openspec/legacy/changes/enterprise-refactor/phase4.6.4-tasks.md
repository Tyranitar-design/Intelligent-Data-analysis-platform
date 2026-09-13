# Phase 4.6.4 — 实施任务清单

## Day 1: 基础设施 (2h)

### Task 1.1: 安装依赖 (30min)
- [ ] 安装 Camofox: `pip install camofox`
- [ ] 安装 CDP Bridge: `pip install cdp-bridge`
- [ ] 安装 PyExecJS: `pip install PyExecJS`
- [ ] 安装 AST 分析: `pip install esprima`
- [ ] 验证安装

### Task 1.2: 创建 AuthManager 模块 (30min)
- [ ] 创建 `crawlers/auth/__init__.py`
- [ ] 创建 `crawlers/auth/auth_manager.py`
- [ ] 实现 Cookie 存储接口
- [ ] 实现 Token 刷新接口

### Task 1.3: 创建 AntiCrawlEngine 模块 (30min)
- [ ] 创建 `crawlers/anticrawl/__init__.py`
- [ ] 创建 `crawlers/anticrawl/anticrawl_engine.py`
- [ ] 实现指纹伪装接口
- [ ] 实现代理轮换接口

### Task 1.4: 创建 JSReverseEngine 模块 (30min)
- [ ] 创建 `crawlers/jsreverse/__init__.py`
- [ ] 创建 `crawlers/jsreverse/js_reverse_engine.py`
- [ ] 实现 AST 分析接口
- [ ] 实现签名提取接口

## Day 2: 核心功能 (3h)

### Task 2.1: Cookie 持久化存储 (45min)
- [ ] 实现 SQLite Cookie 存储
- [ ] 实现 Cookie 加密
- [ ] 实现 Cookie 过期检测
- [ ] 测试 Cookie 读写

### Task 2.2: CDP Bridge 登录流程 (45min)
- [ ] 实现 CDP Bridge 客户端
- [ ] 实现登录交互流程
- [ ] 实现 Cookie 提取
- [ ] 测试豆瓣登录

### Task 2.3: 指纹伪装增强 (45min)
- [ ] 集成 Camofox
- [ ] 实现指纹随机化
- [ ] 实现行为模拟
- [ ] 测试指纹检测

### Task 2.4: 验证码识别接口 (45min)
- [ ] 集成 2captcha API
- [ ] 实现图片验证码识别
- [ ] 实现滑块验证码识别
- [ ] 测试识别准确率

## Day 3: 集成与测试 (3h)

### Task 3.1: 集成到智能采集流程 (45min)
- [ ] 修改 `smart_extractor.py`
- [ ] 添加登录态检测
- [ ] 添加反爬策略选择
- [ ] 测试集成效果

### Task 3.2: 前端新增登录态配置 (45min)
- [ ] 新增登录配置 Tab
- [ ] 实现 Cookie 输入
- [ ] 实现登录按钮
- [ ] 测试前端交互

### Task 3.3: 测试真实登录场景 (45min)
- [ ] 测试豆瓣登录采集
- [ ] 测试微博登录采集
- [ ] 测试小红书登录采集
- [ ] 记录测试结果

### Task 3.4: 测试反爬绕过效果 (45min)
- [ ] 测试 Cloudflare 绕过
- [ ] 测试验证码绕过
- [ ] 测试指纹检测绕过
- [ ] 记录测试结果

## 验收检查点

- [ ] 所有 12 个任务完成
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 文档更新完成
