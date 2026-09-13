"""
站点判别层
==========

输入一个 URL，输出该站点的可采性画像（SiteProfile）与合规判定结果。

探测顺序固定（低成本高确定性优先，避免不必要的渲染开销）：

    robots.txt  →  Sitemap / RSS 发现  →  主文档获取
    →  结构化数据提取（JSON-LD / microdata / OG / meta）
    →  API 线索探测  →  列表 / 详情结构识别
    →  分页模式识别  →  保护状态判定  →  四维合规判定

模块划分：

- ``fetcher``    获取层：robots / sitemap / feeds / 主文档
- ``structure``  结构识别：列表页、详情页、分页、保护状态
- ``fields``     字段发现：结构化数据提取与字段推断
- ``profile``    编排与持久化：SiteProfile 构建
"""

from discover.fetcher import (
    DEFAULT_USER_AGENT,
    FetchResult,
    RobotsInfo,
    SiteFetcher,
    parse_robots,
)

__all__ = [
    "DEFAULT_USER_AGENT",
    "FetchResult",
    "RobotsInfo",
    "SiteFetcher",
    "parse_robots",
]
