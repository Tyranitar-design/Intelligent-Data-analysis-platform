# -*- coding: utf-8 -*-
"""
API 适配器框架
=============

功能:
- 适配器基类 BaseAdapter
- 配置化管理
- 自动发现与注册
- 统一接口
"""
import asyncio
import importlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from crawlers.base import CrawlResult

logger = logging.getLogger(__name__)


# ==================== 适配器注册表 ====================

class AdapterRegistry:
    """适配器注册表 — 自动发现与管理"""
    
    _adapters: Dict[str, Type["BaseAdapter"]] = {}
    
    @classmethod
    def register(cls, name: str, adapter_class: Type["BaseAdapter"]):
        """注册适配器"""
        cls._adapters[name] = adapter_class
        logger.info(f"✅ 注册适配器: {name}")
    
    @classmethod
    def get(cls, name: str) -> Optional[Type["BaseAdapter"]]:
        """获取适配器类"""
        return cls._adapters.get(name)
    
    @classmethod
    def create(cls, name: str, **kwargs) -> Optional["BaseAdapter"]:
        """创建适配器实例"""
        adapter_class = cls.get(name)
        if adapter_class:
            return adapter_class(**kwargs)
        return None
    
    @classmethod
    def list_adapters(cls) -> List[Dict[str, str]]:
        """列出所有已注册的适配器"""
        result = []
        for name, adapter_class in cls._adapters.items():
            result.append({
                "name": name,
                "class": adapter_class.__name__,
                "description": adapter_class.DESCRIPTION if hasattr(adapter_class, 'DESCRIPTION') else "",
                "category": adapter_class.CATEGORY if hasattr(adapter_class, 'CATEGORY') else "general",
            })
        return result
    
    @classmethod
    def auto_discover(cls):
        """自动发现并注册适配器"""
        try:
            from crawlers import adapters as adapters_pkg
            import pkgutil
            
            for _, modname, _ in pkgutil.iter_modules(adapters_pkg.__path__):
                try:
                    importlib.import_module(f"{adapters_pkg.__name__}.{modname}")
                    # 模块中的适配器会通过装饰器自动注册
                    logger.debug(f"发现适配器模块: {modname}")
                except Exception as e:
                    logger.warning(f"加载适配器模块失败 {modname}: {e}")
        except ImportError:
            logger.warning("adapters 包未找到")


# ==================== 适配器基类 ====================

@dataclass
class AdapterConfig:
    """适配器配置基类"""
    name: str = ""
    base_url: str = ""
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseAdapter(ABC):
    """
    适配器基类
    
    所有数据源适配器必须继承此类并实现:
    - fetch(): 获取数据
    - validate_config(): 验证配置（可选）
    
    类属性:
    - NAME: 适配器名称（用于注册）
    - DESCRIPTION: 适配器描述
    - CATEGORY: 适配器分类 (finance/ecommerce/news/social/energy/general)
    - CONFIG_CLASS: 配置类
    """
    
    NAME: str = ""
    DESCRIPTION: str = ""
    CATEGORY: str = "general"
    CONFIG_CLASS: Type[AdapterConfig] = AdapterConfig
    
    def __init__(self, config: AdapterConfig = None, **kwargs):
        self.config = config or self.CONFIG_CLASS(**kwargs)
        self.logger = logging.getLogger(f"adapter.{self.NAME or self.__class__.__name__}")
        self._request_count = 0
    
    @abstractmethod
    async def fetch(self, **kwargs) -> CrawlResult:
        """
        获取数据（子类必须实现）
        
        Args:
            **kwargs: 各适配器特定的参数
            
        Returns:
            CrawlResult 爬取结果
        """
        pass
    
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        return bool(self.config.base_url)
    
    async def fetch_with_retry(self, **kwargs) -> CrawlResult:
        """带重试的获取"""
        last_error = None
        
        for attempt in range(self.config.retry_count):
            try:
                self._request_count += 1
                result = await self.fetch(**kwargs)
                return result
            except Exception as e:
                last_error = e
                self.logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt < self.config.retry_count - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
        
        return CrawlResult(
            success=False,
            data=[],
            message=f"重试 {self.config.retry_count} 次后仍失败: {last_error}",
            source=self.NAME,
            error=str(last_error),
        )
    
    def get_info(self) -> Dict[str, Any]:
        """获取适配器信息"""
        return {
            "name": self.NAME,
            "description": self.DESCRIPTION,
            "category": self.CATEGORY,
            "config": {
                "base_url": self.config.base_url,
                "timeout": self.config.timeout,
            },
            "request_count": self._request_count,
        }


# ==================== 注册装饰器 ====================

def register_adapter(name: str = None, category: str = "general"):
    """
    适配器注册装饰器
    
    用法:
        @register_adapter("eastmoney", category="finance")
        class EastMoneyAdapter(BaseAdapter):
            ...
    """
    def decorator(cls):
        adapter_name = name or cls.__name__.replace("Adapter", "").lower()
        cls.NAME = adapter_name
        cls.CATEGORY = category
        AdapterRegistry.register(adapter_name, cls)
        return cls
    return decorator
