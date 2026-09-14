"""
站点探测 · 编排与持久化
=======================

把获取层、结构识别、字段发现、合规判定串成一条链，产出并持久化 SiteProfile。

固定探测顺序（低成本高确定性优先，避免无谓的渲染开销）：

    robots.txt → Sitemap/RSS 发现 → 主文档获取 → 保护状态判定
    → 结构化数据提取 → 列表/详情结构识别 → 分页识别
    → 详情样本抽样 → 字段覆盖率合并 → 四维合规判定 → 策略生成

同一个 domain + url_pattern 视为同一画像；站点改版时新增 version 而非覆盖。
"""
from __future__ import annotations

import logging
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.compliance_verdict import ComplianceVerdict
from api.models.site_profile import SiteProfile
from compliance.engine import ComplianceEngine
from discover.fetcher import RobotsInfo, SiteFetcher
from discover.fields import FieldSpec, extract_fields_from_page, merge_field_coverage
from discover.structure import StructureInfo, analyze_structure

logger = logging.getLogger(__name__)

# 详情样本抽样上限：太多会拖慢探测，太少覆盖率的统计意义不足
DETAIL_SAMPLE_LIMIT = 3

# 需要渲染的信号：页面几乎没有可见文本但脚本量很大
RENDER_TEXT_THRESHOLD = 400
RENDER_SCRIPT_THRESHOLD = 5


@dataclass
class AnalyzeResult:
    """一次站点分析的完整结果。"""

    profile: dict
    verdict: dict
    cached: bool = False
    fetch_count: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "profile": self.profile,
            "compliance": self.verdict,
            "cached": self.cached,
            "fetch_count": self.fetch_count,
            "notes": self.notes,
        }


def normalize_url_pattern(url: str) -> str:
    """把 URL 归一化成"模式"，同一模式的 URL 复用同一份画像。

    ``/article/12345``      → ``/article/:id``
    ``/news/2026/09/10/a``  → ``/news/:year/:month/:day/a``
    """
    path = urlparse(url).path or "/"
    segments: list[str] = []
    for seg in path.strip("/").split("/"):
        if not seg:
            continue
        if re.fullmatch(r"\d{4}", seg) and 1970 <= int(seg) <= 2100:
            segments.append(":year")
        elif re.fullmatch(r"\d{1,3}", seg):
            # 两位数的月份 / 日期 / 三位数页码无法可靠区分，统一用中性占位符
            segments.append(":num")
        elif seg.isdigit():
            segments.append(":id")
        elif re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", seg):
            segments.append(":date")
        elif re.fullmatch(r"[0-9a-fA-F]{16,}", seg):
            segments.append(":hash")
        elif len(seg) > 40:
            segments.append(":slug")
        else:
            segments.append(seg)
    return "/" + "/".join(segments)


def _needs_render(html: str, soup_text_len: int, script_count: int) -> bool:
    """判断页面是否属于 JS 重度渲染类型。"""
    return soup_text_len < RENDER_TEXT_THRESHOLD and script_count >= RENDER_SCRIPT_THRESHOLD


def build_strategy(
    structure: StructureInfo,
    robots: RobotsInfo,
    access_state: dict,
    needs_render: bool,
) -> dict:
    """生成推荐采集策略链与频率策略。"""
    chain: list[str] = []

    if access_state.get("feeds"):
        chain.append("feed_reader")
    if access_state.get("sitemaps"):
        chain.append("sitemap_walker")
    if structure.list_pattern.item_count >= 3:
        chain.append("structured_extractor")
    chain.append("http_fetcher")
    if needs_render:
        chain.append("browser_renderer")

    # 频率：robots 的 crawl-delay 优先，否则用保守默认值
    if robots.crawl_delay:
        rate_per_second = round(1.0 / max(robots.crawl_delay, 0.1), 3)
        rate_source = "robots crawl-delay"
    else:
        rate_per_second = 1.0
        rate_source = "default"

    pagination = structure.pagination
    incremental = {
        "mode": "list_scan" if structure.list_pattern.item_count >= 3 else "single_page",
        "stop_rule": "consecutive_known_items",
        "consecutive_limit": 10,
        "dedup_key": "normalized_url",
        "content_hash": "simhash64",
    }

    return {
        "chain": chain,
        "rate": {
            "base_per_second": rate_per_second,
            "source": rate_source,
            "min_per_second": 0.1,
            "max_concurrency_per_domain": 2,
        },
        "pagination": {
            "mode": pagination.mode,
            "param": pagination.param,
        },
        "incremental": incremental,
    }


class SiteProfiler:
    """站点画像分析器。"""

    def __init__(
        self,
        session: Session,
        fetcher: Optional[SiteFetcher] = None,
        compliance: Optional[ComplianceEngine] = None,
    ) -> None:
        self.session = session
        self.fetcher = fetcher or SiteFetcher()
        self.compliance = compliance or ComplianceEngine()

    async def analyze(
        self,
        url: str,
        declared_authorization: Optional[str] = None,
        force_refresh: bool = False,
        sample_details: bool = True,
    ) -> AnalyzeResult:
        """分析一个 URL，产出画像与判定。"""
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
        domain = parsed.netloc
        pattern = normalize_url_pattern(url)

        notes: list[str] = []

        # 1. 命中已有画像则直接复用
        if not force_refresh:
            existing = self._load_existing(domain, pattern)
            if existing is not None:
                verdict = self.compliance.evaluate(
                    url,
                    access_state=existing.access_state or {},
                    declared_authorization=declared_authorization,
                )
                # 判定必须留痕：沿用画像但本次判定要落新记录——declared_authorization
                # 等输入不同会产生不同决策，若复用"最近一条旧记录"的 ID，调用方
                # 引用的结论会与本次判定不符（合规门加固后暴露的既有缺陷）。
                record = self._record_verdict(existing.id, url, verdict)
                payload = verdict.to_dict()
                payload["verdict_id"] = record.verdict_uid
                payload["verdict_row_id"] = record.id
                return AnalyzeResult(
                    profile=existing.to_dict(),
                    verdict=payload,
                    cached=True,
                    notes=["命中已有画像，未重新探测"],
                )

        async with self.fetcher as fetcher:
            base = f"{parsed.scheme}://{domain}"

            # 2. robots.txt
            robots = await fetcher.fetch_robots(base)
            if not robots.can_fetch(url):
                notes.append("robots 规则不允许抓取该路径")

            # 3. Sitemap / RSS
            sitemaps = await fetcher.discover_sitemaps(base, robots)

            # 4. 主文档
            doc = await fetcher.get(url)
            if doc.error:
                notes.append(f"主文档获取失败：{doc.error}")

            feeds: list[dict] = []
            structure = StructureInfo()
            field_specs: list[FieldSpec] = []
            needs_render = False

            if doc.ok and doc.text:
                feeds = await fetcher.discover_feeds(doc.text, doc.final_url or url)
                structure = analyze_structure(
                    doc.text,
                    doc.final_url or url,
                    status=doc.status,
                    headers=doc.headers,
                )
                field_specs = extract_fields_from_page(
                    doc.text, doc.final_url or url
                )

                body_text = _visible_text_length(doc.text)
                needs_render = _needs_render(
                    doc.text, body_text, doc.text.count("<script")
                )

                # 5. 详情样本抽样：提升字段覆盖率的统计意义
                if (
                    sample_details
                    and not structure.protection.blocked
                    and structure.detail_candidate
                ):
                    sampled = await self._sample_details(
                        fetcher, structure.detail_candidate, DETAIL_SAMPLE_LIMIT, robots
                    )
                    if sampled:
                        field_specs = merge_field_coverage([field_specs, *sampled])
                        notes.append(f"抽样 {len(sampled)} 个详情页合并字段覆盖率")

            access_state = {
                "http_status": doc.status,
                "protection": structure.protection.kind,
                "protection_evidence": structure.protection.evidence,
                "requires_credentials": structure.protection.requires_credentials,
                "robots_fetched": robots.fetched,
                "robots_allowed": robots.can_fetch(url),
                "robots_disallow": robots.disallow[:20],
                "robots_allow": robots.allow[:20],
                "crawl_delay": robots.crawl_delay,
                "sitemaps": sitemaps,
                "feeds": [f["url"] for f in feeds],
                "fetch_error": doc.error,
            }

            structure_payload = {
                "has_sitemap": bool(sitemaps),
                "has_rss": bool(feeds),
                "list_pattern": structure.list_pattern.item_selector,
                "list_item_count": structure.list_pattern.item_count,
                "detail_sample": structure.detail_candidate,
                "pagination": {
                    "mode": structure.pagination.mode,
                    "param": structure.pagination.param,
                    "evidence": structure.pagination.evidence,
                },
                "headings": structure.headings,
                "needs_render": needs_render,
                "structured_data_kinds": [
                    p.kind for p in _structured_kinds(doc.text)
                ],
            }

            # 6. 合规判定
            data_signals = _detect_data_signals(field_specs, structure)
            verdict = self.compliance.evaluate(
                url,
                access_state=access_state,
                declared_authorization=declared_authorization,
                data_signals=data_signals,
            )

            # 7. 策略
            strategy = build_strategy(structure, robots, access_state, needs_render)

            confidence = _compute_confidence(structure, doc.ok, field_specs)
            coverage = (
                sum(f.coverage for f in field_specs) / len(field_specs)
                if field_specs
                else 0.0
            )

            profile = self._persist(
                domain=domain,
                pattern=pattern,
                sample_url=url,
                site_meta={
                    "title": structure.meta.title,
                    "description": structure.meta.description,
                    "type": structure.meta.site_type,
                    "type_evidence": structure.meta.type_evidence,
                    "lang": structure.meta.lang,
                    "canonical": structure.meta.canonical,
                    "tech_stack": structure.meta.tech_stack,
                },
                access_state=access_state,
                structure=structure_payload,
                fields=[f.to_dict() for f in field_specs],
                strategy=strategy,
                compliance=verdict.to_dict(),
                confidence=confidence,
                coverage=round(coverage, 4),
            )

            record = self._record_verdict(profile.id, url, verdict)

            verdict_payload = verdict.to_dict()
            # 回传对外引用 ID 与内部主键，供后续计划 / 采集引用判定
            verdict_payload["verdict_id"] = record.verdict_uid
            verdict_payload["verdict_row_id"] = record.id

            return AnalyzeResult(
                profile=profile.to_dict(),
                verdict=verdict_payload,
                cached=False,
                fetch_count=fetcher.request_count,
                notes=notes,
            )

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #

    async def _sample_details(
        self,
        fetcher: SiteFetcher,
        candidate: str,
        limit: int,
        robots: RobotsInfo,
    ) -> list[list[FieldSpec]]:
        """抽取详情页样本，用于计算字段覆盖率。"""
        collected: list[list[FieldSpec]] = []
        if not robots.can_fetch(candidate):
            return collected

        doc = await fetcher.get(candidate)
        if doc.ok and doc.text:
            collected.append(extract_fields_from_page(doc.text, candidate))
        return collected

    def _load_existing(self, domain: str, pattern: str) -> Optional[SiteProfile]:
        stmt = (
            select(SiteProfile)
            .where(SiteProfile.domain == domain, SiteProfile.url_pattern == pattern)
            .order_by(SiteProfile.version.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def _persist(
        self,
        *,
        domain: str,
        pattern: str,
        sample_url: str,
        site_meta: dict,
        access_state: dict,
        structure: dict,
        fields: list[dict],
        strategy: dict,
        compliance: dict,
        confidence: float,
        coverage: float,
    ) -> SiteProfile:
        """写入画像；同域同模式存在时新增版本。"""
        previous = self._load_existing(domain, pattern)
        if previous is None:
            profile = SiteProfile(
                domain=domain,
                url_pattern=pattern,
                version=1,
                sample_url=sample_url,
                verified_by="discoverer",
            )
            self.session.add(profile)
        else:
            # 结构无实质变化时原地更新，避免版本膨胀
            if self._is_same_structure(previous.structure or {}, structure):
                profile = previous
            else:
                profile = SiteProfile(
                    domain=domain,
                    url_pattern=pattern,
                    version=(previous.version or 1) + 1,
                    sample_url=sample_url,
                    verified_by="discoverer",
                )
                self.session.add(profile)

        profile.sample_url = sample_url
        profile.site_meta = site_meta
        profile.access_state = access_state
        profile.structure = structure
        profile.fields = fields
        profile.strategy = strategy
        profile.compliance = compliance
        profile.confidence = confidence
        profile.coverage = coverage

        self.session.commit()
        self.session.refresh(profile)
        return profile

    def _record_verdict(
        self, profile_id: int, url: str, verdict: Any
    ) -> ComplianceVerdict:
        """判定记录落库（合规留痕）。返回写入的记录。"""
        record = ComplianceVerdict(
            verdict_uid=self._make_verdict_uid(profile_id, verdict),
            profile_id=profile_id,
            target_url=url[:1000],
            decision=str(verdict.decision),
            dim_access=str(verdict.dim_access),
            dim_authorization=str(verdict.dim_authorization),
            dim_behavior=str(verdict.dim_behavior),
            dim_data=str(verdict.dim_data),
            reasons=verdict.reasons,
            conditions=verdict.conditions,
            alternatives=[a.to_dict() for a in verdict.alternatives],
            coverage_estimate=verdict.coverage_estimate,
            authorization_token=verdict.authorization_token,
            token_expires_at=verdict.token_expires_at,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    @staticmethod
    def _make_verdict_uid(profile_id: int, verdict: Any) -> str:
        """生成判定记录 ID。

        每次判定都要留痕，因此 ID 必须唯一——不能用 profile_id + url 派生，
        否则重复判别同一 URL 会撞唯一约束。
        """
        if verdict.authorization_token:
            return verdict.authorization_token
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"v-{profile_id}-{stamp}-{secrets.token_hex(3)}"

    def _latest_verdict(self, profile_id: int) -> Optional[ComplianceVerdict]:
        """取某个画像最近一次判定记录。"""
        stmt = (
            select(ComplianceVerdict)
            .where(ComplianceVerdict.profile_id == profile_id)
            .order_by(ComplianceVerdict.id.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    @staticmethod
    def _is_same_structure(old: dict, new: dict) -> bool:
        keys = ("list_pattern", "has_sitemap", "has_rss", "needs_render")
        return all(old.get(k) == new.get(k) for k in keys)


# --------------------------------------------------------------------------- #
# 辅助函数
# --------------------------------------------------------------------------- #


def _visible_text_length(html: str) -> int:
    """粗略估算可见文本长度，用于判断是否需要渲染。"""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return len(soup.get_text(strip=True))
    except Exception:  # noqa: BLE001
        return len(html)


def _structured_kinds(html: str) -> list[Any]:
    try:
        from discover.fields import extract_all_structured

        return extract_all_structured(html)
    except Exception:  # noqa: BLE001
        return []


def _detect_data_signals(fields: list[FieldSpec], structure: StructureInfo) -> dict:
    """从字段与结构推断数据属性。

    这里只做保守启发：命中明显个人数据特征才升级到 D3，
    不做过度推断（把一切当个人数据会让平台失去可用性）。
    """
    names = {f.name for f in fields}
    signals: dict[str, Any] = {}

    personal_markers = {"author", "email", "phone", "id_card", "address", "username"}
    if names & personal_markers:
        signals["personal_data"] = True

    if "content" in names and structure.meta.site_type in ("news", "blog", "doc"):
        signals["copyrighted_content"] = True

    return signals


def _compute_confidence(
    structure: StructureInfo, fetch_ok: bool, fields: list[FieldSpec]
) -> float:
    """探测置信度：取多个信号的综合评分。"""
    if not fetch_ok:
        return 0.1

    score = 0.3
    if structure.meta.title:
        score += 0.15
    if structure.meta.site_type != "other":
        score += 0.1
    if structure.list_pattern.item_count >= 3:
        score += 0.15
    if structure.pagination.mode != "none":
        score += 0.1
    if fields:
        score += 0.2
    if structure.protection.blocked:
        score -= 0.3

    return round(max(0.0, min(1.0, score)), 3)
