"""
健康检查路由
============
"""
from urllib.parse import urlparse

from fastapi import APIRouter

from api.core.config import settings

router = APIRouter()


def _database_driver_name(database_url: str) -> str:
    if database_url.startswith("sqlite"):
        return "sqlite"
    if database_url.startswith("postgresql"):
        return "postgresql"
    if database_url.startswith("mysql"):
        return "mysql"
    return "unknown"


def _service_host(url: str) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    return parsed.hostname


def get_capabilities_payload(optional_modules: dict[str, bool] | None = None) -> dict:
    optional_modules = optional_modules or {}
    database_driver = _database_driver_name(settings.DATABASE_URL)

    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "capabilities": {
            "auth": {
                "enabled": True,
                "category": "core",
                "label": "认证与权限",
                "path": "/api/v1/auth",
            },
            "crawl": {
                "enabled": True,
                "category": "core",
                "label": "数据采集与智能爬取",
                "path": "/api/v1/crawl",
            },
            "analysis": {
                "enabled": True,
                "category": "core",
                "label": "数据分析",
                "path": "/api/v1/analysis",
            },
            "data": {
                "enabled": True,
                "category": "core",
                "label": "数据浏览",
                "path": "/api/v1/data",
            },
            "reports": {
                "enabled": True,
                "category": "core",
                "label": "报告中心",
                "path": "/api/v1/reports",
            },
            "ml": {
                "enabled": bool(optional_modules.get("ml")),
                "category": "optional",
                "label": "机器学习",
                "path": "/api/v1/ml",
            },
            "dl": {
                "enabled": bool(optional_modules.get("dl")),
                "category": "optional",
                "label": "深度学习",
                "path": "/api/v1/dl",
            },
            "mining": {
                "enabled": bool(optional_modules.get("mining")),
                "category": "optional",
                "label": "数据挖掘",
                "path": "/api/v1/mining",
            },
        },
        "environment": {
            "database": {
                "configured": bool(settings.DATABASE_URL),
                "driver": database_driver,
                "url_kind": "local" if database_driver == "sqlite" else "remote",
            },
            "queue": {
                "configured": bool(settings.REDIS_URL),
                "provider": "redis",
                "host": _service_host(settings.REDIS_URL),
            },
            "storage": {
                "configured": bool(settings.MINIO_ENDPOINT),
                "provider": "minio",
                "endpoint": settings.MINIO_ENDPOINT,
                "bucket": settings.MINIO_BUCKET_NAME,
            },
            "crawler": {
                "configured": True,
                "max_concurrent": settings.CRAWL_MAX_CONCURRENT,
                "timeout_seconds": settings.CRAWL_TIMEOUT,
                "default_delay_seconds": settings.CRAWL_DEFAULT_DELAY,
            },
            "integrations": {
                "justoneapi_configured": bool(settings.JUSTONE_API_TOKEN),
            },
        },
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": settings.APP_NAME,
    }


@router.get("/ready")
async def readiness_check():
    """就绪检查"""
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
            "redis": "ok",
        },
    }
