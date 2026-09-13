# -*- coding: utf-8 -*-
"""
数据服务 - 爬虫与AI模块之间的桥梁
"""
import pandas as pd
from typing import Dict, List, Any, Optional
from database.models import Database


class DataService:
    """数据服务 - 统一数据访问接口"""

    def __init__(self, db_path: str = None):
        self.db = Database(db_path)

    # ==================== 爬虫数据存储 ====================

    def save_crawl_result(self, source: str, data: List[Dict],
                           category: str = None, keyword: str = None,
                           page: int = 1, platform: str = None) -> Dict[str, Any]:
        """
        保存爬虫结果到数据库

        Args:
            source: 数据源名称
            data: 爬取的数据列表
            category: 数据分类
            keyword: 关键词
            page: 页码
            platform: 平台名称

        Returns:
            保存结果统计
        """
        # 保存爬虫记录
        record_id = self.db.save_crawl_record(
            source=source,
            category=category,
            keyword=keyword,
            page=page,
            count=len(data),
            status='completed'
        )

        # 根据数据源类型保存到对应表
        saved_count = 0

        if source in ['jd', 'taobao', 'pdd', 'ecommerce'] or platform:
            # 电商数据
            saved_count = self.db.save_ecom_products(
                products=data,
                platform=platform or source,
                source_record_id=record_id,
                keyword=keyword
            )
        elif source in ['stock', 'eastmoney', 'sina']:
            # 股票数据
            saved_count = self.db.save_stock_data(
                records=data,
                platform=platform or source,
                source_record_id=record_id
            )
        elif source in ['news', 'netease']:
            # 新闻数据
            saved_count = self.db.save_news(
                news_list=data,
                platform=platform or source,
                source_record_id=record_id
            )
        elif source in ['energy', 'power', 'sgcc', 'csg']:
            # 能源数据
            saved_count = self.db.save_energy_data(
                records=data,
                source_record_id=record_id
            )
        else:
            # 通用 JSON 存储
            pass

        return {
            'record_id': record_id,
            'total_count': len(data),
            'saved_count': saved_count,
            'source': source,
            'platform': platform or source
        }

    # ==================== AI 模块数据读取 ====================

    def get_data_for_analysis(self, source: str = None, platform: str = None,
                               keyword: str = None, limit: int = 1000) -> pd.DataFrame:
        """
        获取数据用于分析

        Args:
            source: 数据源
            platform: 平台
            keyword: 关键词
            limit: 返回数量

        Returns:
            DataFrame
        """
        if platform in ['jd', 'taobao', 'ecommerce'] or source in ['jd', 'taobao', 'ecommerce']:
            data = self.db.get_ecom_products(
                platform=platform or source,
                keyword=keyword,
                limit=limit
            )
        elif platform in ['stock', 'eastmoney'] or source == 'stock':
            data = self.db.get_stock_data(limit=limit)
        elif platform in ['news', 'netease'] or source == 'news':
            data = self.db.get_news(keyword=keyword, limit=limit)
        elif platform in ['energy', 'power'] or source == 'energy':
            data = self.db.get_energy_data(limit=limit)
        else:
            # 默认返回电商数据
            data = self.db.get_ecom_products(limit=limit)

        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()

    def get_ecommerce_data(self, platform: str = None, keywords: List[str] = None,
                           min_price: float = None, max_price: float = None,
                           brands: List[str] = None, limit: int = 1000) -> pd.DataFrame:
        """
        获取电商数据用于分析

        Args:
            platform: 平台
            keywords: 关键词列表
            min_price: 最低价格
            max_price: 最高价格
            brands: 品牌列表
            limit: 数量限制

        Returns:
            DataFrame
        """
        # 获取所有匹配数据
        data = self.db.get_ecom_products(platform=platform, limit=10000)

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # 过滤
        if keywords:
            mask = df['keyword'].isin(keywords) | df['title'].str.contains('|'.join(keywords), na=False)
            df = df[mask]

        if min_price is not None:
            df = df[df['price'] >= min_price]

        if max_price is not None:
            df = df[df['price'] <= max_price]

        if brands:
            df = df[df['brand'].isin(brands)]

        return df.head(limit)

    def get_stock_data_for_ml(self, symbols: List[str] = None,
                               start_date: str = None, end_date: str = None,
                               limit: int = 5000) -> pd.DataFrame:
        """获取股票数据用于机器学习"""
        if symbols:
            dfs = []
            for sym in symbols:
                data = self.db.get_stock_data(symbol=sym, start_date=start_date, end_date=end_date, limit=limit)
                if data:
                    dfs.append(pd.DataFrame(data))
            if dfs:
                return pd.concat(dfs, ignore_index=True)
            return pd.DataFrame()

        data = self.db.get_stock_data(start_date=start_date, end_date=end_date, limit=limit)
        return pd.DataFrame(data) if data else pd.DataFrame()

    # ==================== 统计信息 ====================

    def get_data_summary(self) -> Dict[str, Any]:
        """获取数据概览"""
        db_stats = self.db.get_stats()
        ecom_stats = self.db.get_ecom_stats()

        return {
            'total_records': sum(v for k, v in db_stats.items() if k != 'crawl_records'),
            'crawl_records': db_stats.get('crawl_records', 0),
            'ecom_products': db_stats.get('ecom_products', 0),
            'stock_records': db_stats.get('stock_data', 0),
            'news_records': db_stats.get('news_data', 0),
            'energy_records': db_stats.get('energy_data', 0),
            'ecom_by_platform': ecom_stats.get('by_platform', {}),
            'ecom_top_brands': ecom_stats.get('top_brands', [])
        }

    def get_recent_crawl_history(self, limit: int = 20) -> List[Dict]:
        """获取最近的爬取历史"""
        return self.db.get_crawl_records(limit=limit)

    # ==================== 数据导出 ====================

    def export_to_csv(self, source: str, filepath: str, **kwargs) -> str:
        """导出数据到 CSV"""
        df = self.get_data_for_analysis(source=source, **kwargs)
        if not df.empty:
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            return filepath
        return None

    def export_to_json(self, source: str, filepath: str, **kwargs) -> str:
        """导出数据到 JSON"""
        df = self.get_data_for_analysis(source=source, **kwargs)
        if not df.empty:
            df.to_json(filepath, orient='records', force_ascii=False, indent=2)
            return filepath
        return None
