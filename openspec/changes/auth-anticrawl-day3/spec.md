# OpenSpec: 登录验证与反爬策略 Day 3

## 变更摘要

将登录态管理集成到智能采集流程，新增前端配置界面，完成端到端测试。

## 变更详情

### 1. 后端集成

**文件**: `crawlers/url_crawler.py`
- 集成 AuthManager
- 所有爬取策略支持 auth_platform + use_auth 参数
- Cookie 自动注入到 HTTP 请求

**文件**: `api/routers/crawl.py`
- 新增 7 个登录管理 API
- URLCrawlRequest / SmartExtractRequest 新增登录态字段

### 2. 前端组件

**新增**: `frontend/src/components/AuthManager.tsx`
- 平台选择（5 大平台）
- 自动登录表单
- Cookie JSON 导入
- 会话管理

**修改**: `frontend/src/pages/Crawl.tsx`
- 顶部登录态配置栏
- 智能采集/URL爬取集成登录态参数

### 3. 测试

**新增**: `backend/test_auth_integration.py`
- 5 项集成测试
- 全部通过

## 验证结果

```
[OK] 通过 Cookie 存储
[OK] 通过 AuthManager
[OK] 通过 URLCrawler + 登录态
[OK] 通过 反爬绕过
[OK] 通过 URL 探测

总计: 5/5 通过
```

## 后续任务

- Day 4: 更多平台 / 验证码集成 / 代理池 / 自动刷新
- Phase 5: 企业级特性

---

*OpenSpec 版本: v2.0*
*日期: 2026-05-09*
