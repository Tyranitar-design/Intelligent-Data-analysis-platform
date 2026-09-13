# -*- coding: utf-8 -*-
"""
数据浏览与导出 API - Phase 4.5

功能：
1. 列出所有数据表
2. 查询数据（分页 + 搜索 + 筛选 + 排序）
3. 获取表结构
4. 导出数据（CSV / Excel / JSON）
"""
import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database.models import Database

router = APIRouter()

# 初始化数据库连接
db = Database()


# ==================== 数据表管理 ====================

@router.get("/tables")
async def list_tables():
    """列出所有数据表"""
    conn = db.get_connection()

    # 获取所有表
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row["name"] for row in cursor.fetchall()]

    result = []
    for table_name in tables:
        # 获取表结构
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = []
        for row in cursor.fetchall():
            columns.append({
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(row["notnull"]),
                "default": row["dflt_value"],
                "pk": bool(row["pk"]),
            })

        # 获取记录数
        cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        count = cursor.fetchone()["count"]

        result.append({
            "name": table_name,
            "columns": columns,
            "count": count,
        })

    conn.close()

    return {
        "count": len(result),
        "tables": result,
    }


@router.get("/tables/{table_name}/schema")
async def get_table_schema(table_name: str):
    """获取表结构"""
    conn = db.get_connection()

    # 检查表是否存在
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,)
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"表不存在: {table_name}")

    # 获取表结构
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = []
    for row in cursor.fetchall():
        columns.append({
            "name": row["name"],
            "type": row["type"],
            "notnull": bool(row["notnull"]),
            "default": row["dflt_value"],
            "pk": bool(row["pk"]),
        })

    # 获取记录数
    cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}")
    count = cursor.fetchone()["count"]

    # 获取样本数据（前 3 条）
    cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 3")
    sample = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "name": table_name,
        "columns": columns,
        "count": count,
        "sample": sample,
    }


# ==================== 数据查询 ====================

@router.get("/tables/{table_name}/rows")
async def query_table(
    table_name: str,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=500, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort: Optional[str] = Query(None, description="排序字段"),
    order: str = Query("desc", description="排序方向: asc/desc"),
    filter_column: Optional[str] = Query(None, description="筛选列"),
    filter_value: Optional[str] = Query(None, description="筛选值"),
):
    """
    查询数据表（分页 + 搜索 + 筛选 + 排序）

    支持：
    - 分页: page + size
    - 搜索: search（在所有文本字段中搜索）
    - 筛选: filter_column + filter_value
    - 排序: sort + order
    """
    conn = db.get_connection()

    # 检查表是否存在
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,)
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"表不存在: {table_name}")

    # 获取列名
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row["name"] for row in cursor.fetchall()]

    # 构建查询
    where_clauses = []
    params = []

    # 搜索条件
    if search:
        # 在所有文本字段中搜索
        text_columns = [c for c in columns if c not in ["id", "created_at", "crawled_at", "source_record_id"]]
        search_conditions = []
        for col in text_columns:
            search_conditions.append(f"{col} LIKE ?")
            params.append(f"%{search}%")
        if search_conditions:
            where_clauses.append(f"({' OR '.join(search_conditions)})")

    # 筛选条件
    if filter_column and filter_value:
        if filter_column in columns:
            where_clauses.append(f"{filter_column} = ?")
            params.append(filter_value)

    # 构建 WHERE
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # 构建排序
    order_sql = ""
    if sort and sort in columns:
        order_direction = "DESC" if order.lower() == "desc" else "ASC"
        order_sql = f"ORDER BY {sort} {order_direction}"
    else:
        # 默认按时间倒序
        if "created_at" in columns:
            order_sql = "ORDER BY created_at DESC"
        elif "crawled_at" in columns:
            order_sql = "ORDER BY crawled_at DESC"
        elif "id" in columns:
            order_sql = "ORDER BY id DESC"

    # 获取总数
    count_sql = f"SELECT COUNT(*) as total FROM {table_name} {where_sql}"
    cursor = conn.execute(count_sql, params)
    total = cursor.fetchone()["total"]

    # 分页查询
    offset = (page - 1) * size
    query_sql = f"SELECT * FROM {table_name} {where_sql} {order_sql} LIMIT ? OFFSET ?"
    query_params = params + [size, offset]

    cursor = conn.execute(query_sql, query_params)
    rows = [dict(row) for row in cursor.fetchall()]

    conn.close()

    # 处理 JSON 字段
    for row in rows:
        for key, value in row.items():
            if isinstance(value, str) and value.startswith("["):
                try:
                    row[key] = json.loads(value)
                except:
                    pass

    return {
        "table": table_name,
        "page": page,
        "size": size,
        "total": total,
        "pages": (total + size - 1) // size,
        "count": len(rows),
        "columns": columns,
        "data": rows,
    }


# ==================== 数据导出 ====================

@router.get("/tables/{table_name}/export")
async def export_table(
    table_name: str,
    format: str = Query("csv", description="导出格式: csv/excel/json"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    filter_column: Optional[str] = Query(None, description="筛选列"),
    filter_value: Optional[str] = Query(None, description="筛选值"),
    max_rows: int = Query(10000, ge=1, le=50000, description="最大导出行数"),
):
    """
    导出数据表

    支持格式：
    - csv: CSV 文件
    - excel: Excel 文件
    - json: JSON 文件
    """
    conn = db.get_connection()

    # 检查表是否存在
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,)
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"表不存在: {table_name}")

    # 获取列名
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row["name"] for row in cursor.fetchall()]

    # 构建查询条件
    where_clauses = []
    params = []

    if search:
        text_columns = [c for c in columns if c not in ["id", "created_at", "crawled_at"]]
        search_conditions = []
        for col in text_columns:
            search_conditions.append(f"{col} LIKE ?")
            params.append(f"%{search}%")
        if search_conditions:
            where_clauses.append(f"({' OR '.join(search_conditions)})")

    if filter_column and filter_value:
        if filter_column in columns:
            where_clauses.append(f"{filter_column} = ?")
            params.append(filter_value)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # 查询数据
    query_sql = f"SELECT * FROM {table_name} {where_sql} LIMIT ?"
    query_params = params + [max_rows]

    cursor = conn.execute(query_sql, query_params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="无数据可导出")

    # 转换为 DataFrame
    df = pd.DataFrame(rows)

    # 创建临时文件
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format.lower() == "csv":
        filename = f"{table_name}_{timestamp}.csv"
        filepath = os.path.join(temp_dir, filename)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        media_type = "text/csv"
    elif format.lower() == "excel":
        filename = f"{table_name}_{timestamp}.xlsx"
        filepath = os.path.join(temp_dir, filename)
        df.to_excel(filepath, index=False, engine="openpyxl")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif format.lower() == "json":
        filename = f"{table_name}_{timestamp}.json"
        filepath = os.path.join(temp_dir, filename)
        df.to_json(filepath, orient="records", force_ascii=False, indent=2)
        media_type = "application/json"
    else:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {format}")

    return FileResponse(
        filepath,
        media_type=media_type,
        filename=filename,
    )


# ==================== 数据统计 ====================

@router.get("/tables/{table_name}/stats")
async def get_table_stats(table_name: str):
    """获取表统计信息"""
    conn = db.get_connection()

    # 检查表是否存在
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,)
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"表不存在: {table_name}")

    # 获取列名
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row["name"] for row in cursor.fetchall()]

    # 总数
    cursor = conn.execute(f"SELECT COUNT(*) as total FROM {table_name}")
    total = cursor.fetchone()["total"]

    # 时间范围
    stats = {
        "table": table_name,
        "total_records": total,
        "columns": columns,
    }

    if "created_at" in columns:
        cursor = conn.execute(
            f"SELECT MIN(created_at) as earliest, MAX(created_at) as latest FROM {table_name}"
        )
        row = cursor.fetchone()
        stats["time_range"] = {
            "earliest": row["earliest"],
            "latest": row["latest"],
        }

    if "crawled_at" in columns:
        cursor = conn.execute(
            f"SELECT MIN(crawled_at) as earliest, MAX(crawled_at) as latest FROM {table_name}"
        )
        row = cursor.fetchone()
        stats["crawl_time_range"] = {
            "earliest": row["earliest"],
            "latest": row["latest"],
        }

    # 按平台统计（如果有 platform 列）
    if "platform" in columns:
        cursor = conn.execute(
            f"SELECT platform, COUNT(*) as count FROM {table_name} GROUP BY platform ORDER BY count DESC"
        )
        stats["by_platform"] = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return stats


# ==================== 数据概览 ====================

@router.get("/overview")
async def get_data_overview():
    """获取数据概览"""
    conn = db.get_connection()

    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row["name"] for row in cursor.fetchall()]

    overview = {
        "total_tables": len(tables),
        "tables": [],
        "total_records": 0,
    }

    for table_name in tables:
        cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        count = cursor.fetchone()["count"]
        overview["total_records"] += count
        overview["tables"].append({
            "name": table_name,
            "count": count,
        })

    conn.close()
    return overview
