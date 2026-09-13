# -*- coding: utf-8 -*-
"""
签名提取器

功能：
- 从 JS 代码中提取签名算法
- 还原请求参数
- 生成签名
"""
import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 尝试导入 PyExecJS
try:
    import execjs
    EXECJS_AVAILABLE = True
except ImportError:
    EXECJS_AVAILABLE = False


class SignatureExtractor:
    """签名提取器"""

    def __init__(self):
        self.js_context = None

    def extract_md5_sign(self, js_code: str) -> Optional[Dict]:
        """提取 MD5 签名"""
        # 查找 MD5 相关代码
        patterns = [
            r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[=:]\s*function\s*\([^)]*\)\s*\{[^}]*md5[^}]*\}",
            r"function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*\{[^}]*md5[^}]*\}",
        ]

        for pattern in patterns:
            match = re.search(pattern, js_code, re.IGNORECASE)
            if match:
                return {
                    "type": "md5",
                    "name": match.group(1),
                    "code": match.group(0),
                }

        return None

    def extract_hmac_sign(self, js_code: str) -> Optional[Dict]:
        """提取 HMAC 签名"""
        patterns = [
            r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[=:]\s*function\s*\([^)]*\)\s*\{[^}]*hmac[^}]*\}",
            r"function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*\{[^}]*hmac[^}]*\}",
        ]

        for pattern in patterns:
            match = re.search(pattern, js_code, re.IGNORECASE)
            if match:
                return {
                    "type": "hmac",
                    "name": match.group(1),
                    "code": match.group(0),
                }

        return None

    def extract_timestamp_param(self, js_code: str) -> Optional[str]:
        """提取时间戳参数名"""
        patterns = [
            r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[:=]\s*Date\.now\(\)",
            r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[:=]\s*new\s+Date\(\)\.getTime\(\)",
            r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[:=]\s*Math\.round\(new\s+Date\(\)\.getTime\(\)\s*/\s*1000\)",
        ]

        for pattern in patterns:
            match = re.search(pattern, js_code)
            if match:
                return match.group(1)

        return None

    def extract_nonce_param(self, js_code: str) -> Optional[str]:
        """提取随机数参数名"""
        patterns = [
            r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[:=]\s*Math\.random\(\)",
            r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[:=]\s*['\"][a-f0-9]{8,}['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, js_code)
            if match:
                return match.group(1)

        return None

    def generate_signature(
        self,
        params: Dict[str, Any],
        secret_key: str,
        algorithm: str = "md5",
    ) -> str:
        """生成签名"""
        # 按 key 排序
        sorted_params = sorted(params.items())
        param_str = "&".join([f"{k}={v}" for k, v in sorted_params])

        # 拼接密钥
        sign_str = f"{param_str}&key={secret_key}"

        if algorithm == "md5":
            return hashlib.md5(sign_str.encode()).hexdigest()
        elif algorithm == "sha1":
            return hashlib.sha1(sign_str.encode()).hexdigest()
        elif algorithm == "sha256":
            return hashlib.sha256(sign_str.encode()).hexdigest()
        else:
            raise ValueError(f"不支持的算法: {algorithm}")

    def execute_signature_js(self, js_code: str, func_name: str, params: Dict) -> Optional[str]:
        """执行 JS 签名函数"""
        if not EXECJS_AVAILABLE:
            logger.warning("PyExecJS 未安装")
            return None

        try:
            ctx = execjs.compile(js_code)
            return ctx.call(func_name, params)
        except Exception as e:
            logger.error(f"执行签名函数失败: {e}")
            return None

    def analyze_api_endpoint(self, js_code: str, endpoint: str) -> Dict[str, Any]:
        """分析 API 端点的参数生成逻辑"""
        analysis = {
            "endpoint": endpoint,
            "method": "GET",
            "params": {},
            "headers": {},
            "signature": None,
        }

        # 查找 API 调用
        patterns = [
            rf"['\"]{re.escape(endpoint)}['\"]",
            rf"url\s*[:=]\s*['\"][^'\"]*{re.escape(endpoint)}['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, js_code)
            if match:
                # 提取周围的代码
                start = max(0, match.start() - 500)
                end = min(len(js_code), match.end() + 500)
                context = js_code[start:end]

                # 分析方法
                if "post" in context.lower():
                    analysis["method"] = "POST"

                # 提取参数
                param_matches = re.finditer(
                    r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[:=]\s*['\"]([^'\"]+)['\"]",
                    context
                )
                for m in param_matches:
                    analysis["params"][m.group(1)] = m.group(2)

                # 提取签名
                sig = self.extract_md5_sign(context) or self.extract_hmac_sign(context)
                if sig:
                    analysis["signature"] = sig

                break

        return analysis
