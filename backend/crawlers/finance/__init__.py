# -*- coding: utf-8 -*-
"""
金融爬虫模块
"""
from .eastmoney import EastMoneyCrawler
from .sina import SinaCrawler

__all__ = ["EastMoneyCrawler", "SinaCrawler"]
