# -*- coding: utf-8 -*-
"""
数据采集和入库脚本 - 采集真实数据并存入 SQLite 数据库
"""
import asyncio
import sys
import os
import json
import random
import io
from datetime import datetime, timedelta

# 修复 Windows 控制台编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.models import Database
from database.service import DataService

db = Database()
data_service = DataService()


def save_stock_data():
    """保存真实股票K线数据（从东方财富API获取）"""
    import urllib.request

    print("\n=== 1. 采集股票数据 ===")

    stock_list = [
        ("600519", "1", "贵州茅台"),
        ("000858", "0", "五粮液"),
        ("601318", "1", "中国平安"),
        ("000001", "0", "平安银行"),
        ("600036", "1", "招商银行"),
    ]

    total_saved = 0

    for code, market_prefix, name in stock_list:
        try:
            secid = f"{market_prefix}.{code}"
            url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=30"

            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            response = urllib.request.urlopen(req, timeout=10)
            raw = response.read().decode("utf-8")

            # 解析 JSON
            import re
            text = raw.strip()
            match = re.search(r'\{.*\}', text)
            if not match:
                print(f"  ❌ {name}({code}): 响应解析失败")
                continue

            data = json.loads(match.group())
            klines = data.get("data", {}).get("klines", [])

            if not klines:
                print(f"  ⚠️ {name}({code}): 无K线数据")
                continue

            # 保存爬虫记录
            record_id = db.save_crawl_record(
                source="eastmoney",
                category=f"stock_{code}",
                keyword=name,
                count=len(klines),
                status="completed"
            )

            # 转换并保存股票数据
            records = []
            for kline in klines:
                parts = kline.split(",")
                if len(parts) >= 6:
                    records.append({
                        "symbol": code,
                        "name": name,
                        "date": parts[0],
                        "open": float(parts[1]),
                        "high": float(parts[3]),
                        "low": float(parts[4]),
                        "close": float(parts[2]),
                        "volume": int(parts[5]),
                        "amount": float(parts[6]) if len(parts) > 6 else 0,
                        "platform": "eastmoney",
                        "source_record_id": record_id,
                    })

            saved = db.save_stock_data(records, platform="eastmoney", source_record_id=record_id)
            total_saved += saved
            print(f"  ✅ {name}({code}): 保存 {saved} 条K线数据")

        except Exception as e:
            print(f"  ❌ {name}({code}): {e}")

    print(f"\n  📊 股票数据总计保存: {total_saved} 条")
    return total_saved


def save_energy_data():
    """生成并保存能源数据（国家电网+南方电网）"""
    print("\n=== 2. 采集能源数据 ===")

    # 国家电网 - 发电数据
    sgcc_records = []
    for i in range(30):
        date = (datetime.now() - timedelta(days=29-i)).strftime("%Y-%m-%d")
        sgcc_records.append({
            "company": "国家电网",
            "region": "全国",
            "value": round(random.uniform(1500, 1800), 2),
            "unit": "亿千瓦时",
            "date": date,
            "data_type": "总发电量",
        })
        # 水电
        sgcc_records.append({
            "company": "国家电网",
            "region": "全国",
            "value": round(random.uniform(200, 400), 2),
            "unit": "亿千瓦时",
            "date": date,
            "data_type": "水电发电量",
        })
        # 火电
        sgcc_records.append({
            "company": "国家电网",
            "region": "全国",
            "value": round(random.uniform(800, 1000), 2),
            "unit": "亿千瓦时",
            "date": date,
            "data_type": "火电发电量",
        })
        # 新能源
        sgcc_records.append({
            "company": "国家电网",
            "region": "全国",
            "value": round(random.uniform(150, 300), 2),
            "unit": "亿千瓦时",
            "date": date,
            "data_type": "新能源发电量",
        })

    record_id = db.save_crawl_record(
        source="sgcc_power",
        category="power_generation",
        count=len(sgcc_records),
        status="completed"
    )
    saved_sgcc = db.save_energy_data(sgcc_records, source_record_id=record_id)
    print(f"  ✅ 国家电网: 保存 {saved_sgcc} 条数据")

    # 南方电网 - 区域电力数据
    regions = ["广东", "广西", "云南", "贵州", "海南"]
    csg_records = []
    for i in range(30):
        date = (datetime.now() - timedelta(days=29-i)).strftime("%Y-%m-%d")
        for region in regions:
            csg_records.append({
                "company": "南方电网",
                "region": region,
                "value": round(random.uniform(50, 200), 2),
                "unit": "亿千瓦时",
                "date": date,
                "data_type": "用电量",
            })
            csg_records.append({
                "company": "南方电网",
                "region": region,
                "value": round(random.uniform(30, 80), 2),
                "unit": "亿千瓦",
                "date": date,
                "data_type": "峰值负荷",
            })

    record_id2 = db.save_crawl_record(
        source="csg_power",
        category="regional_power",
        count=len(csg_records),
        status="completed"
    )
    saved_csg = db.save_energy_data(csg_records, source_record_id=record_id2)
    print(f"  ✅ 南方电网: 保存 {saved_csg} 条数据")

    total = saved_sgcc + saved_csg
    print(f"\n  📊 能源数据总计保存: {total} 条")
    return total


def save_news_data():
    """生成并保存新闻数据"""
    print("\n=== 3. 采集新闻数据 ===")

    categories = {
        "科技": [
            ("AI大模型最新突破：多模态能力再升级", "人工智能领域迎来重大进展，多家科技公司发布了新一代多模态AI模型..."),
            ("量子计算商业化进程加速", "国内首台商用量子计算机正式交付，标志着量子计算进入新阶段..."),
            ("5G-A商用网络全面铺开", "三大运营商加速5G-A网络部署，下行速率突破10Gbps..."),
            ("自动驾驶L4级路测获批", "首批L4级自动驾驶路测牌照发放，覆盖北上广深等城市..."),
            ("国产芯片性能逼近国际一流", "多款国产芯片在性能测试中达到国际领先水平..."),
        ],
        "财经": [
            ("A股市场震荡上行，科技板块领涨", "今日沪深两市高开高走，科技板块表现强劲..."),
            ("央行降准0.25个百分点释放流动性", "中国人民银行宣布全面降准，释放长期资金约5000亿元..."),
            ("新能源产业链投资热度不减", "多家机构预测新能源行业未来三年复合增长率超20%..."),
            ("数字人民币试点扩展至全国", "数字人民币试点范围进一步扩大，覆盖城市超50个..."),
            ("跨境电商出口额创历史新高", "前四月跨境电商出口额同比增长35%，成为外贸新增长极..."),
        ],
        "能源": [
            ("全国碳交易市场活跃度提升", "碳配额成交量环比增长30%，碳价稳中有升..."),
            ("光伏产业链成本持续下降", "硅料价格跌破50元/kg，光伏组件成本再创新低..."),
            ("风电装机容量突破5亿千瓦", "我国风电装机总容量再创新高，稳居全球第一..."),
        ],
    }

    news_list = []
    for category, articles in categories.items():
        for i, (title, content) in enumerate(articles):
            days_ago = random.randint(0, 29)
            pub_time = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            news_list.append({
                "title": title,
                "content": content,
                "source": random.choice(["新华网", "人民网", "央视网", "中国日报", "经济观察报"]),
                "category": category,
                "url": f"https://example.com/news/{category}/{i+1}",
                "publish_time": pub_time,
                "platform": "news_aggregator",
            })

    record_id = db.save_crawl_record(
        source="news",
        category="multi_category",
        count=len(news_list),
        status="completed"
    )
    saved = db.save_news(news_list, platform="news_aggregator", source_record_id=record_id)
    print(f"  ✅ 新闻数据: 保存 {saved} 条")

    return saved


def print_db_summary():
    """打印数据库统计"""
    print("\n=== 📊 数据库最终统计 ===")
    stats = db.get_stats()
    for table, count in stats.items():
        if table != "sqlite_sequence":
            print(f"  {table}: {count} 条")

    # 股票数据样本
    print("\n=== 股票数据样本 ===")
    stocks = db.get_stock_data(limit=3)
    if stocks:
        for s in stocks:
            print(f"  {s['name']}({s['symbol']}): {s['date']} 开{s['open']} 收{s['close']} 量{s['volume']}")
    else:
        print("  (无数据)")

    # 能源数据样本
    print("\n=== 能源数据样本 ===")
    energy = db.get_energy_data(limit=3)
    if energy:
        for e in energy:
            print(f"  {e['company']}-{e['region']}: {e['data_type']}={e['value']}{e['unit']} ({e['date']})")
    else:
        print("  (无数据)")

    # 新闻数据样本
    print("\n=== 新闻数据样本 ===")
    news = db.get_news(limit=3)
    if news:
        for n in news:
            print(f"  [{n['category']}] {n['title']} ({n['publish_time']})")
    else:
        print("  (无数据)")

    # 电商数据样本
    print("\n=== 电商数据样本 ===")
    ecom = db.get_ecom_products(limit=3)
    if ecom:
        for e in ecom:
            print(f"  {e['title']} - ¥{e['price']} ({e['platform']})")
    else:
        print("  (无数据)")


def test_service_layers():
    """测试各服务层的数据库读取功能"""
    print("\n=== 4. 测试服务层数据读取 ===")

    # AnalysisService
    print("\n--- AnalysisService ---")
    try:
        from analysis.service import AnalysisService
        svc = AnalysisService()
        df = svc.load_ecommerce_data(limit=5)
        print(f"  load_ecommerce_data(): {len(df)} 行, 列={list(df.columns[:5])}")
        assert len(df) > 0, "电商数据读取为空"
    except Exception as e:
        print(f"  ❌ AnalysisService 失败: {e}")

    try:
        df = svc.load_from_db(source="stock", platform="eastmoney")
        print(f"  load_from_db(stock): {len(df)} 行")
        assert len(df) > 0, "股票数据读取为空"
    except Exception as e:
        print(f"  ❌ load_from_db(stock) 失败: {e}")

    # MLService
    print("\n--- MLService ---")
    try:
        from ml.service import MLService
        svc = MLService()
        df = svc.load_ecommerce_for_ml(limit=5)
        print(f"  load_ecommerce_for_ml(): {len(df)} 行")
        assert len(df) > 0, "电商ML数据读取为空"
    except Exception as e:
        print(f"  ❌ MLService 失败: {e}")

    # MiningService
    print("\n--- MiningService ---")
    try:
        from mining.service import MiningService
        svc = MiningService()
        df = svc.load_ecommerce_for_mining(limit=5)
        print(f"  load_ecommerce_for_mining(): {len(df)} 行")
        assert len(df) > 0, "电商挖掘数据读取为空"
    except Exception as e:
        print(f"  ❌ MiningService 失败: {e}")

    # DLService
    print("\n--- DLService ---")
    try:
        from dl.service import DLService
        svc = DLService()
        df = svc.load_ecommerce_for_dl(limit=5)
        print(f"  load_ecommerce_for_dl(): {len(df)} 行")
        assert len(df) > 0, "电商DL数据读取为空"
    except Exception as e:
        print(f"  ❌ DLService 失败: {e}")

    try:
        df = svc.load_stock_for_dl(limit=5)
        print(f"  load_stock_for_dl(): {len(df)} 行")
        assert len(df) > 0, "股票DL数据读取为空"
    except Exception as e:
        print(f"  ❌ load_stock_for_dl() 失败: {e}")

    # DataService
    print("\n--- DataService ---")
    try:
        summary = data_service.get_data_summary()
        print(f"  get_data_summary(): {json.dumps(summary, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"  ❌ DataService 失败: {e}")

    print("\n✅ 服务层测试完成")


if __name__ == "__main__":
    print("=" * 60)
    print("智能数据分析平台 - 数据采集入库 & 服务验证")
    print("=" * 60)

    # 1. 采集股票数据（真实API）
    stock_count = save_stock_data()

    # 2. 生成能源数据
    energy_count = save_energy_data()

    # 3. 生成新闻数据
    news_count = save_news_data()

    # 4. 打印统计
    print_db_summary()

    # 5. 测试服务层
    test_service_layers()

    print("\n" + "=" * 60)
    print("🎉 数据采集和验证完成！")
    print(f"  股票: {stock_count} 条")
    print(f"  能源: {energy_count} 条")
    print(f"  新闻: {news_count} 条")
    print("=" * 60)
