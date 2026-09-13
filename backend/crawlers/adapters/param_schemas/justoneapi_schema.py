# -*- coding: utf-8 -*-
"""
JustOneAPI 参数 Schema - 27 个平台

JustOneAPI 提供社交媒体数据采集服务，支持：
小红书、抖音、微博、淘宝、B站、京东、知乎等 27 个平台
"""
from . import AdapterParamSchema, ParamField, SchemaRegistry


# ==================== 平台列表 ====================

JUSTONEAPI_PLATFORMS = [
    {"value": "xiaohongshu", "label": "小红书", "icon": "🔴"},
    {"value": "douyin", "label": "抖音", "icon": "🎵"},
    {"value": "weibo", "label": "微博", "icon": "📱"},
    {"value": "taobao", "label": "淘宝", "icon": "🛒"},
    {"value": "bilibili", "label": "B站", "icon": "📺"},
    {"value": "jd", "label": "京东", "icon": "🛍️"},
    {"value": "zhihu", "label": "知乎", "icon": "💡"},
    {"value": "kuaishou", "label": "快手", "icon": "📸"},
    {"value": "pdd", "label": "拼多多", "icon": "🎯"},
    {"value": "xiaohongshu_shop", "label": "小红书商城", "icon": "🏪"},
    {"value": "wechat", "label": "微信公众号", "icon": "💬"},
    {"value": "toutiao", "label": "今日头条", "icon": "📰"},
    {"value": "xigua", "label": "西瓜视频", "icon": "🍉"},
    {"value": "haokan", "label": "好看视频", "icon": "👀"},
    {"value": "qq_news", "label": "腾讯新闻", "icon": "🐧"},
    {"value": "netease", "label": "网易", "icon": "☁️"},
    {"value": "sina", "label": "新浪", "icon": "🌊"},
    {"value": "sohu", "label": "搜狐", "icon": "🦊"},
    {"value": "ifeng", "label": "凤凰", "icon": "🐦"},
    {"value": "yiche", "label": "易车", "icon": "🚗"},
    {"value": "autohome", "label": "汽车之家", "icon": "🏎️"},
    {"value": "anjuke", "label": "安居客", "icon": "🏠"},
    {"value": "lianjia", "label": "链家", "icon": "🔑"},
    {"value": "meituan", "label": "美团", "icon": "🍜"},
    {"value": "dianping", "label": "大众点评", "icon": "⭐"},
    {"value": "ctrip", "label": "携程", "icon": "✈️"},
    {"value": "qunar", "label": "去哪儿", "icon": "🌍"},
]


# ==================== API 列表（按平台） ====================

JUSTONEAPI_APIS = {
    "xiaohongshu": [
        {"value": "search_note_v3", "label": "搜索笔记", "description": "按关键词搜索小红书笔记"},
        {"value": "get_note_v1", "label": "获取笔记详情", "description": "获取单篇笔记的详细信息"},
        {"value": "search_user_v1", "label": "搜索用户", "description": "按关键词搜索用户"},
        {"value": "get_user_notes_v1", "label": "获取用户笔记", "description": "获取指定用户的所有笔记"},
        {"value": "get_note_comments", "label": "获取评论", "description": "获取笔记的评论列表"},
    ],
    "douyin": [
        {"value": "search_video_v1", "label": "搜索视频", "description": "按关键词搜索抖音视频"},
        {"value": "get_video_v1", "label": "获取视频详情", "description": "获取单个视频详情"},
        {"value": "search_user_v1", "label": "搜索用户", "description": "搜索抖音用户"},
        {"value": "get_user_videos_v1", "label": "获取用户视频", "description": "获取用户发布的视频"},
    ],
    "weibo": [
        {"value": "search_weibo_v1", "label": "搜索微博", "description": "按关键词搜索微博"},
        {"value": "get_weibo_v1", "label": "获取微博详情", "description": "获取单条微博详情"},
        {"value": "get_user_weibos_v1", "label": "获取用户微博", "description": "获取用户发布的微博"},
        {"value": "get_hot_search_v1", "label": "获取热搜", "description": "获取微博热搜榜"},
    ],
    "taobao": [
        {"value": "search_item_v1", "label": "搜索商品", "description": "按关键词搜索淘宝商品"},
        {"value": "get_item_v1", "label": "获取商品详情", "description": "获取商品详细信息"},
        {"value": "search_shop_v1", "label": "搜索店铺", "description": "搜索淘宝店铺"},
    ],
    "bilibili": [
        {"value": "search_video_v1", "label": "搜索视频", "description": "按关键词搜索B站视频"},
        {"value": "get_video_v1", "label": "获取视频详情", "description": "获取视频详情"},
        {"value": "search_user_v1", "label": "搜索用户", "description": "搜索B站UP主"},
        {"value": "get_hot_v1", "label": "获取热门", "description": "获取B站热门视频"},
    ],
    "jd": [
        {"value": "search_item_v1", "label": "搜索商品", "description": "按关键词搜索京东商品"},
        {"value": "get_item_v1", "label": "获取商品详情", "description": "获取商品详情"},
        {"value": "search_shop_v1", "label": "搜索店铺", "description": "搜索京东店铺"},
    ],
    "zhihu": [
        {"value": "search_question_v1", "label": "搜索问题", "description": "按关键词搜索知乎问题"},
        {"value": "get_question_v1", "label": "获取问题详情", "description": "获取问题及回答"},
        {"value": "search_article_v1", "label": "搜索文章", "description": "搜索知乎文章"},
        {"value": "get_hot_v1", "label": "获取热榜", "description": "获取知乎热榜"},
    ],
}


# ==================== 通用参数 Schema ====================

def create_justoneapi_schema() -> AdapterParamSchema:
    """创建 JustOneAPI 参数 Schema"""

    schema = AdapterParamSchema(
        adapter="justoneapi",
        version="1.0",
        description="JustOneAPI 社交媒体数据采集 - 支持 27 个平台",
        category="social",
    )

    # 平台选择
    schema.params["platform"] = ParamField(
        type="enum",
        label="选择平台",
        description="选择要采集数据的平台",
        required=True,
        options=JUSTONEAPI_PLATFORMS,
    )

    # API 选择
    schema.params["api"] = ParamField(
        type="enum",
        label="选择功能",
        description="选择要执行的数据采集功能（当前为通用常用功能集）",
        required=True,
        options=[
            {"value": "search_note_v3", "label": "搜索笔记 / 搜索内容"},
            {"value": "get_note_v1", "label": "获取详情"},
            {"value": "get_note_comments", "label": "获取评论"},
            {"value": "search_user_v1", "label": "搜索用户"},
            {"value": "search_video_v1", "label": "搜索视频"},
            {"value": "search_item_v1", "label": "搜索商品"},
            {"value": "search_question_v1", "label": "搜索问题"},
            {"value": "get_hot_search_v1", "label": "获取热搜/热榜"},
        ],
    )

    # 搜索关键词
    schema.params["keyword"] = ParamField(
        type="string",
        label="搜索关键词",
        description="输入搜索关键词，支持中文",
        placeholder="例如: 数据分析",
        required=True,
    )

    # 页码
    schema.params["page"] = ParamField(
        type="integer",
        label="页码",
        description="从第几页开始采集",
        placeholder="1",
        required=False,
        default=1,
        min=1,
        max=50,
    )

    # 每页数量
    schema.params["page_size"] = ParamField(
        type="integer",
        label="每页数量",
        description="每页返回的数据条数",
        required=False,
        default=20,
        min=1,
        max=100,
    )

    # 排序方式
    schema.params["sort"] = ParamField(
        type="enum",
        label="排序方式",
        description="选择数据排序方式",
        required=False,
        default="general",
        options=[
            {"value": "general", "label": "综合排序"},
            {"value": "time", "label": "最新发布"},
            {"value": "hot", "label": "热门优先"},
            {"value": "relevance", "label": "相关度"},
        ],
    )

    # 时间范围
    schema.params["time_range"] = ParamField(
        type="enum",
        label="时间范围",
        description="筛选发布时间范围",
        required=False,
        default="all",
        options=[
            {"value": "all", "label": "全部时间"},
            {"value": "day", "label": "最近一天"},
            {"value": "week", "label": "最近一周"},
            {"value": "month", "label": "最近一月"},
            {"value": "year", "label": "最近一年"},
        ],
    )

    # 是否只采集有图内容
    schema.params["has_image"] = ParamField(
        type="boolean",
        label="只采集有图内容",
        description="仅采集包含图片的内容",
        required=False,
        default=False,
    )

    # 内容类型筛选
    schema.params["content_type"] = ParamField(
        type="enum",
        label="内容类型",
        description="筛选特定类型的内容",
        required=False,
        default="all",
        options=[
            {"value": "all", "label": "全部"},
            {"value": "video", "label": "视频"},
            {"value": "image", "label": "图文"},
            {"value": "text", "label": "纯文本"},
        ],
    )

    return schema


# 注册 Schema
justoneapi_schema = create_justoneapi_schema()
SchemaRegistry.register(justoneapi_schema)
