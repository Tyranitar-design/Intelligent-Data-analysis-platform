# -*- coding: utf-8 -*-
"""
京东 Playwright 爬虫 - 增强版
支持多种选择器和调试模式
"""
import asyncio
import json
import re
import random
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import sys
import io

# 修复编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright


async def crawl_jd_products(
    keyword: str = "手机",
    pages: int = 1,
    headless: bool = False,
    debug: bool = True
) -> List[Dict]:
    """
    爬取京东商品
    
    Args:
        keyword: 搜索关键词
        pages: 爬取页数
        headless: 是否无头模式
        debug: 是否调试模式
        
    Returns:
        商品列表
    """
    all_products = []
    data_dir = Path("D:/智能数据分析平台/data/raw")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        # 创建上下文
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale='zh-CN',
        )
        
        # 注入反检测
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        page = await context.new_page()
        
        try:
            for page_num in range(1, pages + 1):
                print(f"\n[INFO] 爬取第 {page_num} 页...")
                
                # 构建URL
                url = f"https://search.jd.com/Search?keyword={keyword}&page={page_num}"
                print(f"[INFO] 访问: {url}")
                
                # 访问页面
                await page.goto(url)
                await asyncio.sleep(2)
                
                # 滚动加载
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(0.5)
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)
                
                if debug:
                    # 截图
                    screenshot_path = data_dir / f"debug_page_{page_num}.png"
                    await page.screenshot(path=str(screenshot_path))
                    print(f"[DEBUG] 截图: {screenshot_path}")
                    
                    # 打印URL
                    print(f"[DEBUG] 当前URL: {page.url}")
                
                # 等待商品加载
                try:
                    await page.wait_for_selector('.gl-item', timeout=5000)
                except:
                    print("[WARN] 未找到 .gl-item，尝试其他选择器...")
                    
                # 尝试多种选择器
                selectors = [
                    '.gl-item',
                    '.goods-list-v2 li',
                    '#J_goodsList .gl-item',
                ]
                
                items = []
                for sel in selectors:
                    items = await page.query_selector_all(sel)
                    if items:
                        print(f"[DEBUG] 选择器 '{sel}' 找到 {len(items)} 个元素")
                        break
                        
                if not items:
                    print("[WARN] 未找到任何商品元素")
                    # 检查是否需要登录
                    login_btn = await page.query_selector('.nickname, .login-btn')
                    if login_btn:
                        print("[WARN] 可能需要登录")
                    continue
                    
                # 解析商品
                for i, item in enumerate(items):
                    try:
                        # 标题
                        title_el = await item.query_selector('.p-name em, .p-name a')
                        title = await title_el.inner_text() if title_el else ""
                        
                        # 价格
                        price_el = await item.query_selector('.p-price strong, .p-price i')
                        price_text = await price_el.inner_text() if price_el else "0"
                        price = parse_price(price_text)
                        
                        # 店铺
                        shop_el = await item.query_selector('.p-shop a, .p-shop')
                        shop = await shop_el.inner_text() if shop_el else "未知店铺"
                        
                        # 链接
                        link_el = await item.query_selector('.p-name a, a')
                        href = await link_el.get_attribute('href') if link_el else ""
                        
                        if title:
                            all_products.append({
                                "id": f"jd_{keyword}_{page_num}_{i}",
                                "keyword": keyword,
                                "page": page_num,
                                "title": title.strip(),
                                "price": price,
                                "shop": shop.strip(),
                                "url": f"https:{href}" if href.startswith("//") else href,
                                "platform": "jd",
                                "is_mock": False,
                                "crawl_time": datetime.now().isoformat(),
                            })
                    except Exception as e:
                        if debug:
                            print(f"[DEBUG] 解析商品 {i} 失败: {e}")
                        continue
                        
                print(f"[INFO] 第 {page_num} 页获取 {len(all_products[-len(items):])} 条数据")
                
                # 随机延迟
                await asyncio.sleep(random.uniform(2, 4))
                
        finally:
            await browser.close()
            
    # 保存数据
    if all_products:
        filename = f"jd_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = data_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] 数据已保存: {filepath}")
        
    return all_products


def parse_price(text: str) -> float:
    """解析价格"""
    text = re.sub(r'[¥￥$，,]', '', text)
    match = re.search(r'[\d.]+', text)
    return float(match.group()) if match else 0.0


async def main():
    """主函数"""
    print("=" * 60)
    print("京东商品爬虫 - Playwright 版")
    print("=" * 60)
    
    # 小规模测试：只爬1页
    products = await crawl_jd_products(
        keyword="手机",
        pages=1,
        headless=False,
        debug=True
    )
    
    print(f"\n{'=' * 60}")
    print(f"总计获取 {len(products)} 条真实数据")
    print(f"{'=' * 60}")
    
    if products:
        print(f"\n[INFO] 真实数据示例:")
        for i, p in enumerate(products[:5]):
            print(f"  {i+1}. {p['title'][:40]}... - 价格: {p['price']}")
    else:
        print("\n[WARN] 未获取到数据")
        print("可能原因：")
        print("  1. 需要登录")
        print("  2. 反爬检测")
        print("  3. 页面结构变化")


if __name__ == "__main__":
    asyncio.run(main())
