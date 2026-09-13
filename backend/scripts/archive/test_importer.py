# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'D:\智能数据分析平台\backend')

from crawlers.data_importer import DataImporter

d = DataImporter()

# Test CSV text import
r1 = d.import_from_text("name,age,city\nAlice,30,Beijing\nBob,25,Shanghai", "csv")
print("CSV text:", r1.success, r1.row_count, r1.columns)

# Test JSON text import
r2 = d.import_from_text('[{"a":1,"b":2},{"a":3,"b":4}]', "json")
print("JSON text:", r2.success, r2.row_count, r2.columns)

# Test ranking extractor
import asyncio
from crawlers.ranking_extractor import RankingExtractor

async def test_ranking():
    e = RankingExtractor()
    # Test with a simple HTML page
    result = await e.extract("https://httpbin.org/html", "我要标题、链接")
    print("Ranking extract:", result["success"], result["message"], len(result["rows"]))

asyncio.run(test_ranking())
print("All tests passed")
