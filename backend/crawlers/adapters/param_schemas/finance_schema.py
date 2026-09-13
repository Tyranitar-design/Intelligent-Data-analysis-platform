# -*- coding: utf-8 -*-
"""
财经通用适配器参数 Schema

包含：汇率、天气、新闻等通用金融/生活数据适配器
"""
from . import AdapterParamSchema, ParamField, SchemaRegistry


def create_exchangerate_schema() -> AdapterParamSchema:
    """汇率适配器参数 Schema"""
    schema = AdapterParamSchema(
        adapter="exchangerate",
        version="1.0",
        description="实时汇率数据查询",
        category="finance",
    )

    schema.params["base_currency"] = ParamField(
        type="enum",
        label="基准货币",
        description="选择基准货币",
        required=False,
        default="USD",
        options=[
            {"value": "USD", "label": "美元 (USD)"},
            {"value": "CNY", "label": "人民币 (CNY)"},
            {"value": "EUR", "label": "欧元 (EUR)"},
            {"value": "JPY", "label": "日元 (JPY)"},
            {"value": "GBP", "label": "英镑 (GBP)"},
            {"value": "HKD", "label": "港币 (HKD)"},
        ],
    )

    schema.params["target_currencies"] = ParamField(
        type="array",
        label="目标货币",
        description="选择要查询的目标货币（多选，用逗号分隔）",
        placeholder="CNY,EUR,JPY",
        required=False,
        default=["CNY", "EUR", "JPY"],
    )

    return schema


def create_openweather_schema() -> AdapterParamSchema:
    """天气适配器参数 Schema"""
    schema = AdapterParamSchema(
        adapter="openweather",
        version="1.0",
        description="全球天气数据查询",
        category="weather",
    )

    schema.params["city"] = ParamField(
        type="string",
        label="城市",
        description="输入城市名称（支持中文）",
        placeholder="上海",
        required=True,
    )

    schema.params["units"] = ParamField(
        type="enum",
        label="温度单位",
        description="选择温度显示单位",
        required=False,
        default="metric",
        options=[
            {"value": "metric", "label": "摄氏度"},
            {"value": "imperial", "label": "华氏度"},
            {"value": "standard", "label": "开尔文"},
        ],
    )

    schema.params["forecast_days"] = ParamField(
        type="integer",
        label="预报天数",
        description="获取未来几天的天气预报",
        required=False,
        default=3,
        min=1,
        max=7,
    )

    return schema


def create_wikipedia_schema() -> AdapterParamSchema:
    """维基百科适配器参数 Schema"""
    schema = AdapterParamSchema(
        adapter="wikipedia",
        version="1.0",
        description="维基百科搜索与摘要",
        category="research",
    )

    schema.params["query"] = ParamField(
        type="string",
        label="搜索关键词",
        description="输入要搜索的关键词",
        placeholder="人工智能",
        required=True,
    )

    schema.params["language"] = ParamField(
        type="enum",
        label="语言",
        description="选择搜索结果语言",
        required=False,
        default="zh",
        options=[
            {"value": "zh", "label": "中文"},
            {"value": "en", "label": "English"},
            {"value": "ja", "label": "日本語"},
        ],
    )

    schema.params["limit"] = ParamField(
        type="integer",
        label="结果数量",
        description="返回多少条搜索结果",
        required=False,
        default=5,
        min=1,
        max=20,
    )

    return schema


# 注册所有 Schema
SchemaRegistry.register(create_exchangerate_schema())
SchemaRegistry.register(create_openweather_schema())
SchemaRegistry.register(create_wikipedia_schema())
