# -*- coding: utf-8 -*-
"""
榜单/列表页专用抽取器 - Phase 4.6.2

针对结构清晰的榜单页面优化抽取：
- 豆瓣 Top250
- 电影/音乐/书籍榜单
- 商品排行榜
- 新闻热榜

抽取目标字段：
- 排名 (rank)
- 标题/名称 (title)
- 评分 (rating)
- 年份/时间 (year/date)
- 导演/作者/品牌 (creator)
- 链接 (link)
- 封面/图片 (cover)
- 简介/摘要 (summary)
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from .base import CrawlResult
from .url_crawler import URLCrawler

logger = logging.getLogger(__name__)


@dataclass
class RankingField:
    name: str
    aliases: List[str]
    selectors: List[str]  # CSS 选择器候选
    extractors: List[str] = field(default_factory=list)  # 文本提取规则


# 榜单页常见字段定义
RANKING_FIELDS = {
    "排名": RankingField(
        "排名",
        ["排名", "名次", "rank", "序号", "top"],
        [".rank", ".number", ".order", ".index", ".top-num", ".rank-num", ".num"],
    ),
    "标题": RankingField(
        "标题",
        ["标题", "名称", "名字", "title", "name", "片名"],
        [".title", ".name", ".item-title", ".movie-name", ".book-name", ".product-name", "h2", "h3", "h4"],
    ),
    "评分": RankingField(
        "评分",
        ["评分", "分数", "rating", "score", "豆瓣评分", "rating_num"],
        [".rating", ".score", ".rating_num", ".star", ".rate", ".rating_nums"],
    ),
    "年份": RankingField(
        "年份",
        ["年份", "上映时间", "年代", "year", "date", "时间"],
        [".year", ".date", ".time", ".release", ".pubdate"],
    ),
    "导演": RankingField(
        "导演",
        ["导演", "director", "作者", "author", "创作者"],
        [".director", ".author", ".creator", ".artist"],
    ),
    "主演": RankingField(
        "主演",
        ["主演", "演员", "cast", "actor", "star"],
        [".cast", ".actor", ".star", ".performer"],
    ),
    "链接": RankingField(
        "链接",
        ["链接", "地址", "url", "href", "详情"],
        ["a[href]"],
    ),
    "封面": RankingField(
        "封面",
        ["封面", "海报", "图片", "img", "poster", "image", "cover"],
        ["img", ".cover", ".poster", ".thumb", ".thumbnail"],
    ),
    "简介": RankingField(
        "简介",
        ["简介", "摘要", "描述", "summary", "desc", "description", "剧情"],
        [".summary", ".desc", ".description", ".intro", ".brief", "p"],
    ),
    "评论数": RankingField(
        "评论数",
        ["评论数", "评论", "reviews", "comments", "评价数"],
        [".comments", ".reviews", ".comment-count"],
    ),
    "价格": RankingField(
        "价格",
        ["价格", "价钱", "price", "金额", "售价"],
        [".price", ".cost", ".amount"],
    ),
}


class RankingExtractor:
    """榜单页专用抽取器"""

    def __init__(self):
        self.url_crawler = URLCrawler(enable_crawl4ai=True)

    async def extract(self, url: str, requirement: str = "", dynamic: bool = False) -> Dict[str, Any]:
        """
        抽取榜单页数据

        Args:
            url: 榜单页 URL
            requirement: 用户想要的字段描述
            dynamic: 是否强制动态渲染

        Returns:
            结构化结果
        """
        html = None
        source_message = ""
        
        # 优先使用动态爬取器处理动态页面
        if dynamic:
            from .dynamic_crawler import DynamicCrawler, DynamicCrawlOptions
            dynamic_crawler = DynamicCrawler()
            options = DynamicCrawlOptions(
                wait_for=".item",
                wait_time=10,
                auto_scroll=True,
                scroll_count=3,
            )
            crawl_result = await dynamic_crawler.crawl_dynamic(url, options)
            await dynamic_crawler.close()
            
            if crawl_result.success:
                html = self._get_html_from_dynamic(crawl_result)
                source_message = crawl_result.message
            else:
                return {
                    "success": False,
                    "message": crawl_result.message,
                    "rows": [],
                    "fields": [],
                }
        else:
            # 静态爬取：直接获取原始 HTML
            import httpx
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    })
                    resp.raise_for_status()
                    html = resp.text
                    source_message = f"静态爬取成功 | 状态码: {resp.status_code}"
            except Exception as e:
                return {
                    "success": False,
                    "message": f"爬取失败: {str(e)}",
                    "rows": [],
                    "fields": [],
                }

        if not html:
            return {
                "success": False,
                "message": "无法获取页面 HTML",
                "rows": [],
                "fields": [],
            }

        soup = BeautifulSoup(html, "lxml")

        # 识别用户想要的字段
        wanted_fields = self._parse_wanted_fields(requirement)

        # 尝试多种列表容器模式
        rows = self._extract_list_items(soup, wanted_fields)

        if not rows:
            # 兜底：尝试表格
            rows = self._extract_from_tables(soup, wanted_fields)

        if not rows:
            # 最后兜底：通用卡片
            rows = self._extract_generic_cards(soup, wanted_fields)

        # 质量评估
        quality = self._assess_quality(rows, wanted_fields)

        return {
            "success": len(rows) > 0,
            "message": f"抽取完成，共 {len(rows)} 条" if rows else "未识别到列表数据",
            "fields": [{"name": f, "type": "string"} for f in wanted_fields],
            "rows": rows,
            "quality": quality,
            "source_message": source_message,
        }

    def _get_html_from_dynamic(self, crawl_result: CrawlResult) -> Optional[str]:
        """从动态爬取结果中提取 HTML"""
        if not crawl_result.data:
            return None
        
        # 1. 优先找 html 字段
        for item in crawl_result.data:
            if isinstance(item, dict):
                if "html" in item and item["html"]:
                    return item["html"]
                if "content" in item and item["content"]:
                    return item["content"]
        
        # 2. 找包含 HTML 标签的文本
        texts = []
        for item in crawl_result.data:
            if isinstance(item, dict):
                for v in item.values():
                    if isinstance(v, str) and "<" in v and ">" in v:
                        texts.append(v)
        if texts:
            return texts[0]
        
        # 3. 如果是 crawl4ai 结果，尝试 markdown
        for item in crawl_result.data:
            if isinstance(item, dict) and "markdown" in item:
                md = item["markdown"]
                if md:
                    # 简单转换 markdown 为 HTML
                    return f"<html><body><pre>{md}</pre></body></html>"
        
        return None

    def _parse_wanted_fields(self, requirement: str) -> List[str]:
        """从需求中解析想要的字段"""
        text = (requirement or "").lower()
        wanted = []
        seen = set()

        for name, field in RANKING_FIELDS.items():
            for alias in field.aliases:
                if alias.lower() in text and name not in seen:
                    wanted.append(name)
                    seen.add(name)
                    break

        # 默认字段兜底
        if not wanted:
            wanted = ["排名", "标题", "评分", "年份", "链接"]

        return wanted

    def _extract_list_items(self, soup: BeautifulSoup, wanted_fields: List[str]) -> List[Dict[str, Any]]:
        """从列表项中抽取数据"""
        # 先检测是否是豆瓣页面（注意：豆瓣用的是 grid_view 不是 grid-view）
        if soup.select(".grid_view .item") or soup.select(".grid-view .item"):
            return self._extract_douban_items(soup, wanted_fields)
        
        # 检测是否是猫眼页面
        if soup.select(".movie-item") or soup.select("[class*='movie']"):
            return self._extract_maoyan_items(soup, wanted_fields)
        
        # 常见列表容器选择器
        list_selectors = [
            ".grid-view .item",           # 豆瓣
            ".item",                      # 通用 item
            ".list-item",                 # 通用 list-item
            ".rank-item",                 # 排名项
            "li",                         # 列表项
            ".card",                      # 卡片
            ".product",                   # 商品
            ".movie-item",                # 电影项
            ".book-item",                 # 书籍项
        ]

        all_rows = []
        for selector in list_selectors:
            items = soup.select(selector)
            if len(items) >= 3:
                rows = []
                for item in items[:250]:  # 最多 250 条
                    row = self._extract_item_fields(item, wanted_fields)
                    if row.get("标题") or row.get("排名"):
                        rows.append(row)
                if len(rows) >= 3:
                    all_rows.extend(rows)
                    break

        return all_rows

    def _extract_douban_items(self, soup: BeautifulSoup, wanted_fields: List[str]) -> List[Dict[str, Any]]:
        """专用：豆瓣电影 Top250 抽取"""
        # 尝试两种选择器（豆瓣实际用的是 grid_view）
        items = soup.select(".grid_view .item") or soup.select(".grid-view .item")
        if not items:
            # 再尝试直接找 .item
            items = soup.select(".item")
        rows = []
        
        for item in items[:250]:
            row = {}
            
            # 排名
            if "排名" in wanted_fields:
                rank_elem = item.select_one(".pic em")
                row["排名"] = rank_elem.get_text(strip=True) if rank_elem else ""
            
            # 标题
            if "标题" in wanted_fields or "电影名" in wanted_fields:
                title_elem = item.select_one(".info .title")
                if title_elem:
                    row["标题"] = title_elem.get_text(strip=True)
                else:
                    title_elem = item.select_one(".pic img")
                    row["标题"] = title_elem.get("alt", "") if title_elem else ""
            
            # 评分
            if "评分" in wanted_fields:
                rating_elem = item.select_one(".rating_num")
                row["评分"] = rating_elem.get_text(strip=True) if rating_elem else ""
            
            # 年份/导演/主演（在 .bd p 中）
            info_elem = item.select_one(".info .bd p")
            if info_elem:
                info_text = info_elem.get_text(separator=" ", strip=True)
                
                if "导演" in wanted_fields or "主演" in wanted_fields:
                    # 提取导演和主演
                    lines = [line.strip() for line in info_text.split("\n") if line.strip()]
                    for line in lines:
                        if "导演" in line or "主演" in line:
                            parts = line.split("主演:")
                            if len(parts) == 2:
                                director_part = parts[0].strip()
                                if director_part.startswith("导演:"):
                                    director_part = director_part[3:].strip()
                                row["导演"] = director_part
                                row["主演"] = parts[1].strip()
                            else:
                                # 可能没有明确分隔
                                if "导演" in line:
                                    row["导演"] = line.replace("导演:", "").strip()
                                if "主演" in line:
                                    row["主演"] = line.replace("主演:", "").strip()
                
                if "年份" in wanted_fields:
                    # 提取年份
                    m = re.search(r"(\d{4})", info_text)
                    row["年份"] = m.group(1) if m else ""
            
            # 链接
            if "链接" in wanted_fields:
                link_elem = item.select_one(".pic a")
                row["链接"] = link_elem.get("href", "") if link_elem else ""
            
            # 封面
            if "封面" in wanted_fields:
                img_elem = item.select_one(".pic img")
                row["封面"] = img_elem.get("src", "") if img_elem else ""
            
            if any(row.values()):
                rows.append(row)
        
        return rows

    def _extract_maoyan_items(self, soup: BeautifulSoup, wanted_fields: List[str]) -> List[Dict[str, Any]]:
        """专用：猫眼电影抽取"""
        # 猫眼电影有多种结构，尝试多种选择器
        selectors = [
            ".movie-item",
            ".board-item",
            ".film-item",
            "[class*='movie-item']",
            "[class*='film']",
        ]
        
        for selector in selectors:
            items = soup.select(selector)
            if len(items) >= 3:
                rows = []
                for item in items[:250]:
                    row = {}
                    
                    # 标题
                    if "标题" in wanted_fields:
                        title_elem = item.select_one(".name, .title, .movie-name, h4, h3")
                        row["标题"] = title_elem.get_text(strip=True) if title_elem else ""
                    
                    # 评分
                    if "评分" in wanted_fields:
                        rating_elem = item.select_one(".score, .rating, .rate")
                        row["评分"] = rating_elem.get_text(strip=True) if rating_elem else ""
                    
                    # 年份
                    if "年份" in wanted_fields:
                        year_elem = item.select_one(".date, .year, .time")
                        if year_elem:
                            row["年份"] = year_elem.get_text(strip=True)
                        else:
                            # 尝试从文本中提取
                            text = item.get_text(separator=" ", strip=True)
                            m = re.search(r"(\d{4})", text)
                            row["年份"] = m.group(1) if m else ""
                    
                    # 链接
                    if "链接" in wanted_fields:
                        link_elem = item.select_one("a[href]")
                        row["链接"] = link_elem.get("href", "") if link_elem else ""
                    
                    # 封面
                    if "封面" in wanted_fields:
                        img_elem = item.select_one("img")
                        row["封面"] = img_elem.get("src", "") if img_elem else ""
                    
                    if row.get("标题"):
                        rows.append(row)
                
                if len(rows) >= 3:
                    return rows
        
        return []

    def _extract_item_fields(self, item: BeautifulSoup, wanted_fields: List[str]) -> Dict[str, Any]:
        """从单个列表项中抽取字段"""
        row = {}

        for field_name in wanted_fields:
            field_def = RANKING_FIELDS.get(field_name)
            if not field_def:
                continue

            value = None

            # 1. 尝试 CSS 选择器
            for selector in field_def.selectors:
                try:
                    elem = item.select_one(selector)
                    if elem:
                        if field_name == "链接":
                            value = elem.get("href", "")
                        elif field_name == "封面":
                            value = elem.get("src", "") or elem.get("data-src", "")
                        else:
                            value = elem.get_text(strip=True)
                        if value:
                            break
                except Exception:
                    continue

            # 2. 尝试在父元素中搜索
            if not value:
                value = self._search_in_parent(item, field_def)

            # 3. 文本提取规则
            if not value:
                value = self._apply_text_rules(item, field_name)

            row[field_name] = value or ""

        return row

    def _search_in_parent(self, item: BeautifulSoup, field_def: RankingField) -> Optional[str]:
        """在父元素中搜索字段"""
        for alias in field_def.aliases:
            # 查找包含该关键词的元素
            elems = item.find_all(text=re.compile(alias, re.I))
            for elem in elems:
                parent = elem.parent
                if parent:
                    text = parent.get_text(strip=True)
                    # 尝试提取值部分
                    parts = re.split(r"[:：]", text, maxsplit=1)
                    if len(parts) == 2:
                        return parts[1].strip()
        return None

    def _apply_text_rules(self, item: BeautifulSoup, field_name: str) -> Optional[str]:
        """应用文本提取规则"""
        text = item.get_text(separator=" ", strip=True)

        if field_name == "排名":
            m = re.search(r"^\s*(\d{1,3})", text)
            return m.group(1) if m else None

        if field_name == "评分":
            m = re.search(r"(\d(?:\.\d)?)", text)
            return m.group(1) if m else None

        if field_name == "年份":
            m = re.search(r"(19\d{2}|20\d{2})", text)
            return m.group(1) if m else None

        if field_name == "价格":
            m = re.search(r"[¥￥$]?\s*(\d+(?:\.\d+)?)", text)
            return m.group(1) if m else None

        return None

    def _extract_from_tables(self, soup: BeautifulSoup, wanted_fields: List[str]) -> List[Dict[str, Any]]:
        """从表格中抽取数据"""
        tables = soup.find_all("table")
        if not tables:
            return []

        # 找最大的表格
        best_table = max(tables, key=lambda t: len(t.find_all("tr")), default=None)
        if not best_table:
            return []

        rows = []
        trs = best_table.find_all("tr")

        # 提取表头
        headers = []
        header_row = best_table.find("thead")
        if header_row:
            ths = header_row.find_all(["th", "td"])
            headers = [th.get_text(strip=True) for th in ths]

        if not headers and trs:
            ths = trs[0].find_all(["th", "td"])
            headers = [th.get_text(strip=True) for th in ths]

        # 提取数据行
        for tr in trs[1:]:
            tds = tr.find_all(["td", "th"])
            if not tds:
                continue

            row = {}
            for i, td in enumerate(tds):
                if i < len(headers):
                    header = headers[i]
                    # 映射到想要的字段
                    for wanted in wanted_fields:
                        if wanted in header or any(alias in header for alias in RANKING_FIELDS[wanted].aliases):
                            row[wanted] = td.get_text(strip=True)
                            break
                    else:
                        row[header] = td.get_text(strip=True)
                else:
                    row[f"col_{i}"] = td.get_text(strip=True)

            if row:
                rows.append(row)

        return rows

    def _extract_generic_cards(self, soup: BeautifulSoup, wanted_fields: List[str]) -> List[Dict[str, Any]]:
        """通用卡片抽取兜底"""
        cards = soup.find_all(["article", "div"], class_=re.compile(r"card|item|post|product|movie|book", re.I))
        if len(cards) < 3:
            return []

        rows = []
        for card in cards[:250]:
            row = self._extract_item_fields(card, wanted_fields)
            if row.get("标题"):
                rows.append(row)

        return rows

    def _assess_quality(self, rows: List[Dict], wanted_fields: List[str]) -> Dict[str, Any]:
        """评估抽取质量"""
        if not rows:
            return {"score": 0.0, "filled_ratio": 0.0, "issues": ["无结果"]}

        total = len(rows) * len(wanted_fields)
        filled = 0
        for row in rows:
            for field in wanted_fields:
                value = row.get(field)
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
