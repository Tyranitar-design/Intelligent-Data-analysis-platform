# -*- coding: utf-8 -*-
"""
JS 逆向引擎

功能：
- JS 代码获取与分析
- AST 解析
- 参数还原
- 本地执行
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# 尝试导入 esprima
try:
    import esprima
    ESPRIMA_AVAILABLE = True
except ImportError:
    ESPRIMA_AVAILABLE = False

# 尝试导入 PyExecJS
try:
    import execjs
    EXECJS_AVAILABLE = True
except ImportError:
    EXECJS_AVAILABLE = False


class JSReverseEngine:
    """JS 逆向引擎"""

    def __init__(self):
        self.js_context = None
        if EXECJS_AVAILABLE:
            try:
                self.js_context = execjs.compile("")
            except:
                pass

    async def fetch_js(self, js_url: str) -> Optional[str]:
        """获取 JS 文件内容"""
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(js_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "*/*",
                })
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            logger.error(f"获取 JS 失败: {e}")
            return None

    def parse_ast(self, js_code: str) -> Optional[Dict]:
        """解析 AST"""
        if not ESPRIMA_AVAILABLE:
            logger.warning("esprima 未安装，无法解析 AST")
            return None

        try:
            ast = esprima.parseScript(js_code, options={"range": True, "loc": True})
            return ast.toDict()
        except Exception as e:
            logger.error(f"AST 解析失败: {e}")
            return None

    def find_functions(self, ast: Dict, pattern: str = None) -> List[Dict]:
        """查找函数定义"""
        if not ast:
            return []

        functions = []

        def traverse(node):
            if not isinstance(node, dict):
                return

            if node.get("type") == "FunctionDeclaration":
                func_info = {
                    "name": node.get("id", {}).get("name", "anonymous"),
                    "params": [p.get("name", "") for p in node.get("params", [])],
                    "loc": node.get("loc", {}),
                }
                if pattern and pattern.lower() not in func_info["name"].lower():
                    pass
                else:
                    functions.append(func_info)

            for value in node.values():
                if isinstance(value, list):
                    for item in value:
                        traverse(item)
                elif isinstance(value, dict):
                    traverse(value)

        traverse(ast)
        return functions

    def find_variables(self, ast: Dict, pattern: str = None) -> List[Dict]:
        """查找变量定义"""
        if not ast:
            return []

        variables = []

        def traverse(node):
            if not isinstance(node, dict):
                return

            if node.get("type") == "VariableDeclarator":
                var_info = {
                    "name": node.get("id", {}).get("name", ""),
                    "init": self._extract_init(node.get("init")),
                }
                if pattern and pattern.lower() not in var_info["name"].lower():
                    pass
                else:
                    variables.append(var_info)

            for value in node.values():
                if isinstance(value, list):
                    for item in value:
                        traverse(item)
                elif isinstance(value, dict):
                    traverse(value)

        traverse(ast)
        return variables

    def _extract_init(self, init_node) -> str:
        """提取初始化值"""
        if not init_node:
            return ""
        if isinstance(init_node, dict):
            if init_node.get("type") == "Literal":
                return str(init_node.get("value", ""))
            if init_node.get("type") == "ArrayExpression":
                return "[...]"
            if init_node.get("type") == "ObjectExpression":
                return "{...}"
        return "..."

    def extract_function_code(self, js_code: str, func_name: str) -> Optional[str]:
        """提取函数代码"""
        # 使用正则提取函数
        patterns = [
            rf"function\s+{re.escape(func_name)}\s*\([^)]*\)\s*\{{[\s\S]*?\}}",
            rf"{re.escape(func_name)}\s*=\s*function\s*\([^)]*\)\s*\{{[\s\S]*?\}}",
            rf"{re.escape(func_name)}\s*:\s*function\s*\([^)]*\)\s*\{{[\s\S]*?\}}",
        ]

        for pattern in patterns:
            match = re.search(pattern, js_code)
            if match:
                return match.group(0)

        return None

    def execute_js(self, js_code: str, func_name: str = None, args: List = None) -> Any:
        """执行 JS 代码"""
        if not EXECJS_AVAILABLE:
            logger.warning("PyExecJS 未安装，无法执行 JS")
            return None

        try:
            ctx = execjs.compile(js_code)
            if func_name:
                return ctx.call(func_name, *(args or []))
            return ctx.eval("this")
        except Exception as e:
            logger.error(f"JS 执行失败: {e}")
            return None

    def extract_signature_params(self, js_code: str) -> List[Dict]:
        """提取签名相关参数"""
        # 查找常见的签名模式
        patterns = [
            r"([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[=:]\s*function\s*\([^)]*\)\s*\{[^}]*(?:sign|signature|encrypt|hash|md5|sha)[^}]*\}",
            r"function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*\{[^}]*(?:sign|signature|encrypt|hash|md5|sha)[^}]*\}",
        ]

        results = []
        for pattern in patterns:
            matches = re.finditer(pattern, js_code, re.IGNORECASE)
            for match in matches:
                func_name = match.group(1)
                func_code = self.extract_function_code(js_code, func_name)
                if func_code:
                    results.append({
                        "name": func_name,
                        "code": func_code,
                        "match": match.group(0),
                    })

        return results

    def analyze_request_params(self, js_code: str) -> Dict[str, Any]:
        """分析请求参数生成逻辑"""
        analysis = {
            "signature_functions": [],
            "timestamp_usage": [],
            "nonce_usage": [],
            "encryption_usage": [],
        }

        # 查找时间戳使用
        timestamp_patterns = [
            r"Date\.now\(\)",
            r"new\s+Date\(\)",
            r"getTime\(\)",
            r"timestamp",
        ]
        for pattern in timestamp_patterns:
            matches = re.finditer(pattern, js_code, re.IGNORECASE)
            for match in matches:
                analysis["timestamp_usage"].append({
                    "pattern": pattern,
                    "match": match.group(0),
                    "position": match.start(),
                })

        # 查找随机数使用
        nonce_patterns = [
            r"Math\.random\(\)",
            r"random\s*\(",
            r"nonce",
            r"uuid",
        ]
        for pattern in nonce_patterns:
            matches = re.finditer(pattern, js_code, re.IGNORECASE)
            for match in matches:
                analysis["nonce_usage"].append({
                    "pattern": pattern,
                    "match": match.group(0),
                    "position": match.start(),
                })

        # 查找签名函数
        analysis["signature_functions"] = self.extract_signature_params(js_code)

        return analysis
