"""
应用配置
=======

使用 Pydantic Settings 管理配置
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用信息
    APP_NAME: str = "智能数据分析平台"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = Field(default=False, description="调试模式")
    
    # 安全
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="JWT 密钥")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 数据库
    DATABASE_URL: str = Field(
        default="sqlite:///./data_platform.db",
        description="数据库连接 URL (默认 SQLite, 生产环境用 PostgreSQL)"
    )
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis 连接 URL"
    )
    
    # MinIO
    MINIO_ENDPOINT: str = Field(default="localhost:9000", description="MinIO 地址")
    MINIO_ACCESS_KEY: str = Field(default="admin", description="MinIO 访问密钥")
    MINIO_SECRET_KEY: str = Field(default="admin123456", description="MinIO 秘密密钥")
    MINIO_BUCKET_NAME: str = Field(default="data-platform", description="MinIO 桶名")
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", description="Celery Broker")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", description="Celery 结果后端")

    # 调度器（采集定时规则的检查间隔）
    SCHEDULE_TICK_SECONDS: float = Field(
        default=15.0, description="采集调度循环的检查间隔（秒）"
    )
    
    # 爬虫
    CRAWL_MAX_CONCURRENT: int = Field(default=100, description="最大并发爬取数")
    CRAWL_DEFAULT_DELAY: float = Field(default=1.0, description="默认请求延迟(秒)")
    CRAWL_MAX_RETRIES: int = Field(default=3, description="最大重试次数")
    CRAWL_TIMEOUT: int = Field(default=30, description="请求超时(秒)")
    
    # JustOneAPI
    JUSTONE_API_TOKEN: str = Field(default="", description="JustOneAPI Token")
    
    # ML
    ML_DEFAULT_TEST_SIZE: float = Field(default=0.2, description="默认测试集比例")
    ML_DEFAULT_RANDOM_STATE: int = Field(default=42, description="默认随机种子")
    ML_MODEL_DIR: str = Field(default="./data/models", description="模型保存目录")
    
    # 日志
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(default="json", description="日志格式")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
settings = Settings()
