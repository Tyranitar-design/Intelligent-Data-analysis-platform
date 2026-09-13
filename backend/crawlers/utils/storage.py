# -*- coding: utf-8 -*-
"""
数据存储模块
"""
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional


class DataStorage:
    """数据存储管理器"""

    def __init__(self, data_dir: str = None, db_path: str = None):
        if data_dir is None:
            data_dir = "data/raw"
        if db_path is None:
            db_path = "data/crawlers.db"

        self.data_dir = Path(data_dir)
        self.db_path = Path(db_path)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crawl_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                category TEXT,
                count INTEGER,
                filepath TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS crawl_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                category TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def save(self, source: str, data: List[Dict], category: str = None) -> str:
        """
        保存爬取结果

        Args:
            source: 数据源名称
            data: 爬取的数据
            category: 分类

        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source}_{category or 'default'}_{timestamp}.json"
        filepath = self.data_dir / filename

        # 保存到 JSON 文件
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 记录到数据库
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO crawl_records (source, category, count, filepath) VALUES (?, ?, ?, ?)",
            (source, category, len(data), str(filepath))
        )
        conn.commit()
        conn.close()

        return str(filepath)

    def save_batch(self, source: str, data: List[Dict], batch_size: int = 1000):
        """
        批量保存大数据

        Args:
            source: 数据源名称
            data: 数据列表
            batch_size: 每批大小
        """
        total = len(data)
        for i in range(0, total, batch_size):
            batch = data[i:i + batch_size]
            self.save(source, batch, category=f"batch_{i // batch_size}")

    def get_history(self, source: str = None, limit: int = 10) -> List[Dict]:
        """获取爬取历史"""
        conn = sqlite3.connect(str(self.db_path))

        if source:
            rows = conn.execute(
                "SELECT * FROM crawl_records WHERE source = ? ORDER BY created_at DESC LIMIT ?",
                (source, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM crawl_records ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

        conn.close()

        columns = ["id", "source", "category", "count", "filepath", "created_at"]
        return [dict(zip(columns, row)) for row in rows]

    def load_data(self, filepath: str) -> List[Dict]:
        """从文件加载数据"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def delete_old_records(self, days: int = 30):
        """删除指定天数前的记录"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "DELETE FROM crawl_records WHERE created_at < datetime('now', ?)",
            (f"-{days} days",)
        )
        conn.commit()
        conn.close()
