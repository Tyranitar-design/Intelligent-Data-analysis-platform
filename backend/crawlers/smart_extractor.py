# -*- coding: utf-8 -*-
"""
智能字段抽取模块 - Phase 4.6.1

目标：
- 输入 URL + 用户自然语言需求
- 自动理解用户想要的字段
- 从静态/动态网页中提取结构化数据
- 规则优先，保证性能与稳定性

设计原则：
1. 字段识别优先使用规则/关键词映射
2. 页面解析优先复用 URLCrawler 的 HTML/表格/列表能力
3. 输出统一 schema + rows
"""
import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from .base import CrawlResult
from .url_crawler import URLCrawler

logger = logging.getLogger(__name__)


@dataclass
class FieldSpec:
    name: str
    aliases: List[str] = field(default_factory=list)
    field_type: str = "string"
    required: bool = False


class SmartFieldExtractor:
    """智能字段抽取器"""

    def __init__(self):
        self.url_crawler = URLCrawler(enable_crawl4ai=True)
        self.field_catalog = self._build_field_catalog()

    def _build_field_catalog(self) -> Dict[str, FieldSpec]:
        return {
            "排名": FieldSpec("排名", ["排名", "名次", "top", "rank", "序号"], "integer"),
            "标题": FieldSpec("标题", ["标题", "名称", "名字", "title", "name"], "string", True),
            "电影名": FieldSpec("电影名", ["电影名", "片名", "影片名", "movie", "film", "title"], "string", True),
            "评分": FieldSpec("评分", ["评分", "分数", "rating", "score", "豆瓣评分"], "number"),
            "上映时间": FieldSpec("上映时间", ["上映时间", "年份", "日期", "release", "year", "date"], "string"),
            "导演": FieldSpec("导演", ["导演", "director"], "string"),
            "主演": FieldSpec("主演", ["主演", "演员", "cast", "actor", "star"], "string"),
            "链接": FieldSpec("链接", ["链接", "地址", "url", "href"], "string"),
            "封面": FieldSpec("封面", ["封面", "海报", "图片", "img", "poster", "image"], "string"),
            "作者": FieldSpec("作者", ["作者", "author", "发布者"], "string"),
            "摘要": FieldSpec("摘要", ["摘要", "简介", "描述", "summary", "desc", "description"], "string"),
            "评论数": FieldSpec("评论数", ["评论数", "评论", "reviews", "comments"], "integer"),
            "价格": FieldSpec("价格", ["价格", "价钱", "price", "金额"], "number"),
            "标签": FieldSpec("标签", ["标签", "分类", "tag", "category"], "string"),
        }

    def parse_user_fields(self, requirement: str) -> List[FieldSpec]:
        """从自然语言需求中识别用户想要的字段"""
        text = (requirement or "").strip().lower()
        matched: List[FieldSpec] = []
        seen = set()

        for _, spec in self.field_catalog.items():
            for alias in spec.aliases:
                if alias.lower() in text and spec.name not in seen:
                    matched.append(spec)
                    seen.add(spec.name)
                    break

        # 如果没有识别到，给一个通用兜底
        if not matched:
            matched = [
                self.field_catalog["标题"],
                self.field_catalog["链接"],
                self.field_catalog["摘要"],
            ]
        return matched

    async def extract(self, url: str, requirement: str, dynamic: bool = False) -> Dict[str, Any]:
        fields = self.parse_user_fields(requirement)
        force_strategy = "crawl4ai" if dynamic else None
        crawl_result = await self.url_crawler.crawl_url(url=url, force_strategy=force_strategy)

        if not crawl_result.success:
            return {
                "success": False,
                "message": crawl_result.message,
                "fields": [f.name for f in fields],
                "rows": [],
                "quality": None,
            }

        rows = self._project_rows(crawl_result.data, fields)
        quality = self._assess_rows(rows, fields)

        return {
            "success": True,
            "message": f"智能抽取完成，共 {len(rows)} 条",
            "fields": [
                {"name": f.name, "type": f.field_type, "required": f.required}
                for f in fields
            ],
            "rows": rows,
            "raw_count": len(crawl_result.data),
            "quality": quality,
            "source_message": crawl_result.message,
        }

    def _project_rows(self, data: List[Dict[str, Any]], fields: List[FieldSpec]) -> List[Dict[str, Any]]:
        """把原始解析数据投影为用户想要的字段"""
        projected: List[Dict[str, Any]] = []
        for item in data[:500]:
            if not isinstance(item, dict):
                continue
            row: Dict[str, Any] = {}
            for field in fields:
                row[field.name] = self._extract_value(item, field)
            if any(str(v).strip() for v in row.values() if v is not None):
                projected.append(row)
        return projected

    def _extract_value(self, item: Dict[str, Any], field: FieldSpec) -> Any:
        # 1. 精确键匹配
        for key, value in item.items():
            k = str(key).lower()
            if field.name.lower() == k or any(alias.lower() == k for alias in field.aliases):
                return value

        # 2. 模糊键匹配
        for key, value in item.items():
            k = str(key).lower()
            if any(alias.lower() in k for alias in field.aliases):
                return value

        # 3. 从常见文本中提取
        blob = " | ".join(str(v) for v in item.values() if v is not None)
        return self._extract_from_text(blob, field)

    def _extract_from_text(self, text: str, field: FieldSpec) -> Any:
        if not text:
            return ""

        if field.name == "评分":
            m = re.search(r"(?<!\d)(\d(?:\.\d)?)(?!\d)", text)
            return m.group(1) if m else ""

        if field.name == "上映时间":
            m = re.search(r"(19\d{2}|20\d{2})", text)
            return m.group(1) if m else ""

        if field.name == "排名":
            m = re.search(r"^\s*(\d{1,3})", text)
            return m.group(1) if m else ""

        if field.name in ["标题", "电影名"]:
            parts = [p.strip() for p in re.split(r"\||/|·", text) if p.strip()]
            return parts[0][:120] if parts else text[:120]

        if field.name == "链接":
            m = re.search(r"https?://\S+", text)
            return m.group(0) if m else ""

        return text[:200]

    def _assess_rows(self, rows: List[Dict[str, Any]], fields: List[FieldSpec]) -> Dict[str, Any]:
        if not rows:
            return {"score": 0.0, "filled_ratio": 0.0, "issues": ["无结果"]}
        total = len(rows) * max(1, len(fields))
        filled = 0
        for row in rows:
            for field in fields:
                value = row.get(field.name)
                if value not in [None, "", []]:
                    filled += 1
        ratio = filled / total if total else 0.0
        issues = []
        if ratio < 0.5:
            issues.append("字段命中率较低")
        if len(rows) < 3:
            issues.append("结果条数较少")
        return {
            "score": round(min(1.0, ratio + (0.1 if len(rows) >= 10 else 0.0)), 3),
            "filled_ratio": round(ratio, 3),
            "issues": issues,
        }
