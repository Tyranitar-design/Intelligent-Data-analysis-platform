# Phase 2: 采集系统增强 - 实施规划

> 日期: 2026-05-07
> 目标: 构建企业级分布式爬虫系统

---

## 2.1 Scrapling 集成

### 目标
集成 Scrapling 框架，实现反爬绕过、动态渲染、自适应解析

### 核心组件
```
crawlers/
├── scrapling_adapter.py      # Scrapling 适配器封装
├── fetcher.py                # 统一获取器（HTTP/Browser）
├── parser.py                 # 自适应解析器
└── anti_detect.py            # 反检测模块
```

### 功能点
- [ ] Scrapling Fetcher 封装（支持 stealthy/dynamic）
- [ ] Cloudflare / Turnstile 绕过
- [ ] JavaScript 动态渲染
- [ ] 自适应元素定位（页面变化自动恢复）

---

## 2.2 分布式爬虫引擎

### 目标
基于 Celery 构建分布式、可扩展的爬虫引擎

### 核心组件
```
crawlers/
├── engine/
│   ├── scheduler.py          # 任务调度器
│   ├── worker.py             # 工作节点
│   ├── queue.py              # 优先级队列
│   └── monitor.py            # 监控统计
```

### 功能点
- [ ] 任务优先级队列（高/中/低）
- [ ] 并发控制（Semaphore）
- [ ] 自动重试 + 指数退避
- [ ] 断点续传
- [ ] 实时进度追踪
- [ ] 分布式 Worker 扩展

---

## 2.3 API 适配器框架

### 目标
统一接口，支持多种数据源

### 核心组件
```
crawlers/
├── adapters/
│   ├── base.py               # 适配器基类
│   ├── api_adapter.py        # API 适配器
│   ├── web_adapter.py        # 网页适配器
│   └── local_adapter.py      # 本地文件适配器
├── sources/
│   ├── finance/              # 金融数据源
│   ├── ecommerce/            # 电商数据源
│   ├── social/               # 社交数据源
│   └── news/                 # 新闻数据源
```

### 预置数据源
| 类别 | 数据源 | 类型 |
|------|--------|------|
| 金融 | 东方财富、新浪财经、Alpha Vantage | API |
| 电商 | 淘宝、京东 | 爬虫 |
| 社交 | 微博、B站、知乎 | API |
| 新闻 | 36氪、财联社 | RSS/API |
| 能源 | 国家电网 | 公开数据 |

---

## 2.4 用户自定义采集

### 目标
用户可配置采集规则，无需写代码

### 功能点
- [ ] 可视化配置界面
- [ ] CSS/XPath 选择器配置
- [ ] API 参数配置
- [ ] 分页规则配置
- [ ] 数据字段映射
- [ ] 测试运行

### 配置示例
```yaml
crawl_config:
  name: "自定义采集"
  source_type: "web"
  web:
    url: "https://example.com"
    selectors:
      title: "h1::text"
      content: "div.content::text"
    pagination:
      enabled: true
      next_button: "a.next::attr(href)"
```

---

## 2.5 robots.txt 合规

### 目标
自动遵守网站爬虫协议

### 功能点
- [ ] robots.txt 自动解析
- [ ] 爬取前合规检查
- [ ] Crawl-delay 遵守
- [ ] 用户提示与确认
- [ ] 合规报告生成

---

## 实施顺序

```
Day 1 (今晚): 框架搭建
├── 2.1 Scrapling 适配器（基础封装）
├── 2.2 分布式引擎（核心框架）
└── 2.5 robots.txt 合规

Day 2: 适配器开发
├── 2.3 API 适配器框架
├── 预置 5 个金融数据源
└── 2.4 用户自定义采集（基础）

Day 3: 完善与测试
├── 适配器扩展（电商/社交/新闻）
├── 前端采集界面
├── 测试与优化
└── 文档完善
```

---

## 技术要点

### Scrapling 使用
```python
from scrapling.fetchers import Fetcher, StealthyFetcher

# 普通请求
fetcher = Fetcher()
page = fetcher.get('https://example.com')

# 反爬绕过
stealth = StealthyFetcher()
page = stealth.get('https://protected-site.com')

# 自适应解析
title = page.adaptive_selector('h1.title')
```

### Celery 分布式
```python
# 任务定义
@app.task(bind=True)
def crawl_task(self, config):
    # 并发控制
    with semaphore:
        result = crawler.crawl(config)
    return result

# 优先级队列
app.conf.task_routes = {
    'crawl.high': {'queue': 'crawl_high'},
    'crawl.normal': {'queue': 'crawl_normal'},
}
```

### robots.txt 检查
```python
from urllib.robotparser import RobotFileParser

rp = RobotFileParser()
rp.set_url('https://example.com/robots.txt')
rp.read()

can_fetch = rp.can_fetch('*', 'https://example.com/page')
```

---

## 验收标准

- [ ] 支持 10,000+ 并发请求
- [ ] 支持 20+ 预置数据源
- [ ] 支持用户自定义采集规则
- [ ] 自动遵守 robots.txt
- [ ] 分布式可扩展
- [ ] 实时进度追踪

---

*规划: 小彩 | 2026-05-07*
