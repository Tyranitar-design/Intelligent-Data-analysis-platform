"""
MCP 工具 · 判别与采集
=====================

四个工具：``analyze_site`` / ``plan_collection`` / ``run_collection`` / ``job_status``。

每个工具都是**薄封装**：参数校验 + 调用 P1~P4 的 service + 把结果整理成
调用方友好的结构。业务逻辑不在这里重写。
"""
from __future__ import annotations

import logging
from typing import Any

from mcp.protocol import (
    AUTHORIZATION_REQUIRED,
    COMPLIANCE_BLOCKED,
    RESOURCE_NOT_FOUND,
    MCPError,
)
from mcp.registry import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 1. analyze_site
# --------------------------------------------------------------------------- #

ANALYZE_SITE_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "目标 URL（可省略协议，默认 https）"},
        "declared_authorization": {
            "type": "string",
            "enum": [
                "official",
                "own_credentials",
                "written_authorization",
            ],
            "description": "授权基础声明。留空则走授权确认流程",
        },
        "force_refresh": {
            "type": "boolean",
            "description": "忽略已缓存画像，强制重新探测",
        },
    },
    "required": ["url"],
}


async def analyze_site(arguments: dict, ctx: ToolContext) -> dict:
    """分析站点，产出画像、合规判定与推荐采集方案。"""
    from discover.profile import SiteProfiler

    url = str(arguments.get("url") or "").strip()
    if not url:
        raise ValueError("url 不能为空")

    profiler = SiteProfiler(ctx.session)
    result = await profiler.analyze(
        url,
        declared_authorization=arguments.get("declared_authorization"),
        force_refresh=bool(arguments.get("force_refresh", False)),
    )
    return result.to_dict()


# --------------------------------------------------------------------------- #
# 2. plan_collection
# --------------------------------------------------------------------------- #

PLAN_COLLECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "目标 URL"},
        "profile_id": {
            "type": "integer",
            "description": "复用已有画像 ID；留空则按 url 现场判别",
        },
        "requirement": {
            "type": "string",
            "description": "自然语言需求，如「采集全部文章标题与发布时间」。留空则采集全覆盖率字段",
        },
        "declared_authorization": {
            "type": "string",
            "enum": ["official", "own_credentials", "written_authorization"],
        },
    },
    "required": ["url"],
}


async def plan_collection(arguments: dict, ctx: ToolContext) -> dict:
    """生成采集方案。

    这一步**不产生采集请求**——它把画像、需求与策略整理成可复核的方案。
    真正的请求发生在 ``run_collection``。
    """
    from collect.planner import build_plan

    url = str(arguments.get("url") or "").strip()
    if not url:
        raise ValueError("url 不能为空")

    plan, verdict = await build_plan(
        ctx.session,
        url=url,
        profile_id=arguments.get("profile_id"),
        requirement=arguments.get("requirement"),
        declared_authorization=arguments.get("declared_authorization"),
    )

    return {
        "plan": plan.to_dict(),
        "compliance": verdict,
        "field_count": len(plan.field_mapping or []),
        "next_step": (
            "方案已就绪，可调用 run_collection 执行"
            if verdict.get("decision") in ("proceed", None)
            else f"判定为 {verdict.get('decision')}，执行前需补齐授权"
        ),
    }


# --------------------------------------------------------------------------- #
# 3. run_collection
# --------------------------------------------------------------------------- #

RUN_COLLECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "plan_id": {"type": "integer", "description": "采集计划 ID"},
        "authorization_token": {
            "type": "string",
            "description": "判定为 confirm_required 时，补齐授权后签发的令牌",
        },
        "max_items": {
            "type": "integer",
            "description": "本次采集中条目上限，默认 200",
        },
    },
    "required": ["plan_id"],
}


async def run_collection(arguments: dict, ctx: ToolContext) -> dict:
    """执行采集计划。

    合规强制点：``blocked`` 直接拒绝并附替代源；``confirm_required``
    必须携带有效令牌。
    """
    from api.models import CollectPlan
    from collect.planner import ComplianceDenied, check_verdict, resolve_verdict
    from collect.scheduler import CollectScheduler

    plan_id = int(arguments["plan_id"])
    plan = ctx.session.get(CollectPlan, plan_id)
    if plan is None:
        raise MCPError(RESOURCE_NOT_FOUND, f"采集计划不存在: {plan_id}")

    verdict = resolve_verdict(ctx.session, plan.verdict_uid)
    try:
        check_verdict(verdict, arguments.get("authorization_token"))
    except ComplianceDenied as exc:
        code = COMPLIANCE_BLOCKED if exc.kind == "blocked" else AUTHORIZATION_REQUIRED
        raise MCPError(code, exc.message, exc.to_dict()) from exc

    scheduler = CollectScheduler(ctx.session)
    max_items = int(arguments.get("max_items") or 200)
    job = await scheduler.create_job(plan, max_items=max_items)
    job = await scheduler.run_job(job.id)

    return {
        "job": job.to_dict(),
        "hint": (
            "采集完成，可用 query_dataset 前先调 materialize（REST）或直接检索条目"
            if job.status == "succeeded"
            else "采集未全部成功，详见 error_dist"
        ),
    }


# --------------------------------------------------------------------------- #
# 4. job_status
# --------------------------------------------------------------------------- #

JOB_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "job_id": {"type": "integer", "description": "采集任务 ID"},
    },
    "required": ["job_id"],
}


async def job_status(arguments: dict, ctx: ToolContext) -> dict:
    """查看采集任务状态：进度、条目数、去重统计、质量分、错误分布。"""
    from sqlalchemy import select

    from api.models import CollectJob, CollectTask

    job_id = int(arguments["job_id"])
    job = ctx.session.get(CollectJob, job_id)
    if job is None:
        raise MCPError(RESOURCE_NOT_FOUND, f"采集任务不存在: {job_id}")

    tasks = (
        ctx.session.execute(
            select(CollectTask).where(CollectTask.job_id == job_id).order_by(CollectTask.id)
        )
        .scalars()
        .all()
    )

    payload = job.to_dict()
    payload["tasks"] = [
        {
            "task_id": task.id,
            "status": task.status,
            "capability": task.capability_used,
            "attempts": task.attempts,
            "last_error": task.last_error,
        }
        for task in tasks
    ]
    payload["capabilities_used"] = sorted(
        {t.capability_used for t in tasks if t.capability_used}
    )
    return payload


# --------------------------------------------------------------------------- #
# 注册
# --------------------------------------------------------------------------- #

TOOL_SPECS = [
    ToolSpec(
        name="analyze_site",
        description=(
            "分析一个网站：产出站点画像（类型/技术栈/结构/可采字段）、"
            "四维合规判定与推荐采集策略。不产生采集请求。"
        ),
        input_schema=ANALYZE_SITE_SCHEMA,
        handler=analyze_site,
    ),
    ToolSpec(
        name="plan_collection",
        description=(
            "为采集生成方案：字段映射、能力链、频率策略、增量策略。"
            "不产生采集请求，产出可复核的计划。"
        ),
        input_schema=PLAN_COLLECTION_SCHEMA,
        handler=plan_collection,
    ),
    ToolSpec(
        name="run_collection",
        description=(
            "执行采集计划。判定为 blocked 会直接拒绝并给出替代数据源；"
            "判定为 confirm_required 需要携带授权令牌。"
        ),
        input_schema=RUN_COLLECTION_SCHEMA,
        handler=run_collection,
    ),
    ToolSpec(
        name="job_status",
        description=(
            "查询采集任务状态：进度、入库条目数、去重统计、质量分、错误分布、"
            "使用过的采集能力。"
        ),
        input_schema=JOB_STATUS_SCHEMA,
        handler=job_status,
    ),
]
