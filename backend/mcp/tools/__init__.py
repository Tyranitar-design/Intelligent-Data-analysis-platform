"""
MCP 工具集
==========

七个工具，覆盖完整闭环：

    分析 → 规划 → 执行 → 观察 → 取数 → 分析 → 交付

| 工具 | 作用 |
|---|---|
| ``analyze_site``    | 站点画像 + 合规判定 + 推荐方案 |
| ``plan_collection`` | 生成采集方案（不发请求） |
| ``run_collection``  | 执行采集（合规拦截点） |
| ``job_status``      | 任务进度与质量 |
| ``query_dataset``   | 读取数据集 |
| ``run_analysis``    | 执行分析 |
| ``make_report``     | 生成报告 |

粒度是刻意固定的：更细会让调用方承担编排责任、错误率上升；
更粗会让调用方失去控制点和中间反馈。
"""

from mcp.tools.analytics import TOOL_SPECS as ANALYTICS_SPECS
from mcp.tools.discovery import TOOL_SPECS as DISCOVERY_SPECS

# 顺序即语义顺序：先判别，再采集，再分析，最后交付
TOOL_SPECS = [*DISCOVERY_SPECS, *ANALYTICS_SPECS]

__all__ = ["TOOL_SPECS", "DISCOVERY_SPECS", "ANALYTICS_SPECS"]
