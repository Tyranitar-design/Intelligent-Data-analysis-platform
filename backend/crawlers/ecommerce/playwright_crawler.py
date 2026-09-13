# -*- coding: utf-8 -*-
"""
Playwright 人机协作电商爬虫

支持京东、淘宝等平台真实数据采集
人机协作模式：小彩打开页面 → 等待小宇登录 → 继续自动化

作者: 小彩 💫
日期: 2026-04-25
"""
import asyncio
import json
import re
import random
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Playwright 导入（延迟加载）
_playwright = None
_browser = None
_context = None


async def ensure_playwright():
    """确保 Playwright 已安装"""
    global _playwright
    if _playwright is None:
        try:
            from playwright.async_api import async_playwright
            _playwright = await async_playwright().start()
            logger.info("Playwright 初始化成功")
        except ImportError:
            raise ImportError("请先安装 playwright: pip install playwright && playwright install chromium")
    return _playwright


class PlaywrightEcommerceCrawler:
    """Playwright 人机协作电商爬虫"""
    
    def __init__(
        self,
        platform: str = "jd",
        headless: bool = False,  # 人机协作模式需要显示浏览器
        wait_for_login: int = 300,  # 等待登录时间（秒）
        data_dir: str = None
    ):
        """
        初始化爬虫
        
        Args:
            platform: 平台 (jd, taobao)
            headless: 是否无头模式（人机协作需要 False）
            wait_for_login: 等待登录时间（秒）
            data_dir: 数据保存目录
        """
        self.platform = platform
        self.headless = headless
        self.wait_for_login = wait_for_login
        self.data_dir = Path(data_dir) if data_dir else Path("D:/智能数据分析平台/data/raw")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.browser = None
        self.context = None
        self.page = None
        
        # 平台配置
        self.platforms = {
            "jd": {
                "name": "京东",
                "search_url": "https://search.jd.com/Search?keyword={keyword}&page={page}",
                "login_url": "https://passport.jd.com/new/login.aspx",
                "item_selector": ".gl-item",
                "title_selector": ".p-name em",
                "price_selector": ".p-price strong",
                "shop_selector": ".p-shop a",
                "comment_selector": ".p-commit strong",
            },
            "taobao": {
                "name": "淘宝",
                "search_url": "https://s.taobao.com/search?q={keyword}&s={offset}",
                "login_url": "https://login.taobao.com/member/login.jhtml",
                "item_selector": ".items .item",
                "title_selector": ".title a",
                "price_selector": ".price strong",
                "shop_selector": ".shop a",
                "comment_selector": ".deal-cnt",
            }
        }
        
        self.config = self.platforms.get(platform, self.platforms["jd"])
        
    async def start(self):
        """启动浏览器"""
        playwright = await ensure_playwright()
        
        # 启动浏览器（有界面模式）
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        # 创建浏览器上下文（模拟真实用户）
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=self._get_random_ua(),
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )
        
        # 注入反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)
        
        self.page = await self.context.new_page()
        logger.info(f"浏览器启动成功，平台: {self.config['name']}")
        
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            logger.info("浏览器已关闭")
            
    def _get_random_ua(self) -> str:
        """获取随机 User-Agent"""
        uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        ]
        return random.choice(uas)
    
    async def wait_for_manual_login(self):
        """
        等待用户手动登录
        
        人机协作：打开登录页面，等待用户完成登录
        """
        if not self.page:
            await self.start()
            
        print("\n" + "=" * 60)
        print(f"🔐 人机协作模式")
        print("=" * 60)
        print(f"平台: {self.config['name']}")
        print(f"登录页面: {self.config['login_url']}")
        print(f"等待时间: {self.wait_for_login} 秒")
        print("-" * 60)
        print("📋 请在浏览器中完成以下操作：")
        print("   1. 扫码登录 或 账号密码登录")
        print("   2. 完成验证码验证（如有）")
        print("   3. 等待自动继续...")
        print("=" * 60 + "\n")
        
        # 打开登录页面
        await self.page.goto(self.config['login_url'])
        
        # 等待用户登录
        await asyncio.sleep(self.wait_for_login)
        
        print("✅ 继续自动化操作...")
        
    async def check_login_status(self) -> bool:
        """检查是否已登录"""
        if not self.page:
            return False
            
        try:
            # 检查登录状态的通用方法
            if self.platform == "jd":
                # 京东：检查是否有用户信息
                await self.page.goto("https://www.jd.com")
                user_info = await self.page.query_selector('.nickname')
                return user_info is not None
            elif self.platform == "taobao":
                # 淘宝：检查会员名
                await self.page.goto("https://www.taobao.com")
                member = await self.page.query_selector('.site-nav-user')
                return member is not None
        except Exception as e:
            logger.warning(f"检查登录状态失败: {e}")
            return False
            
    async def crawl_products(
        self,
        keyword: str,
        pages: int = 1,
        wait_for_login: bool = True
    ) -> List[Dict]:
        """
        爬取商品数据
        
        Args:
            keyword: 搜索关键词
            pages: 爬取页数
            wait_for_login: 是否等待登录
            
        Returns:
            商品数据列表
        """
        if not self.page:
            await self.start()
            
        # 等待登录
        if wait_for_login:
            await self.wait_for_manual_login()
            
        all_products = []
        
        for page in range(1, pages + 1):
            print(f"\n📦 正在爬取第 {page} 页...")
            
            # 构建搜索 URL
            if self.platform == "jd":
                url = self.config['search_url'].format(keyword=keyword, page=page)
            else:
                offset = (page - 1) * 44
                url = self.config['search_url'].format(keyword=keyword, offset=offset)
                
            # 访问搜索页面
            await self.page.goto(url)
            await asyncio.sleep(2)  # 等待页面加载
            
            # 滚动加载更多内容
            await self._scroll_page()
            
            # 解析商品数据
            products = await self._parse_products(keyword, page)
            all_products.extend(products)
            
            print(f"   获取到 {len(products)} 条数据")
            
            # 随机延迟，避免被检测
            delay = random.uniform(3, 6)
            await asyncio.sleep(delay)
            
        # 保存数据
        if all_products:
            await self._save_data(all_products, keyword)
            
        return all_products
        
    async def _scroll_page(self):
        """滚动页面加载更多内容"""
        for _ in range(3):
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
        await self.page.evaluate("window.scrollTo(0, 0)")
        
    async def _parse_products(self, keyword: str, page: int) -> List[Dict]:
        """解析商品数据"""
        products = []
        
        try:
            # 获取所有商品元素
            items = await self.page.query_selector_all(self.config['item_selector'])
            
            for i, item in enumerate(items):
                try:
                    # 标题
                    title_el = await item.query_selector(self.config['title_selector'])
                    title = await title_el.inner_text() if title_el else ""
                    
                    # 价格
                    price_el = await item.query_selector(self.config['price_selector'])
                    price_text = await price_el.inner_text() if price_el else "0"
                    price = self._parse_price(price_text)
                    
                    # 店铺
                    shop_el = await item.query_selector(self.config['shop_selector'])
                    shop = await shop_el.inner_text() if shop_el else ""
                    
                    # 评价数
                    comment_el = await item.query_selector(self.config['comment_selector'])
                    comments = await comment_el.inner_text() if comment_el else "0"
                    
                    # 链接
                    link_el = await item.query_selector('a')
                    href = await link_el.get_attribute('href') if link_el else ""
                    
                    if title:
                        products.append({
                            "id": f"{self.platform}_{keyword}_{page}_{i}",
                            "keyword": keyword,
                            "page": page,
                            "title": title.strip(),
                            "price": price,
                            "shop": shop.strip(),
                            "comments": comments.strip(),
                            "url": href if href.startswith('http') else f"https:{href}" if href else "",
                            "platform": self.platform,
                            "is_mock": False,
                            "crawl_time": datetime.now().isoformat(),
                        })
                        
                except Exception as e:
                    logger.debug(f"解析商品失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"解析页面失败: {e}")
            
        return products
        
    def _parse_price(self, text: str) -> float:
        """解析价格"""
        # 移除货币符号
        text = re.sub(r'[¥￥$]', '', text)
        # 提取数字
        match = re.search(r'[\d.]+', text)
        if match:
            return float(match.group())
        return 0.0
        
    async def _save_data(self, data: List[Dict], keyword: str):
        """保存数据到文件"""
        filename = f"{self.platform}_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.data_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"\n💾 数据已保存: {filepath}")
        

async def crawl_with_human_help(
    platform: str = "jd",
    keyword: str = "手机",
    pages: int = 1,
    wait_for_login: bool = True,
    login_wait_time: int = 300
) -> List[Dict]:
    """
    人机协作爬取入口函数
    
    Args:
        platform: 平台 (jd, taobao)
        keyword: 搜索关键词
        pages: 爬取页数
        wait_for_login: 是否等待登录
        login_wait_time: 登录等待时间（秒）
        
    Returns:
        商品数据列表
    """
    crawler = PlaywrightEcommerceCrawler(
        platform=platform,
        headless=False,  # 必须有界面
        wait_for_login=login_wait_time
    )
    
    try:
        await crawler.start()
        products = await crawler.crawl_products(
            keyword=keyword,
            pages=pages,
            wait_for_login=wait_for_login
        )
        return products
    finally:
        await crawler.close()


# 测试入口
if __name__ == "__main__":
    import sys
    
    platform = sys.argv[1] if len(sys.argv) > 1 else "jd"
    keyword = sys.argv[2] if len(sys.argv) > 2 else "手机"
    pages = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    
    print(f"\n🚀 Playwright 人机协作爬虫")
    print(f"平台: {platform}")
    print(f"关键词: {keyword}")
    print(f"页数: {pages}")
    
    asyncio.run(crawl_with_human_help(
        platform=platform,
        keyword=keyword,
        pages=pages
    ))
