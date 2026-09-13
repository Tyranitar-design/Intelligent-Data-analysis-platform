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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.core.database import get_db
from api.models import ComplianceVerdict, SiteProfile
from api.schemas.discover import AnalyzeRequest
from discover.profile import SiteProfiler

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
                "decision": (r.compliance or {}).get("decision"),
                "last_verified": r.last_verified.isoformat() if r.last_verified else None,
            }
            for r in rows
        ],
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
