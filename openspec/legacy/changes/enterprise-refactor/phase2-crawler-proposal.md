# Proposal: Phase 2 — 采集系统增强

> 状态: 待批准 | 日期: 2026-05-08
> 方法: SDD v2.1 sdd-propose | 作者: 小彩

---

## 1. 变更意图

在 Phase 1 基础设施之上，增强采集系统的**反爬能力、分布式调度、合规性、扩展性**，使其达到企业级标准。

## 2. 当前基线

| 组件 | 已有 | 缺失 |
|------|------|------|
| 爬虫基类 | ✅ BaseCrawler + 反爬增强 | ❌ 无 Scrapling |
| 数据源 | ✅ 金融/电商/能源/新闻 (4类) | ❌ 无用户自定义采集 |
| 分布式 | ⚠️ distributed.py 基础版 | ❌ 未集成 Celery |
| 合规 | ❌ 无 | ❌ 无 robots.txt 检查 |
| 本地导入 | ⚠️ local_data router 基础版 | ❌ 无 Parquet/增强解析 |
| 适配器 | ❌ 硬编码 | ❌ 无适配器框架 |

## 3. 变更范围 (6 个 Task)

### Task 2.1: Scrapling 集成
- 安装 Scrapling 依赖
- 创建 `ScraplingAdapter` 封装 Scrapling 的 StealthySession
- 集成到 BaseCrawler，新增 `fetch_with_scrapling()` 方法
- 测试反爬绕过（Cloudflare / Turnstile）

### Task 2.2: 分布式爬虫引擎 (Celery)
- 配置 Celery + Redis Broker（已有配置在 config.py）
- 创建 `crawl_tasks.py` 异步任务定义
- 任务状态追踪（pending → running → completed/failed）
- Worker 并发控制 + 优先级队列
- 断点续传 + 自动重试

### Task 2.3: robots.txt 合规
- 创建 `robots_checker.py` 模块
- 每次爬取前自动检查 robots.txt
- 支持 User-Agent 级别的 Allow/Disallow
- 合规报告 + 用户提示

### Task 2.4: API 适配器框架
- 设计适配器基类 `BaseAdapter`
- 预置 5 个金融适配器（东方财富、新浪、Alpha Vantage 等）
- 预置 2 个新闻适配器（36kr、财联社）
- 配置化管理（YAML/JSON 配置文件）
- 适配器注册表 + 自动发现

### Task 2.5: 用户自定义采集
- 用户配置 Schema（web/api/local 三种模式）
- 配置验证 Pydantic model
- 前端配置表单 API
- 测试运行 + 结果预览
- 采集配置存储到数据库

### Task 2.6: 本地文件导入增强
- 支持 CSV / Excel / JSON / Parquet 四种格式
- 大文件分块读取 + 流式处理
- 自动字段类型推断
- 数据预览（前 100 行）
- 编码自动检测

## 4. 非目标（Phase 3+）

- 分析系统（ML/DL Pipeline）
- 前端重构（shadcn/ui 迁移）
- 监控告警（Prometheus/Grafana）
- 认证授权（JWT/RBAC）— 已有基础框架

## 5. 技术方案概要

```
backend/
├── api/
│   ├── routers/
│   │   ├── crawl.py          # 增强：Scrapling + 自定义采集
│   │   └── dataset.py        # 新增：数据集管理
│   ├── models/
│   │   ├── crawl_task.py     # 增强：状态追踪
│   │   └── data_source.py   # 增强：配置化
│   └── tasks/
│       ├── crawl_tasks.py    # 新增：Celery 任务
│       └── __init__.py
├── crawlers/
│   ├── base.py               # 增强：Scrapling 集成
│   ├── scrapling_adapter.py  # 新增
│   ├── robots_checker.py     # 新增
│   ├── adapter_framework.py  # 新增：适配器基类
│   ├── adapters/             # 新增：预置适配器
│   │   ├── __init__.py
│   │   ├── eastmoney.py
│   │   ├── sina.py
│   │   ├── alpha_vantage.py
│   │   ├── kr36.py
│   │   └── cls.py
│   ├── custom/               # 新增：用户自定义
│   │   ├── __init__.py
│   │   ├── schema.py         # 配置 Schema
│   │   └── engine.py         # 自定义采集引擎
│   └── utils/
│       ├── anti_crawler.py   # 已有
│       ├── file_parser.py    # 新增：文件解析
│       └── encoding.py       # 新增：编码检测
├── celery_app.py             # 增强：完整 Celery 配置
└── requirements-v2.txt       # 更新依赖
```

## 6. 依赖新增

| 包 | 用途 | 大小 |
|----|------|------|
| `scrapling` | 反爬绕过 + 浏览器模拟 | ~50MB |
| `celery[redis]` | 分布式任务队列 | ~10MB |
| `chardet` | 编码检测 | ~2MB |
| `pyarrow` | Parquet 文件支持 | ~100MB |
| `openpyxl` | Excel 文件解析 | ~5MB |

## 7. 风险

| 风险 | 概率 | 对策 |
|------|------|------|
| Scrapling 安装复杂 | 中 | 先测试虚拟环境安装 |
| Celery 与现有代码冲突 | 低 | 新增独立模块，不修改 v1 代码 |
| 文件解析大内存 | 中 | 分块读取，流式处理 |

## 8. 预计工期

| Task | 预计时间 | 优先级 |
|------|----------|--------|
| 2.1 Scrapling 集成 | 45 min | P0 |
| 2.2 Celery 分布式引擎 | 60 min | P0 |
| 2.3 robots.txt 合规 | 30 min | P1 |
| 2.4 适配器框架 | 45 min | P0 |
| 2.5 用户自定义采集 | 40 min | P1 |
| 2.6 本地文件导入 | 35 min | P1 |

**总计**: ~4.5 小时，分 2-3 个会话完成

---

*Proposal | 2026-05-08 | 小彩*
