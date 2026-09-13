# -*- coding: utf-8 -*-
"""
Cookie 加密模块

功能：
- Cookie 值加密
- Cookie 值解密
- 密钥管理
"""
import base64
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class CookieEncryptor:
    """Cookie 加密器"""

    def __init__(self, key: str = None):
        """
        初始化加密器

        Args:
            key: 加密密钥，如果不提供则使用环境变量或生成新密钥
        """
        if key:
            self.key = key.encode()
        else:
            # 从环境变量获取或使用默认密钥
            env_key = os.getenv("COOKIE_ENCRYPTION_KEY")
            if env_key:
                self.key = env_key.encode()
            else:
                # 生成新密钥并保存到环境变量
                self.key = Fernet.generate_key()
                os.environ["COOKIE_ENCRYPTION_KEY"] = self.key.decode()
                logger.warning("使用新生成的 Cookie 加密密钥，建议设置环境变量 COOKIE_ENCRYPTION_KEY")

        self.fernet = Fernet(self.key)

    def encrypt(self, value: str) -> str:
        """加密值"""
        try:
            encrypted = self.fernet.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"加密失败: {e}")
            return value

    def decrypt(self, encrypted_value: str) -> Optional[str]:
        """解密值"""
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_value.encode())
            return self.fernet.decrypt(encrypted).decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            return None

    def encrypt_cookie(self, cookie: dict) -> dict:
        """加密 Cookie"""
        encrypted_cookie = cookie.copy()
        if "value" in encrypted_cookie:
            encrypted_cookie["value"] = self.encrypt(encrypted_cookie["value"])
        return encrypted_cookie

    def decrypt_cookie(self, encrypted_cookie: dict) -> dict:
        """解密 Cookie"""
        cookie = encrypted_cookie.copy()
        if "value" in cookie:
            decrypted = self.decrypt(cookie["value"])
            if decrypted:
                cookie["value"] = decrypted
        return cookie
