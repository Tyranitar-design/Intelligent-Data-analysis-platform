# -*- coding: utf-8 -*-
import os, glob, json

files = glob.glob('D:/智能数据分析平台/backend/data/raw/jd_*.json')
files.sort(key=os.path.getmtime, reverse=True)

print("最新的京东数据文件:")
for f in files[:5]:
    with open(f, 'r', encoding='utf-8') as fp:
        data = json.load(fp)
    print(f"  {os.path.basename(f)}")
    print(f"    条数: {len(data)}")
    if data:
        title = data[0].get('title', 'N/A')[:30]
        is_mock = data[0].get('is_mock', 'N/A')
        print(f"    标题: {title}")
        print(f"    真实数据: {is_mock}")
    print()