# Harness Engineering Specification v1.0.0

> 工程化实践规范 - 确保代码质量、可维护性和可扩展性

---

## 核心理念

**Harness (挽具/约束系统)** - 为快速迭代提供结构约束，在保持灵活性的同时确保工程质量。

---

## 1. 接口设计

### 1.1 抽象基类

```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

@runtime_checkable
class CrawlerProtocol(Protocol):
    """爬虫协议定义"""
    async def crawl(self, url: str) -> CrawlResult: ...
    async def probe(self, url: str) -> ProbeResult: ...

class BaseCrawler(ABC):
    """爬虫基类"""

    name: str
    enabled: bool = True

    def __init__(self, config: Config = None):
        self.config = config or self._default_config()
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        """子类初始化"""
        pass

    @abstractmethod
    async def crawl(self, url: str, **kwargs) -> CrawlResult:
        """执行爬取"""
        pass

    def _default_config(self) -> Config:
        """默认配置"""
        return Config()
```

### 1.2 接口约束

| 规则 | 描述 |
|------|------|
| INT-001 | 所有外部接口必须定义 Protocol 或 ABC |
| INT-002 | 接口方法必须使用类型注解 |
| INT-003 | 复杂参数使用 Pydantic/Dataclass |
| INT-004 | 返回值必须定义数据类 |

---

## 2. 配置管理

### 2.1 Pydantic 配置模型

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class ScraperConfig(BaseModel):
    """爬虫配置"""

    # 超时配置
    request_timeout: int = Field(default=30, ge=1, le=300)
    browser_timeout: int = Field(default=60, ge=1, le=600)

    # 并发控制
    max_concurrent: int = Field(default=10, ge=1, le=100)
    rate_limit: float = Field(default=1.0, ge=0.1)

    # 重试策略
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_backoff: float = Field(default=2.0, ge=1.0)

    # 日志
    log_level: LogLevel = LogLevel.INFO

    @validator('rate_limit')
    def validate_rate_limit(cls, v):
        if v <= 0:
            raise ValueError("rate_limit must be positive")
        return v
```

### 2.2 配置规范

| 规则 | 描述 |
|------|------|
| CFG-001 | 使用 Pydantic BaseModel 定义配置 |
| CFG-002 | 使用 Field 设置范围约束 |
| CFG-003 | 使用 validator 进行交叉验证 |
| CFG-004 | 支持环境变量覆盖 (`os.getenv`) |
| CFG-005 | 配置版本化，便于迁移 |

---

## 3. 错误处理

### 3.1 统一异常体系

```python
class ScraperError(Exception):
    """爬虫基础异常"""
    code: str = "SCRAPER_ERROR"
    status_code: int = 500

class ProbeError(ScraperError):
    """探测失败"""
    code = "PROBE_ERROR"
    status_code = 400

class StrategyError(ScraperError):
    """策略执行失败"""
    code = "STRATEGY_ERROR"
    status_code = 500

class StrategyNotAvailable(StrategyError):
    """策略不可用"""
    code = "STRATEGY_NOT_AVAILABLE"

class StrategyTimeout(StrategyError):
    """策略超时"""
    code = "STRATEGY_TIMEOUT"

class QualityError(ScraperError):
    """质量评估失败"""
    code = "QUALITY_ERROR"
    status_code = 422
```

### 3.2 异常处理规范

| 规则 | 描述 |
|------|------|
| ERR-001 | 异常必须定义 code 和 status_code |
| ERR-002 | 使用异常链传递上下文 |
| ERR-003 | 日志记录包含 trace_id |
| ERR-004 | 对外 API 返回标准错误格式 |

### 3.3 标准错误格式

```json
{
    "error": {
        "code": "STRATEGY_TIMEOUT",
        "message": "爬取超时",
        "details": {
            "url": "https://example.com",
            "strategy": "playwright",
            "timeout": 90
        },
        "trace_id": "abc123"
    }
}
```

---

## 4. 数据模型

### 4.1 Pydantic 数据类

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class CrawlStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class CrawlResult(BaseModel):
    """爬取结果"""

    success: bool
    data: List[Dict[str, Any]] = Field(default_factory=list)
    message: str = ""
    source: str = ""

    # 元数据
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    elapsed: Optional[float] = None

    # 质量信息
    quality_score: Optional[float] = None
    quality_issues: List[str] = Field(default_factory=list)

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### 4.2 数据模型规范

| 规则 | 描述 |
|------|------|
| MOD-001 | 使用 Pydantic 定义所有数据模型 |
| MOD-002 | 必填字段使用 Field(..., required=True) |
| MOD-003 | 可选字段提供默认值 |
| MOD-004 | 枚举使用 str, Enum 形式 |
| MOD-005 | 时间统一使用 UTC |

---

## 5. 测试要求

### 5.1 测试结构

```
tests/
├── unit/
│   ├── test_crawler.py
│   └── test_strategy.py
├── integration/
│   └── test_crawl_flow.py
└── fixtures/
    ├── sample_html.py
    └── sample_api_response.py
```

### 5.2 测试规范

| 规则 | 描述 |
|------|------|
| TEST-001 | 单元测试覆盖率 > 80% |
| TEST-002 | 集成测试覆盖率 > 60% |
| TEST-003 | 使用 pytest + pytest-asyncio |
| TEST-004 | Mock 外部依赖 |
| TEST-005 | 测试数据使用 fixtures |

### 5.3 测试示例

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_config():
    return ScraperConfig(max_retries=1)

@pytest.fixture
def mock_http_client():
    client = AsyncMock()
    client.get = AsyncMock(return_value=MagicMock(
        status_code=200,
        text="<html></html>"
    ))
    return client

@pytest.mark.asyncio
async def test_crawl_success(mock_config, mock_http_client):
    """测试爬取成功"""
    crawler = HttpxStrategy(config=mock_config)
    crawler._client = mock_http_client

    result = await crawler.execute("https://example.com")

    assert result.success is True
    assert result.status_code == 200
```

---

## 6. 文档规范

### 6.1 Docstring 格式

```python
class HttpxStrategy:
    """HTTPX 爬取策略

    适用于：
    - API 请求
    - 静态页面
    - JSON/XML 响应

    示例：
        >>> strategy = HttpxStrategy(config)
        >>> result = await strategy.execute("https://api.example.com/data")
    """

    def __init__(self, config: ScraperConfig):
        """初始化策略

        Args:
            config: 爬虫配置
        """
        self.config = config
```

### 6.2 文档规范

| 规则 | 描述 |
|------|------|
| DOC-001 | 所有公共类/方法必须有 docstring |
| DOC-002 | 使用 Google Style Docstring |
| DOC-003 | 示例代码必须可执行 |
| DOC-004 | 参数说明包含类型和约束 |
| DOC-005 | 返回值说明包含成功/失败情况 |

---

## 7. 可观测性

### 7.1 结构化日志

```python
import structlog

logger = structlog.get_logger()

async def crawl(self, url: str) -> CrawlResult:
    """爬取 URL"""
    logger.info(
        "crawl_started",
        url=url,
        strategy=self.name,
        trace_id=get_trace_id()
    )

    try:
        result = await self._do_crawl(url)
        logger.info(
            "crawl_completed",
            url=url,
            success=result.success,
            duration_ms=result.elapsed * 1000,
            trace_id=get_trace_id()
        )
        return result
    except Exception as e:
        logger.error(
            "crawl_failed",
            url=url,
            error=str(e),
            trace_id=get_trace_id()
        )
        raise
```

### 7.2 指标导出

```python
from prometheus_client import Counter, Histogram, Gauge

# 指标定义
REQUESTS_TOTAL = Counter(
    'scraper_requests_total',
    'Total requests',
    ['strategy', 'status']
)

REQUEST_DURATION = Histogram(
    'scraper_request_duration_seconds',
    'Request duration',
    ['strategy']
)

QUALITY_SCORE = Gauge(
    'scraper_quality_score',
    'Quality score',
    ['url']
)

# 使用
with REQUEST_DURATION.labels(strategy='httpx').time():
    result = await crawler.crawl(url)
```

### 7.3 可观测性规范

| 规则 | 描述 |
|------|------|
| OBS-001 | 使用结构化日志（JSON 格式） |
| OBS-002 | 日志包含 trace_id |
| OBS-003 | 导出 Prometheus 指标 |
| OBS-004 | 支持 OpenTelemetry 链路追踪 |
| OBS-005 | 敏感信息脱敏 |

---

## 8. 依赖管理

### 8.1 版本约束

```toml
# pyproject.toml
[project]
dependencies = [
    "httpx>=0.27.0,<1.0.0",
    "pydantic>=2.0,<3.0",
    "structlog>=24.0",
    "prometheus-client>=0.19",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.3",
    "mypy>=1.9",
]
```

### 8.2 依赖规范

| 规则 | 描述 |
|------|------|
| DEP-001 | 使用 pyproject.toml 管理依赖 |
| DEP-002 | 固定主版本号 |
| DEP-003 | 可选依赖明确标记 |
| DEP-004 | 定期更新依赖 |

---

*Spec | 2026-05-09 | v1.0.0*
