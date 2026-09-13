# -*- coding: utf-8 -*-
"""
采集任务 v2.0
=============

Celery 异步任务 — 完整实现
- 优先级任务分发
- 断点续传
- 自动重试（指数退避）
- 任务状态追踪
- 批量采集
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

from celery import shared_task, current_task
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


# ==================== 辅助函数 ====================

def _update_task_status(task_id: str, status: str, progress: float = 0, message: str = ""):
    """更新任务状态到 Redis"""
    try:
        from api.celery_app import celery_app
        redis_client = celery_app.backend.client if hasattr(celery_app.backend, 'client') else None
        if redis_client:
            status_data = {
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": datetime.now().isoformat(),
            }
            redis_client.setex(
                f"crawl_status:{task_id}",
                3600 * 24,  # 24小时过期
                json.dumps(status_data, ensure_ascii=False)
            )
    except Exception as e:
        logger.warning(f"更新任务状态失败: {e}")


def _run_async(coro):
    """在同步 Celery 任务中运行异步函数"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=300)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ==================== 采集任务 ====================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def crawl_high_priority(self, crawl_config: Dict[str, Any]):
    """
    高优先级采集任务
    
    适用于: 实时数据、用户手动触发
    """
    task_id = self.request.id
    _update_task_status(task_id, "running", 0, "高优先级采集开始")
    
    try:
        result = _execute_crawl(crawl_config, task_id)
        _update_task_status(task_id, "completed", 100, "采集完成")
        return result
    except SoftTimeLimitExceeded:
        _update_task_status(task_id, "timeout", 0, "任务超时")
        # 保存断点信息，支持续传
        _save_checkpoint(task_id, crawl_config)
        raise
    except Exception as exc:
        _update_task_status(task_id, "failed", 0, str(exc))
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
)
def crawl_normal_priority(self, crawl_config: Dict[str, Any]):
    """
    普通优先级采集任务
    
    适用于: 定时采集、批量采集
    """
    task_id = self.request.id
    _update_task_status(task_id, "running", 0, "普通优先级采集开始")
    
    try:
        result = _execute_crawl(crawl_config, task_id)
        _update_task_status(task_id, "completed", 100, "采集完成")
        return result
    except SoftTimeLimitExceeded:
        _update_task_status(task_id, "timeout", 0, "任务超时")
        _save_checkpoint(task_id, crawl_config)
        raise
    except Exception as exc:
        _update_task_status(task_id, "failed", 0, str(exc))
        raise self.retry(exc=exc, countdown=120 * (self.request.retries + 1))


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    acks_late=True,
)
def crawl_low_priority(self, crawl_config: Dict[str, Any]):
    """
    低优先级采集任务
    
    适用于: 历史数据回填、后台同步
    """
    task_id = self.request.id
    _update_task_status(task_id, "running", 0, "低优先级采集开始")
    
    try:
        result = _execute_crawl(crawl_config, task_id)
        _update_task_status(task_id, "completed", 100, "采集完成")
        return result
    except Exception as exc:
        _update_task_status(task_id, "failed", 0, str(exc))
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def crawl_website(self, crawl_config: Dict[str, Any]):
    """
    网页爬取任务

    Args:
        crawl_config: {
            "url": "https://...",
            "selectors": {"title": "h1", "content": "div.content"},
            "container_selector": "div.item",
            "item_selectors": {"title": "h3", "link": "a::attr(href)"},
            "use_scrapling": false,
            "stealthy": false,
            "priority": "normal"  # high/normal/low
        }
    """
    task_id = self.request.id
    _update_task_status(task_id, "running", 0, "网页爬取开始")

    try:
        from crawlers.base import BaseCrawler, CrawlResult

        # 根据配置选择是否启用 Scrapling
        use_scrapling = crawl_config.get("use_scrapling", False)
        stealthy = crawl_config.get("stealthy", False)

        class DynamicCrawler(BaseCrawler):
            async def crawl(self, **kwargs):
                config = kwargs.get("crawl_config", {})
                url = config.get("url", "")

                if use_scrapling or stealthy:
                    # 使用 Scrapling
                    result = await self.fetch_with_scrapling(
                        url=url,
                        selectors=config.get("selectors"),
                        container_selector=config.get("container_selector"),
                        item_selectors=config.get("item_selectors"),
                        stealthy=stealthy,
                    )
                    if result:
                        data = result.get("data", [result.get("data", {})] if result.get("type") == "dict" else result.get("data", []))
                        return CrawlResult(
                            success=True,
                            data=data if isinstance(data, list) else [data],
                            message="Scrapling 爬取成功",
                            source=url,
                        )

                # 使用 httpx
                html = await self.fetch_auto(url)
                if html:
                    return CrawlResult(
                        success=True,
                        data=[{"raw_html": html[:5000]}],  # 限制大小
                        message="httpx 爬取成功",
                        source=url,
                    )

                return CrawlResult(
                    success=False,
                    data=[],
                    message="爬取失败",
                    source=url,
                )

        crawler = DynamicCrawler(
            name=f"web_crawl_{task_id[:8]}",
            enable_scrapling=use_scrapling,
        )
        result = _run_async(crawler.run(crawl_config=crawl_config))

        _update_task_status(task_id, "completed", 100, "爬取完成")
        return result.to_dict()

    except SoftTimeLimitExceeded:
        _update_task_status(task_id, "timeout", 0, "爬取超时")
        raise
    except Exception as exc:
        _update_task_status(task_id, "failed", 0, str(exc))
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def crawl_api_task(self, api_config: Dict[str, Any]):
    """
    API 采集任务

    Args:
        api_config: {
            "url": "https://api.example.com/data",
            "method": "GET",
            "params": {"key": "value"},
            "headers": {"Authorization": "Bearer xxx"},
            "data_path": "results.data",  # JSON 响应中数据的路径
            "pagination": {
                "type": "page",  # page / cursor / offset
                "page_param": "page",
                "max_pages": 10,
            }
        }
    """
    task_id = self.request.id
    _update_task_status(task_id, "running", 0, "API 采集开始")

    try:
        import httpx

        url = api_config.get("url", "")
        method = api_config.get("method", "GET").upper()
        params = api_config.get("params", {})
        headers = api_config.get("headers", {})
        data_path = api_config.get("data_path", "")
        pagination = api_config.get("pagination")

        all_data = []
        page = 1
        max_pages = pagination.get("max_pages", 1) if pagination else 1

        while page <= max_pages:
            # 设置分页参数
            request_params = dict(params)
            if pagination and pagination.get("type") == "page":
                request_params[pagination.get("page_param", "page")] = page

            _update_task_status(
                task_id, "running",
                progress=(page / max_pages) * 100,
                message=f"API 采集中 (第 {page}/{max_pages} 页)"
            )

            async def _fetch():
                async with httpx.AsyncClient(timeout=30) as client:
                    if method == "GET":
                        resp = await client.get(url, params=request_params, headers=headers)
                    else:
                        resp = await client.post(url, json=request_params, headers=headers)
                    resp.raise_for_status()
                    return resp.json()

            result = _run_async(_fetch())

            # 提取数据
            if data_path:
                for key in data_path.split("."):
                    result = result.get(key, {})
                if isinstance(result, list):
                    all_data.extend(result)
                elif result:
                    all_data.append(result)
            else:
                if isinstance(result, list):
                    all_data.extend(result)
                else:
                    all_data.append(result)

            # 检查是否还有下一页
            if not pagination or not result:
                break
            page += 1
            time.sleep(0.5)  # 请求间隔

        _update_task_status(task_id, "completed", 100, f"API 采集完成，共 {len(all_data)} 条")
        return {
            "status": "success",
            "task_id": task_id,
            "count": len(all_data),
            "data": all_data[:1000],  # 限制返回量
        }

    except Exception as exc:
        _update_task_status(task_id, "failed", 0, str(exc))
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def crawl_batch(self, tasks_config: List[Dict[str, Any]]):
    """
    批量采集任务

    Args:
        tasks_config: [
            {"type": "api", "config": {...}},
            {"type": "web", "config": {...}},
        ]
    """
    task_id = self.request.id
    total = len(tasks_config)
    _update_task_status(task_id, "running", 0, f"批量采集开始，共 {total} 个子任务")

    results = []
    for i, task_config in enumerate(tasks_config):
        task_type = task_config.get("type", "api")
        config = task_config.get("config", {})

        _update_task_status(
            task_id, "running",
            progress=((i + 1) / total) * 100,
            message=f"批量采集中 ({i + 1}/{total})"
        )

        try:
            if task_type == "api":
                sub_result = crawl_api_task(config)
            elif task_type == "web":
                sub_result = crawl_website(config)
            else:
                sub_result = {"status": "error", "message": f"未知任务类型: {task_type}"}

            results.append({"index": i, "type": task_type, "result": sub_result, "success": True})
        except Exception as e:
            results.append({"index": i, "type": task_type, "error": str(e), "success": False})

    success_count = sum(1 for r in results if r.get("success"))
    _update_task_status(
        task_id, "completed", 100,
        f"批量采集完成，成功 {success_count}/{total}"
    )

    return {
        "status": "success",
        "task_id": task_id,
        "total": total,
        "success_count": success_count,
        "fail_count": total - success_count,
        "results": results,
    }


@shared_task(
    bind=True,
    max_retries=2,
)
def process_local_file(self, file_path: str, file_config: Dict[str, Any] = None):
    """
    处理本地文件任务

    Args:
        file_path: 文件路径
        file_config: {
            "file_type": "csv",  # csv / excel / json / parquet
            "encoding": "utf-8",
            "delimiter": ",",
            "sheet_name": 0,
            "max_rows": 10000,
            "preview_rows": 100,
        }
    """
    task_id = self.request.id
    config = file_config or {}
    _update_task_status(task_id, "running", 0, f"文件处理开始: {file_path}")

    try:
        from crawlers.utils.file_parser import FileParser
        parser = FileParser()
        result = parser.parse_file(
            file_path=file_path,
            file_type=config.get("file_type"),
            encoding=config.get("encoding"),
            delimiter=config.get("delimiter", ","),
            sheet_name=config.get("sheet_name", 0),
            max_rows=config.get("max_rows", 10000),
            preview_rows=config.get("preview_rows", 100),
        )

        _update_task_status(task_id, "completed", 100, f"文件处理完成，共 {result.get('row_count', 0)} 行")
        return result

    except Exception as exc:
        _update_task_status(task_id, "failed", 0, str(exc))
        raise self.retry(exc=exc, countdown=30)


# ==================== 辅助任务 ====================

@shared_task
def cleanup_stale_tasks():
    """清理过期的任务状态"""
    try:
        from api.celery_app import celery_app
        redis_client = celery_app.backend.client if hasattr(celery_app.backend, 'client') else None
        if redis_client:
            # 清理超过 24 小时的任务状态
            pattern = "crawl_status:*"
            keys = redis_client.keys(pattern)
            cleaned = 0
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode()
                ttl = redis_client.ttl(key)
                if ttl == -1:  # 没有过期时间的 key
                    redis_client.delete(key)
                    cleaned += 1
            logger.info(f"清理了 {cleaned} 个过期任务状态")
            return {"cleaned": cleaned}
    except Exception as e:
        logger.error(f"清理任务失败: {e}")
        return {"error": str(e)}


@shared_task
def get_crawl_task_status(task_id: str):
    """获取采集任务状态"""
    try:
        from api.celery_app import celery_app
        redis_client = celery_app.backend.client if hasattr(celery_app.backend, 'client') else None
        if redis_client:
            status_data = redis_client.get(f"crawl_status:{task_id}")
            if status_data:
                return json.loads(status_data)
    except Exception:
        pass
    return {"task_id": task_id, "status": "unknown"}


# ==================== 内部实现 ====================

def _execute_crawl(crawl_config: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    """执行采集任务（内部实现）"""
    source_type = crawl_config.get("source_type", "api")
    
    if source_type == "api":
        result = crawl_api_task(crawl_config)
    elif source_type == "web":
        result = crawl_website(crawl_config)
    elif source_type == "local":
        result = process_local_file(
            crawl_config.get("file_path", ""),
            crawl_config
        )
    else:
        raise ValueError(f"未知的采集类型: {source_type}")
    
    return result


def _save_checkpoint(task_id: str, crawl_config: Dict[str, Any]):
    """保存断点信息（用于断点续传）"""
    try:
        from api.celery_app import celery_app
        redis_client = celery_app.backend.client if hasattr(celery_app.backend, 'client') else None
        if redis_client:
            checkpoint = {
                "task_id": task_id,
                "config": crawl_config,
                "checkpoint_at": datetime.now().isoformat(),
            }
            redis_client.setex(
                f"checkpoint:{task_id}",
                3600 * 48,  # 48小时过期
                json.dumps(checkpoint, ensure_ascii=False)
            )
            logger.info(f"断点已保存: {task_id}")
    except Exception as e:
        logger.warning(f"保存断点失败: {e}")


def _load_checkpoint(task_id: str) -> Optional[Dict[str, Any]]:
    """加载断点信息"""
    try:
        from api.celery_app import celery_app
        redis_client = celery_app.backend.client if hasattr(celery_app.backend, 'client') else None
        if redis_client:
            data = redis_client.get(f"checkpoint:{task_id}")
            if data:
                return json.loads(data)
    except Exception:
        pass
    return None
