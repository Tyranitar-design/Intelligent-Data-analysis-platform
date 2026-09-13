#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建超级用户脚本
运行: python create_superuser.py
"""
import os
import sys

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
os.environ.setdefault('USE_SQLITE', 'true')

import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = 'admin'
email = 'admin@example.com'
password = 'admin123'

if User.objects.filter(username=username).exists():
    print(f"超级用户 '{username}' 已存在")
else:
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"超级用户 '{username}' 创建成功！")
