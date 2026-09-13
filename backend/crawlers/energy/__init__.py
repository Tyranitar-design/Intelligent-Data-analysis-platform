# -*- coding: utf-8 -*-
"""
电网数据爬虫模块

支持的数据源:
- 国家电网 (www.sgcc.com.cn)
- 南方电网 (www.csg.cn)
- 各省电网公司
"""
from .sgcc import SGCCPowerCrawler
from .csg import CSGPowerCrawler

__all__ = ["SGCCPowerCrawler", "CSGPowerCrawler"]
