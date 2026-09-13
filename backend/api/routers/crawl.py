"""
数据采集路由 - 真实API + 分布式采集
"""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from api.database import get_db
from api.models import DataSource, CrawlTask
from api.schemas import (
    DataSourceCreate, DataSourceResponse,
    CrawlTaskCreate, CrawlTaskResponse,
    SuccessResponse
)
from crawlers.services import CrawlService
from crawlers.adapter_framework import AdapterRegistry
import crawlers.adapters  # 触发预置适配器模块导入与注册
from pydantic import BaseModel, Field

# 确保适配器被发现注册
AdapterRegistry.auto_discover()

router = APIRouter()
crawl_service = CrawlService()
logger = logging.getLogger(__name__)

# ==================== Phase 4.5: 参数 Schema 系统 ====================

from crawlers.adapters.param_schemas import SchemaRegistry

# ==================== Day 3: 登录态管理 API ====================

from crawlers.auth.auth_manager import AuthManager
from crawlers.auth.login_flows import list_supported_platforms

auth_manager = AuthManager()


class LoginRequest(BaseModel):
    """登录请求"""
    platform: str = Field(..., description="平台名称 (zhihu/weibo/douban/bilibili/xiaohongshu)")
    username: str = Field(..., description="用户名/手机号/邮箱")
    password: str = Field(..., description="密码")
    custom_url: Optional[str] = Field(None, description="自定义登录 URL (可选)")
    custom_selectors: Optional[Dict[str, str]] = Field(None, description="自定义选择器 (可选)")


class CookieLoginRequest(BaseModel):
    """Cookie 登录请求"""
    platform: str = Field(..., description="平台名称")
    cookies: List[Dict[str, Any]] = Field(..., description="Cookie 列表")


@router.get("/auth/platforms")
async def list_auth_platforms():
    """列出支持登录的平台"""
    platforms = auth_manager.list_supported_platforms()
    return {
        "count": len(platforms),
        "platforms": platforms,
    }


@router.get("/auth/sessions")
async def list_auth_sessions():
    """列出已登录的会话"""
    platforms = auth_manager.cookie_store.list_platforms()
    sessions = []
    for platform in platforms:
        session = auth_manager.cookie_store.get_session(platform)
        cookies = auth_manager.cookie_store.get_cookies(platform)
        sessions.append({
            "platform": platform,
            "has_session": session is not None,
            "cookies_count": len(cookies),
            "expires_at": session.get("expires_at") if session else None,
        })
    return {
        "count": len(sessions),
        "sessions": sessions,
    }


@router.post("/auth/login")
async def platform_login(request: LoginRequest):
    """平台登录 (Playwright 自动登录)"""
    result = await auth_manager.login_with_playwright(
        platform=request.platform,
        username=request.username,
        password=request.password,
        login_url=request.custom_url,
        username_selector=request.custom_selectors.get("username") if request.custom_selectors else None,
        password_selector=request.custom_selectors.get("password") if request.custom_selectors else None,
        submit_selector=request.custom_selectors.get("submit") if request.custom_selectors else None,
        wait_for=request.custom_selectors.get("wait_for") if request.custom_selectors else None,
    )
    return result


@router.post("/auth/cookie")
async def cookie_login(request: CookieLoginRequest):
    """Cookie 登录"""
    result = await auth_manager.login_with_cookies(
        platform=request.platform,
        cookies=request.cookies,
    )
    return result


@router.get("/auth/status/{platform}")
async def check_auth_status(platform: str, check_url: Optional[str] = None):
    """检查登录状态"""
    result = await auth_manager.check_login_status(platform, check_url)
    return result


@router.delete("/auth/logout/{platform}")
async def logout_platform(platform: str):
    """登出平台"""
    success = await auth_manager.logout(platform)
    return {"success": success, "message": f"已登出: {platform}"}


@router.get("/auth/headers/{platform}")
async def get_auth_headers(platform: str):
    """获取认证头"""
    headers = await auth_manager.get_auth_headers(platform)
    return {"platform": platform, "headers": headers}


@router.get("/param-schemas")
async def list_param_schemas():
    """列出所有适配器参数 Schema"""
    schemas = SchemaRegistry.list_all()
    return {
        "count": len(schemas),
        "schemas": schemas,
    }


@router.get("/param-schemas/{adapter}")
async def get_param_schema(adapter: str):
    """获取指定适配器的参数 Schema"""
    schema = SchemaRegistry.get_schema_detail(adapter)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema 不存在: {adapter}")
    return schema


@router.post("/param-schemas/{adapter}/validate")
async def validate_params(adapter: str, params: Dict[str, Any]):
    """验证参数"""
    schema = SchemaRegistry.get(adapter)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema 不存在: {adapter}")

    result = schema.validate(params)
    return result


# ==================== Phase 4.5: URL 自由爬取 ====================

from crawlers.url_crawler import URLCrawler
from crawlers.pagination import detect_pagination, generate_page_urls, extract_pagination_info
from crawlers.smart_extractor import SmartFieldExtractor
from crawlers.ranking_extractor import RankingExtractor
from crawlers.data_importer import DataImporter
from crawlers.dataset_service import DatasetService
from crawlers.dynamic_crawler import DynamicCrawler, DynamicCrawlOptions
from crawlers.intelligent import AdaptiveScraper, CrawlIntent, IntentType, ScraperConfig

url_crawler = URLCrawler()
smart_extractor = SmartFieldExtractor()
ranking_extractor = RankingExtractor()
data_importer = DataImporter()
dataset_service = DatasetService()
dynamic_crawler = DynamicCrawler()
smart_scraper_v2 = AdaptiveScraper(ScraperConfig())


class URLCrawlRequest(BaseModel):
    """URL 爬取请求"""
    url: str = Field(..., description="目标 URL")
    selectors: Optional[Dict[str, str]] = Field(None, description="CSS 选择器 {字段名: 选择器}")
    container_selector: Optional[str] = Field(None, description="列表容器选择器")
    item_selectors: Optional[Dict[str, str]] = Field(None, description="列表项字段选择器")
    force_strategy: Optional[str] = Field(None, description="强制策略: api/static/stealthy/crawl4ai")
    wait_for: Optional[str] = Field(None, description="等待渲染的选择器")
    auto_scroll: bool = Field(False, description="是否自动滚动")
    timeout: int = Field(30, ge=5, le=120, description="超时时间(秒)")
    auth_platform: Optional[str] = Field(None, description="登录平台 (如: zhihu, weibo)")
    use_auth: bool = Field(False, description="是否使用登录态")


class URLProbeRequest(BaseModel):
    """URL 探测请求"""
    url: str = Field(..., description="目标 URL")


class PaginationCrawlRequest(BaseModel):
    """分页爬取请求"""
    url: str = Field(..., description="第 1 页 URL")
    start_page: int = Field(1, ge=1, description="起始页码")
    end_page: int = Field(5, ge=1, le=50, description="结束页码")
    concurrency: int = Field(3, ge=1, le=10, description="并发数")
    selectors: Optional[Dict[str, str]] = Field(None, description="CSS 选择器")
    container_selector: Optional[str] = Field(None, description="列表容器选择器")
    item_selectors: Optional[Dict[str, str]] = Field(None, description="列表项字段选择器")


class SmartExtractRequest(BaseModel):
    """智能字段抽取请求"""
    url: str = Field(..., description="目标 URL")
    requirement: str = Field(..., description="想提取的字段描述，如：电影排名、评分、上映时间")
    dynamic: bool = Field(False, description="是否强制按动态页面处理")
    mode: str = Field("auto", description="抽取模式: auto/ranking/general")
    wait_for: Optional[str] = Field(None, description="等待元素 CSS 选择器")
    auto_scroll: bool = Field(False, description="是否自动滚动加载")
    scroll_count: int = Field(3, ge=1, le=20, description="滚动次数")
    click_selector: Optional[str] = Field(None, description="点击加载更多选择器")
    click_count: int = Field(1, ge=1, le=10, description="点击次数")
    auth_platform: Optional[str] = Field(None, description="登录平台 (如: zhihu, weibo)")
    use_auth: bool = Field(False, description="是否使用登录态")


class ImportFileRequest(BaseModel):
    """文件导入请求"""
    file_path: str = Field(..., description="文件路径")
    file_type: Optional[str] = Field(None, description="文件类型 (自动检测)")
    sheet_name: Optional[Any] = Field(0, description="Excel Sheet")
    encoding: Optional[str] = Field(None, description="编码")
    delimiter: str = Field(",", description="CSV 分隔符")
    table_index: int = Field(0, description="HTML 表格索引")


class SaveDatasetRequest(BaseModel):
    """保存数据集请求"""
    name: str = Field(..., description="数据集名称")
    description: str = Field("", description="数据集描述")
    columns: List[str] = Field(..., description="字段列表")
    data: List[Dict[str, Any]] = Field(..., description="数据行")
    source_url: Optional[str] = Field(None, description="数据来源 URL")
    source_type: str = Field("crawl", description="来源类型")


class SmartProbeV2Request(BaseModel):
    """智能爬虫 v2 探测请求"""
    url: str = Field(..., description="目标 URL")


class SmartCrawlV2Request(BaseModel):
    """智能爬虫 v2 爬取请求"""
    url: str = Field(..., description="目标 URL")
    require_auth: bool = Field(False, description="是否需要认证")
    auth_platform: Optional[str] = Field(None, description="认证平台")
    pagination: bool = Field(False, description="是否分页")
    headers: Dict[str, str] = Field(default_factory=dict, description="附加请求头")
    cookies: Dict[str, str] = Field(default_factory=dict, description="附加 Cookie")


@router.post("/url/probe")
async def probe_url(request: URLProbeRequest):
    """探测 URL 类型和特征"""
    probe = await url_crawler.probe_url(request.url)
    return {
        "url": probe.url,
        "content_type": probe.content_type,
        "status_code": probe.status_code,
        "is_api": probe.is_api,
        "is_static_html": probe.is_static_html,
        "is_dynamic": probe.is_dynamic,
        "is_protected": probe.is_protected,
        "requires_login": probe.requires_login,
        "charset": probe.charset,
        "content_length": probe.content_length,
        "error": probe.error,
        "suggested_strategy": url_crawler._choose_strategy(probe) if not probe.error else None,
    }


@router.post("/smart/v2/probe")
async def smart_probe_v2(request: SmartProbeV2Request):
    """智能爬虫 v2 探测"""
    probe = await smart_scraper_v2.probe(request.url)
    return {
        "success": True,
        "url": probe.url,
        "status_code": probe.status_code,
        "content_type": probe.content_type,
        "is_html": probe.is_html,
        "is_json": probe.is_json,
        "is_protected": probe.is_protected,
        "requires_auth": probe.requires_auth,
        "has_pagination": probe.has_pagination,
        "intent": probe.detected_intent.value if probe.detected_intent else None,
        "response_time": probe.response_time,
        "error": probe.error,
    }


@router.post("/smart/v2/crawl")
async def smart_crawl_v2(request: SmartCrawlV2Request):
    """智能爬虫 v2 抓取"""
    cookies = request.cookies.copy()

    if request.require_auth and request.auth_platform and not cookies:
        auth_cookies = auth_manager.cookie_store.get_cookies(request.auth_platform)
        cookies = {c["name"]: c["value"] for c in auth_cookies}

    intent_type = IntentType.AUTHENTICATED if request.require_auth else IntentType.STATIC_CONTENT
    intent = CrawlIntent(
        intent_type=intent_type,
        require_auth=request.require_auth,
        auth_platform=request.auth_platform,
        pagination=request.pagination,
        headers=request.headers,
        cookies=cookies,
    )

    result = await smart_scraper_v2.crawl(request.url, intent=intent)
    return {
        "success": result.success,
        "url": result.url,
        "strategy_used": result.strategy_used,
        "quality_score": result.quality_score,
        "duration_ms": result.duration_ms,
        "error": result.error,
        "data": result.data,
        "metadata": result.metadata,
        "probe": {
            "status_code": result.probe_result.status_code if result.probe_result else None,
            "content_type": result.probe_result.content_type if result.probe_result else None,
            "intent": result.probe_result.detected_intent.value if result.probe_result and result.probe_result.detected_intent else None,
        },
    }


@router.post("/smart/extract")
async def smart_extract(request: SmartExtractRequest):
    """智能字段抽取：URL + 自然语言字段需求 -> 结构化表格"""
    # 动态页面增强
    if request.dynamic or request.wait_for or request.auto_scroll or request.click_selector:
        options = DynamicCrawlOptions(
            wait_for=request.wait_for,
            wait_time=10,
            auto_scroll=request.auto_scroll,
            scroll_count=request.scroll_count,
            click_selector=request.click_selector,
            click_count=request.click_count,
        )
        # 如果有登录态，注入到 dynamic_crawler
        if request.use_auth and request.auth_platform:
            auth_cookies = url_crawler.auth_manager.cookie_store.get_cookies(request.auth_platform)
            if auth_cookies:
                options.cookies = auth_cookies
                logger.info(f"智能抽取使用登录态: {request.auth_platform}, {len(auth_cookies)} cookies")
        
        crawl_result = await dynamic_crawler.crawl_dynamic(request.url, options)
        if crawl_result.success and crawl_result.data:
            # 从动态爬取结果中提取 HTML
            html = None
            for item in crawl_result.data:
                if isinstance(item, dict):
                    html = item.get("html") or item.get("content")
                    if html:
                        break
            if html:
                # 用 ranking_extractor 或 smart_extractor 解析 HTML
                if request.mode == "ranking" or (request.mode == "auto" and _is_ranking_page(request.url, request.requirement)):
                    return await ranking_extractor.extract(
                        url=request.url,
                        requirement=request.requirement,
                        dynamic=False,  # 已经动态渲染过了
                    )
                return await smart_extractor.extract(
                    url=request.url,
                    requirement=request.requirement,
                    dynamic=False,
                )

    # 自动判断：榜单页走专用抽取器
    if request.mode == "ranking" or (request.mode == "auto" and _is_ranking_page(request.url, request.requirement)):
        return await ranking_extractor.extract(
            url=request.url,
            requirement=request.requirement,
            dynamic=request.dynamic,
        )
    return await smart_extractor.extract(
        url=request.url,
        requirement=request.requirement,
        dynamic=request.dynamic,
    )


def _is_ranking_page(url: str, requirement: str) -> bool:
    """判断是否是榜单页"""
    url_lower = url.lower()
    req_lower = requirement.lower()
    ranking_signals = [
        "top", "rank", "榜单", "排行", "排名", "250", "chart",
        "豆瓣", "movie", "film", "book", "music",
    ]
    return any(s in url_lower or s in req_lower for s in ranking_signals)


@router.post("/import/file")
async def import_file(request: ImportFileRequest):
    """多格式文件导入"""
    result = data_importer.import_file(
        file_path=request.file_path,
        file_type=request.file_type or None,
        sheet_name=request.sheet_name,
        encoding=request.encoding,
        delimiter=request.delimiter,
        table_index=request.table_index,
    )
    return {
        "success": result.success,
        "message": result.message,
        "error": result.error,
        "columns": result.columns,
        "row_count": result.row_count,
        "column_count": result.column_count,
        "source_type": result.source_type,
        "data": result.data[:200],
    }


@router.post("/smart/save")
async def smart_save_dataset(request: SaveDatasetRequest):
    """一键保存采集结果为数据集"""
    result = dataset_service.save_dataset(
        name=request.name,
        description=request.description,
        columns=request.columns,
        data=request.data,
        source_url=request.source_url,
        source_type=request.source_type,
    )
    return result


@router.get("/datasets")
async def list_datasets(limit: int = Query(50, ge=1, le=200)):
    """列出所有数据集"""
    datasets = dataset_service.list_datasets(limit=limit)
    return {
        "success": True,
        "count": len(datasets),
        "datasets": datasets,
    }


@router.get("/datasets/{table_name}/data")
async def get_dataset_data(table_name: str, limit: int = Query(100, ge=1, le=1000)):
    """获取数据集数据"""
    result = dataset_service.get_dataset_data(table_name=table_name, limit=limit)
    return {
        "success": True,
        **result,
    }


@router.post("/url/crawl")
async def crawl_url(request: URLCrawlRequest):
    """智能爬取单个 URL"""
    result = await url_crawler.crawl_url(
        url=request.url,
        selectors=request.selectors,
        container_selector=request.container_selector,
        item_selectors=request.item_selectors,
        force_strategy=request.force_strategy,
        wait_for=request.wait_for,
        auto_scroll=request.auto_scroll,
        timeout=request.timeout,
        auth_platform=request.auth_platform,
        use_auth=request.use_auth,
    )

    # 保存到数据库
    if result.success and result.data:
        try:
            result.save_to_db(platform="url_crawler", keyword=request.url[:200])
        except Exception:
            pass

    return {
        "success": result.success,
        "message": result.message,
        "count": result.count,
        "data": result.data[:200],  # 限制返回量
        "elapsed": result.elapsed,
        "error": result.error,
        "crawled_at": datetime.now().isoformat(),
    }


@router.post("/url/crawl/paginated")
async def crawl_paginated(request: PaginationCrawlRequest):
    """分页爬取"""
    # 生成翻页 URL
    urls = generate_page_urls(request.url, request.start_page, request.end_page)

    # 批量爬取
    results = await url_crawler.crawl_urls(
        urls=urls,
        concurrency=request.concurrency,
        selectors=request.selectors,
        container_selector=request.container_selector,
        item_selectors=request.item_selectors,
    )

    # 合并结果
    all_data = []
    success_count = 0
    total_elapsed = 0
    errors = []

    for i, result in enumerate(results):
        if result.success:
            success_count += 1
            all_data.extend(result.data)
        else:
            errors.append({"page": request.start_page + i, "error": result.error})
        total_elapsed += result.elapsed

    return {
        "success": True,
        "message": f"分页爬取完成 | 成功: {success_count}/{len(urls)} 页 | 总数据: {len(all_data)} 条",
        "pages": {
            "total": len(urls),
            "success": success_count,
            "failed": len(urls) - success_count,
        },
        "count": len(all_data),
        "data": all_data[:500],
        "errors": errors,
        "elapsed": total_elapsed,
        "crawled_at": datetime.now().isoformat(),
    }


# ==================== 数据源管理 ====================

@router.get("/sources", response_model=List[DataSourceResponse])
async def list_sources(db: Session = Depends(get_db)):
    return db.query(DataSource).all()


@router.post("/sources", response_model=DataSourceResponse)
async def create_source(data: DataSourceCreate, db: Session = Depends(get_db)):
    source = DataSource(**data.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


# ==================== 金融数据接口 ====================

@router.get("/finance/stock/{stock_code}")
async def crawl_stock_kline(
    stock_code: str,
    days: int = Query(30, ge=1, le=365),
    market: str = Query("sh", description="sh=上证, sz=深证")
):
    """爬取股票K线 (东方财富真实API)"""
    result = await crawl_service.crawl_stock(stock_code, days, market)

    if result.success and result.data:
        try:
            result.save_to_db(platform="eastmoney", keyword=stock_code, category=f"stock_{stock_code}")
        except Exception:
            pass

    return {
        "success": result.success,
        "message": result.message,
        "count": result.count,
        "data": result.data,
        "db_record_id": result.db_record_id,
        "crawled_at": datetime.now().isoformat()
    }


@router.get("/finance/index")
async def crawl_index_quotes():
    """获取主要指数实时行情 (新浪财经)"""
    result = await crawl_service.crawl_index_quotes()
    return {
        "success": result.success,
        "count": result.count,
        "data": result.data,
        "crawled_at": datetime.now().isoformat()
    }


@router.get("/finance/sectors")
async def crawl_sectors(
    sector_type: str = Query("industry", description="industry/concept/area"),
    limit: int = Query(20, ge=5, le=100)
):
    """获取板块行情 (东方财富)"""
    result = await crawl_service.crawl_sectors(sector_type, limit)
    return {
        "success": result.success,
        "count": result.count,
        "data": result.data,
    }


@router.get("/finance/power-stocks")
async def crawl_power_stocks():
    """获取电力行业股票行情"""
    result = await crawl_service.crawl_power_stocks()
    return {
        "success": result.success,
        "count": result.count,
        "data": result.data,
    }


# ==================== 批量股票采集 ====================

class BatchStockRequest(BaseModel):
    stocks: List[Dict[str, str]] = Field(..., description='[{"code":"600519","name":"贵州茅台","market":"sh"}]')
    days: int = Field(30, ge=1, le=365)


@router.post("/finance/stock/batch")
async def crawl_stocks_batch(request: BatchStockRequest):
    """批量爬取多只股票"""
    result = await crawl_service.crawl_stocks_batch(request.stocks, request.days)

    if result.success and result.data:
        try:
            result.save_to_db(platform="eastmoney", category="stock_batch")
        except Exception:
            pass

    return {
        "success": result.success,
        "message": result.message,
        "count": result.count,
        "crawled_at": datetime.now().isoformat()
    }


# ==================== 新闻接口 ====================

@router.get("/news/tech")
async def crawl_tech_news(per_page: int = Query(30, ge=5, le=50)):
    """爬取36kr科技快讯 (真实API)"""
    result = await crawl_service.crawl_tech_news(per_page)

    if result.success and result.data:
        try:
            result.save_to_db(platform="36kr", category="tech")
        except Exception:
            pass

    return {
        "success": result.success,
        "count": result.count,
        "data": result.data,
    }


@router.get("/news/finance")
async def crawl_finance_news(page: int = Query(1, ge=1, le=10), per_page: int = Query(30, ge=5, le=50)):
    """爬取财联社电报 (真实API)"""
    result = await crawl_service.crawl_finance_news(page, per_page)

    if result.success and result.data:
        try:
            result.save_to_db(platform="cls", category="finance")
        except Exception:
            pass

    return {
        "success": result.success,
        "count": result.count,
        "data": result.data,
    }


@router.get("/news/all")
async def crawl_all_news(pages: int = Query(2, ge=1, le=5)):
    """爬取所有新闻源 (36kr + 财联社)"""
    result = await crawl_service.crawl_all_news(pages)

    if result.success and result.data:
        try:
            result.save_to_db(platform="multi_news", category="all")
        except Exception:
            pass

    return {
        "success": result.success,
        "count": result.count,
        "data": result.data,
    }


# ==================== 电商接口 ====================

@router.get("/ecommerce/jd")
async def crawl_jd(
    keywords: str = Query("手机", description="关键词，逗号分隔"),
    pages: int = Query(1, ge=1, le=5)
):
    """爬取京东商品数据"""
    crawler = crawl_service.jd
    keyword_list = [k.strip() for k in keywords.split(",")]
    result = await crawler.crawl(keyword_list, pages)

    if result.success and result.data:
        try:
            result.save_to_db(platform="jd", keyword=keywords)
        except Exception:
            pass

    return {
        "success": result.success,
        "count": result.count,
        "data": result.data[:100],  # 限制返回量
        "crawled_at": datetime.now().isoformat()
    }


# ==================== 分布式批量采集 ====================

class DistributedCrawlRequest(BaseModel):
    tasks: List[Dict[str, Any]]
    concurrency: int = Field(5, ge=1, le=20)


@router.post("/distributed")
async def distributed_crawl(request: DistributedCrawlRequest):
    """
    分布式批量采集

    示例 tasks:
    [
        {"source": "eastmoney", "func": "crawl_stock_kline", "args": ["600519", 30, "sh"]},
        {"source": "36kr", "func": "crawl_newsflash", "kwargs": {"per_page": 30}},
        {"source": "sina", "func": "crawl_power_stocks"},
    ]
    """
    stats = await crawl_service.distributed_crawl(request.tasks, request.concurrency)
    return {
        "success": True,
        "stats": stats,
        "crawled_at": datetime.now().isoformat()
    }


# ==================== 一键采集 ====================

@router.get("/collect/all")
async def collect_all_data():
    """一键采集所有数据源"""
    results = {}

    # 1. 指数行情
    r = await crawl_service.crawl_index_quotes()
    results["index_quotes"] = {"success": r.success, "count": r.count}

    # 2. 板块行情
    r = await crawl_service.crawl_sectors("industry", 10)
    results["sectors"] = {"success": r.success, "count": r.count}

    # 3. 电力股
    r = await crawl_service.crawl_power_stocks()
    results["power_stocks"] = {"success": r.success, "count": r.count}

    # 4. 36kr 新闻
    r = await crawl_service.crawl_tech_news(20)
    if r.success and r.data:
        r.save_to_db(platform="36kr", category="tech")
    results["tech_news"] = {"success": r.success, "count": r.count}

    # 5. 财联社
    r = await crawl_service.crawl_finance_news(1, 20)
    if r.success and r.data:
        r.save_to_db(platform="cls", category="finance")
    results["finance_news"] = {"success": r.success, "count": r.count}

    return {
        "success": True,
        "results": results,
        "crawled_at": datetime.now().isoformat()
    }


# ==================== 爬虫任务管理 ====================

@router.get("/tasks")
async def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(CrawlTask).all()
    return [
        {
            "id": t.id,
            "source_id": t.source_id,
            "source_name": t.source.name if t.source else None,
            "status": t.status,
            "config": t.config or {},
            "result": t.result or {},
            "total_items": t.total_items or 0,
            "saved_items": t.saved_items or 0,
            "error_message": t.error_message or "",
            "started_at": t.started_at,
            "completed_at": t.completed_at,
            "created_at": t.created_at,
        }
        for t in tasks
    ]


# ==================== 历史数据 ====================

@router.get("/history")
async def get_crawl_history(limit: int = Query(50, ge=1, le=200)):
    history = crawl_service.get_history(limit=limit)
    return {"count": len(history), "data": history}


# ==================== Phase 2: 新增接口 ====================

from crawlers.adapter_framework import AdapterRegistry
from crawlers.robots_checker import RobotsChecker
from crawlers.custom import CrawlConfigSchema, CustomCrawlEngine, SourceType
from crawlers.utils.file_parser import FileParser

robots_checker = RobotsChecker()
custom_engine = CustomCrawlEngine()
file_parser = FileParser()


# --- 适配器管理 ---

@router.get("/adapters")
async def list_adapters():
    """列出所有已注册的适配器"""
    adapters = AdapterRegistry.list_adapters()
    return {"count": len(adapters), "adapters": adapters}


@router.get("/adapters/{name}/info")
async def get_adapter_info(name: str):
    """获取适配器详情"""
    adapter_class = AdapterRegistry.get(name)
    if not adapter_class:
        raise HTTPException(status_code=404, detail=f"适配器不存在: {name}")
    adapter = AdapterRegistry.create(name)
    return adapter.get_info()


@router.post("/adapters/{name}/fetch")
async def fetch_from_adapter(name: str, params: Dict[str, Any] = None):
    """使用适配器获取数据"""
    adapter = AdapterRegistry.create(name)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"适配器不存在: {name}")

    payload = params or {}

    # JustOneAPI 前端参数 → 后端适配器类型映射
    if name == "justoneapi":
        platform = payload.get("platform", "")
        api_name = payload.get("api", "")
        api_type_map = {
            ("xiaohongshu", "search_note_v3"): "xiaohongshu_search",
            ("xiaohongshu", "get_note_v1"): "xiaohongshu_note",
            ("xiaohongshu", "get_note_comments"): "xiaohongshu_comments",
            ("xiaohongshu", "search_user_v1"): "xiaohongshu_user_search",
            ("douyin", "search_video_v1"): "douyin_search",
            ("weibo", "get_hot_search_v1"): "weibo_hot",
            ("taobao", "search_item_v1"): "taobao_search",
            ("bilibili", "search_video_v1"): "bilibili_search",
            ("jd", "search_item_v1"): "jd_search",
            ("zhihu", "search_question_v1"): "zhihu_search",
        }
        mapped_type = api_type_map.get((platform, api_name))
        if mapped_type:
            payload = {**payload, "type": mapped_type}
        elif platform and api_name:
            payload = {**payload, "type": f"{platform}_{api_name}"}
    
    result = await adapter.fetch_with_retry(**payload)
    return {
        "success": result.success,
        "message": result.message,
        "count": result.count,
        "data": result.data[:500],  # 限制返回量
        "elapsed": result.elapsed,
        "error": result.error,
    }


# --- robots.txt 合规检查 ---

@router.get("/robots-check")
async def check_robots(url: str = Query(..., description="要检查的 URL")):
    """检查 URL 是否符合 robots.txt 规则"""
    report = await robots_checker.check(url)
    return report.to_dict()


@router.post("/robots-check/batch")
async def check_robots_batch(urls: List[str]):
    """批量检查 URL 合规性"""
    reports = await robots_checker.check_batch(urls)
    return {
        "count": len(reports),
        "results": [r.to_dict() for r in reports],
    }


# --- 用户自定义采集 ---

@router.post("/custom")
async def custom_crawl(config: CrawlConfigSchema):
    """用户自定义采集"""
    result = await custom_engine.execute(config)
    return {
        "success": result.success,
        "message": result.message,
        "count": result.count,
        "data": result.data[:500],
        "elapsed": result.elapsed,
        "error": result.error,
    }


@router.post("/custom/test")
async def custom_crawl_test(config: CrawlConfigSchema):
    """测试运行自定义采集（限制数据量）"""
    result = await custom_engine.test_run(config, max_items=10)
    return result


# --- 本地文件导入 ---

class FileUploadConfig(BaseModel):
    file_type: str = Field(default=None, description="文件类型 (自动检测)")
    encoding: Optional[str] = Field(default=None, description="编码")
    delimiter: str = Field(default=",", description="CSV 分隔符")
    sheet_name: Any = Field(default=0, description="Excel Sheet")
    skip_rows: int = Field(default=0, description="跳过行数")
    max_rows: int = Field(default=10000, description="最大行数")
    preview_rows: int = Field(default=100, description="预览行数")


@router.post("/local/parse")
async def parse_local_file(file_path: str, config: FileUploadConfig = None):
    """解析本地文件"""
    if config is None:
        config = FileUploadConfig()
    
    try:
        result = file_parser.parse_file(
            file_path=file_path,
            file_type=config.file_type,
            encoding=config.encoding,
            delimiter=config.delimiter,
            sheet_name=config.sheet_name,
            skip_rows=config.skip_rows,
            max_rows=config.max_rows,
            preview_rows=config.preview_rows,
        )
        return {"success": True, "result": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Celery 任务管理 ---

@router.post("/celery/submit")
async def submit_celery_task(
    source_type: str = Query(..., description="api/web/local"),
    priority: str = Query("normal", description="high/normal/low"),
    config: Dict[str, Any] = None,
):
    """提交 Celery 采集任务"""
    from api.tasks.crawl_tasks import crawl_high_priority, crawl_normal_priority, crawl_low_priority
    
    task_config = config or {}
    task_config["source_type"] = source_type
    
    if priority == "high":
        task = crawl_high_priority.delay(task_config)
    elif priority == "low":
        task = crawl_low_priority.delay(task_config)
    else:
        task = crawl_normal_priority.delay(task_config)
    
    return {
        "success": True,
        "task_id": task.id,
        "priority": priority,
        "status": "submitted",
        "message": f"任务已提交 (priority={priority})",
    }


@router.get("/celery/status/{task_id}")
async def get_celery_task_status(task_id: str):
    """查询 Celery 任务状态"""
    from api.tasks.crawl_tasks import get_crawl_task_status
    
    result = get_crawl_task_status(task_id)
    
    # 同时查询 Celery 原生状态
    from api.celery_app import celery_app
    celery_result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "celery_status": celery_result.status,
        **result,
    }


# --- Scrapling 状态 ---

@router.get("/scrapling/status")
async def get_scrapling_status():
    """获取 Scrapling 状态"""
    from crawlers.scrapling_adapter import ScraplingAdapter, ScraplingConfig
    
    adapter = ScraplingAdapter()
    return {
        "available": adapter.available,
        "stealthy_available": adapter.stealthy_available,
        "config": {
            "enabled": adapter.config.enabled,
            "timeout": adapter.config.timeout,
            "bypass_cloudflare": adapter.config.bypass_cloudflare,
        },
    }
