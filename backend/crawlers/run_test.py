# -*- coding: utf-8 -*-
"""
爬虫测试脚本 - 快速验证爬虫功能

使用方法:
    python run_test.py
"""
import asyncio
import json

from crawlers.finance.eastmoney import EastMoneyStockCrawler
from crawlers.finance.sina import SinaFinanceCrawler, MAJOR_INDEXES
from crawlers.news.netease import NeteaseNewsCrawler
from crawlers.ecommerce.crawler import TaobaoCrawler, JDCrawler
from crawlers.services import CrawlService


def print_separator(title: str = ""):
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


async def test_finance():
    """测试金融爬虫"""
    print_separator("金融数据爬虫测试")

    # 测试新浪财经指数
    print("\n[1] 新浪财经 - 上证指数")
    crawler = SinaFinanceCrawler()
    result = await crawler.crawl_index("sh000001")
    print(f"    状态: {'成功' if result.success else '失败'}")
    print(f"    消息: {result.message}")
    if result.data:
        data = result.data[0]
        print(f"    指数: {data.get('name', 'N/A')}")
        print(f"    当前点位: {data.get('price', 'N/A')}")

    # 测试主要指数批量
    print("\n[2] 新浪财经 - 主要指数批量")
    result = await crawler.crawl_batch_index(list(MAJOR_INDEXES.keys()))
    print(f"    状态: {'成功' if result.success else '失败'}")
    print(f"    消息: {result.message}")
    print(f"    数据条数: {result.count}")

    # 测试东方财富股票（如果网络允许）
    print("\n[3] 东方财富 - 股票K线数据")
    crawler2 = EastMoneyStockCrawler()
    result = await crawler2.crawl("600000", days=5)
    print(f"    状态: {'成功' if result.success else '失败'}")
    print(f"    消息: {result.message}")
    print(f"    数据条数: {result.count}")
    if result.data:
        print(f"    最新数据: {result.data[0]}")


async def test_news():
    """测试新闻爬虫"""
    print_separator("新闻数据爬虫测试")

    crawler = NeteaseNewsCrawler()

    # 测试科技新闻
    print("\n[1] 网易新闻 - 科技分类")
    result = await crawler.crawl_category("tech", max_count=10)
    print(f"    状态: {'成功' if result.success else '失败'}")
    print(f"    消息: {result.message}")
    print(f"    数据条数: {result.count}")
    if result.data:
        print(f"    第一条: {result.data[0].get('title', 'N/A')[:50]}...")

    # 测试财经新闻
    print("\n[2] 网易新闻 - 财经分类")
    result = await crawler.crawl_category("finance", max_count=10)
    print(f"    状态: {'成功' if result.success else '失败'}")
    print(f"    数据条数: {result.count}")


async def test_ecommerce():
    """测试电商爬虫"""
    print_separator("电商数据爬虫测试")

    # 测试淘宝
    print("\n[1] 淘宝商品数据")
    crawler = TaobaoCrawler()
    result = await crawler.crawl(["手机", "电脑"], pages=1)
    print(f"    状态: {'成功' if result.success else '失败'}")
    print(f"    消息: {result.message}")
    print(f"    数据条数: {result.count}")
    if result.data:
        print(f"    示例商品: {result.data[0].get('title', 'N/A')[:40]}...")
        print(f"    价格: ¥{result.data[0].get('price', 'N/A')}")

    # 测试京东
    print("\n[2] 京东商品数据")
    crawler2 = JDCrawler()
    result = await crawler2.crawl(["耳机"], pages=1)
    print(f"    状态: {'成功' if result.success else '失败'}")
    print(f"    数据条数: {result.count}")


async def test_service():
    """测试服务层"""
    print_separator("服务层测试")

    service = CrawlService()

    # 生成模拟数据
    print("\n[1] 生成模拟金融数据")
    data = CrawlService.generate_sample_finance_data(days=10)
    print(f"    生成条数: {len(data)}")
    print(f"    最新: {data[-1] if data else 'N/A'}")

    print("\n[2] 生成模拟电商数据")
    data = CrawlService.generate_sample_ecommerce_data(keywords=["手机"], pages=1)
    print(f"    生成条数: {len(data)}")
    if data:
        print(f"    示例: {data[0].get('title', 'N/A')}")

    # 历史记录
    print("\n[3] 爬取历史记录")
    history = service.get_history(limit=5)
    print(f"    历史记录数: {len(history)}")


async def main():
    """主函数"""
    print_separator("爬虫功能测试")
    print("智能数据分析平台 - 爬虫模块测试")
    print()

    try:
        await test_finance()
    except Exception as e:
        print(f"    错误: {e}")

    try:
        await test_news()
    except Exception as e:
        print(f"    错误: {e}")

    try:
        await test_ecommerce()
    except Exception as e:
        print(f"    错误: {e}")

    try:
        await test_service()
    except Exception as e:
        print(f"    错误: {e}")

    print_separator("测试完成")
    print("如需进一步测试，请查看 data/raw 目录中的爬取数据")


if __name__ == "__main__":
    asyncio.run(main())
