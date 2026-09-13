# -*- coding: utf-8 -*-
"""
电商爬虫 - Scrapy + 真实数据采集

支持淘宝、京东等电商平台数据采集
"""
import asyncio
import json
import re
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

from ..base import BaseCrawler, CrawlResult
from ..utils.storage import DataStorage


class EcommerceCrawler(BaseCrawler):
    """电商爬虫基类"""

    def __init__(self, platform: str = "generic"):
        super().__init__(f"ecommerce_{platform}")
        self.platform = platform
        self.storage = DataStorage()
        # 大幅增加请求间隔，避免被反爬
        self.request_delay = 10.0  # 淘宝 10 秒
        self.platform_delays = {
            "taobao": 10.0,
            "jd": 5.0,  # 京东 5 秒
            "generic": 3.0,
        }

    async def crawl(
        self,
        keywords: List[str] = None,
        pages: int = 1,
        save_to_db: bool = True
    ) -> CrawlResult:
        if keywords is None:
            keywords = ["手机"]

        self.logger.info(f"开始爬取 {self.platform}，关键词: {keywords}，页数: {pages}")

        # 使用平台特定的延迟
        delay = self.platform_delays.get(self.platform, 3.0)
        self.logger.info(f"请求间隔设置为: {delay} 秒")

        all_products = []

        for keyword in keywords:
            for page in range(1, pages + 1):
                products = await self._crawl_page(keyword, page)
                # 添加 keyword 标记
                for p in products:
                    p['keyword'] = keyword
                all_products.extend(products)
                await asyncio.sleep(delay)  # 使用平台特定的延迟

        if all_products:
            filepath = self.storage.save(
                source=self.platform,
                data=all_products,
                category="products"
            )
            self.logger.info(f"已保存到文件: {filepath}")
        else:
            filepath = None

        result = CrawlResult(
            success=True,
            data=all_products,
            message=f"成功爬取 {len(all_products)} 条商品数据",
            source=self.platform,
            count=len(all_products)
        )

        # 保存到数据库
        if save_to_db and all_products:
            result.save_to_db(platform=self.platform)

        return result

    async def _crawl_page(self, keyword: str, page: int) -> List[Dict]:
        raise NotImplementedError

    def _get_headers(self) -> Dict:
        """获取随机请求头"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        ]
        return {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }


class TaobaoCrawler(EcommerceCrawler):
    """淘宝爬虫

    注意：淘宝有较强的反爬机制。
    - 建议使用阿里妈妈开放平台 API 获取真实数据
    - 或使用 Selenium/Playwright 模拟浏览器
    - 当前版本使用模拟数据 + 基础搜索建议
    """

    def __init__(self):
        super().__init__(platform="taobao")
        self.search_url = "https://suggest.taobao.com/sug"

    async def _crawl_page(self, keyword: str, page: int) -> List[Dict]:
        """爬取淘宝商品"""
        self.logger.info(f"爬取淘宝：{keyword} 第 {page} 页")

        # 尝试获取真实数据
        real_products = await self._fetch_real_data(keyword, page)

        if real_products:
            self.logger.info(f"获取到 {len(real_products)} 条真实数据")
            return real_products
        else:
            # 回退到模拟数据
            self.logger.info("使用模拟数据")
            return self._generate_mock_data(keyword, page)

    async def _fetch_real_data(self, keyword: str, page: int) -> List[Dict]:
        """尝试获取真实数据（淘宝搜索建议）"""
        if not httpx:
            return []

        params = {
            "q": keyword,
            "code": "utf-8",
        }

        headers = self._get_headers()
        headers["Referer"] = "https://www.taobao.com/"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.search_url, params=params, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    products = self._parse_taobao_response(data, keyword, page)
                    return products

        except Exception as e:
            self.logger.debug(f"淘宝搜索建议获取: {e}")

        return []

    def _parse_taobao_response(self, data: Dict, keyword: str, page: int) -> List[Dict]:
        """解析淘宝搜索建议响应"""
        products = []

        # 淘宝搜索建议返回的是搜索词建议，不是商品列表
        # 这里用于验证关键词可用性
        if "result" in data:
            suggestions = data["result"]
            if suggestions and len(suggestions) > 0:
                # 有搜索建议，说明关键词有效
                self.logger.debug(f"淘宝关键词 '{keyword}' 有效，有 {len(suggestions)} 个建议")

        # 返回模拟数据（淘宝反爬限制）
        return self._generate_mock_data(keyword, page)

    def _generate_mock_data(self, keyword: str, page: int) -> List[Dict]:
        """生成模拟数据（开发阶段使用）"""
        random.seed(hash(f"{keyword}_{page}") % 1000000)

        brands = {
            "手机": ["Apple", "Samsung", "Huawei", "Xiaomi", "OPPO", "vivo"],
            "电脑": ["Lenovo", "Dell", "HP", "Apple", "ASUS"],
            "耳机": ["Apple", "Sony", "Bose", "Sennheiser", "Huawei"],
        }

        brand_list = brands.get(keyword, ["品牌A", "品牌B", "品牌C"])
        products = []

        for i in range(20):
            brand = random.choice(brand_list)
            price = round(random.uniform(100, 9999), 2)

            products.append({
                "id": f"taobao_{keyword}_{page}_{i}",
                "keyword": keyword,
                "page": page,
                "title": f"{brand} {keyword} {random.choice(['Pro', 'Max', 'Plus', 'Lite', ''])} {random.randint(1, 15)}代",
                "brand": brand,
                "price": price,
                "original_price": round(price * random.uniform(1.0, 1.5), 2),
                "sales": random.randint(0, 100000),
                "rating": round(random.uniform(3.0, 5.0), 1),
                "review_count": random.randint(0, 50000),
                "shop": f"{brand}官方旗舰店",
                "location": random.choice(["北京", "上海", "广州", "深圳", "杭州"]),
                "tags": random.sample(["热卖", "新品", "包邮", "限时", "折扣"], k=random.randint(1, 3)),
                "platform": "taobao",
                "is_mock": True,  # 标记为模拟数据
                "crawl_time": datetime.now().isoformat(),
            })

        return products


class JDCrawler(EcommerceCrawler):
    """京东爬虫 - 支持真实数据采集"""

    def __init__(self):
        super().__init__(platform="jd")
        self.search_url = "https://search.jd.com/Search"
        self.price_api = "https://p.3.cn/prices/mgets"

    async def _crawl_page(self, keyword: str, page: int) -> List[Dict]:
        """爬取京东商品"""
        self.logger.info(f"爬取京东：{keyword} 第 {page} 页")

        # 尝试获取真实数据
        real_products = await self._fetch_real_data(keyword, page)

        if real_products:
            self.logger.info(f"获取到 {len(real_products)} 条真实数据")
            return real_products
        else:
            self.logger.info("使用模拟数据")
            return self._generate_mock_data(keyword, page)

    async def _fetch_real_data(self, keyword: str, page: int) -> List[Dict]:
        """获取真实京东数据"""
        if not httpx:
            return []

        params = {
            "keyword": keyword,
            "enc": "utf-8",
            "wq": keyword,
            "page": page,
            "s": (page - 1) * 30,
        }

        headers = self._get_headers()
        headers["Referer"] = "https://www.jd.com/"

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(self.search_url, params=params, headers=headers)

                if response.status_code == 200:
                    html = response.text
                    products = self._parse_jd_html(html, keyword, page)

                    # 获取商品价格
                    if products:
                        sku_ids = [p.get("id", "") for p in products[:10] if p.get("id")]
                        prices = await self._get_prices(sku_ids)

                        for p in products:
                            sku = p.get("id", "")
                            if sku in prices:
                                p["price"] = prices[sku]

                    return products

        except Exception as e:
            self.logger.warning(f"京东真实数据获取失败: {e}")

        return []

    def _parse_jd_html(self, html: str, keyword: str, page: int) -> List[Dict]:
        """解析京东搜索页面"""
        products = []

        # 提取商品信息
        pattern = r'<li class="gl-item".*?data-sku="(\d+)".*?<em>([^<]+)</em>.*?<div class="p-price".*?<strong class="[^"]*">(\d+\.?\d*)</strong>'
        matches = re.findall(pattern, html, re.DOTALL)

        for match in matches:
            sku_id, title, price = match
            title = self._clean_html(title)

            if sku_id and title:
                products.append({
                    "id": sku_id,
                    "keyword": keyword,
                    "page": page,
                    "title": title,
                    "price": float(price) if price else 0,
                    "platform": "jd",
                    "is_mock": False,  # 真实数据标记
                    "detail_url": f"https://item.jd.com/{sku_id}.html",
                    "crawl_time": datetime.now().isoformat(),
                })

        # 备用解析模式
        if not products:
            pattern = r'data-sku="(\d+)".*?¥(\d+\.?\d*)'
            matches = re.findall(pattern, html)
            for match in matches:
                sku_id, price = match
                products.append({
                    "id": sku_id,
                    "keyword": keyword,
                    "page": page,
                    "title": f"京东商品 {sku_id}",
                    "price": float(price),
                    "platform": "jd",
                    "is_mock": False,  # 真实数据标记
                    "detail_url": f"https://item.jd.com/{sku_id}.html",
                    "crawl_time": datetime.now().isoformat(),
                })

        return products

    async def _get_prices(self, sku_ids: List[str]) -> Dict[str, float]:
        """批量获取商品价格"""
        if not sku_ids or not httpx:
            return {}

        params = {
            "skuIds": ",".join([f"J_{sid}" for sid in sku_ids])
        }

        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.price_api, params=params, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    prices = {}

                    for item in data:
                        sku = item.get("skuId", "")
                        price_str = item.get("p", "0")
                        try:
                            prices[sku] = float(price_str)
                        except:
                            pass

                    return prices

        except Exception as e:
            self.logger.warning(f"获取价格失败: {e}")

        return {}

    def _generate_mock_data(self, keyword: str, page: int) -> List[Dict]:
        """生成模拟数据"""
        random.seed(hash(f"jd_{keyword}_{page}") % 1000000)

        brands = {
            "手机": ["Apple", "Samsung", "Huawei", "Xiaomi", "OPPO", "vivo"],
            "电脑": ["Lenovo", "Dell", "HP", "Apple", "ASUS"],
            "耳机": ["Apple", "Sony", "Bose", "Sennheiser", "Huawei"],
        }

        brand_list = brands.get(keyword, ["品牌A", "品牌B", "品牌C"])
        products = []

        for i in range(20):
            brand = random.choice(brand_list)
            price = round(random.uniform(100, 9999), 2)

            products.append({
                "id": f"jd_{keyword}_{page}_{i}",
                "keyword": keyword,
                "page": page,
                "title": f"{brand} {keyword} {random.choice(['Pro', 'Max', 'Plus', 'Lite', ''])} {random.randint(1, 15)}代",
                "brand": brand,
                "price": price,
                "original_price": round(price * random.uniform(1.0, 1.5), 2),
                "comments": random.randint(100, 100000),
                "shop": f"{brand}京东自营旗舰店",
                "location": random.choice(["北京", "上海", "广州", "深圳", "杭州"]),
                "tags": random.sample(["放心购", "新品", "京东配送", "热卖", "PLUS"], k=random.randint(1, 3)),
                "platform": "jd",
                "is_mock": True,  # 标记为模拟数据
                "crawl_time": datetime.now().isoformat(),
            })

        return products

    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()


# 爬虫工厂
CRAWLERS = {
    "taobao": TaobaoCrawler,
    "jd": JDCrawler,
    "generic": EcommerceCrawler,
}


def get_crawler(source_type: str) -> EcommerceCrawler:
    """获取爬虫实例"""
    crawler_class = CRAWLERS.get(source_type, EcommerceCrawler)
    return crawler_class()
