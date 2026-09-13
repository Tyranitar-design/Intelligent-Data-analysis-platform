# -*- coding: utf-8 -*-
"""
Robots.txt 合规检查器
====================

功能:
- 解析 robots.txt 文件
- 检查 URL 是否允许爬取
- 支持 User-Agent 级别的 Allow/Disallow 规则
- 支持通配符和路径匹配
- 缓存解析结果（避免重复请求）
- 生成合规报告
"""
import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import httpx

logger = logging.getLogger(__name__)


@dataclass
class RobotsRule:
    """robots.txt 规则"""
    user_agent: str
    path: str
    allow: bool  # True = Allow, False = Disallow
    priority: int = 0  # 规则优先级（路径越长优先级越高）


@dataclass
class ComplianceReport:
    """合规报告"""
    url: str
    allowed: bool
    source: str  # "robots.txt" / "default" / "error"
    rule: Optional[RobotsRule] = None
    crawl_delay: Optional[float] = None
    sitemap: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "url": self.url,
            "allowed": self.allowed,
            "source": self.source,
            "rule": {
                "user_agent": self.rule.user_agent,
                "path": self.rule.path,
                "allow": self.rule.allow,
            } if self.rule else None,
            "crawl_delay": self.crawl_delay,
            "sitemap": self.sitemap,
            "warnings": self.warnings,
        }


class RobotsChecker:
    """
    Robots.txt 合规检查器
    
    使用方式:
        checker = RobotsChecker()
        report = await checker.check("https://example.com/data")
        if report.allowed:
            # 允许爬取
        else:
            # 不允许爬取
    """
    
    # 默认 User-Agent
    DEFAULT_USER_AGENT = "DataPlatformBot"
    
    # 缓存时间（秒）
    CACHE_TTL = 3600  # 1小时
    
    def __init__(self, user_agent: str = None):
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self._cache: Dict[str, Tuple[float, List[RobotsRule], Dict]] = {}  # domain -> (timestamp, rules, meta)
    
    def _get_robots_url(self, url: str) -> str:
        """获取 robots.txt 的 URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    async def _fetch_robots_txt(self, robots_url: str) -> Optional[str]:
        """获取 robots.txt 内容"""
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(robots_url, headers={
                    "User-Agent": self.user_agent,
                })
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 404:
                    # 没有 robots.txt，默认允许
                    return None
                else:
                    logger.warning(f"获取 robots.txt 失败: {robots_url} (状态: {response.status_code})")
                    return None
        except Exception as e:
            logger.warning(f"获取 robots.txt 异常: {e}")
            return None
    
    def _parse_robots_txt(self, content: str) -> Tuple[List[RobotsRule], Dict]:
        """
        解析 robots.txt 内容
        
        返回: (规则列表, 元数据{crawl_delay, sitemap等})
        """
        rules = []
        meta = {"crawl_delay": None, "sitemaps": []}
        
        current_agents = []
        
        for line in content.splitlines():
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            
            # 分割键值
            if ":" not in line:
                continue
            
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            
            if key == "user-agent":
                current_agents.append(value)
            elif key == "disallow" and current_agents:
                if value:  # 空的 Disallow 表示允许所有
                    for agent in current_agents:
                        rules.append(RobotsRule(
                            user_agent=agent,
                            path=value,
                            allow=False,
                            priority=len(value),
                        ))
            elif key == "allow" and current_agents:
                if value:
                    for agent in current_agents:
                        rules.append(RobotsRule(
                            user_agent=agent,
                            path=value,
                            allow=True,
                            priority=len(value),
                        ))
            elif key == "crawl-delay" and current_agents:
                try:
                    meta["crawl_delay"] = float(value)
                except ValueError:
                    pass
            elif key == "sitemap":
                meta["sitemaps"].append(value)
            
            # 新的 User-agent 组开始
            if key == "user-agent" and current_agents and value != current_agents[-1]:
                # 只有遇到不同的 User-agent 才结束当前组
                pass
        
        # 排序规则：路径越长优先级越高，Allow 优先于 Disallow
        rules.sort(key=lambda r: (-r.priority, not r.allow))
        
        return rules, meta
    
    def _match_path(self, pattern: str, path: str) -> bool:
        """
        匹配 robots.txt 路径规则
        
        支持通配符:
        - * 匹配任意字符
        - $ 匹配路径结尾
        """
        # 转义正则特殊字符
        regex_pattern = re.escape(pattern)
        # 处理通配符
        regex_pattern = regex_pattern.replace(r"\*", ".*")
        # 处理结尾匹配
        if regex_pattern.endswith(r"\$"):
            regex_pattern = regex_pattern[:-2] + "$"
        
        try:
            return bool(re.match(regex_pattern, path))
        except re.error:
            return pattern == path
    
    def _is_allowed(self, rules: List[RobotsRule], path: str, user_agent: str) -> Tuple[bool, Optional[RobotsRule]]:
        """检查路径是否允许爬取"""
        matching_rules = []
        
        for rule in rules:
            # 检查 User-Agent 匹配
            if rule.user_agent == "*" or rule.user_agent.lower() == user_agent.lower():
                if self._match_path(rule.path, path):
                    matching_rules.append(rule)
        
        if not matching_rules:
            # 没有匹配的规则，默认允许
            return True, None
        
        # 返回优先级最高的规则（路径最长，Allow 优先）
        best_rule = matching_rules[0]
        return best_rule.allow, best_rule
    
    async def _get_rules(self, url: str) -> Tuple[List[RobotsRule], Dict]:
        """获取指定 URL 的 robots.txt 规则（带缓存）"""
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # 检查缓存
        if domain in self._cache:
            timestamp, rules, meta = self._cache[domain]
            if time.time() - timestamp < self.CACHE_TTL:
                return rules, meta
        
        # 获取并解析
        robots_url = self._get_robots_url(url)
        content = await self._fetch_robots_txt(robots_url)
        
        if content is None:
            # 没有 robots.txt 或获取失败，默认允许
            return [], {"crawl_delay": None, "sitemaps": []}
        
        rules, meta = self._parse_robots_txt(content)
        
        # 缓存
        self._cache[domain] = (time.time(), rules, meta)
        
        return rules, meta
    
    async def check(self, url: str, user_agent: str = None) -> ComplianceReport:
        """
        检查 URL 是否允许爬取
        
        Args:
            url: 目标 URL
            user_agent: User-Agent 字符串
            
        Returns:
            ComplianceReport 合规报告
        """
        agent = user_agent or self.user_agent
        warnings = []
        
        try:
            rules, meta = await self._get_rules(url)
            
            if not rules:
                # 没有 robots.txt 或没有匹配规则
                return ComplianceReport(
                    url=url,
                    allowed=True,
                    source="default",
                    crawl_delay=meta.get("crawl_delay"),
                    sitemap=meta.get("sitemaps", [None])[0] if meta.get("sitemaps") else None,
                    warnings=["未找到 robots.txt 或无匹配规则，默认允许"],
                )
            
            # 检查路径
            parsed = urlparse(url)
            path = parsed.path or "/"
            if parsed.query:
                path += f"?{parsed.query}"
            
            allowed, rule = self._is_allowed(rules, path, agent)
            
            return ComplianceReport(
                url=url,
                allowed=allowed,
                source="robots.txt",
                rule=rule,
                crawl_delay=meta.get("crawl_delay"),
                sitemap=meta.get("sitemaps", [None])[0] if meta.get("sitemaps") else None,
                warnings=warnings,
            )
            
        except Exception as e:
            logger.error(f"合规检查异常: {e}")
            return ComplianceReport(
                url=url,
                allowed=True,  # 异常时默认允许，但标记警告
                source="error",
                warnings=[f"合规检查异常: {str(e)}，默认允许但建议手动确认"],
            )
    
    async def check_batch(self, urls: List[str], user_agent: str = None) -> List[ComplianceReport]:
        """批量检查 URL"""
        tasks = [self.check(url, user_agent) for url in urls]
        return await asyncio.gather(*tasks)
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
