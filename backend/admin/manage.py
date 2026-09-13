# -*- coding: utf-8 -*-
"""
Django Admin Entry Point
智能数据分析平台 - Django 管理后台
"""
import os
import sys

# Windows 编码支持
if sys.platform == 'win32':
    import subprocess
    subprocess.run(['chcp', '65001'], shell=True, capture_output=True)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
os.environ.setdefault('USE_SQLITE', 'true')  # 默认使用 SQLite 开发

import django
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
    execute_from_command_line()