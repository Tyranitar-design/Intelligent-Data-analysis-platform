#!/usr/bin/env python3
"""
数据分析平台自定义 Linter
========================

为智能数据分析平台设计的 Harness 验证工具。
技术栈: React + FastAPI + Django + Python

用法:
    python scripts/data_platform_linter.py          # 检查全部
    python scripts/data_platform_linter.py --fix    # 尝试自动修复
    python scripts/data_platform_linter.py --path backend/api  # 检查指定路径

作者: 小彩
日期: 2026-05-07
"""

import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class LintIssue:
    rule: str
    severity: Severity
    file: str
    line: int
    message: str
    suggestion: str = ""


@dataclass
class LintResult:
    issues: List[LintIssue] = field(default_factory=list)
    files_checked: int = 0
    rules_checked: int = 0

    def add(self, issue: LintIssue):
        self.issues.append(issue)

    @property
    def errors(self) -> List[LintIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> List[LintIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def print_report(self):
        print("\n" + "=" * 70)
        print("[REPORT] 数据分析平台 Harness 验证报告")
        print("=" * 70)

        if not self.issues:
            print("\n[PASS] 所有检查通过！未发现 issues。")
            return

        errors = self.errors
        warnings = self.warnings
        infos = [i for i in self.issues if i.severity == Severity.INFO]

        if errors:
            print(f"\n[ERRORS] ({len(errors)})")
            for issue in errors:
                self._print_issue(issue)

        if warnings:
            print(f"\n[WARNINGS] ({len(warnings)})")
            for issue in warnings:
                self._print_issue(issue)

        if infos:
            print(f"\n[INFO] ({len(infos)})")
            for issue in infos:
                self._print_issue(issue)

        print("\n" + "-" * 70)
        print(f"总计: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} info")
        print(f"检查文件: {self.files_checked}, 检查规则: {self.rules_checked}")
        print("=" * 70)

    def _print_issue(self, issue: LintIssue):
        print(f"\n[{issue.severity.value}] {issue.rule}")
        print(f"  文件: {issue.file}:{issue.line}")
        print(f"  问题: {issue.message}")
        if issue.suggestion:
            print(f"  建议: {issue.suggestion}")


class DataPlatformLinter:
    """数据分析平台 Linter 核心类"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend" / "src"
        self.result = LintResult()

    def run_all_checks(self) -> LintResult:
        """运行所有检查"""
        print("[START] 开始数据分析平台 Harness 验证...")
        print(f"项目根目录: {self.project_root}")
        print(f"后端目录: {self.backend_dir}")
        print(f"前端目录: {self.frontend_dir}")

        # 后端检查
        if self.backend_dir.exists():
            self._check_api_versioning()
            self._check_crawler_ethics()
            self._check_env_secrets()
            self._check_ml_model_versioning()
            self._check_data_pipeline_validation()

        # 前端检查
        if self.frontend_dir.exists():
            self._check_react_hook_rules()
            self._check_api_error_handling()
            self._check_component_complexity()

        # 通用检查
        self._check_requirements_sync()
        self._check_django_admin_security()

        self.result.rules_checked = 10
        return self.result

    def _check_api_versioning(self):
        """RULE: api-versioning - API 必须有版本前缀"""
        print("[CHECK] 检查 API 版本控制...")

        api_dir = self.backend_dir / "api" / "routers"
        if not api_dir.exists():
            return

        for py_file in api_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            self.result.files_checked += 1
            content = py_file.read_text(encoding="utf-8")

            # 检查是否使用 APIRouter 并包含版本前缀
            if "APIRouter" in content:
                # 检查路由注册是否包含 /api/v1/
                if not re.search(r'"/api/v\d+/', content) and not re.search(r'prefix\s*=\s*"/api/v\d+"', content):
                    self.result.add(LintIssue(
                        rule="api-versioning",
                        severity=Severity.WARNING,
                        file=str(py_file.relative_to(self.project_root)),
                        line=1,
                        message="API 路由缺少版本前缀 (/api/v1/)",
                        suggestion="在 APIRouter 中添加 prefix='/api/v1' 或在注册时包含版本前缀"
                    ))

    def _check_crawler_ethics(self):
        """RULE: crawler-ethics - 爬虫必须有 robots.txt 检查和限速"""
        print("[CHECK] 检查爬虫伦理...")

        crawlers_dir = self.backend_dir / "crawlers"
        if not crawlers_dir.exists():
            return

        # 检查基础爬虫类
        base_crawler = crawlers_dir / "base.py"
        if base_crawler.exists():
            self.result.files_checked += 1
            content = base_crawler.read_text(encoding="utf-8")

            # 检查是否有 robots.txt 检查
            has_robots_check = "robots.txt" in content.lower() or "robotparser" in content.lower()
            if not has_robots_check:
                self.result.add(LintIssue(
                    rule="crawler-ethics",
                    severity=Severity.WARNING,
                    file=str(base_crawler.relative_to(self.project_root)),
                    line=1,
                    message="爬虫基类缺少 robots.txt 检查",
                    suggestion="添加 urllib.robotparser 检查目标网站的 robots.txt"
                ))

            # 检查是否有请求延迟/限速
            has_rate_limit = "delay" in content.lower() or "rate" in content.lower() or "sleep" in content.lower()
            if not has_rate_limit:
                self.result.add(LintIssue(
                    rule="crawler-ethics",
                    severity=Severity.WARNING,
                    file=str(base_crawler.relative_to(self.project_root)),
                    line=1,
                    message="爬虫基类缺少请求限速机制",
                    suggestion="添加 time.sleep() 或 asyncio.sleep() 实现请求间隔"
                ))

        # 检查爬虫配置文件
        config_file = crawlers_dir / "config.py"
        if config_file.exists():
            self.result.files_checked += 1
            content = config_file.read_text(encoding="utf-8")

            if "request_delay" not in content and "rate_limit" not in content.lower():
                self.result.add(LintIssue(
                    rule="crawler-ethics",
                    severity=Severity.WARNING,
                    file=str(config_file.relative_to(self.project_root)),
                    line=1,
                    message="爬虫配置缺少请求延迟设置",
                    suggestion="在 CrawlerConfig 中添加 request_delay 字段"
                ))

    def _check_env_secrets(self):
        """RULE: env-secrets - 禁止硬编码 API Key / 密码"""
        print("[CHECK] 检查密钥安全...")

        secret_patterns = [
            (r'(api[_-]?key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9]{16,}["\']', "API Key"),
            (r'(password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']', "密码"),
            (r'(secret|token)\s*[=:]\s*["\'][a-zA-Z0-9]{16,}["\']', "Secret/Token"),
            (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API Key"),
        ]

        exclude_dirs = {"venv", "__pycache__", ".git", "node_modules"}

        for py_file in self.backend_dir.rglob("*.py"):
            # 跳过排除目录
            if any(excluded in str(py_file) for excluded in exclude_dirs):
                continue

            self.result.files_checked += 1
            content = py_file.read_text(encoding="utf-8")

            for pattern, secret_type in secret_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # 排除环境变量读取
                    line_content = content[:match.start()].split("\n")[-1] if content[:match.start()] else ""
                    if "env" in line_content.lower() or "os.getenv" in line_content or "config" in line_content.lower():
                        continue

                    line_num = content[:match.start()].count("\n") + 1
                    self.result.add(LintIssue(
                        rule="env-secrets",
                        severity=Severity.ERROR,
                        file=str(py_file.relative_to(self.project_root)),
                        line=line_num,
                        message=f"检测到硬编码的 {secret_type}",
                        suggestion="使用环境变量 (os.environ) 或 .env 文件管理密钥"
                    ))

    def _check_ml_model_versioning(self):
        """RULE: ml-model-versioning - ML 模型必须有版本号"""
        print("[CHECK] 检查 ML 模型版本管理...")

        ml_dir = self.backend_dir / "ml"
        if not ml_dir.exists():
            return

        for py_file in ml_dir.rglob("*.py"):
            self.result.files_checked += 1
            content = py_file.read_text(encoding="utf-8")

            # 检查是否有模型保存逻辑
            if "joblib.dump" in content or "torch.save" in content or "pickle.dump" in content:
                # 检查是否包含版本号或时间戳
                has_version = "version" in content.lower() or "timestamp" in content.lower() or "datetime" in content
                if not has_version:
                    self.result.add(LintIssue(
                        rule="ml-model-versioning",
                        severity=Severity.WARNING,
                        file=str(py_file.relative_to(self.project_root)),
                        line=1,
                        message="模型保存逻辑缺少版本号或时间戳",
                        suggestion="在模型文件名中包含版本号 (v1.0.0) 或时间戳 (20240507)"
                    ))

    def _check_data_pipeline_validation(self):
        """RULE: data-pipeline-validation - 数据管道必须有输入/输出校验"""
        print("[CHECK] 检查数据管道验证...")

        analysis_dir = self.backend_dir / "analysis"
        if not analysis_dir.exists():
            return

        for py_file in analysis_dir.rglob("*.py"):
            self.result.files_checked += 1
            content = py_file.read_text(encoding="utf-8")

            # 检查是否有数据校验逻辑
            has_validation = "validate" in content.lower() or "assert" in content or "check" in content.lower()
            if not has_validation:
                self.result.add(LintIssue(
                    rule="data-pipeline-validation",
                    severity=Severity.INFO,
                    file=str(py_file.relative_to(self.project_root)),
                    line=1,
                    message="数据分析管道可能缺少输入验证",
                    suggestion="添加数据类型检查和空值验证"
                ))

    def _check_react_hook_rules(self):
        """RULE: react-hook-rules - Hooks 必须在顶层调用"""
        print("[CHECK] 检查 React Hooks 规范...")

        for tsx_file in self.frontend_dir.rglob("*.tsx"):
            self.result.files_checked += 1
            content = tsx_file.read_text(encoding="utf-8")

            # 检查 useEffect/useState 是否在条件语句中
            lines = content.split("\n")
            in_conditional = False
            conditional_depth = 0

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # 跟踪条件深度
                if stripped.startswith("if ") or stripped.startswith("for ") or stripped.startswith("while "):
                    in_conditional = True
                    conditional_depth += 1

                if stripped.startswith("}") and conditional_depth > 0:
                    conditional_depth -= 1
                    if conditional_depth == 0:
                        in_conditional = False

                # 检查 hook 调用是否在条件中
                if in_conditional and any(hook in stripped for hook in ["useState(", "useEffect(", "useCallback(", "useMemo("]):
                    self.result.add(LintIssue(
                        rule="react-hook-rules",
                        severity=Severity.ERROR,
                        file=str(tsx_file.relative_to(self.project_root)),
                        line=i,
                        message="Hook 在条件语句中调用，违反 Hooks 规则",
                        suggestion="将 Hook 调用移到组件顶层，不在 if/for/while 中使用"
                    ))

    def _check_api_error_handling(self):
        """RULE: api-error-handling - API 调用必须有错误处理"""
        print("[CHECK] 检查前端 API 错误处理...")

        services_dir = self.frontend_dir / "services"
        if not services_dir.exists():
            return

        for ts_file in services_dir.rglob("*.ts"):
            self.result.files_checked += 1
            content = ts_file.read_text(encoding="utf-8")

            # 检查是否有错误处理
            has_error_handling = "catch" in content or "try" in content
            if not has_error_handling:
                self.result.add(LintIssue(
                    rule="api-error-handling",
                    severity=Severity.WARNING,
                    file=str(ts_file.relative_to(self.project_root)),
                    line=1,
                    message="API 服务文件缺少错误处理",
                    suggestion="添加 try/catch 或 .catch() 处理 API 错误"
                ))

    def _check_component_complexity(self):
        """检查组件复杂度"""
        print("[CHECK] 检查组件复杂度...")

        pages_dir = self.frontend_dir / "pages"
        if not pages_dir.exists():
            return

        for tsx_file in pages_dir.rglob("*.tsx"):
            self.result.files_checked += 1
            content = tsx_file.read_text(encoding="utf-8")
            line_count = len(content.splitlines())

            if line_count > 500:
                self.result.add(LintIssue(
                    rule="component-complexity",
                    severity=Severity.WARNING,
                    file=str(tsx_file.relative_to(self.project_root)),
                    line=1,
                    message=f"页面组件行数过多 ({line_count} 行)",
                    suggestion="拆分为子组件或提取自定义 Hooks"
                ))

    def _check_requirements_sync(self):
        """RULE: requirements-sync - requirements.txt 必须与实际依赖同步"""
        print("[CHECK] 检查依赖同步...")

        req_file = self.backend_dir / "requirements.txt"
        if not req_file.exists():
            self.result.add(LintIssue(
                rule="requirements-sync",
                severity=Severity.WARNING,
                file="backend/requirements.txt",
                line=0,
                message="缺少 requirements.txt 文件",
                suggestion="创建 requirements.txt 记录项目依赖"
            ))
            return

        self.result.files_checked += 1
        content = req_file.read_text(encoding="utf-8")

        # 检查是否有版本号
        lines_without_version = [line for line in content.split("\n") if line.strip() and not line.startswith("#") and "==" not in line and ">=" not in line]
        if lines_without_version:
            self.result.add(LintIssue(
                rule="requirements-sync",
                severity=Severity.INFO,
                file=str(req_file.relative_to(self.project_root)),
                line=1,
                message="部分依赖缺少版本号",
                suggestion="为所有依赖指定版本号 (==x.y.z 或 >=x.y.z)"
            ))

    def _check_django_admin_security(self):
        """RULE: django-admin-security - Django Admin 安全配置"""
        print("[CHECK] 检查 Django Admin 安全...")

        admin_dir = self.backend_dir / "admin"
        if not admin_dir.exists():
            return

        settings_file = admin_dir / "settings.py"
        if settings_file.exists():
            self.result.files_checked += 1
            content = settings_file.read_text(encoding="utf-8")

            # 检查 DEBUG 设置
            if "DEBUG = True" in content:
                self.result.add(LintIssue(
                    rule="django-admin-security",
                    severity=Severity.WARNING,
                    file=str(settings_file.relative_to(self.project_root)),
                    line=content.find("DEBUG = True") // len(content.split("\n")[0]) + 1,
                    message="Django DEBUG 模式开启，生产环境应关闭",
                    suggestion="生产环境设置 DEBUG = False"
                ))

            # 检查 SECRET_KEY
            if "SECRET_KEY" in content and ("your-secret-key" in content or "change-me" in content):
                self.result.add(LintIssue(
                    rule="django-admin-security",
                    severity=Severity.ERROR,
                    file=str(settings_file.relative_to(self.project_root)),
                    line=1,
                    message="Django SECRET_KEY 使用默认值",
                    suggestion="使用环境变量设置 SECRET_KEY"
                ))

    @staticmethod
    def _find_line(content: str, pattern: str) -> int:
        """查找模式在内容中的行号"""
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if pattern in line:
                return i
        return 1


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="数据分析平台 Harness Linter")
    parser.add_argument("--path", help="指定检查路径")
    parser.add_argument("--fix", action="store_true", help="尝试自动修复")
    parser.add_argument("--rules", help="指定规则（逗号分隔）")

    args = parser.parse_args()

    # 确定项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print(f"[LINTER] 数据分析平台 Harness Linter v1.0")
    print(f"项目路径: {project_root}")

    linter = DataPlatformLinter(str(project_root))
    result = linter.run_all_checks()
    result.print_report()

    # 返回退出码
    sys.exit(1 if result.errors else 0)


if __name__ == "__main__":
    main()
