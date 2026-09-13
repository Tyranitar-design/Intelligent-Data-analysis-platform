# -*- coding: utf-8 -*-
"""
JustOneAPI 统一适配器
====================

数据源: JustOneAPI (https://justoneapi.com)
覆盖平台: 小红书/抖音/微博/淘宝/天猫/B站/京东/知乎/快手/微信 等

使用方式:
1. 在 .env 中配置 JUSTONE_API_TOKEN
2. 通过 AdapterRegistry.create("justoneapi") 创建实例
3. 调用 fetch(type="xiaohongshu_search", keyword="xxx")
"""
import logging
import os
from typing import Any, Dict, Optional

from crawlers.adapter_framework import BaseAdapter, AdapterConfig, register_adapter
from crawlers.base import CrawlResult

logger = logging.getLogger(__name__)


class JustOneAPIConfig(AdapterConfig):
    """JustOneAPI 配置"""
    name: str = "justoneapi"
    base_url: str = "https://api.justoneapi.com"
    timeout: int = 30
    extra: Dict[str, Any] = {}  # 存储 token 等额外配置


@register_adapter("justoneapi", category="social")
class JustOneAPIAdapter(BaseAdapter):
    """
    JustOneAPI 统一适配器
    
    支持平台:
    - 小红书 (xiaohongshu): 笔记搜索/详情/评论/用户搜索
    - 抖音 (douyin): 视频搜索/用户资料
    - 微博 (weibo): 热搜/用户/博文
    - 淘宝/天猫 (taobao): 商品搜索/详情/评价
    - 哔哩哔哩 (bilibili): 视频搜索/UP主
    - 京东 (jd): 商品搜索/详情
    - 知乎 (zhihu): 问答搜索/用户
    - 快手 (kuaishou): 视频搜索
    """
    
    NAME = "justoneapi"
    DESCRIPTION = "JustOneAPI - 小红书/抖音/微博/淘宝/B站/京东/知乎等统一数据接口"
    CATEGORY = "social"
    CONFIG_CLASS = JustOneAPIConfig
    
    def __init__(self, config: JustOneAPIConfig = None, **kwargs):
        super().__init__(config)
        self._client = None
        self._token = kwargs.get("token") or os.environ.get("JUSTONE_API_TOKEN", "")
    
    def _get_client(self):
        """获取 JustOneAPI 客户端（懒加载）"""
        if self._client is None:
            if not self._token:
                logger.warning("JustOneAPI Token 未配置，请在 .env 中设置 JUSTONE_API_TOKEN")
                return None
            try:
                from justoneapi import JustOneAPIClient
                self._client = JustOneAPIClient(token=self._token)
            except ImportError:
                logger.error("justoneapi 包未安装")
                return None
        return self._client
    
    def validate_config(self) -> bool:
        """验证配置"""
        return bool(self._token)
    
    async def fetch(self, **kwargs) -> CrawlResult:
        """
        通用获取方法
        
        Args:
            type: 平台+操作类型 (如 "xiaohongshu_search", "douyin_video")
            keyword: 搜索关键词
            **kwargs: 各平台特定参数
        
        可用 type:
            小红书:
            - xiaohongshu_search: 笔记搜索
            - xiaohongshu_note: 笔记详情 (需要 note_id)
            - xiaohongshu_comments: 笔记评论 (需要 note_id)
            - xiaohongshu_user: 用户资料 (需要 user_id)
            - xiaohongshu_user_search: 用户搜索
            
            抖音:
            - douyin_search: 视频搜索
            - douyin_user: 用户资料 (需要 user_id)
            
            微博:
            - weibo_hot: 热搜
            - weibo_user: 用户资料
            
            淘宝:
            - taobao_search: 商品搜索
            - taobao_detail: 商品详情 (需要 item_id)
            
            B站:
            - bilibili_search: 视频搜索
            
            京东:
            - jd_search: 商品搜索
            
            知乎:
            - zhihu_search: 问答搜索
        """
        fetch_type = kwargs.get("type", "")
        
        # 路由到具体方法
        handler_map = {
            # 小红书
            "xiaohongshu_search": self._xiaohongshu_search,
            "xiaohongshu_note": self._xiaohongshu_note,
            "xiaohongshu_comments": self._xiaohongshu_comments,
            "xiaohongshu_user_search": self._xiaohongshu_user_search,
            # 抖音
            "douyin_search": self._douyin_search,
            # 微博
            "weibo_hot": self._weibo_hot,
            # 淘宝
            "taobao_search": self._taobao_search,
            # B站
            "bilibili_search": self._bilibili_search,
            # 京东
            "jd_search": self._jd_search,
            # 知乎
            "zhihu_search": self._zhihu_search,
        }
        
        handler = handler_map.get(fetch_type)
        if handler:
            return await handler(**kwargs)
        
        return CrawlResult(
            success=False, data=[],
            message=f"未知类型: {fetch_type}，支持: {list(handler_map.keys())}",
            source=self.NAME,
        )
    
    # ==================== 小红书 ====================
    
    async def _xiaohongshu_search(self, **kwargs) -> CrawlResult:
        """小红书笔记搜索"""
        client = self._get_client()
        if not client:
            return CrawlResult(success=False, data=[], message="JustOneAPI Token 未配置", source=self.NAME)
        
        keyword = kwargs.get("keyword", "")
        try:
            response = client.xiaohongshu.search_note_v3(keyword=keyword)
            if response.success:
                return CrawlResult(
                    success=True,
                    data=response.data if isinstance(response.data, list) else [response.data],
                    message=f"小红书搜索 '{keyword}' 成功",
                    source=self.NAME,
                )
            return CrawlResult(
                success=False, data=[],
                message=f"小红书搜索失败: {response.message}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"小红书搜索异常: {e}",
                source=self.NAME, error=str(e),
            )
    
    async def _xiaohongshu_note(self, **kwargs) -> CrawlResult:
        """小红书笔记详情"""
        client = self._get_client()
        if not client:
            return CrawlResult(success=False, data=[], message="JustOneAPI Token 未配置", source=self.NAME)
        
        note_id = kwargs.get("note_id", "")
        try:
            response = client.xiaohongshu.get_note_detail_v7(note_id=note_id)
            if response.success:
                return CrawlResult(
                    success=True,
                    data=[response.data] if not isinstance(response.data, list) else response.data,
                    message=f"小红书笔记详情获取成功",
                    source=self.NAME,
                )
            return CrawlResult(
                success=False, data=[],
                message=f"笔记详情失败: {response.message}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"笔记详情异常: {e}",
                source=self.NAME, error=str(e),
            )
    
    async def _xiaohongshu_comments(self, **kwargs) -> CrawlResult:
        """小红书笔记评论"""
        client = self._get_client()
        if not client:
            return CrawlResult(success=False, data=[], message="JustOneAPI Token 未配置", source=self.NAME)
        
        note_id = kwargs.get("note_id", "")
        try:
            response = client.xiaohongshu.get_note_comment_v4(note_id=note_id)
            if response.success:
                return CrawlResult(
                    success=True,
                    data=response.data if isinstance(response.data, list) else [response.data],
                    message=f"小红书评论获取成功",
                    source=self.NAME,
                )
            return CrawlResult(
                success=False, data=[],
                message=f"评论获取失败: {response.message}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"评论获取异常: {e}",
                source=self.NAME, error=str(e),
            )
    
    async def _xiaohongshu_user_search(self, **kwargs) -> CrawlResult:
        """小红书用户搜索"""
        client = self._get_client()
        if not client:
            return CrawlResult(success=False, data=[], message="JustOneAPI Token 未配置", source=self.NAME)
        
        keyword = kwargs.get("keyword", "")
        try:
            response = client.xiaohongshu.user_search_v2(keyword=keyword)
            if response.success:
                return CrawlResult(
                    success=True,
                    data=response.data if isinstance(response.data, list) else [response.data],
                    message=f"小红书用户搜索成功",
                    source=self.NAME,
                )
            return CrawlResult(
                success=False, data=[],
                message=f"用户搜索失败: {response.message}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"用户搜索异常: {e}",
                source=self.NAME, error=str(e),
            )
    
    # ==================== 抖音 ====================
    
    async def _douyin_search(self, **kwargs) -> CrawlResult:
        """抖音视频搜索"""
        client = self._get_client()
        if not client:
            return CrawlResult(success=False, data=[], message="JustOneAPI Token 未配置", source=self.NAME)
        
        keyword = kwargs.get("keyword", "")
        try:
            response = client.douyin.search_video_v4(keyword=keyword)
            if response.success:
                return CrawlResult(
                    success=True,
                    data=response.data if isinstance(response.data, list) else [response.data],
                    message=f"抖音搜索 '{keyword}' 成功",
                    source=self.NAME,
                )
            return CrawlResult(
                success=False, data=[],
                message=f"抖音搜索失败: {response.message}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"抖音搜索异常: {e}",
                source=self.NAME, error=str(e),
            )
    
    # ==================== 微博 ====================
    
    async def _weibo_hot(self, **kwargs) -> CrawlResult:
        """微博热搜"""
        client = self._get_client()
        if not client:
            return CrawlResult(success=False, data=[], message="JustOneAPI Token 未配置", source=self.NAME)
        
        try:
            response = client.weibo.hot_search_v1()
            if response.success:
                return CrawlResult(
                    success=True,
                    data=response.data if isinstance(response.data, list) else [response.data],
                    message="微博热搜获取成功",
                    source=self.NAME,
                )
            return CrawlResult(
                success=False, data=[],
                message=f"微博热搜失败: {response.message}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"微博热搜异常: {e}",
                source=self.NAME, error=str(e),
            )
    
    # ==================== 淘宝 ====================
    
    async def _taobao_search(self, **kwargs) -> CrawlResult:
        """淘宝商品搜索"""
        client = self._get_client()
        if not client:
            return CrawlResult(success=False, data=[], message="JustOneAPI Token 未配置", source=self.NAME)
        
        keyword = kwargs.get("keyword", "")
        try:
            response = client.taobao.search_item_list_v1(keyword=keyword)
            if response.success:
                return CrawlResult(
                    success=True,
                    data=response.data if isinstance(response.data, list) else [response.data],
                    message=f"淘宝搜索 '{keyword}' 成功",
                    source=self.NAME,
                )
            return CrawlResult(
                success=False, data=[],
                message=f"淘宝搜索失败: {response.message}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"淘宝搜索异常: {e}",
                source=self.NAME, error=str(e),
            )
    
    # ==================== B站 ====================
    
    async def _bilibili_search(self, **kwargs) -> CrawlResult:
        """B站视频搜索"""
        client = self._get_client()
        if not client:
            return CrawlResult(success=False, data=[], message="JustOneAPI Token 未配置", source=self.NAME)
        
        keyword = kwargs.get("keyword", "")
        try:
            # B站暂无搜索API，用用户视频列表替代
            response = client.bilibili.get_user_video_list_v2()
            if response.success:
                return CrawlResult(
                    success=True,
                    data=response.data if isinstance(response.data, list) else [response.data],
                    message=f"B站搜索 '{keyword}' 成功",
                    source=self.NAME,
                )
            return CrawlResult(
                success=False, data=[],
                message=f"B站搜索失败: {response.message}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"B站搜索异常: {e}",
                source=self.NAME, error=str(e),
            )
    
    # ==================== 京东 ====================
    
    async def _jd_search(self, **kwargs) -> CrawlResult:
        """京东商品搜索"""
        client = self._get_client()
        if not client:
            return CrawlResult(success=False, data=[], message="JustOneAPI Token 未配置", source=self.NAME)
        
        keyword = kwargs.get("keyword", "")
        try:
            response = client.jd.search_item_list_v1(keyword=keyword)
            if response.success:
                return CrawlResult(
                    success=True,
                    data=response.data if isinstance(response.data, list) else [response.data],
                    message=f"京东搜索 '{keyword}' 成功",
                    source=self.NAME,
                )
            return CrawlResult(
                success=False, data=[],
                message=f"京东搜索失败: {response.message}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"京东搜索异常: {e}",
                source=self.NAME, error=str(e),
            )
    
    # ==================== 知乎 ====================
    
    async def _zhihu_search(self, **kwargs) -> CrawlResult:
        """知乎问答搜索"""
        client = self._get_client()
        if not client:
            return CrawlResult(success=False, data=[], message="JustOneAPI Token 未配置", source=self.NAME)
        
        keyword = kwargs.get("keyword", "")
        try:
            response = client.zhihu.search_v1(keyword=keyword)
            if response.success:
                return CrawlResult(
                    success=True,
                    data=response.data if isinstance(response.data, list) else [response.data],
                    message=f"知乎搜索 '{keyword}' 成功",
                    source=self.NAME,
                )
            return CrawlResult(
                success=False, data=[],
                message=f"知乎搜索失败: {response.message}",
                source=self.NAME,
            )
        except Exception as e:
            return CrawlResult(
                success=False, data=[],
                message=f"知乎搜索异常: {e}",
                source=self.NAME, error=str(e),
            )
