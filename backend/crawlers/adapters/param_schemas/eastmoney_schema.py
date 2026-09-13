# -*- coding: utf-8 -*-
"""
东方财富适配器参数 Schema
"""
from . import AdapterParamSchema, ParamField, SchemaRegistry


def create_eastmoney_schema() -> AdapterParamSchema:
    """创建东方财富参数 Schema"""

    schema = AdapterParamSchema(
        adapter="eastmoney",
        version="1.0",
        description="东方财富金融数据采集 - 股票K线、板块行情、实时数据",
        category="finance",
    )

    # 功能选择
    schema.params["function"] = ParamField(
        type="enum",
        label="功能",
        description="选择要采集的数据类型",
        required=True,
        default="stock_kline",
        options=[
            {"value": "stock_kline", "label": "股票K线", "description": "获取股票历史K线数据"},
            {"value": "stock_quote", "label": "股票行情", "description": "获取股票实时行情"},
            {"value": "sector_quote", "label": "板块行情", "description": "获取板块/行业行情"},
            {"value": "index_quote", "label": "指数行情", "description": "获取大盘指数行情"},
            {"value": "fund_list", "label": "基金列表", "description": "获取基金列表"},
        ],
    )

    # 股票代码
    schema.params["stock_code"] = ParamField(
        type="string",
        label="股票代码",
        description="输入股票代码，如 600519",
        placeholder="600519",
        required=False,
    )

    # 市场
    schema.params["market"] = ParamField(
        type="enum",
        label="市场",
        description="选择股票市场",
        required=False,
        default="sh",
        options=[
            {"value": "sh", "label": "上海"},
            {"value": "sz", "label": "深圳"},
            {"value": "bj", "label": "北京"},
            {"value": "hk", "label": "港股"},
        ],
    )

    # 天数
    schema.params["days"] = ParamField(
        type="integer",
        label="天数",
        description="获取最近多少天的数据",
        placeholder="30",
        required=False,
        default=30,
        min=1,
        max=365,
    )

    # K线周期
    schema.params["period"] = ParamField(
        type="enum",
        label="K线周期",
        description="选择K线周期",
        required=False,
        default="day",
        options=[
            {"value": "day", "label": "日线"},
            {"value": "week", "label": "周线"},
            {"value": "month", "label": "月线"},
            {"value": "60", "label": "60分钟"},
            {"value": "30", "label": "30分钟"},
            {"value": "15", "label": "15分钟"},
        ],
    )

    # 板块类型
    schema.params["sector_type"] = ParamField(
        type="enum",
        label="板块类型",
        description="选择板块类型",
        required=False,
        default="industry",
        options=[
            {"value": "industry", "label": "行业板块"},
            {"value": "concept", "label": "概念板块"},
            {"value": "area", "label": "地域板块"},
        ],
    )

    # 限制数量
    schema.params["limit"] = ParamField(
        type="integer",
        label="数量限制",
        description="最多返回多少条数据",
        placeholder="20",
        required=False,
        default=20,
        min=1,
        max=100,
    )

    return schema


# 注册 Schema
eastmoney_schema = create_eastmoney_schema()
SchemaRegistry.register(eastmoney_schema)
