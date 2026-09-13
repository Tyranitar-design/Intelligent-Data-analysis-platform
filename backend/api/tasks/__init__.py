"""
任务模块
=======
"""
from api.tasks.crawl_tasks import crawl_website, crawl_api_task, process_local_file
from api.tasks.analysis_tasks import run_eda_analysis, train_ml_model, run_data_mining

__all__ = [
    "crawl_website",
    "crawl_api_task",
    "process_local_file",
    "run_eda_analysis",
    "train_ml_model",
    "run_data_mining",
]
