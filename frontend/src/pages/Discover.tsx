/**
 * 站点分析
 * ========
 *
 * 输入一个 URL，产出站点画像与四维合规判定。
 *
 * 页面组织按"信息在决策中的顺序"排布：
 *   先给结论（判定）→ 再给依据（四维）→ 再给可操作项（字段与策略）。
 * 反过来先铺一堆技术细节，用户还得自己找结论。
 */
import { useState } from 'react'
import { motion } from 'motion/react'
import {
  AlertTriangle,
  CheckCircle2,
  Compass,
  Globe2,
  Layers,
  Loader2,
  Radar,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  XCircle,
} from 'lucide-react'

import apiClient from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

// --------------------------------------------------------------------------- //
// 类型
// --------------------------------------------------------------------------- //

interface FieldSpec {
  name: string
  path: string
  source: string
  type: string
  sample?: unknown
  coverage: number
}

interface ComplianceBlock {
  decision: 'proceed' | 'confirm_required' | 'blocked'
  dimensions: Record<string, string>
  reasons: string[]
  conditions: string[]
  alternatives: { kind: string; detail: string; coverage: number }[]
  coverage_estimate: number
  authorization_token?: string | null
  verdict_id?: string
}

interface ProfileBlock {
  profile_id: number
  domain: string
  url_pattern: string
  site: Record<string, unknown>
  access: Record<string, unknown>
  structure: Record<string, unknown>
  fields: FieldSpec[]
  strategy: Record<string, unknown>
  confidence: number
  coverage: number
}

interface AnalyzeResponse {
  profile: ProfileBlock
  compliance: ComplianceBlock
  cached: boolean
  fetch_count: number
  notes: string[]
}

const DECISION_META = {
  proceed: {
    label: '可执行',
    cls: 'badge-ok',
    icon: CheckCircle2,
    hint: '公开可访问且不存在技术隔离，可直接进入采集',
  },
  confirm_required: {
    label: '待确认',
    cls: 'badge-warn',
    icon: AlertTriangle,
    hint: '需补齐授权声明后执行',
  },
  blocked: {
    label: '不可采',
    cls: 'badge-err',
    icon: XCircle,
    hint: '存在技术隔离或数据属性受限，请使用替代数据源',
  },
} as const

const DIMENSION_LABELS: Record<string, string> = {
  access: '可访问性',
  authorization: '授权基础',
  behavior: '行为合规',
  data: '数据属性',
}

// --------------------------------------------------------------------------- //
// 页面
// --------------------------------------------------------------------------- //

export default function DiscoverPage() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)

  async function analyze(force = false) {
    const target = url.trim()
    if (!target) {
      setError('请输入要分析的站点 URL')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.post<AnalyzeResponse>('/discover/analyze', {
        url: target,
        force_refresh: force,
      })
      setResult(data)
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setError(
        typeof detail === 'string'
          ? detail
          : detail
            ? JSON.stringify(detail)
            : '分析失败，请确认后端已启动',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {/* ---- 输入区 ---- */}
      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="aurora glass rounded-xl p-5"
      >
        <div className="mb-3 flex items-center gap-2">
          <Compass className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold">站点可采性判别</h2>
          <span className="text-xs text-muted-foreground">
            输入任意 URL，自动识别结构、字段与合规边界
          </span>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void analyze(false)
            }}
            placeholder="https://example.com/news"
            className="h-10 flex-1"
            disabled={loading}
          />
          <Button onClick={() => void analyze(false)} disabled={loading} className="h-10 px-5">
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                探测中
              </>
            ) : (
              <>
                <Radar className="mr-2 h-4 w-4" />
                开始分析
              </>
            )}
          </Button>
        </div>

        {error && (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
            <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span className="break-all">{error}</span>
          </div>
        )}

        <p className="mt-3 text-[0.7rem] leading-relaxed text-muted-foreground">
          探测遵循 robots 路径级约束与自适应频率，不绕过任何访问控制。
          遇验证码 / 付费墙 / 鉴权墙会如实标记并给出替代数据源。
        </p>
      </motion.section>

      {/* ---- 空态 ---- */}
      {!result && !loading && <EmptyState />}

      {/* ---- 结果 ---- */}
      {result && (
        <div className="space-y-5">
          <div className="grid gap-4 lg:grid-cols-[1.25fr_1fr]">
            <SiteCard profile={result.profile} notes={result.notes} cached={result.cached} />
            <ComplianceCard compliance={result.compliance} />
          </div>
          <FieldsCard fields={result.profile.fields} />
          <StrategyCard profile={result.profile} />
        </div>
      )}
    </div>
  )
}

// --------------------------------------------------------------------------- //
// 子组件
// --------------------------------------------------------------------------- //

function EmptyState() {
  const steps = [
    { icon: Globe2, title: '探测结构', desc: 'robots、Sitemap、RSS、结构化数据' },
    { icon: Layers, title: '识别字段', desc: '列表与详情模式、字段覆盖率' },
    { icon: ShieldCheck, title: '合规判定', desc: '可访问性 × 授权 × 行为 × 数据' },
    { icon: Sparkles, title: '生成方案', desc: '能力链、频率、增量策略' },
  ]
  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.15, duration: 0.4 }}
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
    >
      {steps.map((step, index) => (
        <div
          key={step.title}
          className="glass glass-hover animate-rise rounded-xl p-4"
          style={{ ['--stagger' as string]: `${index * 70}ms` }}
        >
          <step.icon className="mb-2.5 h-4 w-4 text-primary" />
          <div className="text-[0.83rem] font-medium">{step.title}</div>
          <div className="mt-0.5 text-[0.72rem] leading-relaxed text-muted-foreground">
            {step.desc}
          </div>
        </div>
      ))}
    </motion.section>
  )
}

function SiteCard({
  profile,
  notes,
  cached,
}: {
  profile: ProfileBlock
  notes: string[]
  cached: boolean
}) {
  const site = profile.site ?? {}
  const structure = profile.structure ?? {}
  const tech = (site.tech_stack as string[]) ?? []

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass rounded-xl p-5"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Globe2 className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold">站点画像</h3>
        </div>
        {cached && <span className="badge-dot badge-info">命中缓存</span>}
      </div>

      <div className="mb-4 space-y-1">
        <div className="truncate text-base font-medium">
          {(site.title as string) || profile.domain}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="mono-tag">{profile.domain}</span>
          {Boolean(site.type) && (
            <span className="badge-dot badge-info">{String(site.type)}</span>
          )}
          {Boolean(site.lang) && <span className="mono-tag">{String(site.lang)}</span>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <Metric label="探测置信度" value={fmtPercent(profile.confidence)} bar={profile.confidence} />
        <Metric label="字段覆盖率" value={fmtPercent(profile.coverage)} bar={profile.coverage} />
      </div>

      <div className="mt-4 space-y-2">
        <Row label="列表结构" value={String(structure.list_pattern || '未识别')} mono />
        <Row
          label="分页方式"
          value={
            (structure.pagination as { mode?: string })?.mode
              ? `${(structure.pagination as { mode?: string }).mode}${
                  (structure.pagination as { param?: string })?.param
                    ? ` · ${(structure.pagination as { param?: string }).param}`
                    : ''
                }`
              : '未识别'
          }
        />
        <Row
          label="结构化通道"
          value={[
            structure.has_sitemap ? 'Sitemap' : null,
            structure.has_rss ? 'RSS' : null,
          ]
            .filter(Boolean)
            .join(' · ') || '无'}
        />
        {tech.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {tech.map((t) => (
              <span key={t} className="mono-tag">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {notes.length > 0 && (
        <ul className="mt-4 space-y-1 border-t border-border/60 pt-3">
          {notes.map((note) => (
            <li key={note} className="text-[0.72rem] leading-relaxed text-muted-foreground">
              · {note}
            </li>
          ))}
        </ul>
      )}
    </motion.div>
  )
}

function ComplianceCard({ compliance }: { compliance: ComplianceBlock }) {
  const meta = DECISION_META[compliance.decision] ?? DECISION_META.confirm_required
  const Icon = meta.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.06 }}
      className="glass rounded-xl p-5"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold">合规判定</h3>
        </div>
        <span className={cn('badge-dot', meta.cls)}>{meta.label}</span>
      </div>

      <div className="mb-4 flex items-start gap-2.5 rounded-lg bg-muted/40 px-3 py-2.5">
        <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="text-[0.78rem] leading-relaxed text-muted-foreground">
          {meta.hint}
        </span>
      </div>

      {/* 四维矩阵 */}
      <div className="mb-4 grid grid-cols-2 gap-2">
        {Object.entries(compliance.dimensions ?? {}).map(([key, value]) => (
          <div
            key={key}
            className="rounded-lg border border-border/70 bg-card/40 px-3 py-2"
          >
            <div className="section-title">{DIMENSION_LABELS[key] ?? key}</div>
            <div className="mono-tag mt-1 inline-block">{value}</div>
          </div>
        ))}
      </div>

      {compliance.conditions?.length > 0 && (
        <div className="mb-3">
          <div className="section-title mb-1.5">执行前需满足</div>
          <ul className="space-y-1">
            {compliance.conditions.map((c) => (
              <li key={c} className="text-[0.75rem] leading-relaxed text-muted-foreground">
                · {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {compliance.alternatives?.length > 0 && (
        <div>
          <div className="section-title mb-1.5">
            替代数据源（覆盖率估算 {fmtPercent(compliance.coverage_estimate)}）
          </div>
          <ul className="space-y-1.5">
            {compliance.alternatives.map((alt) => (
              <li key={alt.kind} className="flex items-start justify-between gap-3">
                <span className="text-[0.75rem] leading-relaxed text-muted-foreground">
                  · {alt.detail}
                </span>
                <span className="mono-tag shrink-0">{fmtPercent(alt.coverage)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {compliance.decision === 'proceed' && (
        <div className="mt-4 border-t border-border/60 pt-3 text-[0.72rem] leading-relaxed text-muted-foreground">
          判定依据：{compliance.reasons?.[0] ?? '公开可访问'}
          {compliance.reasons?.length > 1 && ` 等 ${compliance.reasons.length} 项`}
        </div>
      )}
    </motion.div>
  )
}

function FieldsCard({ fields }: { fields: FieldSpec[] }) {
  if (!fields?.length) {
    return (
      <div className="glass rounded-xl p-5 text-sm text-muted-foreground">
        未识别到可采字段。
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.12 }}
      className="glass overflow-hidden rounded-xl"
    >
      <div className="flex items-center gap-2 border-b border-border/60 px-5 py-3.5">
        <Layers className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold">可采字段</h3>
        <span className="text-xs text-muted-foreground">{fields.length} 个</span>
      </div>

      <div className="max-h-[420px] overflow-auto">
        <table className="w-full min-w-[720px] text-left text-xs">
          <thead className="sticky top-0 bg-card">
            <tr className="text-muted-foreground">
              <th className="px-5 py-2 font-medium">字段</th>
              <th className="px-3 py-2 font-medium">来源</th>
              <th className="px-3 py-2 font-medium">类型</th>
              <th className="px-3 py-2 font-medium">覆盖率</th>
              <th className="px-5 py-2 font-medium">样本</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((field) => (
              <tr key={field.name} className="border-t border-border/40">
                <td className="px-5 py-2 font-medium">{field.name}</td>
                <td className="px-3 py-2">
                  <span className="mono-tag">{field.source}</span>
                </td>
                <td className="px-3 py-2 text-muted-foreground">{field.type}</td>
                <td className="px-3 py-2">
                  <CoverageBar value={field.coverage} />
                </td>
                <td className="max-w-[280px] truncate px-5 py-2 text-muted-foreground">
                  {field.sample == null ? '—' : String(field.sample)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  )
}

function StrategyCard({ profile }: { profile: ProfileBlock }) {
  const strategy = profile.strategy ?? {}
  const chain = (strategy.chain as string[]) ?? []
  const rate = (strategy.rate as Record<string, unknown>) ?? {}

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.18 }}
      className="glass rounded-xl p-5"
    >
      <div className="mb-3 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold">推荐采集策略</h3>
      </div>

      <div className="section-title mb-2">能力链（按适配度排序，失败自动降级）</div>
      <div className="mb-4 flex flex-wrap items-center gap-1.5">
        {chain.length === 0 && (
          <span className="text-xs text-muted-foreground">无可用能力链</span>
        )}
        {chain.map((name, index) => (
          <span key={name} className="flex items-center gap-1.5">
            {index > 0 && <span className="text-muted-foreground">→</span>}
            <span className="mono-tag">{name}</span>
          </span>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Row label="基准速率" value={`${rate.base_per_second ?? '—'} 次/秒`} />
        <Row label="速率来源" value={String(rate.source ?? '默认')} />
        <Row label="域名并发" value={String(rate.max_concurrency_per_domain ?? '—')} />
      </div>
    </motion.div>
  )
}

function Metric({ label, value, bar }: { label: string; value: string; bar: number }) {
  return (
    <div>
      <div className="section-title">{label}</div>
      <div className="mt-1 text-sm font-medium">{value}</div>
      <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full rounded-full bg-primary"
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, Math.max(0, bar * 100))}%` }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
    </div>
  )
}

function CoverageBar({ value }: { value: number }) {
  const percent = Math.round((value ?? 0) * 100)
  const tone =
    percent >= 80 ? 'bg-emerald-500' : percent >= 40 ? 'bg-primary' : 'bg-amber-500'
  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-16 overflow-hidden rounded-full bg-muted">
        <div className={cn('h-full rounded-full', tone)} style={{ width: `${percent}%` }} />
      </div>
      <span className="tabular-nums text-muted-foreground">{percent}%</span>
    </div>
  )
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className={cn('truncate', mono && 'mono-tag')}>{value}</span>
    </div>
  )
}

function fmtPercent(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${Math.round(value * 100)}%`
}
