# -*- coding: utf-8 -*-
"""
策略基类 - 智能爬虫系统 v2.0

定义所有爬取策略的抽象接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models import (
    CrawlIntent,
    ProbeResult,
    StrategyResult,
)


class BaseStrategy(ABC):
    """爬取策略基类

    所有爬取策略必须继承此类并实现核心方法。
    """

    name: str = "base"
    priority: int = 0

    @abstractmethod
    async def can_handle(self, probe: ProbeResult) -> bool:
        """判断是否可处理该 URL

        Args:
            probe: URL 探测结果

        Returns:
            True 如果策略可以处理此 URL
        """
        pass

    @abstractmethod
    async def execute(
        self,
        url: str,
        intent: Optional[CrawlIntent] = None,
        **kwargs: Any,
    ) -> StrategyResult:
        """执行爬取

        Args:
            url: 目标 URL
            intent: 爬取意图
            **kwargs: 其他参数

        Returns:
            策略执行结果
        """
        pass

    async def validate(self, result: StrategyResult) -> bool:
        """验证结果

        Args:
            result: 策略执行结果

        Returns:
            True 如果结果有效
        """
        return result.success and result.data is not None

    def get_priority(self) -> int:
        """获取策略优先级"""
        return self.priority

    def get_name(self) -> str:
        """获取策略名称"""
        return self.name

    def supports_intent(self, intent: CrawlIntent) -> bool:
        """检查是否支持指定意图

        Args:
            intent: 爬取意图

        Returns:
            True 如果支持
        """
        return True

    def get_capabilities(self) -> List[str]:
        """获取策略能力列表

        Returns:
            能力描述列表
        """
        return []

    def get_timeout(self) -> int:
        """获取超时时间

        Returns:
            超时秒数
        """
        return 30
