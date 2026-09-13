# Vibe Coding Specification v1.0.0

> 代码风格与协作规范 - 保持代码一致性、可读性和团队协作效率

---

## 核心理念

**Vibe (氛围/风格)** - 代码不仅是功能实现，更是团队协作的媒介。好的代码风格让阅读者感受到一致的"氛围"，降低认知负担。

---

## 1. 命名规范

### 1.1 Python 命名

```python
# ✓ 好的命名
class CrawlResult:
    """爬取结果"""

    def __init__(self, url: str, data: list[dict]):
        self.source_url = url  # snake_case
        self.raw_data = data
        self._cached = None    # 私有属性

    @property
    def is_empty(self) -> bool:
        """判断是否为空"""
        return len(self.raw_data) == 0

    async def fetch_page(self, page: int = 1) -> None:
        """获取页面"""
        ...

# ✗ 不好的命名
class result:  # 类名不用 snake_case
    def __init__(self, URL, Data):  # 全大写参数
        self.url = URL  # 重复命名
        self.data = Data
        self.cache = None  # 混淆私有
```

### 1.2 命名对照表

| 场景 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `CrawlResult`, `ScraperConfig` |
| 函数/方法 | snake_case | `fetch_page`, `get_data` |
| 变量 | snake_case | `page_count`, `result_list` |
| 常量 | UPPER_SNAKE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| 私有属性 | _snake_case | `_cache`, `_internal_state` |
| 类型别名 | PascalCase | `ResultList`, `UrlMap` |
| 枚举成员 | PascalCase | `Status.PENDING` |

### 1.3 命名规范

| 规则 | 描述 |
|------|------|
| NAME-001 | 类名使用名词或名词短语 |
| NAME-002 | 方法名使用动词或动词短语 |
| NAME-003 | 避免缩写（除非通用：url, id, api） |
| NAME-004 | 布尔变量使用 is/has/can 前缀 |
| NAME-005 | 避免单字母变量（循环变量除外） |

---

## 2. 代码格式

### 2.1 Ruff 配置

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",     # pycodestyle errors
    "W",     # pycodestyle warnings
    "F",     # Pyflakes
    "I",     # isort
    "N",     # pep8-naming
    "UP",    # pyupgrade
    "ASYNC", # async utilities
]
ignore = [
    "E501",  # line too long (handled by formatter)
]
```

### 2.2 Black 配置

```toml
[tool.black]
line-length = 100
target-version = ["py310"]
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | build
  | dist
)/
'''
```

### 2.3 格式规范

| 规则 | 描述 |
|------|------|
| FMT-001 | 使用 Black 格式化（行长度 100） |
| FMT-002 | 使用 isort 排序导入 |
| FMT-003 | 导入顺序：标准库 > 第三方 > 本地 |
| FMT-004 | 避免无用的导入 |
| FMT-005 | 空行分隔逻辑块 |

---

## 3. 类型注解

### 3.1 类型注解规范

```python
from typing import TypeVar, Generic, Callable, Awaitable
from collections.abc import AsyncIterator

T = TypeVar('T')
R = TypeVar('R')

# ✓ 好的类型注解
async def fetch_data(url: str) -> dict[str, Any]:
    """获取数据"""
    ...

async def process_items(
    items: list[int],
    processor: Callable[[int], Awaitable[str]]
) -> list[str]:
    """处理项目"""
    ...

async def stream_logs() -> AsyncIterator[str]:
    """流式日志"""
    yield "log line"

# ✗ 不好的类型注解
async def fetch_data(url):  # 缺少注解
    ...

def process(items: List[Optional[int]]) -> List[str]:  # 使用 List 而非 list
    ...
```

### 3.2 类型注解规范

| 规则 | 描述 |
|------|------|
| TYPE-001 | 公共接口必须有类型注解 |
| TYPE-002 | 使用 lowercase 类型（list, dict） |
| TYPE-003 | 复杂类型使用 TypeVar |
| TYPE-004 | 可选参数使用 `X | None` 而非 `Optional[X]` |
| TYPE-005 | 避免类型注解过于具体 |

---

## 4. 异步编程

### 4.1 Async/Await 规范

```python
import asyncio
from contextlib import asynccontextmanager

# ✓ 好的异步代码
async def fetch_all(urls: list[str]) -> list[CrawlResult]:
    """并发获取所有 URL"""
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(crawl_one(url)) for url in urls]
    return [task.result() for task in tasks]

@asynccontextmanager
async def managed_browser():
    """浏览器上下文管理器"""
    browser = await launch_browser()
    try:
        yield browser
    finally:
        await browser.close()

# ✗ 不好的异步代码
async def bad_fetch_all(urls):
    """串行获取（错误）"""
    results = []
    for url in urls:
        results.append(await crawl_one(url))  # 串行执行
    return results
```

### 4.2 异步规范

| 规则 | 描述 |
|------|------|
| ASYNC-001 | IO 操作使用 async/await |
| ASYNC-002 | 使用 asyncio.gather 或 TaskGroup 并发 |
| ASYNC-003 | 使用 contextmanager 管理资源 |
| ASYNC-004 | 避免在循环中 await（使用 gather） |
| ASYNC-005 | 设置合理的超时 |

---

## 5. 注释与文档

### 5.1 注释规范

```python
# ✓ 好的注释
# 限速器使用令牌桶算法
# 参考：https://example.com/rate-limiting
class TokenBucket:
    ...

# ✗ 不好的注释
# 这是个限速器
class TokenBucket:
    ...
```

### 5.2 Docstring 规范

```python
def crawl_url(url: str, options: CrawlOptions = None) -> CrawlResult:
    """爬取单个 URL

    自动选择最佳策略执行爬取，支持降级和重试。

    Args:
        url: 目标 URL
        options: 爬取选项，默认 None 使用全局配置

    Returns:
        爬取结果，success 指示是否成功

    Raises:
        ScraperError: 爬取失败时
        ValidationError: URL 格式无效

    Example:
        >>> result = await crawler.crawl_url("https://example.com")
        >>> print(f"Got {len(result.data)} items")
    """
    ...
```

### 5.3 文档规范

| 规则 | 描述 |
|------|------|
| DOC-001 | 公共 API 必须有 docstring |
| DOC-002 | docstring 包含 Args/Returns/Raises |
| DOC-003 | 复杂逻辑用注释解释 WHY，非 WHAT |
| DOC-004 | TODO 注释使用固定格式 |
| DOC-005 | 避免无意义的注释 |

---

## 6. 错误处理

### 6.1 错误处理规范

```python
# ✓ 好的错误处理
async def safe_crawl(url: str) -> CrawlResult:
    """安全爬取，捕获所有异常"""
    try:
        return await crawler.crawl(url)
    except ValidationError as e:
        logger.warning("invalid_url", url=url, error=str(e))
        return CrawlResult(success=False, message="Invalid URL")
    except NetworkError as e:
        logger.error("network_error", url=url, error=str(e))
        raise  # 需要上层处理
    except Exception as e:
        logger.exception("unexpected_error", url=url)
        raise ScrapingError(f"Unexpected: {e}") from e

# ✗ 不好的错误处理
async def bad_crawl(url):
    try:
        return await crawler.crawl(url)
    except:  # 捕获所有异常
        return None
```

### 6.2 错误处理规范

| 规则 | 描述 |
|------|------|
| ERR-001 | 不使用裸 except，指定异常类型 |
| ERR-002 | 记录日志包含上下文信息 |
| ERR-003 | 保留异常链（`raise ... from e`） |
| ERR-004 | 区分可恢复/不可恢复错误 |
| ERR-005 | 对外 API 返回标准错误格式 |

---

## 7. 代码组织

### 7.1 模块结构

```python
# ✓ 好的模块结构
backend/crawlers/
├── __init__.py           # 公开 API
├── config.py             # 配置
├── base.py               # 基类
├── exceptions.py         # 异常
├── models.py             # 数据模型
├── strategies/           # 策略子包
│   ├── __init__.py
│   ├── base.py
│   └── httpx.py
└── utils/               # 工具子包
    ├── __init__.py
    └── helpers.py
```

### 7.2 代码组织规范

| 规则 | 描述 |
|------|------|
| ORG-001 | 单一职责原则（一个模块做一件事） |
| ORG-002 | 相关功能放在一起 |
| ORG-003 | `__init__.py` 明确公开 API |
| ORG-004 | 避免循环导入 |
| ORG-005 | 相对导入用于包内导入 |

---

## 8. Git 协作

### 8.1 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

示例：
```
feat(crawler): add intelligent strategy selection

- Auto-detect URL type based on content-type header
- Support strategy fallback on failure
- Add Prometheus metrics for strategy switches

Closes #123
```

### 8.2 类型列表

| 类型 | 描述 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档更新 |
| style | 代码格式（不影响功能） |
| refactor | 重构（无功能变化） |
| perf | 性能优化 |
| test | 测试相关 |
| chore | 构建/工具变更 |

### 8.3 Git 规范

| 规则 | 描述 |
|------|------|
| GIT-001 | 提交信息使用上述格式 |
| GIT-002 | 保持提交粒度适中 |
| GIT-003 | 提交信息描述 WHY |
| GIT-004 | 关联 Issue（Closes #xxx） |
| GIT-005 | 使用分支开发，主分支保护 |

---

*Spec | 2026-05-09 | v1.0.0*
