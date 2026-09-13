# -*- coding: utf-8 -*-
"""Smoke Center scenario registry."""
from .models import SmokeScenarioDefinition


SCENARIOS = [
    SmokeScenarioDefinition(
        scenario_id="local-upload-basic",
        title="本地数据主链验收",
        description="使用本地或上传结构化数据验证数据集、分析与报告主链。",
        mode="local",
        requires_robots_check=False,
        requires_auth=False,
        requires_human=False,
        preferred_strategy="local",
        required_inputs=["dataset_payload"],
        post_steps=["dataset_save", "analysis", "report"],
    ),
    SmokeScenarioDefinition(
        scenario_id="live-public-static",
        title="公开静态 URL 验收",
        description="对公开静态页面执行 robots 检查、URL 探测、采集和主链验收。",
        mode="live-public",
        requires_robots_check=True,
        requires_auth=False,
        requires_human=False,
        preferred_strategy="url/crawl",
        required_inputs=["url"],
        post_steps=["probe", "crawl", "dataset_save", "analysis", "report"],
    ),
    SmokeScenarioDefinition(
        scenario_id="live-public-dynamic-js",
        title="公开动态 JS URL 验收",
        description="对公开动态页面执行 robots 检查、smart v2 探测、动态采集和主链验收。",
        mode="live-public",
        requires_robots_check=True,
        requires_auth=False,
        requires_human=False,
        preferred_strategy="smart/v2",
        required_inputs=["url"],
        post_steps=["probe", "crawl", "dataset_save", "analysis", "report"],
    ),
    SmokeScenarioDefinition(
        scenario_id="live-assisted-bilibili",
        title="Bilibili 人机协同验收",
        description="通过人工协同完成登录或验证码，再验证会话复用与登录态采集。",
        mode="live-assisted",
        requires_robots_check=True,
        requires_auth=True,
        requires_human=True,
        preferred_strategy="assisted-auth",
        platform="bilibili",
        required_inputs=["url", "platform"],
        post_steps=["open_login", "session_capture", "session_reuse_check", "crawl", "dataset_save", "analysis", "report"],
    ),
]


def list_scenarios() -> list[SmokeScenarioDefinition]:
    """Return all registered smoke scenarios."""
    return SCENARIOS


def get_scenario(scenario_id: str) -> SmokeScenarioDefinition | None:
    """Return a scenario by id."""
    for scenario in SCENARIOS:
        if scenario.scenario_id == scenario_id:
            return scenario
    return None
