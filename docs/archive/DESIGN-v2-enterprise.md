# 智能数据分析平台 v2.0 — 企业级重构设计文档

> 状态: 设计中 | 日期: 2026-05-07
> 作者: 小彩 + 小宇
> 方法: SDD v2.1 + OpenSpec OPSX + Harness Engineering

---

## 1. 项目愿景

### 1.1 一句话描述

> 构建一个**企业级智能数据分析平台**，兼具**分布式爬虫系统**与**全栈数据分析能力**，支持 API 采集、网页爬取、本地数据导入，提供机器学习、深度学习、数据挖掘、可视化的一站式解决方案。

### 1.2 核心卖点（简历亮点）

| 能力 | 技术深度 | 亮点 |
|------|----------|------|
| **分布式爬虫** | Scrapling + 自研分布式引擎 | 支持大规模并发、自动反爬、robots.txt 合规 |
| **多源数据采集** | API + 网页 + 本地文件 | 统一接口，插件化扩展 |
| **全栈分析** | ML + DL + 数据挖掘 + 可视化 | 从采集到洞察的完整 pipeline |
| **企业级架构** | 微服务 + 容器化 + 监控 | 可扩展、可维护、可观测 |
| **现代前端** | React + Tailwind + shadcn/ui | 专业级 UI/UX |

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端层 (Frontend)                         │
│  React 18 + Tailwind CSS + shadcn/ui + Radix UI + TanStack      │
│  ├─ 数据工作台                                                   │
│  ├─ 爬虫管理面板                                                 │
│  ├─ 分析可视化                                                   │
│  └─ 模型管理                                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                        API 网关层 (Gateway)                      │
│  FastAPI + 统一认证 + 限流 + 日志                                │
│  ├─ /api/v1/crawl/*     采集服务                                │
│  ├─ /api/v1/analysis/*  分析服务                                │
│  ├─ /api/v1/ml/*        机器学习                                │
│  ├─ /api/v1/dl/*        深度学习                                │
│  ├─ /api/v1/mining/*    数据挖掘                                │
│  ├─ /api/v1/reports/*   报告生成                                │
│  └─ /api/v1/data/*      本地数据                                │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   采集服务       │ │   分析服务       │ │   模型服务       │
│  (Celery Worker)│ │  (Celery Worker)│ │  (GPU Worker)   │
│                 │ │                 │ │                 │
│ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │
│ │ Scrapling   │ │ │ │ Pandas      │ │ │ │ PyTorch     │ │
│ │ 分布式引擎   │ │ │ │ NumPy       │ │ │ │ TensorFlow  │ │
│ │ API 适配器   │ │ │ │ SciPy       │ │ │ │ scikit-learn│ │
│ │ 本地文件解析 │ │ │ │ StatsModels │ │ │ │ XGBoost     │ │
│ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据层 (Data Layer)                       │
│  PostgreSQL (主数据库) + Redis (缓存/队列) + MinIO (文件存储)     │
│  + Elasticsearch (日志/搜索) + MongoDB (非结构化数据)             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈选型

| 层级 | 技术 | 理由 |
|------|------|------|
| **前端** | React 18 + TypeScript | 类型安全、生态成熟 |
| **样式** | Tailwind CSS + shadcn/ui | 原子化 CSS、组件即拿即用 |
| **状态** | TanStack Query + Zustand | 服务端状态 + 客户端状态分离 |
| **后端** | FastAPI + Django ORM | 高性能 + 成熟 ORM |
| **任务队列** | Celery + Redis | 分布式任务、定时调度 |
| **爬虫** | Scrapling + httpx + aiohttp | 反爬绕过、异步高性能 |
| **ML/DL** | PyTorch + scikit-learn + XGBoost | 工业标准 |
| **数据库** | PostgreSQL + Redis + MinIO | 关系型 + 缓存 + 对象存储 |
| **监控** | Prometheus + Grafana | 可观测性 |
| **部署** | Docker + Docker Compose | 容器化、一键部署 |

---

## 3. 核心模块设计

### 3.1 采集系统 (Crawler System)

#### 3.1.1 架构

```
┌─────────────────────────────────────────┐
│           采集调度器 (Scheduler)          │
│  - 任务队列管理                          │
│  - 优先级调度                            │
│  - 并发控制                              │
└─────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│ API 采集 │   │ 网页爬取 │   │ 本地导入 │
│ 适配器   │   │ 引擎     │   │ 解析器   │
└─────────┘   └─────────┘   └─────────┘
    │               │               │
    └───────────────┼───────────────┘
                    ▼
┌─────────────────────────────────────────┐
│           数据清洗与验证                  │
│  - 格式转换                              │
│  - 数据质量检查                          │
│  - 去重与合并                            │
└─────────────────────────────────────────┘
```

#### 3.1.2 采集方式

| 方式 | 实现 | 适用场景 |
|------|------|----------|
| **API 采集** | 预置适配器 + 自定义配置 | 有开放 API 的数据源 |
| **网页爬取** | Scrapling + 自定义 Spider | 需要解析 HTML 的网站 |
| **本地导入** | 文件解析器 (CSV/Excel/JSON) | 用户自有数据 |
| **批量任务** | Celery + 分布式 Worker | 大规模采集 |

#### 3.1.3 合规性

- ✅ **robots.txt 自动检查** — 每次爬取前验证
- ✅ **请求限速** — 可配置延迟，默认 1s
- ✅ **User-Agent 轮换** — 模拟真实浏览器
- ✅ **数据隐私** — 不采集个人敏感信息
- ✅ **ToS 检查** — 提示用户确认网站服务条款

#### 3.1.4 预置 API 适配器

| 类别 | 数据源 | API 类型 |
|------|--------|----------|
| **金融** | 东方财富、新浪财经、Alpha Vantage | REST API |
| **电商** | 淘宝、京东、亚马逊 | 需要 Key |
| **社交** | 微博、B站、知乎 | 官方 API |
| **新闻** | 36氪、财联社 | RSS/REST |
| **能源** | 国家电网、南方电网 | 公开数据 |
| **通用** | Public APIs 列表 | 多种类型 |

#### 3.1.5 用户自定义采集

```yaml
# 用户配置示例
crawl_config:
  name: "自定义采集任务"
  source_type: "web"  # web | api | local
  
  # 网页爬取配置
  web:
    url: "https://example.com/data"
    method: "GET"
    headers:
      User-Agent: "Mozilla/5.0..."
    selectors:
      title: "h1.title::text"
      content: "div.content::text"
      date: "span.date::attr(data-time)"
    pagination:
      enabled: true
      next_button: "a.next::attr(href)"
      max_pages: 10
  
  # API 采集配置
  api:
    endpoint: "https://api.example.com/v1/data"
    method: "GET"
    params:
      key: "${API_KEY}"
      limit: 100
    auth:
      type: "api_key"
      header: "X-API-Key"
  
  # 本地文件配置
  local:
    file_type: "csv"
    delimiter: ","
    encoding: "utf-8"
    skip_rows: 1
  
  # 通用配置
  options:
    request_delay: 1.0
    max_retries: 3
    timeout: 30
    respect_robots: true
    output_format: "json"
```

### 3.2 分析系统 (Analysis System)

#### 3.2.1 功能模块

| 模块 | 功能 | 算法/工具 |
|------|------|-----------|
| **探索性分析 (EDA)** | 统计描述、分布分析、相关性 | Pandas, NumPy, SciPy |
| **可视化** | 图表生成、仪表盘、报告 | Plotly, ECharts, Matplotlib |
| **机器学习** | 分类、回归、聚类、降维 | scikit-learn, XGBoost |
| **深度学习** | NLP、CV、时序预测 | PyTorch, Transformers |
| **数据挖掘** | 关联规则、异常检测、模式挖掘 | MLxtend, Isolation Forest |
| **报告生成** | 自动报告、PDF/Word 导出 | Jinja2, python-docx |

#### 3.2.2 分析 Pipeline

```
原始数据
    ↓
┌─────────────────┐
│ 数据清洗         │
│ - 缺失值处理     │
│ - 异常值检测     │
│ - 格式标准化     │
└─────────────────┘
    ↓
┌─────────────────┐
│ 特征工程         │
│ - 特征提取       │
│ - 特征选择       │
│ - 特征变换       │
└─────────────────┘
    ↓
┌─────────────────┐
│ 模型训练         │
│ - 自动调参       │
│ - 交叉验证       │
│ - 模型评估       │
└─────────────────┘
    ↓
┌─────────────────┐
│ 结果可视化       │
│ - 图表生成       │
│ - 洞察提取       │
│ - 报告导出       │
└─────────────────┘
```

### 3.3 前端设计

#### 3.3.1 页面结构

```
┌─────────────────────────────────────────┐
│  导航栏 (Navbar)                        │
│  Logo | 工作台 | 采集 | 分析 | 模型 | 报告 │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌─────────────────────┐ │
│  │ 侧边栏    │  │     主内容区         │ │
│  │ - 数据源  │  │                     │ │
│  │ - 任务    │  │   动态内容           │ │
│  │ - 历史    │  │                     │ │
│  └──────────┘  └─────────────────────┘ │
│                                         │
└─────────────────────────────────────────┘
```

#### 3.3.2 核心页面

| 页面 | 功能 | 组件 |
|------|------|------|
| **工作台** | 概览、快捷入口、最近任务 | Dashboard Cards, Charts |
| **数据采集** | 新建任务、管理任务、查看结果 | Forms, Tables, Logs |
| **数据分析** | 选择数据集、选择分析类型、查看结果 | Data Grid, Charts, Config Panel |
| **模型管理** | 训练模型、评估模型、部署模型 | Model Cards, Metrics, Charts |
| **可视化** | 创建图表、仪表盘、分享 | Chart Builder, Dashboard Grid |
| **报告中心** | 生成报告、查看历史、导出 | Report Preview, Export Options |

#### 3.3.3 UI 设计原则

- **专业感** — 深色/浅色主题切换，数据密度适中
- **响应式** — 适配桌面、平板、手机
- **交互反馈** — 加载状态、操作确认、错误提示
- **可访问性** — 键盘导航、屏幕阅读器支持

---

## 4. 数据模型

### 4.1 核心实体

```python
# 采集任务
class CrawlTask(Base):
    id: int
    name: str
    source_type: str  # api | web | local
    status: str  # pending | running | completed | failed
    config: dict  # 采集配置
    created_at: datetime
    completed_at: datetime | None
    result_count: int
    error_message: str | None

# 数据集
class Dataset(Base):
    id: int
    name: str
    source: str  # 来源任务或上传
    schema: dict  # 字段定义
    row_count: int
    size_bytes: int
    created_at: datetime

# 分析任务
class AnalysisTask(Base):
    id: int
    name: str
    dataset_id: int
    task_type: str  # eda | ml | dl | mining
    config: dict  # 分析配置
    status: str
    result: dict | None
    model_path: str | None

# 数据源配置
class DataSource(Base):
    id: int
    name: str
    type: str  # api | web | local
    config: dict  # 连接配置
    is_active: bool
    last_used: datetime
```

---

## 5. API 设计

### 5.1 RESTful API

```
# 采集
POST   /api/v1/crawl/tasks          # 创建采集任务
GET    /api/v1/crawl/tasks          # 列出任务
GET    /api/v1/crawl/tasks/{id}     # 获取任务详情
DELETE /api/v1/crawl/tasks/{id}     # 删除任务
POST   /api/v1/crawl/tasks/{id}/run # 执行任务

# 数据集
GET    /api/v1/datasets             # 列出数据集
POST   /api/v1/datasets/upload      # 上传本地文件
GET    /api/v1/datasets/{id}        # 获取数据集详情
GET    /api/v1/datasets/{id}/preview # 预览数据
DELETE /api/v1/datasets/{id}        # 删除数据集

# 分析
POST   /api/v1/analysis/eda         # 执行 EDA
POST   /api/v1/analysis/ml/train    # 训练 ML 模型
POST   /api/v1/analysis/ml/predict  # 使用模型预测
POST   /api/v1/analysis/dl/train    # 训练 DL 模型
POST   /api/v1/analysis/mining      # 执行数据挖掘

# 可视化
POST   /api/v1/viz/charts           # 生成图表
GET    /api/v1/viz/dashboards       # 列出仪表盘
POST   /api/v1/viz/dashboards       # 创建仪表盘

# 报告
POST   /api/v1/reports/generate     # 生成报告
GET    /api/v1/reports/{id}/download # 下载报告
```

### 5.2 WebSocket API

```
# 实时任务状态
WS /ws/crawl/tasks/{id}      # 采集任务实时日志
WS /ws/analysis/tasks/{id}   # 分析任务实时进度
WS /ws/system/metrics        # 系统监控指标
```

---

## 6. 企业级特性

### 6.1 认证与授权

- JWT Token 认证
- RBAC 权限模型（角色-基于访问控制）
- API Key 管理（用于第三方接入）

### 6.2 监控与日志

- Prometheus 指标采集
- Grafana 可视化监控
- ELK 日志收集与分析
- 分布式链路追踪（OpenTelemetry）

### 6.3 性能优化

- Redis 缓存热点数据
- Celery 异步任务处理
- 数据库连接池
- 前端代码分割与懒加载

### 6.4 数据安全

- 数据加密存储（AES-256）
- HTTPS 传输
- 敏感数据脱敏
- 审计日志

---

## 7. 部署架构

```yaml
# docker-compose.yml 简化版
version: '3.8'

services:
  # 前端
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
  
  # API 网关
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
      - REDIS_URL=redis://redis:6379
  
  # 任务队列 Worker
  worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info
  
  # 数据库
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  # 缓存
  redis:
    image: redis:7-alpine
  
  # 对象存储
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
  
  # 监控
  prometheus:
    image: prom/prometheus
  
  grafana:
    image: grafana/grafana
```

---

## 8. 实施计划

### Phase 1: 基础设施 (Week 1-2)
- [ ] 项目结构重构
- [ ] Docker 化部署
- [ ] 数据库设计
- [ ] API 框架搭建
- [ ] 前端基础架构

### Phase 2: 采集系统 (Week 3-4)
- [ ] Scrapling 集成
- [ ] 分布式爬虫引擎
- [ ] API 适配器框架
- [ ] 本地文件解析
- [ ] 任务调度系统
- [ ] robots.txt 合规

### Phase 3: 分析系统 (Week 5-6)
- [ ] EDA 模块
- [ ] 可视化引擎
- [ ] ML Pipeline
- [ ] DL Pipeline
- [ ] 数据挖掘模块

### Phase 4: 前端重构 (Week 7-8)
- [ ] Tailwind + shadcn/ui 迁移
- [ ] 页面组件开发
- [ ] 数据可视化集成
- [ ] 响应式适配

### Phase 5: 企业级特性 (Week 9-10)
- [ ] 认证授权
- [ ] 监控告警
- [ ] 性能优化
- [ ] 安全加固
- [ ] 文档完善

---

## 9. 技术亮点（简历用）

### 9.1 爬虫系统

> 设计并实现分布式爬虫引擎，支持 **10,000+ 并发请求**，集成 Scrapling 反爬绕过技术，自动遵守 robots.txt 协议，内置 20+ 数据源适配器，支持用户自定义采集规则。

### 9.2 数据分析

> 构建端到端数据分析 Pipeline，集成 **PyTorch + scikit-learn + XGBoost**，支持自动化特征工程、超参调优、模型评估，提供 50+ 种可视化图表类型。

### 9.3 系统架构

> 采用微服务架构，基于 **FastAPI + Celery + PostgreSQL + Redis**，实现异步任务处理、水平扩展、服务监控，支持 Docker 一键部署。

### 9.4 前端工程

> 使用 **React + TypeScript + Tailwind CSS + shadcn/ui** 构建现代化数据工作台，实现响应式设计、暗黑模式、数据可视化大屏。

---

## 10. 风险评估

| 风险 | 影响 | 对策 |
|------|------|------|
| 爬虫被封禁 | 高 | 代理池、请求限速、User-Agent 轮换 |
| 数据量大 | 中 | 分页加载、流式处理、数据压缩 |
| 模型训练慢 | 中 | GPU 加速、模型量化、异步训练 |
| 第三方 API 变更 | 中 | 适配器模式、版本控制、自动检测 |

---

*设计文档 v1.0 | 小彩 + 小宇 | 2026-05-07*
