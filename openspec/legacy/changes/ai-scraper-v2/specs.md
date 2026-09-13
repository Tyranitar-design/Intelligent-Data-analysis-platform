# Specs: 智能爬虫系统 v2.0

> 基于 Harness Engineering + Vibe Coding 规范的企业级爬虫系统

---

## 模块架构

```
backend/crawlers/intelligent/
├── __init__.py                 # 模块导出
├── adaptive_scraper.py        # 核心：自适应爬虫引擎
├── intent_engine.py           # 意图识别与策略选择
├── quality_assessor.py         # 数据质量评估
├── adapt_manager.py           # 运行时适配管理
├── observ_logger.py           # 可观测性日志
├── strategies/                # 爬取策略
│   ├── __init__.py
│   ├── base.py               # 策略基类
│   ├── httpx_strategy.py     # httpx 策略
│   ├── scrapling_strategy.py # Scrapling 策略
│   ├── crawl4ai_strategy.py  # crawl4ai 策略
│   └── playwright_strategy.py # Playwright 策略
├── models.py                 # Pydantic 数据模型
└── exceptions.py             # 统一异常体系
```

---

## 功能规格

### 1. 自适应爬虫引擎 (AdaptiveScraper)

#### 1.1 核心接口
```python
class AdaptiveScraper(ABC):
    """自适应爬虫引擎核心接口"""

    @abstractmethod
    async def crawl(self, url: str, intent: CrawlIntent = None) -> CrawlResult:
        """智能爬取"""
        pass

    @abstractmethod
    async def probe(self, url: str) -> ProbeResult:
        """URL 探测"""
        pass
```

#### 1.2 配置模型
```python
@dataclass
class ScraperConfig:
    # 超时配置
    request_timeout: int = 30
    browser_timeout: int = 60

    # 并发控制
    max_concurrent: int = 10
    rate_limit: float = 1.0  # 请求/秒

    # 重试策略
    max_retries: int = 3
    retry_backoff: float = 2.0

    # 策略选择
    preferred_strategies: List[str] = field(
        default_factory=lambda: ["httpx", "scrapling", "crawl4ai", "playwright"]
    )

    # 质量阈值
    min_quality_score: float = 0.6

    # 可观测性
    enable_tracing: bool = True
    log_level: str = "INFO"
```

#### 1.3 行为规范
- **REQ-ISC-001**: 支持上下文管理器（`async with`）
- **REQ-ISC-002**: 支持依赖注入配置
- **REQ-ISC-003**: 支持生命周期钩子（`on_start`, `on_success`, `on_error`）
- **REQ-ISC-004**: 支持指标导出（Prometheus 格式）

---

### 2. 意图引擎 (Intent Engine)

#### 2.1 意图分类
```python
class IntentType(Enum):
    """爬取意图类型"""
    STATIC_CONTENT = "static_content"      # 静态内容
    DYNAMIC_CONTENT = "dynamic_content"    # 动态内容
    API_DATA = "api_data"                  # API 数据
    PROTECTED_CONTENT = "protected"         # 受保护内容
    AUTHENTICATED = "authenticated"        # 需要认证
    PAGINATED = "paginated"                # 分页数据
    STREAMING = "streaming"                # 流式数据
```

#### 2.2 探测规则
| 特征 | 意图 | 策略 |
|------|------|------|
| Content-Type: application/json | API_DATA | httpx |
| Content-Type: text/html + 无 JS 特征 | STATIC_CONTENT | httpx |
| 存在 Cloudflare/Turnstile | PROTECTED_CONTENT | Scrapling |
| 需要登录 Cookie | AUTHENTICATED | Playwright |
| 检测到分页结构 | PAGINATED | 自适应分页 |

#### 2.3 规则规格
- **REQ-INT-001**: 支持 YAML 配置文件定义规则
- **REQ-INT-002**: 支持规则优先级排序
- **REQ-INT-003**: 支持规则动态注册
- **REQ-INT-004**: 支持规则命中统计

---

### 3. 质量评估器 (Quality Assessor)

#### 3.1 评分维度
```python
@dataclass
class QualityScore:
    """质量评分"""
    completeness: float = 0.0   # 完整性 (0-1)
    validity: float = 0.0       # 有效性 (0-1)
    freshness: float = 0.0      # 新鲜度 (0-1)
    consistency: float = 0.0    # 一致性 (0-1)
    overall: float = 0.0        # 综合评分 (0-1)

@dataclass
class QualityReport:
    """质量报告"""
    score: QualityScore
    issues: List[QualityIssue]
    suggestions: List[str]
    metadata: Dict[str, Any]
```

#### 3.2 评估规则
| 维度 | 检查项 | 权重 |
|------|--------|------|
| completeness | 非空字段比例 >= 80% | 25% |
| completeness | 数据量符合预期 | 15% |
| validity | 字段类型正确 | 20% |
| validity | URL/Email 格式正确 | 10% |
| freshness | 数据非过期 | 15% |
| consistency | 字段值一致 | 15% |

#### 3.3 规格要求
- **REQ-QA-001**: 返回标准 QualityReport
- **REQ-QA-002**: 支持增量评估（diff 模式）
- **REQ-QA-003**: 支持自定义评估规则
- **REQ-QA-004**: 支持质量阈值告警

---

### 4. 适配管理器 (Adapt Manager)

#### 4.1 策略切换
```python
class StrategySwitch(Enum):
    """策略切换类型"""
    UPGRADE = "upgrade"    # 升级策略
    DEGRADE = "degrade"    # 降级策略
    SWITCH = "switch"      # 切换策略
    RETRY = "retry"       # 重试
    ABORT = "abort"       # 终止
```

#### 4.2 自适应规则
- **REQ-ADM-001**: 5xx 错误 → 重试 + 降级
- **REQ-ADM-002**: 403/418 → 升级到 Scrapling
- **REQ-ADM-003**: 超时 → 升级到 Playwright
- **REQ-ADM-004**: 质量评分 < 阈值 → 重新爬取或换策略
- **REQ-ADM-005**: 连续失败 3 次 → 标记问题并告警

#### 4.3 熔断机制
```python
@dataclass
class CircuitBreaker:
    """熔断器配置"""
    failure_threshold: int = 5      # 失败次数阈值
    recovery_timeout: int = 60      # 恢复超时（秒）
    half_open_max_calls: int = 3    # 半开状态最大调用数
```

---

### 5. 策略层 (Strategies)

#### 5.1 策略基类
```python
class BaseStrategy(ABC):
    """爬取策略基类"""

    name: str = "base"
    priority: int = 0

    @abstractmethod
    async def can_handle(self, probe: ProbeResult) -> bool:
        """判断是否可处理"""
        pass

    @abstractmethod
    async def execute(self, url: str, **kwargs) -> StrategyResult:
        """执行爬取"""
        pass

    async def validate(self, result: StrategyResult) -> bool:
        """验证结果"""
        return result.success and result.data is not None
```

#### 5.2 策略实现

| 策略 | 适用场景 | 优先级 | 超时 |
|------|----------|--------|------|
| httpx | API / 静态页面 | 100 | 30s |
| Scrapling | 反爬页面 | 80 | 45s |
| crawl4ai | SPA / 内容提取 | 60 | 60s |
| Playwright | 复杂交互 | 40 | 90s |

#### 5.3 规格要求
- **REQ-STR-001**: 所有策略实现 BaseStrategy 接口
- **REQ-STR-002**: 支持策略链式调用
- **REQ-STR-003**: 支持策略超时控制
- **REQ-STR-004**: 支持策略降级路径

---

### 6. 可观测性 (Observability)

#### 6.1 日志规范
```python
class CrawlLogLevel(Enum):
    """爬虫日志级别"""
    TRACE = 5   # 详细追踪
    DEBUG = 10  # 调试信息
    INFO = 20   # 一般信息
    WARNING = 30 # 警告
    ERROR = 40  # 错误
    CRITICAL = 50  # 严重
```

#### 6.2 日志格式
```json
{
    "timestamp": "2026-05-09T10:30:00.000Z",
    "level": "INFO",
    "logger": "intelligent.httpx_strategy",
    "message": "Request completed",
    "trace_id": "abc123",
    "span_id": "def456",
    "url": "https://example.com",
    "strategy": "httpx",
    "duration_ms": 234,
    "status_code": 200,
    "response_size": 12345
}
```

#### 6.3 指标定义
| 指标名 | 类型 | 说明 |
|--------|------|------|
| scraper_requests_total | Counter | 总请求数 |
| scraper_requests_success | Counter | 成功请求数 |
| scraper_requests_failed | Counter | 失败请求数 |
| scraper_request_duration_seconds | Histogram | 请求耗时 |
| scraper_strategy_switches_total | Counter | 策略切换次数 |
| scraper_quality_score | Gauge | 质量评分 |

#### 6.4 规格要求
- **REQ-OBS-001**: 结构化 JSON 日志输出
- **REQ-OBS-002**: 支持 OpenTelemetry 链路追踪
- **REQ-OBS-003**: 支持 Prometheus 指标导出
- **REQ-OBS-004**: 支持日志级别动态调整
- **REQ-OBS-005**: 敏感信息脱敏（Cookie、Token）

---

## 异常体系

```python
# 异常层级
ScraperError (基类)
├── ProbeError          # 探测失败
├── StrategyError       # 策略执行失败
│   ├── StrategyNotAvailable  # 策略不可用
│   ├── StrategyTimeout       # 策略超时
│   └── StrategyValidationError  # 结果验证失败
├── QualityError        # 质量评估失败
├── AdaptError          # 适配管理错误
└── ObservabilityError  # 可观测性错误
```

---

## 配置示例

### 基础配置 (config.yaml)
```yaml
scraper:
  request_timeout: 30
  browser_timeout: 60
  max_concurrent: 10
  rate_limit: 1.0
  max_retries: 3
  retry_backoff: 2.0
  min_quality_score: 0.6

strategies:
  - name: httpx
    enabled: true
    priority: 100
  - name: scrapling
    enabled: true
    priority: 80
  - name: crawl4ai
    enabled: true
    priority: 60
  - name: playwright
    enabled: true
    priority: 40

circuit_breaker:
  failure_threshold: 5
  recovery_timeout: 60
  half_open_max_calls: 3

observability:
  enable_tracing: true
  enable_metrics: true
  log_level: INFO
  log_format: json
```

---

## API 设计

### Python 接口
```python
# 基础使用
from crawlers.intelligent import AdaptiveScraper, ScraperConfig

config = ScraperConfig(min_quality_score=0.7)
scraper = AdaptiveScraper(config)

async with scraper:
    result = await scraper.crawl("https://example.com")
    print(f"Quality: {result.quality_score.overall}")

# 高级用法
result = await scraper.crawl(
    url="https://example.com",
    intent=IntentType.DYNAMIC_CONTENT,
    require_auth=True,
    auth_platform="example",
    pagination=True,
)
```

---

## 测试要求

| 测试类型 | 覆盖率目标 | 工具 |
|----------|------------|------|
| 单元测试 | >80% | pytest |
| 集成测试 | >60% | pytest + httpx |
| E2E 测试 | 关键路径 | pytest + Playwright |

---

## 兼容性

- **Python**: >= 3.10
- **依赖**:
  - httpx >= 0.27.0
  - crawl4ai >= 0.4.0
  - pydantic >= 2.0
  - opentelemetry-api >= 1.20

---

## 实施里程碑

| 阶段 | 内容 | 交付物 |
|------|------|--------|
| M1 | 核心框架 + 策略基类 | adaptive_scraper.py, strategies/ |
| M2 | Intent Engine + 策略实现 | intent_engine.py, 4 个策略 |
| M3 | Quality Assessor | quality_assessor.py |
| M4 | Adapt Manager | adapt_manager.py |
| M5 | Observ Logger + 集成 | observ_logger.py, 完整集成 |
| M6 | 测试 + 文档 | tests/, README |

---

*Specs | 2026-05-09 | v2.0*
