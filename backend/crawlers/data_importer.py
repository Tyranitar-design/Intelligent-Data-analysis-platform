# -*- coding: utf-8 -*-
"""
多格式数据导入模块 - Phase 4.6.2

支持格式：
- CSV
- Excel (.xlsx, .xls)
- JSON
- Parquet
- HTML 表格

统一输出：结构化数据（字段列表 + 行数据）
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    data: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    message: str = ""
    error: Optional[str] = None
    row_count: int = 0
    column_count: int = 0
    source_type: str = ""


class DataImporter:
    """多格式数据导入器"""

    SUPPORTED_FORMATS = {
        "csv": [".csv"],
        "excel": [".xlsx", ".xls"],
        "json": [".json"],
        "parquet": [".parquet"],
        "html": [".html", ".htm"],
    }

    def detect_format(self, file_path: str) -> Optional[str]:
        """自动检测文件格式"""
        ext = Path(file_path).suffix.lower()
        for fmt, exts in self.SUPPORTED_FORMATS.items():
            if ext in exts:
                return fmt
        return None

    def import_file(self, file_path: str, file_type: str = None, **kwargs) -> ImportResult:
        """
        导入文件

        Args:
            file_path: 文件路径
            file_type: 指定格式（自动检测时可不传）
            **kwargs: 各格式特定参数
                - csv: encoding, delimiter, skip_rows
                - excel: sheet_name, skip_rows
                - json: orient
                - html: table_index
                - parquet: columns
        """
        path = Path(file_path)
        if not path.exists():
            return ImportResult(success=False, error=f"文件不存在: {file_path}")

        fmt = file_type or self.detect_format(file_path)
        if not fmt:
            return ImportResult(success=False, error=f"不支持的文件格式: {path.suffix}")

        try:
            if fmt == "csv":
                return self._import_csv(file_path, **kwargs)
            elif fmt == "excel":
                return self._import_excel(file_path, **kwargs)
            elif fmt == "json":
                return self._import_json(file_path, **kwargs)
            elif fmt == "parquet":
                return self._import_parquet(file_path, **kwargs)
            elif fmt == "html":
                return self._import_html(file_path, **kwargs)
            else:
                return ImportResult(success=False, error=f"未实现的格式: {fmt}")
        except Exception as e:
            logger.error(f"导入失败 [{fmt}]: {e}")
            return ImportResult(success=False, error=str(e))

    def _import_csv(self, file_path: str, encoding: str = None, delimiter: str = ",",
                    skip_rows: int = 0, max_rows: int = 100000) -> ImportResult:
        """导入 CSV"""
        try:
            df = pd.read_csv(
                file_path,
                encoding=encoding or "utf-8-sig",
                delimiter=delimiter,
                skiprows=skip_rows,
                nrows=max_rows,
                low_memory=False,
            )
            return self._dataframe_to_result(df, "csv")
        except UnicodeDecodeError:
            # 尝试其他编码
            df = pd.read_csv(
                file_path,
                encoding="gbk",
                delimiter=delimiter,
                skiprows=skip_rows,
                nrows=max_rows,
                low_memory=False,
            )
            return self._dataframe_to_result(df, "csv")

    def _import_excel(self, file_path: str, sheet_name=None, skip_rows: int = 0,
                      max_rows: int = 100000) -> ImportResult:
        """导入 Excel"""
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name or 0,
            skiprows=skip_rows,
            nrows=max_rows,
            engine="openpyxl",
        )
        return self._dataframe_to_result(df, "excel")

    def _import_json(self, file_path: str, orient: str = "records") -> ImportResult:
        """导入 JSON"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # 尝试找到列表字段
            list_fields = [k for k, v in data.items() if isinstance(v, list)]
            if list_fields:
                df = pd.DataFrame(data[list_fields[0]])
            else:
                df = pd.DataFrame([data])
        else:
            return ImportResult(success=False, error="JSON 格式不支持")

        return self._dataframe_to_result(df, "json")

    def _import_parquet(self, file_path: str, columns: List[str] = None) -> ImportResult:
        """导入 Parquet"""
        df = pd.read_parquet(file_path, columns=columns)
        return self._dataframe_to_result(df, "parquet")

    def _import_html(self, file_path: str, table_index: int = 0) -> ImportResult:
        """导入 HTML 表格"""
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "lxml")
        tables = soup.find_all("table")

        if not tables:
            return ImportResult(success=False, error="HTML 中未找到表格")

        if table_index >= len(tables):
            return ImportResult(success=False, error=f"表格索引越界，共 {len(tables)} 个表格")

        # 用 pandas 解析表格
        dfs = pd.read_html(str(tables[table_index]))
        if not dfs:
            return ImportResult(success=False, error="无法解析表格")

        return self._dataframe_to_result(dfs[0], "html")

    def _dataframe_to_result(self, df: pd.DataFrame, source_type: str) -> ImportResult:
        """DataFrame 转统一结果"""
        # 处理 NaN
        df = df.where(pd.notnull(df), None)

        # 限制数据量
        if len(df) > 100000:
            df = df.head(100000)

        columns = list(df.columns)
        data = df.to_dict(orient="records")

        return ImportResult(
            success=True,
            data=data,
            columns=columns,
            message=f"导入成功: {len(data)} 行 × {len(columns)} 列",
            row_count=len(data),
            column_count=len(columns),
            source_type=source_type,
        )

    def import_from_text(self, text: str, format_hint: str = "csv", **kwargs) -> ImportResult:
        """
        从文本内容导入（用于粘贴/直接输入）

        Args:
            text: 文本内容
            format_hint: 格式提示 (csv/json)
        """
        try:
            if format_hint == "csv":
                from io import StringIO
                df = pd.read_csv(StringIO(text), **kwargs)
                return self._dataframe_to_result(df, "csv")
            elif format_hint == "json":
                data = json.loads(text)
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame([data])
                return self._dataframe_to_result(df, "json")
            else:
                return ImportResult(success=False, error=f"不支持的文本格式: {format_hint}")
        except Exception as e:
            return ImportResult(success=False, error=str(e))
