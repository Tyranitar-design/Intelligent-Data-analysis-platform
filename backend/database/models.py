# -*- coding: utf-8 -*-
"""
数据库模型 - 统一的数据库操作层
"""
import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _parse_sqlite_path(url: str) -> Optional[Path]:
    """从 sqlite URL 解析文件路径；非 sqlite 或无法解析时返回 None。

    统一配置源的底层实现：让本模块与 SQLAlchemy 引擎使用同一份
    ``DATABASE_URL``，避免"数据浏览走一个库、采集写入走另一个库"。
    """
    url = (url or "").strip()
    if not url.startswith("sqlite") or ":///" not in url:
        return None
    raw = url.split(":///", 1)[1]
    # sqlite:////abs/path → raw = "/abs/path"；sqlite:///D:/x → raw = "D:/x"
    if raw.startswith("/") and len(raw) > 2 and raw[2] == ":":
        raw = raw[1:]  # "/D:/x" → "D:/x"
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _database_url_from_env_file() -> Optional[str]:
    """读取 backend/.env 中的 DATABASE_URL（单键轻量解析，不引依赖）。"""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return None
    try:
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == "DATABASE_URL":
                return value.strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def resolve_default_db_path() -> Path:
    """解析默认数据库文件路径（统一配置源）。

    优先级：
        1. 环境变量 ``DATABASE_URL``（测试隔离 / 容器部署入口）
        2. ``backend/.env`` 的 ``DATABASE_URL``（本机开发）
        3. 历史默认 ``backend/data_platform.db``
    """
    for url in (os.environ.get("DATABASE_URL"), _database_url_from_env_file()):
        parsed = _parse_sqlite_path(url or "")
        if parsed is not None:
            return parsed
    return Path(__file__).parent.parent / "data_platform.db"


class Database:
    """统一数据库管理器"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = resolve_default_db_path()

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self.get_connection()

        # 1. 爬虫记录表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crawl_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                category TEXT,
                keyword TEXT,
                page INTEGER DEFAULT 1,
                count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'completed',
                error_msg TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. 电商商品表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ecom_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE,
                title TEXT,
                brand TEXT,
                price REAL,
                original_price REAL,
                sales INTEGER,
                rating REAL,
                review_count INTEGER,
                comments INTEGER,
                shop TEXT,
                location TEXT,
                tags TEXT,
                platform TEXT NOT NULL,
                keyword TEXT,
                source_record_id INTEGER,
                detail_url TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_record_id) REFERENCES crawl_records(id)
            )
        """)

        # 3. 财经数据表（股票）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                amount REAL,
                platform TEXT DEFAULT 'eastmoney',
                source_record_id INTEGER,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_record_id) REFERENCES crawl_records(id),
                UNIQUE(symbol, date)
            )
        """)

        # 4. 新闻数据表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                source TEXT,
                category TEXT,
                url TEXT,
                publish_time TEXT,
                platform TEXT,
                source_record_id INTEGER,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_record_id) REFERENCES crawl_records(id)
            )
        """)

        # 5. 能源数据表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS energy_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT,
                region TEXT,
                value REAL,
                unit TEXT,
                date TEXT,
                data_type TEXT,
                source_record_id INTEGER,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_record_id) REFERENCES crawl_records(id)
            )
        """)

        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ecom_platform ON ecom_products(platform)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ecom_brand ON ecom_products(brand)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ecom_keyword ON ecom_products(keyword)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_symbol ON stock_data(symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_data(date)")

        conn.commit()
        conn.close()

    # ==================== 爬虫记录 ====================

    def save_crawl_record(self, source: str, category: str = None,
                          keyword: str = None, page: int = 1,
                          count: int = 0, status: str = 'completed',
                          error_msg: str = None) -> int:
        """保存爬虫记录"""
        conn = self.get_connection()
        cursor = conn.execute(
            """INSERT INTO crawl_records (source, category, keyword, page, count, status, error_msg)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (source, category, keyword, page, count, status, error_msg)
        )
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id

    def get_crawl_records(self, source: str = None, limit: int = 50) -> List[Dict]:
        """获取爬虫记录"""
        conn = self.get_connection()
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
        return [dict(row) for row in rows]

    # ==================== 电商数据 ====================

    def save_ecom_products(self, products: List[Dict], platform: str,
                           source_record_id: int = None, keyword: str = None) -> int:
        """批量保存电商商品"""
        if not products:
            return 0

        conn = self.get_connection()
        count = 0

        for p in products:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO ecom_products
                    (product_id, title, brand, price, original_price, sales, rating,
                     review_count, comments, shop, location, tags, platform, keyword,
                     detail_url, source_record_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p.get('id'),
                    p.get('title'),
                    p.get('brand'),
                    p.get('price'),
                    p.get('original_price'),
                    p.get('sales'),
                    p.get('rating'),
                    p.get('review_count'),
                    p.get('comments'),
                    p.get('shop'),
                    p.get('location'),
                    json.dumps(p.get('tags', []), ensure_ascii=False) if p.get('tags') else None,
                    platform,
                    keyword or p.get('keyword'),
                    p.get('detail_url'),
                    source_record_id
                ))
                count += 1
            except Exception:
                continue

        conn.commit()
        conn.close()
        return count

    def get_ecom_products(self, platform: str = None, brand: str = None,
                           keyword: str = None, limit: int = 100) -> List[Dict]:
        """获取电商商品"""
        conn = self.get_connection()
        query = "SELECT * FROM ecom_products WHERE 1=1"
        params = []

        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if brand:
            query += " AND brand = ?"
            params.append(brand)
        if keyword:
            query += " AND (keyword = ? OR title LIKE ?)"
            params.extend([keyword, f'%{keyword}%'])

        query += " ORDER BY crawled_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        products = []
        for row in rows:
            p = dict(row)
            if p.get('tags'):
                try:
                    p['tags'] = json.loads(p['tags'])
                except:
                    p['tags'] = []
            products.append(p)

        return products

    def get_ecom_stats(self) -> Dict[str, Any]:
        """获取电商数据统计"""
        conn = self.get_connection()

        # 总数统计
        total = conn.execute("SELECT COUNT(*) as c FROM ecom_products").fetchone()['c']

        # 按平台统计
        by_platform = {}
        rows = conn.execute("""
            SELECT platform, COUNT(*) as c, AVG(price) as avg_price
            FROM ecom_products GROUP BY platform
        """).fetchall()
        for row in rows:
            by_platform[row['platform']] = {
                'count': row['c'],
                'avg_price': round(row['avg_price'], 2) if row['avg_price'] else 0
            }

        # 品牌统计
        top_brands = conn.execute("""
            SELECT brand, COUNT(*) as c FROM ecom_products
            WHERE brand IS NOT NULL GROUP BY brand ORDER BY c DESC LIMIT 10
        """).fetchall()

        conn.close()

        return {
            'total': total,
            'by_platform': by_platform,
            'top_brands': [dict(row) for row in top_brands]
        }

    # ==================== 股票数据 ====================

    def save_stock_data(self, records: List[Dict], platform: str = 'eastmoney',
                         source_record_id: int = None) -> int:
        """保存股票数据"""
        if not records:
            return 0

        conn = self.get_connection()
        count = 0

        for r in records:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO stock_data
                    (symbol, name, date, open, high, low, close, volume, amount, platform, source_record_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r.get('symbol'),
                    r.get('name'),
                    r.get('date'),
                    r.get('open'),
                    r.get('high'),
                    r.get('low'),
                    r.get('close'),
                    r.get('volume'),
                    r.get('amount'),
                    platform,
                    source_record_id
                ))
                count += 1
            except Exception:
                continue

        conn.commit()
        conn.close()
        return count

    def get_stock_data(self, symbol: str = None, start_date: str = None,
                        end_date: str = None, limit: int = 500) -> List[Dict]:
        """获取股票数据"""
        conn = self.get_connection()
        query = "SELECT * FROM stock_data WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ==================== 新闻数据 ====================

    def save_news(self, news_list: List[Dict], platform: str = 'netease',
                   source_record_id: int = None) -> int:
        """保存新闻"""
        if not news_list:
            return 0

        conn = self.get_connection()
        count = 0

        for n in news_list:
            try:
                conn.execute("""
                    INSERT INTO news_data (title, content, source, category, url, publish_time, platform, source_record_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    n.get('title'),
                    n.get('content'),
                    n.get('source'),
                    n.get('category'),
                    n.get('url'),
                    n.get('publish_time'),
                    platform,
                    source_record_id
                ))
                count += 1
            except Exception:
                continue

        conn.commit()
        conn.close()
        return count

    def get_news(self, category: str = None, keyword: str = None, limit: int = 50) -> List[Dict]:
        """获取新闻"""
        conn = self.get_connection()
        query = "SELECT * FROM news_data WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if keyword:
            query += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f'%{keyword}%', f'%{keyword}%'])

        query += " ORDER BY publish_time DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ==================== 能源数据 ====================

    def save_energy_data(self, records: List[Dict], source_record_id: int = None) -> int:
        """保存能源数据"""
        if not records:
            return 0

        conn = self.get_connection()
        count = 0

        for r in records:
            try:
                conn.execute("""
                    INSERT INTO energy_data (company, region, value, unit, date, data_type, source_record_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    r.get('company'),
                    r.get('region'),
                    r.get('value'),
                    r.get('unit'),
                    r.get('date'),
                    r.get('data_type'),
                    source_record_id
                ))
                count += 1
            except Exception:
                continue

        conn.commit()
        conn.close()
        return count

    def get_energy_data(self, company: str = None, start_date: str = None, limit: int = 100) -> List[Dict]:
        """获取能源数据"""
        conn = self.get_connection()
        query = "SELECT * FROM energy_data WHERE 1=1"
        params = []

        if company:
            query += " AND company = ?"
            params.append(company)
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计"""
        conn = self.get_connection()

        stats = {}

        # 各表记录数
        tables = ['ecom_products', 'stock_data', 'news_data', 'energy_data', 'crawl_records']
        for table in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()['c']
                stats[table] = count
            except:
                stats[table] = 0

        conn.close()
        return stats
