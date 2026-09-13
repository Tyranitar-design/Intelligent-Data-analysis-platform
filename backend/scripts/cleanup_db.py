# -*- coding: utf-8 -*-
"""
清理数据库中的脏数据 + 补采五粮液
"""
import sys
import os
import json
import io
import urllib.request
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.models import Database

db = Database()

# 1. 清理 ecom_products 中不是电商的脏数据
print("=== 清理脏数据 ===")
conn = db.get_connection()

# 删除 platform 为 stock/energy 的脏数据
rows = conn.execute("DELETE FROM ecom_products WHERE platform IN ('stock', 'energy', 'sgcc', 'csg')").fetchall()
conn.commit()
remaining = conn.execute("SELECT COUNT(*) FROM ecom_products").fetchone()[0]
print(f"  电商表清理完成，剩余 {remaining} 条")

# 删除 stock_data 中的测试假数据 (platform='test')
rows2 = conn.execute("DELETE FROM stock_data WHERE platform = 'test'").fetchall()
conn.commit()
stock_count = conn.execute("SELECT COUNT(*) FROM stock_data").fetchone()[0]
print(f"  股票表清理完成，剩余 {stock_count} 条")

# 2. 补采五粮液
print("\n=== 补采五粮液 ===")
try:
    code = "000858"
    secid = f"0.{code}"
    url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=30"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    response = urllib.request.urlopen(req, timeout=10)
    raw = response.read().decode("utf-8")
    match = re.search(r'\{.*\}', raw.strip())
    if match:
        data = json.loads(match.group())
        klines = data.get("data", {}).get("klines", [])
        if klines:
            record_id = db.save_crawl_record(source="eastmoney", category=f"stock_{code}", keyword="五粮液", count=len(klines))
            records = []
            for kline in klines:
                parts = kline.split(",")
                if len(parts) >= 6:
                    records.append({
                        "symbol": code, "name": "五粮液", "date": parts[0],
                        "open": float(parts[1]), "high": float(parts[3]), "low": float(parts[4]),
                        "close": float(parts[2]), "volume": int(parts[5]),
                        "amount": float(parts[6]) if len(parts) > 6 else 0,
                        "platform": "eastmoney", "source_record_id": record_id,
                    })
            saved = db.save_stock_data(records, platform="eastmoney", source_record_id=record_id)
            print(f"  五粮液: 保存 {saved} 条")
except Exception as e:
    print(f"  五粮液补采失败: {e}")

# 3. 最终统计
print("\n=== 最终数据库统计 ===")
stats = db.get_stats()
for table, count in stats.items():
    if table not in ("sqlite_sequence",):
        print(f"  {table}: {count} 条")

conn.close()
print("\nDone!")
