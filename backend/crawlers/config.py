# -*- coding: utf-8 -*-
"""
爬虫配置
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CrawlerConfig:
    """爬虫配置"""

    # 请求设置
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 2.0

    # 反爬设置
    request_delay: float = 1.0
    user_agent_rotation: bool = True

    # 代理设置
    use_proxy: bool = False
    proxy_list: List[str] = field(default_factory=list)

    # 数据存储
    data_dir: str = "data/raw"
    save_json: bool = True
    save_db: bool = True

    # 日志
    log_level: str = "INFO"


# 默认配置
DEFAULT_CONFIG = CrawlerConfig()


# 各平台特定配置
FINANCE_CONFIG = CrawlerConfig(
    request_delay=1.0,
    request_timeout=30,
)

NEWS_CONFIG = CrawlerConfig(
    request_delay=2.0,
    request_timeout=60,
)
