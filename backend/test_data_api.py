# -*- coding: utf-8 -*-
"""测试数据 API"""
import sys
sys.path.insert(0, r'D:\智能数据分析平台\backend')

print('=== Testing Data API ===')

# Test import
from api.routers.data import router
print('[OK] Data router imported')

# Test database
from database.models import Database
db = Database()
conn = db.get_connection()
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r['name'] for r in cursor.fetchall()]
conn.close()
print('[OK] Database tables: %s' % ', '.join(tables))

# Test data query
from database.service import DataService
service = DataService()
summary = service.get_data_summary()
print('[OK] Data summary: %d total records' % summary.get('total_records', 0))

# Test table listing
from api.routers.data import db as data_db
conn = data_db.get_connection()
cursor = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
)
all_tables = [r['name'] for r in cursor.fetchall()]
conn.close()
print('[OK] All tables: %s' % ', '.join(all_tables))

print()
print('=== Data API tests passed ===')
