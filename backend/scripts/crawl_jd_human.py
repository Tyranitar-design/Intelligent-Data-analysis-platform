# -*- coding: utf-8 -*-
"""
京东 Playwright 爬虫 - 人机协作版
完整工作流：小彩打开登录页 → 小宇扫码登录 → 小彩继续爬取

作者: 小彩 💫
日期: 2026-04-25
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


async def human_collaboration_crawler(
    keyword: str = "手机",
    pages: int = 1,
    wait_login_seconds: int = 300  # 等待登录时间（5分钟）
) -> List[Dict]:
    """
    人机协作爬虫 - 完整版
    
    工作流程：
    1. 打开京东搜索页
    2. 检测是否需要登录
    3. 如果需要，跳转到登录页面
    4. 等待小宇手动登录（5分钟）
    5. 登录成功后，自动爬取数据
    
    Args:
        keyword: 搜索关键词
        pages: 爬取页数
        wait_login_seconds: 等待登录时间（秒）
        
    Returns:
        商品列表
    """
    all_products = []
    data_dir = Path("D:/智能数据分析平台/data/raw")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        # 启动浏览器（有界面）
        browser = await p.chromium.launch(
            headless=False,  # 必须有界面
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
            # ===== 第1步：尝试访问搜索页 =====
            print("\n" + "=" * 60)
            print("京东商品爬虫 - 人机协作版")
            print("=" * 60)
            print(f"\n关键词: {keyword}")
            print(f"页数: {pages}")
            
            url = f"https://search.jd.com/Search?keyword={keyword}&page=1"
            print(f"\n[STEP 1] 访问搜索页面...")
            print(f"[URL] {url}")
            
            await page.goto(url)
            await asyncio.sleep(2)
            
            # ===== 第2步：检测是否需要登录 =====
            print(f"\n[STEP 2] 检测登录状态...")
            current_url = page.url
            print(f"[URL] {current_url}")
            
            needs_login = "passport.jd.com" in current_url or "login" in current_url.lower()
            
            if needs_login:
                print("\n" + "!" * 60)
                print("需要登录！进入人机协作模式")
                print("!" * 60)
                
                # 打印登录等待信息
                print(f"\n[STEP 3] 等待小宇手动登录...")
                print(f"[INFO] 等待时间: {wait_login_seconds} 秒 ({wait_login_seconds // 60} 分钟)")
                print("\n" + "-" * 60)
                print("请在浏览器中完成以下操作：")
                print("  1. 使用手机扫码登录")
                print("  2. 完成验证码验证（如有）")
                print("  3. 登录成功后浏览器会自动继续")
                print("-" * 60 + "\n")
                
                # 等待用户登录
                login_start_time = datetime.now()
                
                # 每10秒检查一次是否登录成功
                checked = False
                for i in range(wait_login_seconds // 10):
                    await asyncio.sleep(10)
                    
                    # 检查当前URL
                    current_url = page.url
                    
                    if "passport.jd.com" not in current_url and "login" not in current_url.lower():
                        print(f"\n[OK] 登录成功！检测到已离开登录页面")
                        print(f"[URL] {current_url}")
                        checked = True
                        break
                    else:
                        elapsed = (datetime.now() - login_start_time).seconds
                        remaining = wait_login_seconds - elapsed
                        if i % 3 == 0:  # 每30秒打印一次
                            print(f"[WAIT] 等待登录中... 剩余 {remaining} 秒")
                
                if not checked:
                    print("\n[WARN] 登录等待超时，将尝试继续...")
                    
            else:
                print("[OK] 无需登录，已在登录状态")
                
            # ===== 第3步：检查是否成功访问搜索页 =====
            print(f"\n[STEP 4] 验证搜索页面访问...")
            
            # 如果还在登录页，尝试手动访问
            if "passport.jd.com" in page.url or "login" in page.url.lower():
                print("[WARN] 仍在登录页面，尝试刷新...")
                await page.goto(url)
                await asyncio.sleep(3)
            
            # 再次检查
            if "passport.jd.com" in page.url:
                print("[ERROR] 无法访问搜索页面，请重新登录")
                return []
                
            print(f"[OK] 当前页面: {page.url[:60]}...")
            
            # ===== 第4步：爬取数据 =====
            print(f"\n[STEP 5] 开始爬取数据...")
            
            for page_num in range(1, pages + 1):
                print(f"\n  --- 第 {page_num} 页 ---")
                
                # 构建URL
                url = f"https://search.jd.com/Search?keyword={keyword}&page={page_num}"
                await page.goto(url)
                await asyncio.sleep(2)
                
                # 滚动加载
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(0.5)
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)
                
                # 等待商品加载
                try:
                    await page.wait_for_selector('.gl-item', timeout=5000)
                except:
                    print(f"[WARN] 页面加载可能有问题，继续尝试...")
                
                # 获取商品
                items = await page.query_selector_all('.gl-item, #J_goodsList .gl-item')
                
                if not items:
                    print(f"[WARN] 未获取到商品数据")
                    continue
                    
                print(f"[INFO] 找到 {len(items)} 个商品")
                
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
                        link_el = await item.query_selector('.p-name a')
                        href = await link_el.get_attribute('href') if link_el else ""
                        
                        if title:
                            all_products.append({
                                "id": f"jd_{keyword}_{page_num}_{i}",
                                "keyword": keyword,
                                "page": page_num,
                                "title": title.strip(),
                                "price": price,
                                "shop": shop.strip() if shop else "未知店铺",
                                "url": f"https:{href}" if href.startswith("//") else href,
                                "platform": "jd",
                                "is_mock": False,
                                "crawl_time": datetime.now().isoformat(),
                            })
                    except Exception as e:
                        continue
                        
                print(f"[OK] 第 {page_num} 页获取 {len(items)} 条数据")
                
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
    """主函数 - 人机协作模式"""
    print("\n" + "#" * 60)
    print("# 京东商品爬虫 - 人机协作版")
    print("#" * 60)
    print("\n[INFO] 爬虫将启动浏览器并尝试访问京东搜索页")
    print("[INFO] 如果需要登录，会等待小宇扫码登录后继续")
    print("[INFO] 爬取完成后数据会自动保存\n")
    
    products = await human_collaboration_crawler(
        keyword="手机",
        pages=1,  # 先测试1页
        wait_login_seconds=300  # 等待5分钟
    )
    
    print(f"\n{'=' * 60}")
    print(f"爬取完成！共获取 {len(products)} 条真实数据")
    print(f"{'=' * 60}")
    
    if products:
        print(f"\n[INFO] 真实数据示例:")
        for i, p in enumerate(products[:5]):
            print(f"  {i+1}. {p['title'][:35]}... - 价格: {p['price']}")
    else:
        print("\n[WARN] 未获取到数据")


if __name__ == "__main__":
    asyncio.run(main())