# -*- coding: utf-8 -*-
"""
数据解析工具
"""
import json
import re
from typing import Any, Dict, List, Optional, Union
from bs4 import BeautifulSoup
from datetime import datetime


class DataParser:
    """数据解析器"""

    @staticmethod
    def parse_html(html: str, selector: str = "body") -> Optional[BeautifulSoup]:
        """解析 HTML"""
        if not html:
            return None
        return BeautifulSoup(html, "lxml")

    @staticmethod
    def parse_json(text: str) -> Optional[Dict]:
        """解析 JSON"""
        try:
            # 处理 JSONP 回调
            text = DataParser._handle_jsonp(text)
            return json.loads(text)
        except json.JSONDecodeError as e:
            return None

    @staticmethod
    def _handle_jsonp(text: str) -> str:
        """处理 JSONP 格式"""
        # 去除 JSONP 回调函数
        match = re.match(r"^[^(]*\((.*)\)[^)]*$", text.strip())
        if match:
            return match.group(1)
        return text

    @staticmethod
    def extract_text(element, selector: str, default: str = "") -> str:
        """提取文本"""
        if element is None:
            return default
        found = element.select_one(selector)
        return found.get_text(strip=True) if found else default

    @staticmethod
    def extract_attr(element, selector: str, attr: str, default: str = "") -> str:
        """提取属性"""
        if element is None:
            return default
        found = element.select_one(selector)
        return found.get(attr, default) if found else default

    @staticmethod
    def parse_stock_data(raw_data: str) -> List[Dict]:
        """解析股票数据（东方财富格式）"""
        try:
            data = DataParser.parse_json(raw_data)
            if data and "data" in data:
                records = data["data"].get("klines", [])
                result = []
                for record in records:
                    # 格式: "日期,开盘,收盘,最高,最低,成交量,成交额,振幅"
                    parts = record.split(",")
                    if len(parts) >= 6:
                        result.append({
                            "date": parts[0],
                            "open": float(parts[1]),
                            "close": float(parts[2]),
                            "high": float(parts[3]),
                            "low": float(parts[4]),
                            "volume": int(parts[5]),
                            "amount": float(parts[6]) if len(parts) > 6 else 0,
                        })
                return result
            return []
        except Exception:
            return []

    @staticmethod
    def parse_sina_data(raw_data: str) -> Dict:
        """解析新浪财经数据"""
        try:
            # 格式: var hq_str_sh000001="name,price,change,pct,volume,amount,..."
            match = re.search(r'"([^"]+)"', raw_data)
            if match:
                parts = match.group(1).split(",")
                return {
                    "name": parts[0] if len(parts) > 0 else "",
                    "price": float(parts[1]) if len(parts) > 1 and parts[1] else 0,
                    "change": float(parts[2]) if len(parts) > 2 and parts[2] else 0,
                    "pct": float(parts[3]) if len(parts) > 3 and parts[3] else 0,
                    "open": float(parts[4]) if len(parts) > 4 and parts[4] else 0,
                    "high": float(parts[5]) if len(parts) > 5 and parts[5] else 0,
                    "low": float(parts[6]) if len(parts) > 6 and parts[6] else 0,
                    "volume": int(parts[8]) if len(parts) > 8 and parts[8] else 0,
                    "amount": float(parts[9]) if len(parts) > 9 and parts[9] else 0,
                    "update_time": f"{parts[30]} {parts[31]}" if len(parts) > 31 else "",
                }
            return {}
        except Exception:
            return {}

    @staticmethod
    def parse_netease_news(raw_data: str) -> List[Dict]:
        """解析网易新闻数据"""
        try:
            # 处理 JSONP 格式
            data = DataParser.parse_json(raw_data)
            if data and "推荐" in data:
                news_list = []
                for item in data["推荐"]:
                    news_list.append({
                        "title": item.get("title", ""),
                        "url": item.get("docurl", ""),
                        "source": "网易新闻",
                        "category": item.get("classify", ""),
                        "publish_time": item.get("ptime", ""),
                        "summary": item.get("digest", ""),
                    })
                return news_list
            return []
        except Exception:
            return []
