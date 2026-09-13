# Design: 企业级重构 v2.0

## 架构决策

### 1. 为什么选 FastAPI + Django ORM？

| 选项 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| FastAPI + SQLAlchemy | 高性能、异步 | ORM 较新 | ✅ 选用 |
| Django + DRF | 生态成熟 | 同步、较重 | ❌ 放弃 |
| Flask + SQLAlchemy | 轻量 | 需自己组装 | ❌ 放弃 |

**决策理由**: FastAPI 的异步性能适合高并发爬虫场景，Django ORM 提供成熟的模型管理。

### 2. 为什么选 Scrapling？

| 选项 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| Scrapling | 反爬绕过、自适应解析 | 较新 | ✅ 选用 |
| Scrapy | 生态成熟 | 配置复杂 | ❌ 放弃 |
| BeautifulSoup | 简单 | 无反爬 | ❌ 放弃 |

**决策理由**: Scrapling 内置反爬绕过，支持自适应解析，适合企业级爬虫需求。

### 3. 为什么选 Tailwind + shadcn/ui？

| 选项 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| Tailwind + shadcn | 原子化、组件即拿即用 | 学习曲线 | ✅ 选用 |
| Ant Design | 组件丰富 | 样式定制难 | ❌ 放弃 |
| Material UI | 设计规范 | 体积大 | ❌ 放弃 |

**决策理由**: Tailwind 的原子化 CSS 适合快速定制，shadcn/ui 提供高质量组件。

## 数据流设计

```
用户操作
    ↓
前端 (React)
    ↓ HTTP/WebSocket
API 网关 (FastAPI)
    ↓
任务分发 (Celery)
    ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ 采集 Worker  │ │ 分析 Worker  │ │ 模型 Worker  │
│ (Scrapling)  │ │ (Pandas)    │ │ (PyTorch)   │
└─────────────┘ └─────────────┘ └─────────────┘
    ↓               ↓               ↓
┌─────────────────────────────────────────────┐
│ 数据存储 (PostgreSQL + Redis + MinIO)        │
└─────────────────────────────────────────────┘
    ↓
前端展示
```

## 关键设计模式

### 1. 适配器模式 (Adapter)

用于统一不同数据源的接口：

```python
class DataSourceAdapter(ABC):
    @abstractmethod
    async def fetch(self, config: dict) -> CrawlResult:
        pass

class APIAdapter(DataSourceAdapter):
    async def fetch(self, config: dict) -> CrawlResult:
        # HTTP 请求
        pass

class WebAdapter(DataSourceAdapter):
    async def fetch(self, config: dict) -> CrawlResult:
        # Scrapling 爬取
        pass

class LocalAdapter(DataSourceAdapter):
    async def fetch(self, config: dict) -> CrawlResult:
        # 文件解析
        pass
```

### 2. 策略模式 (Strategy)

用于切换不同的分析算法：

```python
class AnalysisStrategy(ABC):
    @abstractmethod
    async def analyze(self, dataset: Dataset, config: dict) -> AnalysisResult:
        pass

class EDAStrategy(AnalysisStrategy):
    async def analyze(self, dataset, config):
        # 探索性分析
        pass

class MLStrategy(AnalysisStrategy):
    async def analyze(self, dataset, config):
        # 机器学习
        pass
```

### 3. 观察者模式 (Observer)

用于实时任务状态通知：

```python
class TaskObserver(ABC):
    @abstractmethod
    async def on_update(self, task_id: str, status: str):
        pass

class WebSocketNotifier(TaskObserver):
    async def on_update(self, task_id, status):
        # 推送 WebSocket 消息
        pass

class LoggerObserver(TaskObserver):
    async def on_update(self, task_id, status):
        # 记录日志
        pass
```

## 数据库设计

### ER 图

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    User      │     │  CrawlTask   │     │   Dataset    │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id (PK)      │────<│ user_id (FK) │     │ id (PK)      │
│ username     │     │ id (PK)      │────<│ source_id    │
│ email        │     │ name         │     │ name         │
│ role         │     │ status       │     │ schema       │
└──────────────┘     │ config       │     │ row_count    │
                     │ result       │     └──────────────┘
                     └──────────────┘           │
                            │                   │
                            ▼                   ▼
                     ┌──────────────┐     ┌──────────────┐
                     │ AnalysisTask │     │    Model     │
                     ├──────────────┤     ├──────────────┤
                     │ id (PK)      │     │ id (PK)      │
                     │ dataset_id   │────<│ dataset_id   │
                     │ type         │     │ name         │
                     │ result       │     │ path         │
                     └──────────────┘     │ metrics      │
                                          └──────────────┘
```

## API 版本策略

- **URL 版本**: `/api/v1/...`
- **Header 版本**: `Accept: application/vnd.api.v1+json`
- **向后兼容**: v1 保持兼容，v2 在需要时创建

## 错误处理策略

```python
# 统一错误响应
{
    "error": {
        "code": "INVALID_INPUT",
        "message": "请求参数错误",
        "details": [
            {"field": "url", "message": "URL 格式不正确"}
        ],
        "request_id": "req_123456"
    }
}
```

## 缓存策略

| 数据类型 | 缓存方式 | TTL |
|----------|----------|-----|
| 用户会话 | Redis | 24h |
| 数据集元数据 | Redis | 1h |
| 分析结果 | Redis | 30min |
| 静态资源 | CDN | 1d |

---

*Design | 2026-05-07*
