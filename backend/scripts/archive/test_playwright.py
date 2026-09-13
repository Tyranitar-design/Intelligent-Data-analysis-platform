# -*- coding: utf-8 -*-
"""
快速测试 Playwright 爬虫能否获取真实数据
无需等待登录，只测试页面访问和数据解析
"""
import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from crawlers.ecommerce.playwright_crawler import PlaywrightEcommerceCrawler

async def quick_test():
    """快速测试 - 无需登录"""
    print("=" * 60)
    print("快速测试 Playwright 爬虫")
    print("=" * 60)
    
    crawler = PlaywrightEcommerceCrawler(
        platform="jd",
        headless=False,  # 需要显示浏览器
        wait_for_login=10  # 短时间等待
    )
    
    try:
        # 启动浏览器
        print("\n[INFO] 启动浏览器...")
        await crawler.start()
        
        # 直接访问搜索页面（不等待登录）
        keyword = "手机"
        page = 1
        url = crawler.config['search_url'].format(keyword=keyword, page=page)
        
        print(f"\n[INFO] 访问: {url}")
        await crawler.page.goto(url)
        await asyncio.sleep(3)
        
        # 滚动页面
        await crawler._scroll_page()
        await asyncio.sleep(2)
        
        # 解析数据
        print("\n[INFO] 解析页面数据...")
        products = await crawler._parse_products(keyword, page)
        
        print(f"\n[OK] 成功获取 {len(products)} 条数据")
        
        if products:
            print(f"\n真实数据 vs 模拟数据: is_mock = {products[0].get('is_mock', True)}")
            print(f"\n前 3 条数据:")
            for i, item in enumerate(products[:3]):
                title = item.get('title', 'N/A')[:40]
                price = item.get('price', 0)
                print(f"  {i+1}. {title}... - 价格:{price}")
        else:
            print("\n[WARN] 未获取到数据，可能是反爬或页面结构变化")
            
        # 保存数据
        if products:
            await crawler._save_data(products, keyword)
            
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await crawler.close()

if __name__ == "__main__":
    asyncio.run(quick_test())