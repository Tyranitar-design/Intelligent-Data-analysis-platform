# Proposal: 智能爬虫系统 v2.0 规范重构

## 概述

基于 [harness-engineering](../harness-engineering-1.0.0/specs.md) 和 [vibe-coding](./vibe-coding-1.0.0/specs.md) 规范，对现有爬虫系统进行企业级重构。

## 现状分析

### 已有能力
- `crawlers/` - 核心爬虫模块（分布式爬取、反爬对抗、认证管理）
- `anticrawl/` - 反爬对抗引擎、浏览器池管理
- `jsreverse/` - JS逆向引擎、签名提取器
- `auth/` - Cookie加密器、认证管理器
- `adapters/` - 多源数据适配器（东方财富、雪球等）

### 问题识别
1. **架构分散** - 缺少统一的智能调度层
2. **策略固化** - 爬取策略硬编码，难以动态切换
3. **质量缺失** - 缺乏数据质量评估与自愈机制
4. **可观测性弱** - 缺少统一日志与追踪体系
5. **扩展性差** - 新增爬虫需要大量重复代码

## 目标

构建一个**智能、自适应、可观测**的爬虫系统，具备：
- 自动探测与策略选择
- 数据质量自评估与修复
- 完整的可观测性支持
- 统一的扩展接口

## 实现方案

### 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Intelligent Scraper Engine                │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────┐ │
│  │  Intent    │  │  Quality  │  │  Adapt    │  │ Observ  │ │
│  │  Engine    │  │  Assessor  │  │  Manager  │  │ Logger  │ │
│  └───────────┘  └───────────┘  └───────────┘  └─────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Strategy Selection Layer                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ httpx    │ │ Scrapling│ │ crawl4ai │ │ Playwright     │  │
│  │ Strategy │ │ Strategy │ │ Strategy │ │ Strategy       │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Execution Layer                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Request  │ │ Browser  │ │ JS       │ │ Data           │  │
│  │ Pool     │ │ Pool     │ │ Executor │ │ Parser         │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 核心模块

1. **Intent Engine (意图引擎)**
   - URL 自动分类与意图识别
   - 动态策略选择
   - 意图学习与优化

2. **Quality Assessor (质量评估器)**
   - 结构完整性检查
   - 数据有效性验证
   - 完整性评分系统

3. **Adapt Manager (适配管理器)**
   - 运行时策略切换
   - 失败恢复机制
   - 自适应降级

4. **Observ Logger (可观测性日志)**
   - 结构化日志记录
   - 性能指标收集
   - 调用链路追踪

### 技术规范

遵循 [harness-engineering](../harness-engineering-1.0.0/specs.md):
- 核心接口：`AdaptiveScraper` 抽象类
- 配置管理：Pydantic 配置模型
- 错误处理：统一异常体系
- 测试覆盖：每模块 >80%

遵循 [vibe-coding](./vibe-coding-1.0.0/specs.md):
- 命名规范：snake_case（内部）/ camelCase（外部）
- 文档规范：Google Style Docstring
- 代码风格：Black + Ruff

## 影响范围

- 新增：`backend/crawlers/intelligent/` 模块
- 修改：`backend/crawlers/url_crawler.py` 集成
- 新增：`backend/tests/crawlers/intelligent/` 测试
- 修改：`backend/requirements.txt` 依赖更新

## 风险评估

- **低风险**：新模块，不影响现有功能
- **依赖**：crawl4ai 生态需要测试

## 时间估算

- Phase 1（核心框架）：1周
- Phase 2（质量评估）：3天
- Phase 3（可观测性）：2天
- Phase 4（集成测试）：2天

**总计**：约 2 周

## 参考资料

- [Harness Engineering Specs](../harness-engineering-1.0.0/specs.md)
- [Vibe Coding Specs](./vibe-coding-1.0.0/specs.md)
- [Enterprise Refactor Specs](../enterprise-refactor/specs.md)
- [Web Scraper Core Skill](../../.claude/skills/web-scraper-core-1.0.0/SKILL.md)
- [AI Web Scraper Skill](../../.claude/skills/ai-web-scraper-1.0.0/SKILL.md)
