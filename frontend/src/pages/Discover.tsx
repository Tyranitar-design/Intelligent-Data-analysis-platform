/**
 * 站点分析（v4 · 对标 DataHarbor 目标图）
 * ================================
 *
 * 输入一个 URL，产出站点画像与四维合规判定。
 *
 * v4 布局（目标图校准）：
 *   目标行（域名 + 状态 + 时间戳 + 重新探测）
 *   → 三栏（检测置信度圆弧 + 结构强度 / 字段覆盖矩阵 + TOP8 / 速率基线 + 能力链）
 *   → 字段样本预览 + 合规判定。
 *
 * 数据真实性纪律：圆弧 / 矩阵 / 强度条 / 速率全部来自接口实值，
 * 无历史采样的面板不做假曲线。
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
  RefreshCw,
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
    cls: 'pill-ok',
    icon: CheckCircle2,
    hint: '公开可访问且不存在技术隔离，可直接进入采集',
  },
  confirm_required: {
    label: '待确认',
    cls: 'pill-warn',
    icon: AlertTriangle,
    hint: '需补齐授权声明后执行',
  },
  blocked: {
    label: '不可采',
    cls: 'pill-err',
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
  const [analyzedAt, setAnalyzedAt] = useState('')

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
      setAnalyzedAt(
        new Date().toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        }),
      )
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

      {/* ---- 结果（v4 布局） ---- */}
      {result && (
        <div className="space-y-5">
          {/* 目标行 */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
            className="panel scan-sweep flex flex-wrap items-center justify-between gap-4 px-5 py-4"
          >
            <div className="flex min-w-0 items-center gap-3">
              <Globe2 className="h-5 w-5 shrink-0 text-primary" />
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="num truncate text-[1.05rem] font-semibold">
                    {result.profile.domain}
                  </h2>
                  <span className={cn('pill', DECISION_META[result.compliance.decision]?.cls ?? 'pill-info')}>
                    {DECISION_META[result.compliance.decision]?.label ?? '已探测'}
                  </span>
                  {result.cached && <span className="chip">命中缓存</span>}
                </div>
                <p className="mt-0.5 text-[0.72rem] text-muted-foreground">
                  字段 {result.profile.fields.length} 个 · 页面分析 {result.fetch_count} 次 ·{' '}
                  <span className="num">{analyzedAt}</span>
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void analyze(true)}
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
              )}
              重新探测
            </Button>
          </motion.div>

          {/* 三栏：置信度 / 字段矩阵 / 速率基线 */}
          <div className="grid gap-4 lg:grid-cols-[1fr_1.15fr_0.85fr]">
            <ConfidenceCard profile={result.profile} fetchCount={result.fetch_count} />
            <FieldsMatrixCard fields={result.profile.fields} />
            <RateCard profile={result.profile} />
          </div>

          {/* 字段样本预览 + 合规判定 */}
          <div className="grid items-start gap-4 lg:grid-cols-[1.25fr_1fr]">
            <FieldsPreview fields={result.profile.fields} />
            <ComplianceCard compliance={result.compliance} />
          </div>
        </div>
      )}
    </div>
  )
}

// --------------------------------------------------------------------------- //
// v4 子组件
// --------------------------------------------------------------------------- //

/** 检测置信度：圆弧仪表盘 + 指标列 + 结构识别强度 */
function ConfidenceCard({
  profile,
  fetchCount,
}: {
  profile: ProfileBlock
  fetchCount: number
}) {
  const structure = profile.structure ?? {}
  const access = profile.access ?? {}
  const pct = Math.max(0, Math.min(1, profile.confidence ?? 0))

  const pagination = structure.pagination as { mode?: string; param?: string } | undefined
  const structuredKinds = (structure.structured_data_kinds as string[]) ?? []

  const rows: { label: string; value: string; level: 1 | 2 | 3 }[] = [
    {
      label: '列表结构',
      value: String(structure.list_pattern || '未识别'),
      level: structure.list_pattern ? (String(structure.list_pattern).includes(':') ? 3 : 2) : 1,
    },
    {
      label: '分页方式',
      value: pagination?.mode && pagination.mode !== 'none'
        ? `${pagination.mode}${pagination.param ? ` · ${pagination.param}` : ''}`
        : '未识别',
      level: pagination?.mode && pagination.mode !== 'none' ? (pagination.param ? 3 : 2) : 1,
    },
    {
      label: '结构化数据',
      value: structuredKinds.length ? structuredKinds.join(' · ') : '无',
      level: structuredKinds.length >= 2 ? 3 : structuredKinds.length === 1 ? 2 : 1,
    },
    {
      label: '站点通道',
      value:
        [access.sitemaps ? 'Sitemap' : null, access.feeds ? 'RSS' : null]
          .filter(Boolean)
          .join(' · ') || '无',
      level: (access.sitemaps ? 1 : 0) + (access.feeds ? 1 : 0) >= 2 ? 3 : access.sitemaps || access.feeds ? 2 : 1,
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="panel p-5"
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold">检测置信度</h3>
        <span className="chip">{pct >= 0.8 ? '高置信' : pct >= 0.6 ? '中置信' : '低置信'}</span>
      </div>

      <div className="flex items-center gap-5">
        <Gauge value={pct} />
        <div className="min-w-0 flex-1 space-y-2 text-xs">
          <MiniRow label="页面分析数" value={String(fetchCount)} />
          <MiniRow label="平均字段覆盖" value={fmtPercent(profile.coverage)} />
          <MiniRow label="URL 模式" value={profile.url_pattern} />
        </div>
      </div>

      <div className="mt-5 space-y-2.5">
        <div className="label-xs">结构识别结果</div>
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between gap-3">
            <span className="shrink-0 text-xs text-muted-foreground">{row.label}</span>
            <span className="num min-w-0 truncate text-xs">{row.value}</span>
            <StrengthBars level={row.level} />
          </div>
        ))}
      </div>
    </motion.div>
  )
}

/** 270° 圆弧仪表盘（SVG） */
function Gauge({ value }: { value: number }) {
  const R = 62
  const CIRC = 2 * Math.PI * R
  const ARC = CIRC * 0.75
  const fill = ARC * value
  const percent = Math.round(value * 100)

  return (
    <div className="relative h-[132px] w-[132px] shrink-0">
      <svg viewBox="0 0 160 160" className="h-full w-full">
        <circle
          cx="80"
          cy="80"
          r={R}
          fill="none"
          stroke="hsl(var(--surface-3))"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${ARC} ${CIRC}`}
          transform="rotate(135 80 80)"
        />
        <motion.circle
          cx="80"
          cy="80"
          r={R}
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${fill} ${CIRC}`}
          transform="rotate(135 80 80)"
          initial={{ strokeDasharray: `0 ${CIRC}` }}
          animate={{ strokeDasharray: `${fill} ${CIRC}` }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="num text-[1.65rem] font-semibold leading-none">{percent}%</span>
        <span className="mt-1 text-[0.6rem] text-muted-foreground">confidence</span>
      </div>
    </div>
  )
}

/** 三格强度条 */
function StrengthBars({ level }: { level: 1 | 2 | 3 }) {
  return (
    <span className="flex shrink-0 gap-[3px]">
      {[1, 2, 3].map((index) => (
        <span
          key={index}
          className={cn(
            'h-3 w-[5px] rounded-[2px]',
            index <= level ? 'bg-primary' : 'bg-primary/15',
          )}
        />
      ))}
    </span>
  )
}

/** 字段覆盖矩阵 + TOP8 */
function FieldsMatrixCard({ fields }: { fields: FieldSpec[] }) {
  const rows = [...(fields ?? [])].slice(0, 10)
  const top = [...(fields ?? [])].sort((a, b) => (b.coverage ?? 0) - (a.coverage ?? 0)).slice(0, 8)
  const COLS = 10

  const cellTone = (coverage: number) =>
    coverage >= 0.8
      ? 'bg-primary'
      : coverage >= 0.5
        ? 'bg-primary/65'
        : coverage >= 0.2
          ? 'bg-primary/30'
          : 'bg-primary/12'

  if (!rows.length) {
    return (
      <div className="panel flex items-center justify-center p-5 text-sm text-muted-foreground">
        未识别到可采字段
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.05 }}
      className="panel p-5"
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold">字段覆盖矩阵</h3>
        <span className="text-[0.66rem] text-muted-foreground">
          共识别 {fields.length} 个字段 · 格子点亮比例 = 覆盖率
        </span>
      </div>

      <div className="flex gap-5">
        {/* 矩阵 */}
        <div className="min-w-0 flex-1 space-y-[5px]">
          {rows.map((field) => {
            const lit = Math.round(Math.max(0, Math.min(1, field.coverage ?? 0)) * COLS)
            return (
              <div key={field.name} className="flex items-center gap-2" title={`${field.name} · ${fmtPercent(field.coverage)}`}>
                <span className="w-[68px] shrink-0 truncate text-right text-[0.66rem] text-muted-foreground">
                  {field.name}
                </span>
                <div className="flex flex-1 gap-[3px]">
                  {Array.from({ length: COLS }).map((_, index) => (
                    <span
                      key={index}
                      className={cn(
                        'h-[13px] flex-1 rounded-[2px]',
                        index < lit ? cellTone(field.coverage ?? 0) : 'bg-muted/60',
                      )}
                    />
                  ))}
                </div>
              </div>
            )
          })}
        </div>

        {/* TOP8 */}
        <div className="w-[150px] shrink-0">
          <div className="label-xs mb-2">覆盖率 TOP 8</div>
          <div className="space-y-1.5">
            {top.map((field) => (
              <div key={field.name}>
                <div className="flex items-center justify-between text-[0.64rem]">
                  <span className="truncate">{field.name}</span>
                  <span className="num text-muted-foreground">{fmtPercent(field.coverage)}</span>
                </div>
                <div className="bar-track mt-0.5" style={{ height: 4 }}>
                  <motion.div
                    className="bar-fill"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.round((field.coverage ?? 0) * 100)}%` }}
                    transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border/60 pt-3 text-[0.62rem] text-muted-foreground">
        {[
          { tone: 'bg-primary', label: '≥ 80%' },
          { tone: 'bg-primary/65', label: '50 – 80%' },
          { tone: 'bg-primary/30', label: '20 – 50%' },
          { tone: 'bg-primary/12', label: '< 20%' },
        ].map((item) => (
          <span key={item.label} className="flex items-center gap-1.5">
            <span className={cn('h-2.5 w-2.5 rounded-[2px]', item.tone)} />
            {item.label}
          </span>
        ))}
      </div>
    </motion.div>
  )
}

/** 速率基线 + 能力链 */
function RateCard({ profile }: { profile: ProfileBlock }) {
  const strategy = profile.strategy ?? {}
  const chain = (strategy.chain as string[]) ?? []
  const rate = (strategy.rate as Record<string, unknown>) ?? {}
  const base = Number(rate.base_per_second ?? 1)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="panel flex flex-col p-5"
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold">请求速率基线</h3>
        <span className="chip chip-active">自适应</span>
      </div>

      <div className="flex items-end gap-2">
        <span className="num text-[2.1rem] font-semibold leading-none text-primary">
          {base.toFixed(1)}
        </span>
        <span className="mb-0.5 text-xs text-muted-foreground">req/s</span>
      </div>

      <div className="mt-4 space-y-2.5 text-xs">
        <MiniRow label="速率来源" value={String(rate.source ?? '默认基线')} />
        <MiniRow
          label="建议速率"
          value={`${Number(rate.min_per_second ?? 0.1).toFixed(1)} – ${base.toFixed(1)} req/s`}
        />
        <MiniRow
          label="域名并发"
          value={String(rate.max_concurrency_per_domain ?? '—')}
        />
      </div>

      <div className="mt-5 border-t border-border/60 pt-3.5">
        <div className="label-xs mb-2">能力链（失败自动降级）</div>
        {chain.length === 0 ? (
          <span className="text-xs text-muted-foreground">无可用能力链</span>
        ) : (
          <ol className="space-y-1.5">
            {chain.map((name, index) => (
              <li key={name} className="flex items-center gap-2 text-xs">
                <span className="num grid h-4 w-4 place-items-center rounded bg-primary/12 text-[0.58rem] text-primary">
                  {index + 1}
                </span>
                <span className="truncate">{name}</span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </motion.div>
  )
}

/** 字段样本预览（v4 精简表） */
function FieldsPreview({ fields }: { fields: FieldSpec[] }) {
  if (!fields?.length) {
    return (
      <div className="panel p-5 text-sm text-muted-foreground">未识别到可采字段。</div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.15 }}
      className="panel overflow-hidden"
    >
      <div className="flex items-center gap-2 px-5 pb-2 pt-4">
        <Layers className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold">字段样本预览</h3>
        <span className="text-xs text-muted-foreground">{fields.length} 个字段</span>
      </div>

      <div className="max-h-[380px] overflow-auto">
        <table className="w-full min-w-[680px] text-left text-xs">
          <thead className="sticky top-0 bg-card">
            <tr className="text-muted-foreground">
              <th className="px-5 py-2 font-medium">字段</th>
              <th className="px-3 py-2 font-medium">类型</th>
              <th className="px-3 py-2 font-medium">覆盖</th>
              <th className="px-5 py-2 font-medium">样本</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((field) => (
              <tr key={field.name} className="border-t border-border/40">
                <td className="max-w-[160px] truncate px-5 py-2 font-medium" title={`${field.source}:${field.path}`}>
                  {field.name}
                </td>
                <td className="px-3 py-2 text-muted-foreground">{field.type}</td>
                <td className="px-3 py-2">
                  <CoverageBar value={field.coverage} />
                </td>
                <td className="max-w-[260px] truncate px-5 py-2 text-muted-foreground">
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

function ComplianceCard({ compliance }: { compliance: ComplianceBlock }) {
  const meta = DECISION_META[compliance.decision] ?? DECISION_META.confirm_required
  const Icon = meta.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="panel p-5"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold">合规判定</h3>
        </div>
        <span className={cn('pill', meta.cls)}>{meta.label}</span>
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
          className="panel animate-rise p-4"
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

// --------------------------------------------------------------------------- //
// 辅助
// --------------------------------------------------------------------------- //

function MiniRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="num truncate" title={value}>
        {value}
      </span>
    </div>
  )
}

function CoverageBar({ value }: { value: number }) {
  const percent = Math.round((value ?? 0) * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="bar-track w-16">
        <div className="bar-fill" style={{ width: `${percent}%` }} />
      </div>
      <span className="num text-muted-foreground">{percent}%</span>
    </div>
  )
}

function fmtPercent(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${Math.round(value * 100)}%`
}
