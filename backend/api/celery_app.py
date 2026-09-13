# -*- coding: utf-8 -*-
"""
Celery 应用配置 v2.0
====================

增强版: 完整的分布式任务队列配置
- 优先级队列 (crawl-high / crawl-normal / crawl-low)
- 任务状态追踪
- 断点续传
- 自动重试策略
"""
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure, task_retry
import logging
import time

logger = logging.getLogger(__name__)

# 创建 Celery 应用
celery_app = Celery(
    "data_platform",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=[
        "api.tasks.crawl_tasks",
        "api.tasks.analysis_tasks",
    ],
)

# Celery 配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    
    # 任务执行
    task_track_started=True,
    task_time_limit=3600,         # 1小时硬超时
    task_soft_time_limit=3000,    # 50分钟软超时
    
    # 结果存储
    result_expires=3600 * 24,     # 24小时过期
    result_backend="redis://localhost:6379/0",
    
    # 并发设置
    worker_prefetch_multiplier=1,  # 每次只预取1个任务，确保公平调度
    worker_max_tasks_per_child=500,  # 每个 Worker 子进程最多处理 500 个任务后重启（防内存泄漏）
    worker_max_memory_per_child=300000,  # 300MB 内存限制
    
    # 任务路由 — 优先级队列
    task_routes={
        # 采集队列（按优先级）
        "api.tasks.crawl_tasks.crawl_high_priority": {"queue": "crawl-high"},
        "api.tasks.crawl_tasks.crawl_normal_priority": {"queue": "crawl-normal"},
        "api.tasks.crawl_tasks.crawl_low_priority": {"queue": "crawl-low"},
        "api.tasks.crawl_tasks.crawl_website": {"queue": "crawl-normal"},
        "api.tasks.crawl_tasks.crawl_api_task": {"queue": "crawl-normal"},
        "api.tasks.crawl_tasks.crawl_batch": {"queue": "crawl-low"},
        "api.tasks.crawl_tasks.process_local_file": {"queue": "crawl-normal"},
        
        # 分析队列
        "api.tasks.analysis_tasks.*": {"queue": "analysis"},
    },
    
    # 默认队列
    task_default_queue="default",
    
    # 队列定义（用于 celery -A celery_app inspect active_queues）
    task_queues={
        "crawl-high": {
            "exchange": "crawl",
            "routing_key": "crawl.high",
        },
        "crawl-normal": {
            "exchange": "crawl",
            "routing_key": "crawl.normal",
        },
        "crawl-low": {
            "exchange": "crawl",
            "routing_key": "crawl.low",
        },
        "analysis": {
            "exchange": "analysis",
            "routing_key": "analysis",
        },
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
    },
    
    # 定时任务
    beat_schedule={
        "cleanup-old-tasks": {
            "task": "api.tasks.crawl_tasks.cleanup_stale_tasks",
            "schedule": 3600 * 24,  # 每天清理
        },
    },
    
    # 任务结果扩展
    task_send_sent_event=True,
    task_queue_max_priority=10,  # 支持 0-10 优先级
)


# ==================== 信号处理 ====================

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extras):
    """任务开始前"""
    logger.info(f"▶️ 任务开始: {task.name}[{task_id}]")
    # 记录任务开始时间到 Redis（用于断点续传判断）
    try:
        from celery.result import AsyncResult
        redis_client = celery_app.backend.client if hasattr(celery_app.backend, 'client') else None
        if redis_client:
            redis_client.setex(
                f"task_start:{task_id}",
                3600 * 2,  # 2小时过期
                str(time.time())
            )
    except Exception:
        pass


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **extras):
    """任务结束后"""
    logger.info(f"✅ 任务结束: {task.name}[{task_id}] - 状态: {state}")


@task_failure.connect
def task_failure_handler(task_id, exception, traceback, **extras):
    """任务失败处理"""
    logger.error(f"❌ 任务失败: {task_id} - 异常: {exception}")


@task_retry.connect
def task_retry_handler(task_id, reason, **extras):
    """任务重试处理"""
    logger.warning(f"🔄 任务重试: {task_id} - 原因: {reason}")


if __name__ == "__main__":
    celery_app.start()
