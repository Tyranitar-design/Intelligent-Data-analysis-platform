# -*- coding: utf-8 -*-
"""
登录态认证模块

功能：
- Cookie 持久化存储
- Token 自动刷新
- 多账号管理
- 登录状态检测
- CDP 登录交互
"""
from .auth_manager import AuthManager
from .cookie_store import CookieStore

__all__ = ['AuthManager', 'CookieStore']
