# Phase 4.5 — 用户体验优化方案

**日期**: 2026-05-09
**状态**: 规划完成，待实施
**目标**: 面向大众，降低门槛，实用至上

---

## 🎯 核心原则

> **让不懂 JSON 的人也能用！**

- 能填表单就不写代码
- 能点按钮就不输参数
- 能看说明就不猜含义
- 能预览就不盲采

---

## 📦 模块 1: URL 自由爬取

### 用户故事
> "我有一个网址，帮我爬数据回来"

### 技术方案

| 场景 | 检测方式 | 技术选择 | 说明 |
|------|----------|----------|------|
| REST API (返回 JSON) | 先 HEAD 请求，检查 Content-Type | `requests` 直接调用 | 最快，零渲染 |
| 普通网页 (静态 HTML) | 检查是否有 JS 渲染需求 | `Scrapling Fetcher` | 自动解析 HTML |
| 反爬网页 (Cloudflare 等) | 检测 403/Challenge 页面 | `Scrapling StealthyFetcher` | 浏览器模拟 |
| SPA/动态网页 | 检测是否需要 JS 执行 | `crawl4ai` | 智能提取正文 |
| 登录态网页 | 用户标记"需要登录" | `CDP Bridge MCP` (未来) | 操作已登录浏览器 |

### 自动判断流程

```
用户输入 URL
    ↓
[1] HEAD 请求探测
    ├─ Content-Type: application/json → API 模式
    ├─ 返回 403/Challenge → StealthyFetcher
    └─ 正常 HTML ↓
[2] 分析 HTML 复杂度
    ├─ 简单静态页面 → Fetcher
    ├─ SPA/大量 JS → crawl4ai
    └─ 用户指定"需登录" → CDP Bridge (提示安装)
[3] 执行爬取
    ↓
[4] 智能解析结果
    ├─ 尝试识别结构化数据 (表格/列表/卡片)
    ├─ 自动提取为 DataFrame
    └─ 返回预览 + 存入数据集
```

### crawl4ai 集成方案

```python
# crawl4ai — 专为 LLM 设计的网页爬取
# 特点: 自动提取正文、去除噪音、输出 Markdown/结构化数据
# GitHub: https://github.com/unclecode/crawl4ai

from crawl4ai import AsyncWebCrawler

async def crawl_with_crawl4ai(url: str):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return {
            "markdown": result.markdown,      # Markdown 正文
            "html": result.cleaned_html,        # 清理后 HTML
            "links": result.links,             # 页面链接
            "media": result.media,             # 图片/视频
            "metadata": result.metadata,       # 页面元数据
        }
```

### 需要安装

```bash
pip install crawl4ai    # 自动提取网页正文
pip install lxml        # HTML 解析加速
```

---

## 📦 模块 2: 分页爬取 & 大规模爬取

### 技术矩阵

| 能力 | 技术 | 说明 |
|------|------|------|
| **分页爬取** | URL 模板 + 自动翻页 | 用户给第1页URL，自动识别分页规律 |
| **深度爬取** | BFS/DFS 链接跟踪 | 从起始URL开始，跟踪内链 |
| **大规模爬取** | Celery 分布式 + 限速 | 多 Worker 并发，受控节奏 |
| **断点续爬** | Checkpoint 机制 | 已爬URL记录，中断后可恢复 |
| **增量爬取** | 内容指纹 (hash) | 只爬新增/变更内容 |
| **定时爬取** | Cron 调度 | 每小时/每天自动执行 |

### 分页模式识别

```python
# 常见分页模式 (自动识别)
PAGINATION_PATTERNS = [
    # ?page=1, ?page=2
    {"type": "query_param", "param": "page", "regex": r"page=(\d+)"},
    # /p/1, /p/2
    {"type": "path_segment", "regex": r"/p/(\d+)"},
    # ?offset=0, ?offset=20
    {"type": "query_param", "param": "offset", "regex": r"offset=(\d+)"},
    # ?pn=1, ?pn=2 (百度)
    {"type": "query_param", "param": "pn", "regex": r"pn=(\d+)"},
]
```

### 大规模爬取架构

```
用户配置 (URL列表/范围/深度)
    ↓
[任务拆分] 每页/每URL → 一个 Celery Task
    ↓
[Celery Worker Pool] 
    ├─ Worker 1: 爬取 + 限速
    ├─ Worker 2: 爬取 + 限速
    └─ Worker 3: 爬取 + 限速
    ↓
[结果收集] Redis → 去重 → 存储
    ↓
[进度展示] 前端实时刷新
```

### Celery 配置增强

```python
# 大规模爬取专用队列
CELERY_ROUTES = {
    "crawl_single": {"queue": "crawl-high"},     # 单页 → 高优先级
    "crawl_batch": {"queue": "crawl-normal"},     # 批量 → 普通
    "crawl_massive": {"queue": "crawl-low"},      # 大规模 → 低优先级
}
# 限速: 每个域名最多 2 req/s
# 去重: URL hash set in Redis
# 断点: 已完成 URL 持久化到 SQLite
```

---

## 📦 模块 3: 适配器参数表单化

### 设计原则

```
用户选择适配器/平台/API
    ↓
后端返回参数 Schema (JSON Schema)
    ↓
前端根据 Schema 动态渲染表单
    ↓
用户填表 → 自动生成请求参数
```

### 参数 Schema 示例

```json
{
  "adapter": "justoneapi",
  "platform": "xiaohongshu",
  "api": "search_note_v3",
  "params": {
    "keyword": {
      "type": "string",
      "label": "搜索关键词",
      "placeholder": "例如: 数据分析",
      "required": true,
      "description": "搜索的关键词，支持中文"
    },
    "page": {
      "type": "integer",
      "label": "页码",
      "default": 1,
      "min": 1,
      "max": 50,
      "description": "从第几页开始"
    },
    "sort": {
      "type": "enum",
      "label": "排序方式",
      "options": [
        {"value": "general", "label": "综合排序"},
        {"value": "time", "label": "最新发布"},
        {"value": "hot", "label": "热门优先"}
      ],
      "default": "general"
    }
  }
}
```

### 前端渲染逻辑

```tsx
// 根据 schema 渲染表单
function renderField(param: ParamSchema) {
  switch (param.type) {
    case 'string':  return <Input placeholder={param.placeholder} />
    case 'integer': return <Input type="number" min={param.min} max={param.max} />
    case 'enum':    return <Select options={param.options} />
    case 'boolean': return <Switch />
    case 'array':   return <TagInput />  // 标签输入
  }
  // 每个字段都显示: label + 输入框 + 描述说明
}
```

---

## 📦 模块 4: JustOneAPI 可视化选择

### 三级选择器

```
第1级: 选平台
┌──────────────────────────────────┐
│ 🔴 小红书  🎵 抖音  📱 微博      │
│ 🛒 淘宝    📺 B站   🛍️ 京东      │
│ 💡 知乎    📸 快手  🎯 拼多多     │
│ ...27个平台                      │
└──────────────────────────────────┘
          ↓
第2级: 选 API
┌──────────────────────────────────┐
│ 🔍 搜索笔记 (search_note_v3)    │
│ 📄 获取笔记详情 (get_note_v1)    │
│ 👤 搜索用户 (search_user_v1)    │
│ 💬 获取评论 (get_note_comments) │
└──────────────────────────────────┘
          ↓
第3级: 填参数 (动态表单)
┌──────────────────────────────────┐
│ 搜索关键词: [数据分析        ]   │
│ 排序方式:   [综合排序     ▼ ]   │
│ 页码:       [1              ]   │
│                                  │
│ 💡 搜索小红书笔记，返回笔记列表  │
│    关键词必填，支持中文搜索       │
└──────────────────────────────────┘
```

---

## 📦 模块 5: 数据展示页 (新页面)

### 功能设计

```
┌─────────────────────────────────────────┐
│ 📊 数据浏览                              │
│                                          │
│ 🔍 [搜索关键词...] [筛选列▼] [导出▼]    │
│                                          │
│ ┌──────┬────────┬────────┬───────┐      │
│ │ ID   │ 标题    │ 价格    │ 来源  │      │
│ ├──────┼────────┼────────┼───────┤      │
│ │ 1    │ 数据... │ ¥299   │ 小红书│      │
│ │ 2    │ AI学... │ ¥0     │ 知乎  │      │
│ │ 3    │ 深度... │ ¥199   │ 京东  │      │
│ └──────┴────────┴────────┴───────┘      │
│                                          │
│ ◀ 1 2 3 ... 10 ▶  每页 [20▼] 共 200 条  │
│                                          │
│ [导出 CSV] [导出 Excel] [导出 JSON]      │
└─────────────────────────────────────────┘
```

### 后端 API

```python
# 数据查询 API
GET /api/v1/data/tables          # 列出所有数据表
GET /api/v1/data/{table}/rows   # 查询数据 (分页+搜索+筛选)
  ?page=1&size=20&search=关键词&sort=price&order=desc
GET /api/v1/data/{table}/schema  # 获取表结构 (列名+类型)
GET /api/v1/data/{table}/export  # 导出数据
  ?format=csv|excel|json
DELETE /api/v1/data/{table}/rows/{id}  # 删除行
```

---

## 📦 模块 6: 采集历史 & 任务管理增强

### 功能

| 功能 | 说明 |
|------|------|
| 采集历史 | 展示所有已采集数据 (时间/来源/数量) |
| 任务进度条 | 实时显示爬取进度 (已爬/总数) |
| 结果预览 | 任务完成后直接预览数据 |
| 一键重跑 | 失败任务一键重新执行 |
| 定时任务 | 配置周期性采集 (每天/每小时) |

---

## 🏗️ 后端需要新增/修改的文件

| 文件 | 说明 |
|------|------|
| `crawlers/url_crawler.py` | URL 自由爬取 (crawl4ai + 自动判断) |
| `crawlers/pagination.py` | 分页模式识别 + 自动翻页 |
| `crawlers/massive_crawler.py` | 大规模爬取 (Celery + 去重 + 断点) |
| `api/routers/data.py` (增强) | 数据查询 + 搜索 + 导出 |
| `api/routers/crawl.py` (增强) | 参数 Schema 接口 + URL 爬取接口 |
| `crawlers/adapters/param_schemas/` | 各适配器参数 Schema 定义 |
| `crawlers/adapters/param_schemas/justoneapi.py` | JustOneAPI 27 平台参数 |
| `crawlers/adapters/param_schemas/eastmoney.py` | 东方财富参数 |
| ... 其他适配器 | ...

## 🎨 前端需要新增/修改的页面

| 页面 | 说明 |
|------|------|
| `Crawl.tsx` (重构) | URL 输入 + 适配器选择 + 动态表单 |
| `DataBrowser.tsx` (新增) | 数据表格展示 + 搜索 + 导出 |
| `CrawlHistory.tsx` (新增) | 采集历史 + 任务管理 |
| JustOneAPI 组件 | 平台选择 → API 选择 → 参数表单 |

---

## 📅 实施计划

### Day 1 (明天)

| 顺序 | Task | 预计 |
|------|------|------|
| 1 | 安装 crawl4ai，创建 URL 自由爬取后端 | 30min |
| 2 | 创建参数 Schema 系统 (后端) | 30min |
| 3 | JustOneAPI 27 平台参数文档 | 45min |
| 4 | 数据查询/导出后端 API | 30min |
| 5 | 前端: URL 自由爬取页 + 动态表单 | 45min |
| 6 | 前端: 数据展示页 | 30min |
| 7 | 前端: JustOneAPI 可视化选择 | 30min |

### Day 2 (后天)

| 顺序 | Task | 预计 |
|------|------|------|
| 1 | 分页爬取 (后端 + 前端) | 45min |
| 2 | 大规模爬取 (Celery 增强) | 45min |
| 3 | 采集历史 + 任务管理增强 | 30min |
| 4 | 全面测试 + 验证 | 30min |

---

## 🔑 关键技术选型

| 需求 | 技术选择 | 理由 |
|------|----------|------|
| URL 自由爬取 | crawl4ai + Scrapling | crawl4ai 智能提取正文，Scrapling 应对反爬 |
| 分页识别 | 正则 + DOM 分析 | 自动识别常见分页模式 |
| 大规模爬取 | Celery + Redis | 已有基础设施，扩展即可 |
| 参数表单化 | JSON Schema → 动态渲染 | 一套 Schema 驱动所有适配器 |
| 数据展示 | 服务端分页 + 搜索 | 大数据量不在前端加载 |
| 导出 | Pandas → CSV/Excel/JSON | 已有依赖 |

---

*方案设计: 小彩 | 2026-05-09 00:19*
