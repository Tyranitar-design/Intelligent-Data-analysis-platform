# -*- coding: utf-8 -*-
"""
登录流程定义

预置常见平台的登录流程配置
"""
from typing import Dict, Any

# 预置登录流程配置
LOGIN_FLOWS = {
    "douban": {
        "name": "豆瓣",
        "login_url": "https://accounts.douban.com/passport/login",
        "username_selector": "#username",
        "password_selector": "#password",
        "submit_selector": ".account-form-field-submit .btn",
        "wait_for": ".nav-user-account",
        "check_url": "https://www.douban.com",
        "check_selector": ".nav-user-account",
    },
    "weibo": {
        "name": "微博",
        "login_url": "https://weibo.com/login.php",
        "username_selector": "#loginname",
        "password_selector": "input[type='password']",
        "submit_selector": ".W_btn_a",
        "wait_for": ".gn_name",
        "check_url": "https://weibo.com",
        "check_selector": ".gn_name",
    },
    "zhihu": {
        "name": "知乎",
        "login_url": "https://www.zhihu.com/signin",
        "username_selector": "input[name='username']",
        "password_selector": "input[name='password']",
        "submit_selector": ".SignFlow-submitButton",
        "wait_for": ".AppHeader-profile",
        "check_url": "https://www.zhihu.com",
        "check_selector": ".AppHeader-profile",
    },
    "xiaohongshu": {
        "name": "小红书",
        "login_url": "https://www.xiaohongshu.com/login",
        "username_selector": "input[placeholder='手机号']",
        "password_selector": "input[placeholder='验证码']",
        "submit_selector": ".login-btn",
        "wait_for": ".user-info",
        "check_url": "https://www.xiaohongshu.com",
        "check_selector": ".user-info",
    },
    "bilibili": {
        "name": "B站",
        "login_url": "https://passport.bilibili.com/login",
        "username_selector": "#login-username",
        "password_selector": "#login-passwd",
        "submit_selector": ".btn-login",
        "wait_for": ".header-entry-avatar",
        "check_url": "https://www.bilibili.com",
        "check_selector": ".header-entry-avatar",
    },
}


def get_login_flow(platform: str) -> Dict[str, Any]:
    """获取登录流程配置"""
    return LOGIN_FLOWS.get(platform, {})


def list_supported_platforms() -> Dict[str, str]:
    """列出支持的平台"""
    return {k: v["name"] for k, v in LOGIN_FLOWS.items()}
