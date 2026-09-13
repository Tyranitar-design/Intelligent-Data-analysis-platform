# -*- coding: utf-8 -*-
"""
文件解析器
=========

功能:
- CSV / Excel / JSON / Parquet 四种格式
- 大文件分块读取 + 流式处理
- 自动字段类型推断
- 编码自动检测
- 数据预览
"""
import csv
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FileParser:
    """多格式文件解析器"""
    
    # 支持的文件类型
    SUPPORTED_TYPES = {"csv", "excel", "json", "parquet"}
    
    # Excel 扩展名映射
    EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}
    
    def parse_file(
        self,
        file_path: str,
        file_type: str = None,
        encoding: str = None,
        delimiter: str = ",",
        sheet_name: Any = 0,
        skip_rows: int = 0,
        max_rows: int = 10000,
        preview_rows: int = 100,
    ) -> Dict[str, Any]:
        """
        解析文件
        
        Args:
            file_path: 文件路径
            file_type: 文件类型 (自动检测)
            encoding: 文件编码 (自动检测)
            delimiter: CSV 分隔符
            sheet_name: Excel Sheet
            skip_rows: 跳过行数
            max_rows: 最大读取行数
            preview_rows: 预览行数
            
        Returns:
            {
                "file_type": str,
                "row_count": int,
                "columns": List[str],
                "dtypes": Dict[str, str],
                "preview": List[Dict],
                "file_size": int,
                "encoding": str,
            }
        """
        # 检查文件存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 自动检测文件类型
        if file_type is None:
            file_type = self._detect_file_type(file_path)
        
        if file_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"不支持的文件类型: {file_type}，支持: {self.SUPPORTED_TYPES}")
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        
        # 自动检测编码
        if encoding is None:
            encoding = self._detect_encoding(file_path)
        
        # 按类型解析
        if file_type == "csv":
            return self._parse_csv(file_path, encoding, delimiter, skip_rows, max_rows, preview_rows, file_size)
        elif file_type == "excel":
            return self._parse_excel(file_path, sheet_name, skip_rows, max_rows, preview_rows, file_size)
        elif file_type == "json":
            return self._parse_json(file_path, encoding, max_rows, preview_rows, file_size)
        elif file_type == "parquet":
            return self._parse_parquet(file_path, max_rows, preview_rows, file_size)
    
    def _detect_file_type(self, file_path: str) -> str:
        """自动检测文件类型"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".csv":
            return "csv"
        elif ext in self.EXCEL_EXTENSIONS:
            return "excel"
        elif ext == ".json":
            return "json"
        elif ext == ".parquet" or ext == ".pq":
            return "parquet"
        else:
            # 尝试通过内容检测
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read(1000)
                    try:
                        json.loads(content)
                        return "json"
                    except json.JSONDecodeError:
                        pass
                    
                    # 检查是否有分隔符
                    if "," in content or "\t" in content:
                        return "csv"
            except Exception:
                pass
        
        return "csv"  # 默认 CSV
    
    def _detect_encoding(self, file_path: str) -> str:
        """自动检测文件编码"""
        try:
            import chardet
            with open(file_path, "rb") as f:
                raw = f.read(10000)
                result = chardet.detect(raw)
                encoding = result.get("encoding", "utf-8")
                confidence = result.get("confidence", 0)
                
                if confidence > 0.7:
                    logger.info(f"检测到编码: {encoding} (置信度: {confidence:.2f})")
                    return encoding
        except ImportError:
            logger.debug("chardet 未安装，使用默认编码 utf-8")
        except Exception as e:
            logger.warning(f"编码检测失败: {e}")
        
        return "utf-8"
    
    def _parse_csv(
        self, file_path: str, encoding: str, delimiter: str,
        skip_rows: int, max_rows: int, preview_rows: int, file_size: int,
    ) -> Dict[str, Any]:
        """解析 CSV 文件"""
        rows = []
        columns = []
        
        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                # 跳过行
                for _ in range(skip_rows):
                    next(reader, None)
                
                columns = reader.fieldnames or []
                row_count = 0
                
                for row in reader:
                    if row_count >= max_rows:
                        break
                    rows.append(dict(row))
                    row_count += 1
            
            # 类型推断
            dtypes = self._infer_dtypes(rows, columns)
            
            return {
                "file_type": "csv",
                "row_count": len(rows),
                "columns": columns,
                "dtypes": dtypes,
                "preview": rows[:preview_rows],
                "file_size": file_size,
                "encoding": encoding,
            }
            
        except Exception as e:
            raise ValueError(f"CSV 解析失败: {e}")
    
    def _parse_excel(
        self, file_path: str, sheet_name: Any,
        skip_rows: int, max_rows: int, preview_rows: int, file_size: int,
    ) -> Dict[str, Any]:
        """解析 Excel 文件"""
        try:
            import openpyxl
        except ImportError:
            raise ImportError("Excel 解析需要安装 openpyxl: pip install openpyxl")
        
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            
            # 获取 Sheet
            if isinstance(sheet_name, int):
                ws = wb.worksheets[sheet_name]
            else:
                ws = wb[sheet_name]
            
            rows = []
            columns = []
            row_count = 0
            
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i < skip_rows:
                    continue
                
                if i == skip_rows:
                    # 第一行作为列名
                    columns = [str(cell) if cell is not None else f"col_{j}" for j, cell in enumerate(row)]
                    continue
                
                if row_count >= max_rows:
                    break
                
                row_dict = {}
                for j, (col, val) in enumerate(zip(columns, row)):
                    row_dict[col] = val
                
                rows.append(row_dict)
                row_count += 1
            
            wb.close()
            
            dtypes = self._infer_dtypes(rows, columns)
            
            return {
                "file_type": "excel",
                "row_count": len(rows),
                "columns": columns,
                "dtypes": dtypes,
                "preview": rows[:preview_rows],
                "file_size": file_size,
                "encoding": "binary",
                "sheet_name": sheet_name,
            }
            
        except Exception as e:
            raise ValueError(f"Excel 解析失败: {e}")
    
    def _parse_json(
        self, file_path: str, encoding: str,
        max_rows: int, preview_rows: int, file_size: int,
    ) -> Dict[str, Any]:
        """解析 JSON 文件"""
        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                data = json.load(f)
            
            # 统一为列表
            if isinstance(data, dict):
                rows = [data]
            elif isinstance(data, list):
                rows = data[:max_rows]
            else:
                rows = [{"value": data}]
            
            # 提取列名
            columns = []
            if rows and isinstance(rows[0], dict):
                columns = list(rows[0].keys())
            
            dtypes = self._infer_dtypes(rows, columns)
            
            return {
                "file_type": "json",
                "row_count": len(rows),
                "columns": columns,
                "dtypes": dtypes,
                "preview": rows[:preview_rows],
                "file_size": file_size,
                "encoding": encoding,
            }
            
        except Exception as e:
            raise ValueError(f"JSON 解析失败: {e}")
    
    def _parse_parquet(
        self, file_path: str,
        max_rows: int, preview_rows: int, file_size: int,
    ) -> Dict[str, Any]:
        """解析 Parquet 文件"""
        try:
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError("Parquet 解析需要安装 pyarrow: pip install pyarrow")
        
        try:
            table = pq.read_table(file_path)
            
            # 限制行数
            if len(table) > max_rows:
                table = table.slice(0, max_rows)
            
            # 转换为字典列表
            df = table.to_pandas()
            columns = list(df.columns)
            rows = df.head(preview_rows).to_dict(orient="records")
            
            # 类型推断
            dtypes = {}
            for col in columns:
                dtype_str = str(df[col].dtype)
                if "int" in dtype_str:
                    dtypes[col] = "integer"
                elif "float" in dtype_str:
                    dtypes[col] = "float"
                elif "datetime" in dtype_str:
                    dtypes[col] = "datetime"
                elif "bool" in dtype_str:
                    dtypes[col] = "boolean"
                else:
                    dtypes[col] = "string"
            
            return {
                "file_type": "parquet",
                "row_count": len(df),
                "columns": columns,
                "dtypes": dtypes,
                "preview": rows,
                "file_size": file_size,
                "encoding": "binary",
            }
            
        except Exception as e:
            raise ValueError(f"Parquet 解析失败: {e}")
    
    def _infer_dtypes(self, rows: List[Dict], columns: List[str]) -> Dict[str, str]:
        """推断字段类型"""
        dtypes = {}
        
        if not rows:
            return {col: "string" for col in columns}
        
        sample_size = min(100, len(rows))
        sample = rows[:sample_size]
        
        for col in columns:
            type_counts = {
                "integer": 0,
                "float": 0,
                "boolean": 0,
                "null": 0,
                "string": 0,
            }
            
            for row in sample:
                val = row.get(col)
                
                if val is None or val == "" or val == "None":
                    type_counts["null"] += 1
                elif isinstance(val, bool):
                    type_counts["boolean"] += 1
                elif isinstance(val, int):
                    type_counts["integer"] += 1
                elif isinstance(val, float):
                    type_counts["float"] += 1
                else:
                    # 尝试推断字符串类型
                    try:
                        int(val)
                        type_counts["integer"] += 1
                    except (ValueError, TypeError):
                        try:
                            float(val)
                            type_counts["float"] += 1
                        except (ValueError, TypeError):
                            type_counts["string"] += 1
            
            # 选择最多的类型
            non_null = {k: v for k, v in type_counts.items() if k != "null" and v > 0}
            if non_null:
                dtypes[col] = max(non_null, key=non_null.get)
            else:
                dtypes[col] = "string"
        
        return dtypes
