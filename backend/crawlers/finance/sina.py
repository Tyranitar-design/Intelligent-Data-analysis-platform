# -*- coding: utf-8 -*-
"""
新浪财经爬虫 - 指数/行情/历史K线 (真实可用)

数据源: hq.sinajs.cn + money.finance.sina.com.cn
- 实时行情（指数、个股）
- 历史K线
- 板块行情
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..base import BaseCrawler, CrawlResult


class SinaCrawler(BaseCrawler):
    """新浪财经数据爬虫"""

    HQ_URL = "https://hq.sinajs.cn/list={codes}"
    HIST_URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"

    # 常用指数
    MAJOR_INDEXES = {
        "sh000001": "上证指数",
        "sz399001": "深证成指",
        "sh000300": "沪深300",
        "sz399006": "创业板指",
        "sh000016": "上证50",
        "sh000688": "科创50",
        "sh000905": "中证500",
        "sz399005": "中小100",
    }

    def __init__(self):
        super().__init__("sina")
        self.request_delay = 0.8

    async def crawl_realtime_quotes(self, codes: List[str]) -> CrawlResult:
        """
        批量获取实时行情

        Args:
            codes: 代码列表 (如 ["sh000001", "sz399001", "sh600519"])
        """
        self.logger.info(f"获取实时行情: {len(codes)} 个")

        url = self.HQ_URL.format(codes=",".join(codes))
        headers = {
            "Referer": "https://finance.sina.com.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        html = await self.fetch(url, headers=headers)
        if not html:
            return CrawlResult(success=False, data=[], message="行情请求失败", source="sina")

        data_list = []
        for line in html.strip().split("\n"):
            if not line.strip():
                continue
            parsed = self._parse_sina_line(line, codes)
            if parsed:
                data_list.append(parsed)

        return CrawlResult(
            success=True, data=data_list,
            message=f"获取 {len(data_list)} 条行情",
            source="sina", count=len(data_list)
        )

    async def crawl_index_quotes(self) -> CrawlResult:
        """获取主要指数实时行情"""
        return await self.crawl_realtime_quotes(list(self.MAJOR_INDEXES.keys()))

    async def crawl_stock_history(
        self,
        symbol: str,
        days: int = 30,
        scale: int = 240
    ) -> CrawlResult:
        """
        获取股票历史K线

        Args:
            symbol: 股票代码 (如 "sh600519")
            days: 天数
            scale: 240=日K, 1680=周K, 7200=月K
        """
        self.logger.info(f"获取历史K线: {symbol} {days}天")

        params = {
            "symbol": symbol,
            "scale": scale,
            "ma": "no",
            "datalen": days,
        }

        html = await self.fetch(self.HIST_URL, params=params)
        if not html:
            return CrawlResult(success=False, data=[], message=f"请求失败 {symbol}", source="sina_hist")

        try:
            data = json.loads(html)
            records = []
            for item in data:
                records.append({
                    "symbol": symbol,
                    "date": item.get("day", ""),
                    "open": float(item.get("open", 0)),
                    "high": float(item.get("high", 0)),
                    "close": float(item.get("close", 0)),
                    "low": float(item.get("low", 0)),
                    "volume": int(item.get("volume", 0)),
                    "ma5": float(item.get("ma_price5", 0)) if item.get("ma_price5") else 0,
                    "ma10": float(item.get("ma_price10", 0)) if item.get("ma_price10") else 0,
                    "ma20": float(item.get("ma_price20", 0)) if item.get("ma_price20") else 0,
                    "ma30": float(item.get("ma_price30", 0)) if item.get("ma_price30") else 0,
                })

            return CrawlResult(
                success=True, data=records,
                message=f"获取 {symbol} {len(records)} 条历史K线",
                source="sina_hist", count=len(records)
            )
        except Exception as e:
            return CrawlResult(success=False, data=[], message=f"解析失败: {e}", source="sina_hist")

    async def crawl(self, **kwargs) -> CrawlResult:
        """实现抽象方法"""
        return await self.crawl_index_quotes()

    async def crawl_power_stocks(self) -> CrawlResult:
        """
        爬取电力行业股票实时行情

        通过新浪财经获取电力板块主要股票
        """
        power_codes = {
            "sh600900": "长江电力",
            "sh600795": "国电电力",
            "sh600886": "国投电力",
            "sh600025": "华能水电",
            "sh600905": "三峡能源",
            "sh600011": "华能国际",
            "sh600885": "三峡能源",  # 备用
        }

        result = await self.crawl_realtime_quotes(list(power_codes.keys()))

        # 添加行业标签
        for item in result.data:
            item["industry"] = "电力"
            item["name"] = power_codes.get(item.get("code", ""), "")

        return CrawlResult(
            success=result.success, data=result.data,
            message=f"获取 {len(result.data)} 只电力股行情",
            source="sina_power", count=result.count
        )

    def _parse_sina_line(self, line: str, all_codes: List[str]) -> Optional[Dict]:
        """解析单行新浪行情数据"""
        import re
        m = re.search(r'"([^"]+)"', line)
        if not m:
            return None

        parts = m.group(1).split(",")
        if len(parts) < 4:
            return None

        # 从行中提取代码
        code_match = re.search(r'hq_str_([a-z]+)(\d+)', line)
        if not code_match:
            return None

        market = code_match.group(1)
        code = code_match.group(2)
        full_code = f"{market}{code}"

        # 查找名称
        name = parts[0] if parts[0] else full_code

        return {
            "code": full_code,
            "name": name,
            "open": float(parts[1]) if parts[1] else 0,
            "prev_close": float(parts[2]) if parts[2] else 0,
            "price": float(parts[3]) if parts[3] else 0,
            "high": float(parts[4]) if len(parts) > 4 and parts[4] else 0,
            "low": float(parts[5]) if len(parts) > 5 and parts[5] else 0,
            "volume": int(float(parts[8])) if len(parts) > 8 and parts[8] else 0,
            "amount": float(parts[9]) if len(parts) > 9 and parts[9] else 0,
            "change_pct": round((float(parts[3]) - float(parts[2])) / float(parts[2]) * 100, 2) if float(parts[2]) else 0,
            "timestamp": datetime.now().isoformat(),
        }
