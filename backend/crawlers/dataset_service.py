# -*- coding: utf-8 -*-
"""
数据集服务 - 一键保存采集结果为数据集

功能：
1. 将智能采集/爬取结果保存为数据集
2. 自动创建数据表存储数据
3. 记录数据集元信息
4. 支持数据集列表查询
"""
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.models import Database

logger = logging.getLogger(__name__)


class DatasetService:
    """数据集服务"""

    def __init__(self, db: Database = None):
        self.db = db or Database()

    def save_dataset(self, name: str, description: str, columns: List[str],
                     data: List[Dict[str, Any]], source_url: str = None,
                     source_type: str = "crawl") -> Dict[str, Any]:
        """
        保存数据集

        Args:
            name: 数据集名称
            description: 数据集描述
            columns: 字段列表
            data: 数据行
            source_url: 数据来源 URL
            source_type: 来源类型 (crawl/import/manual)

        Returns:
            保存结果
        """
        if not data:
            return {"success": False, "error": "数据为空，无法保存"}

        # 生成安全的表名
        table_name = self._generate_table_name(name)

        try:
            conn = self.db.get_connection()

            # 1. 创建数据表
            self._create_data_table(conn, table_name, columns, data)

            # 2. 插入数据
            inserted = self._insert_data(conn, table_name, columns, data)

            # 3. 保存数据集元信息
            dataset_id = self._save_dataset_meta(conn, name, description,
                                                  table_name, columns, len(data),
                                                  source_url, source_type)

            conn.close()

            return {
                "success": True,
                "dataset_id": dataset_id,
                "name": name,
                "table_name": table_name,
                "row_count": inserted,
                "column_count": len(columns),
                "columns": columns,
                "message": f"数据集保存成功: {name} ({inserted} 行 × {len(columns)} 列)",
            }

        except Exception as e:
            logger.error(f"保存数据集失败: {e}")
            return {"success": False, "error": str(e)}

    def _generate_table_name(self, name: str) -> str:
        """生成安全的数据表名"""
        # 去掉特殊字符，转小写
        safe = re.sub(r'[^\w\u4e00-\u9fff]', '_', name).lower()
        safe = re.sub(r'_+', '_', safe).strip('_')
        # 加上时间戳避免冲突
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"dataset_{safe}_{timestamp}"

    def _create_data_table(self, conn, table_name: str, columns: List[str],
                           data: List[Dict]) -> None:
        """创建数据表"""
        # 推断字段类型
        column_defs = []
        for col in columns:
            col_type = self._infer_column_type(col, data)
            safe_col = re.sub(r'[^\w\u4e00-\u9fff]', '_', col)
            column_defs.append(f"\"{safe_col}\" {col_type}")

        create_sql = f"""
            CREATE TABLE IF NOT EXISTS "{table_name}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {', '.join(column_defs)},
                _source TEXT,
                _created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        conn.execute(create_sql)
        conn.commit()

    def _infer_column_type(self, column: str, data: List[Dict]) -> str:
        """推断字段类型"""
        # 采样前 100 条
        samples = []
        for row in data[:100]:
            val = row.get(column)
            if val is not None and val != "":
                samples.append(val)

        if not samples:
            return "TEXT"

        # 检查是否全是数字
        numeric_count = 0
        for val in samples:
            try:
                float(str(val))
                numeric_count += 1
            except:
                pass

        if numeric_count == len(samples):
            # 检查是否全是整数
            int_count = 0
            for val in samples:
                try:
                    int(float(str(val)))
                    int_count += 1
                except:
                    pass
            if int_count == len(samples):
                return "INTEGER"
            return "REAL"

        # 检查是否像日期
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}',
            r'^\d{4}/\d{2}/\d{2}',
            r'^\d{4}年',
        ]
        date_count = 0
        for val in samples:
            val_str = str(val)
            if any(re.match(p, val_str) for p in date_patterns):
                date_count += 1

        if date_count == len(samples):
            return "TEXT"  # SQLite 没有 DATE 类型

        return "TEXT"

    def _insert_data(self, conn, table_name: str, columns: List[str],
                     data: List[Dict]) -> int:
        """插入数据"""
        safe_columns = [re.sub(r'[^\w\u4e00-\u9fff]', '_', c) for c in columns]
        placeholders = ', '.join(['?' for _ in safe_columns])
        col_names = ', '.join([f'"{c}"' for c in safe_columns])

        insert_sql = f"""
            INSERT INTO "{table_name}" ({col_names}, _source)
            VALUES ({placeholders}, ?)
        """

        count = 0
        for row in data:
            values = []
            for col in columns:
                val = row.get(col)
                if val is None:
                    values.append(None)
                else:
                    values.append(str(val))
            values.append("smart_extract")

            try:
                conn.execute(insert_sql, values)
                count += 1
            except Exception as e:
                logger.warning(f"插入数据失败: {e}")

        conn.commit()
        return count

    def _save_dataset_meta(self, conn, name: str, description: str,
                           table_name: str, columns: List[str], row_count: int,
                           source_url: str, source_type: str) -> int:
        """保存数据集元信息"""
        # 列名已对齐当前 ORM 定义：schema 存列信息、size_bytes 存字节数、
        # dataset_type 标记内容类型、source_type 记录来源（NOT NULL）。
        cursor = conn.execute("""
            INSERT INTO datasets (name, description, dataset_type, table_name, source_type,
                                  row_count, column_count, schema, size_bytes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            description or "",
            "raw",
            table_name,
            source_type,
            row_count,
            len(columns),
            json.dumps(columns, ensure_ascii=False),
            0,
            datetime.now().isoformat(),
        ))
        conn.commit()
        return cursor.lastrowid

    def list_datasets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出所有数据集"""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT * FROM datasets ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()

        result = []
        for row in rows:
            r = dict(row)
            if r.get('schema'):
                try:
                    r['schema'] = json.loads(r['schema'])
                except (TypeError, ValueError):
                    pass
            result.append(r)
        return result

    def get_dataset_data(self, table_name: str, limit: int = 100) -> Dict[str, Any]:
        """获取数据集数据"""
        conn = self.db.get_connection()

        # 获取列名
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = [row['name'] for row in cursor.fetchall()]

        # 获取数据
        cursor = conn.execute(
            f"SELECT * FROM {table_name} LIMIT ?",
            (limit,)
        )
        rows = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            "table_name": table_name,
            "columns": columns,
            "row_count": len(rows),
            "data": rows,
        }
