"""
站点判别路由
============

- ``POST /api/v1/discover/analyze``  分析一个 URL，产出画像与合规判定
- ``GET  /api/v1/discover/profiles``  列出已缓存的站点画像
- ``GET  /api/v1/discover/profiles/{id}``  查看单个画像详情
- ``GET  /api/v1/discover/verdicts``  列出合规判定记录
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.core.database import get_db
from api.models import ComplianceVerdict, SiteProfile
from api.schemas.discover import AnalyzeRequest, AuthorizationPatch
from discover.profile import SiteProfiler
from mcp.audit import record as record_audit

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", summary="分析站点并生成画像与合规判定")
async def analyze_site(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> dict:
    """探测目标 URL，返回 SiteProfile、四维判定与推荐采集策略。

    判定为 ``confirm_required`` 时返回 ``authorization_token``，
    调用方补齐授权声明后可携带该 token 重放采集请求。
    """
    profiler = SiteProfiler(db)
    try:
        result = await profiler.analyze(
            payload.url,
            declared_authorization=payload.declared_authorization,
            force_refresh=payload.force_refresh,
            sample_details=payload.sample_details,
        )
    except Exception as exc:  # noqa: BLE001 - 探测失败要转成结构化错误
        logger.exception("站点分析失败: %s", payload.url)
        raise HTTPException(
            status_code=502,
            detail={"error": "analyze_failed", "message": str(exc)[:300]},
        ) from exc

    return result.to_dict()


@router.get("/profiles", summary="列出站点画像")
def list_profiles(
    domain: Optional[str] = Query(None, description="按域名过滤"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """列出已缓存的站点画像（按最近验证时间倒序）。"""
    stmt = select(SiteProfile)
    count_stmt = select(func.count()).select_from(SiteProfile)

    if domain:
        stmt = stmt.where(SiteProfile.domain == domain)
        count_stmt = count_stmt.where(SiteProfile.domain == domain)

    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(SiteProfile.last_verified.desc()).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "profile_id": r.id,
                "domain": r.domain,
                "url_pattern": r.url_pattern,
                "version": r.version,
                "site_type": (r.site_meta or {}).get("type"),
                "title": (r.site_meta or {}).get("title"),
                "confidence": r.confidence,
                "coverage": r.coverage,
                "field_count": len(r.fields or []),
                "decision": (r.compliance or {}).get("decision"),
                "last_verified": r.last_verified.isoformat() if r.last_verified else None,
            }
            for r in rows
        ],
    }


@router.get("/profiles/stats", summary="站点画像统计")
def profile_stats(db: Session = Depends(get_db)) -> dict:
    """按判定 / 类型聚合画像分布，并统计过期画像（>14 天未验证）。

    注意：本路由必须注册在 ``/profiles/{profile_id}`` **之前**——
    否则 "stats" 会被当作路径参数解析（由测试守护）。
    """
    rows = db.execute(select(SiteProfile)).scalars().all()
    now = datetime.now(timezone.utc)

    by_decision = {"proceed": 0, "confirm_required": 0, "blocked": 0, "unknown": 0}
    by_type: dict[str, int] = {}
    stale_count = 0

    for profile in rows:
        decision = (profile.compliance or {}).get("decision") or "unknown"
        by_decision[decision if decision in by_decision else "unknown"] += 1

        site_type = (profile.site_meta or {}).get("type") or "unknown"
        by_type[site_type] = by_type.get(site_type, 0) + 1

        last_verified = profile.last_verified
        if last_verified is not None:
            aware = (
                last_verified
                if last_verified.tzinfo
                else last_verified.replace(tzinfo=timezone.utc)
            )
            if (now - aware).days > 14:
                stale_count += 1

    return {
        "total": len(rows),
        "by_decision": by_decision,
        "by_type": by_type,
        "stale_count": stale_count,
    }


@router.get("/profiles/{profile_id}", summary="查看画像详情")
def get_profile(profile_id: int, db: Session = Depends(get_db)) -> dict:
    """按 ID 获取完整画像。"""
    profile = db.get(SiteProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="画像不存在")
    return profile.to_dict()


@router.get("/verdicts", summary="列出合规判定记录")
def list_verdicts(
    decision: Optional[str] = Query(
        None, description="按判定结果过滤：proceed / confirm_required / blocked"
    ),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """列出判定留痕，供审计与复核。"""
    stmt = select(ComplianceVerdict)
    count_stmt = select(func.count()).select_from(ComplianceVerdict)

    if decision:
        stmt = stmt.where(ComplianceVerdict.decision == decision)
        count_stmt = count_stmt.where(ComplianceVerdict.decision == decision)

    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(ComplianceVerdict.created_at.desc()).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [r.to_dict() for r in rows],
    }


# --------------------------------------------------------------------------- #
# 合规中心
# --------------------------------------------------------------------------- #

# 补齐授权时声明基础 → 授权维度的映射（与判定引擎 judge_authorization 对齐）
_BASIS_TO_DIM = {
    "official": "B1",
    "own_credentials": "B2",
    "written_authorization": "B3",
}


@router.get("/verdicts/stats", summary="合规判定统计")
def verdict_stats(db: Session = Depends(get_db)) -> dict:
    """聚合统计 + 可访问性×授权基础 矩阵分布，供合规中心总览。"""
    total = db.execute(select(func.count()).select_from(ComplianceVerdict)).scalar_one()

    by_decision = {
        decision: count
        for decision, count in db.execute(
            select(ComplianceVerdict.decision, func.count()).group_by(
                ComplianceVerdict.decision
            )
        ).all()
    }

    matrix = [
        {"access": access, "authorization": authorization, "count": count}
        for access, authorization, count in db.execute(
            select(
                ComplianceVerdict.dim_access,
                ComplianceVerdict.dim_authorization,
                func.count(),
            ).group_by(
                ComplianceVerdict.dim_access, ComplianceVerdict.dim_authorization
            )
        ).all()
    ]

    return {
        "total": total,
        "by_decision": {
            "proceed": by_decision.get("proceed", 0),
            "confirm_required": by_decision.get("confirm_required", 0),
            "blocked": by_decision.get("blocked", 0),
        },
        "matrix": matrix,
    }


@router.patch(
    "/verdicts/{verdict_uid}/authorization", summary="补齐授权声明并解锁判定"
)
def confirm_verdict_authorization(
    verdict_uid: str,
    payload: AuthorizationPatch,
    db: Session = Depends(get_db),
) -> dict:
    """对 ``confirm_required`` 判定补齐授权声明。

    - 写回 ``operator`` / ``authorization_basis``，授权维度更新，判定解锁为 ``proceed``；
    - 写审计留痕（谁、何时、依据什么解锁）；
    - ``blocked`` 判定不可通过此接口解锁 —— 硬边界由技术措施 / 凭证来源 /
      数据属性决定，不因人工确认而改变。
    """
    verdict = (
        db.execute(
            select(ComplianceVerdict)
            .where(ComplianceVerdict.verdict_uid == verdict_uid)
            .limit(1)
        )
        .scalars()
        .first()
    )
    if verdict is None:
        raise HTTPException(status_code=404, detail="判定不存在")

    if verdict.decision == "blocked":
        raise HTTPException(
            status_code=400,
            detail="阻断判定不可通过补齐授权解锁（技术措施 / 凭证来源 / 数据属性边界）",
        )
    if verdict.decision == "proceed":
        raise HTTPException(status_code=400, detail="该判定已可执行，无需补齐授权")

    verdict.operator = payload.operator[:100]
    verdict.authorization_basis = payload.basis
    verdict.dim_authorization = _BASIS_TO_DIM[payload.basis]
    verdict.decision = "proceed"
    db.commit()
    db.refresh(verdict)

    record_audit(
        db,
        principal_id=payload.operator,
        action="compliance.authorization_confirmed",
        result="ok",
        target_type="compliance_verdict",
        target_id=verdict.verdict_uid,
        verdict_row_id=verdict.id,
        detail={
            "basis": payload.basis,
            "note": (payload.note or "")[:300],
        },
    )

    return {"verdict": verdict.to_dict(), "unlocked": True}
