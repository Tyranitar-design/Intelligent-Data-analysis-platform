# -*- coding: utf-8 -*-
"""
反爬策略模块

功能：
- 指纹伪装
- 行为模拟
- 验证码处理
- 代理轮换
"""
from .anticrawl_engine import AntiCrawlEngine
from .fingerprint import FingerprintMasker

__all__ = ['AntiCrawlEngine', 'FingerprintMasker']
