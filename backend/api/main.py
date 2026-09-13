"""
智能数据分析平台 API
===================

Canonical backend entrypoint.
"""
from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.core.config import settings
from api.core.database import init_db
from api.routers import (
    analysis,
    analytics,
    auth,
    collect,
    crawl,
    data,
    discover,
    health,
    mcp,
    reports,
    smoke,
)


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _try_import_optional_router(module_name: str):
    """按可用性导入可选路由模块。"""
    try:
        module = __import__(module_name, fromlist=["router"])
        logger.info(f"✅ Optional router available: {module_name}")
        return module
    except Exception as exc:
        logger.warning(f"⚠️ Optional router disabled: {module_name} ({exc})")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    logger.info("✅ 数据库初始化完成")
    yield
    logger.info("👋 应用关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="企业级智能数据分析平台 - 集数据采集、智能分析、预测建模、可视化展示于一体",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    logger.info(f"📥 {request.method} {request.url.path}")
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"📤 {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-API-Version"] = settings.APP_VERSION
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"❌ 未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": str(exc) if settings.DEBUG else None,
            }
        },
    )


app.include_router(health.router, tags=["健康检查"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(crawl.router, prefix="/api/v1/crawl", tags=["数据采集"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["数据分析"])
app.include_router(data.router, prefix="/api/v1/data", tags=["数据浏览"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["报告"])
app.include_router(smoke.router, prefix="/api/v1/smoke", tags=["验收中心"])
app.include_router(discover.router, prefix="/api/v1/discover", tags=["站点判别"])
app.include_router(collect.router, prefix="/api/v1/collect", tags=["数据采集 v3"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["分析 v3"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP 工具面"])

optional_ml = _try_import_optional_router("api.routers.ml")
optional_dl = _try_import_optional_router("api.routers.dl")
optional_mining = _try_import_optional_router("api.routers.mining")
optional_router_status = {
    "ml": optional_ml is not None,
    "dl": optional_dl is not None,
    "mining": optional_mining is not None,
}

if optional_ml is not None:
    app.include_router(optional_ml.router, prefix="/api/v1/ml", tags=["机器学习"])
if optional_dl is not None:
    app.include_router(optional_dl.router, prefix="/api/v1/dl", tags=["深度学习"])
if optional_mining is not None:
    app.include_router(optional_mining.router, prefix="/api/v1/mining", tags=["数据挖掘"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "capabilities": "/capabilities",
    }


@app.get("/api/v1")
async def api_info():
    """API 信息"""
    return {
        "version": "v1",
        "endpoints": {
            "auth": "/api/v1/auth",
            "crawl": "/api/v1/crawl",
            "analysis": "/api/v1/analysis",
            "data": "/api/v1/data",
            "reports": "/api/v1/reports",
            "smoke": "/api/v1/smoke",
            **({"ml": "/api/v1/ml"} if optional_ml is not None else {}),
            **({"dl": "/api/v1/dl"} if optional_dl is not None else {}),
            **({"mining": "/api/v1/mining"} if optional_mining is not None else {}),
        },
    }


@app.get("/capabilities")
async def capabilities_info():
    """系统能力与环境状态。"""
    return health.get_capabilities_payload(optional_router_status)


@app.get("/api/v1/capabilities")
async def capabilities_info_v1():
    """系统能力与环境状态（v1 别名）。"""
    return health.get_capabilities_payload(optional_router_status)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
