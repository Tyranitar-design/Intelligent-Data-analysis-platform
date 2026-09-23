/**
 * 合规中心
 * ========
 *
 * 「合规必须落成代码」的外显面：
 * - 判定统计与 A×B 矩阵总览（数据驱动，不加装饰性颜色）
 * - 待确认判定可补齐授权（写回判定 + 审计留痕）
 * - 阻断判定展示替代数据源与覆盖率（硬边界，不提供解锁）
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  ChevronDown,
  Loader2,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
} from 'lucide-react'

import apiClient from '@/api/client'
import CountUp from '@/components/motion/CountUp'
import Reveal from '@/components/motion/Reveal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

interface VerdictItem {
  verdict_id: string
  profile_id: number | null
  target_url: string
  decision: 'proceed' | 'confirm_required' | 'blocked'
  dimensions: { access: string; authorization: string; behavior: string; data: string }
  reasons: string[]
  conditions: string[]
  alternatives: { kind: string; detail: string; coverage: number }[]
  coverage_estimate: number | null
  has_token: boolean
  token_expires_at: string | null
  operator: string | null
  authorization_basis: string | null
  created_at: string | null
}

interface StatsPayload {
  total: number
  by_decision: { proceed: number; confirm_required: number; blocked: number }
  matrix: { access: string; authorization: string; count: number }[]
}

const ACCESS_DIM = ['A1', 'A2', 'A3', 'A4']
const AUTH_DIM = ['B1', 'B2', 'B3', 'B4', 'B5']

// v5：判定列用实底 pill（参考图统一语言）
const DECISION_TONE: Record<string, string> = {
  proceed: 'pill-ok',
  confirm_required: 'pill-warn',
  blocked: 'pill-err',
}

const DECISION_LABEL: Record<string, string> = {
  proceed: '可执行',
  confirm_required: '待确认',
  blocked: '已阻断',
}

const BASIS_OPTIONS = [
  { value: 'official', label: '官方开放' },
  { value: 'own_credentials', label: '自有凭证' },
  { value: 'written_authorization', label: '书面授权' },
] as const

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function shortUrl(url: string): string {
  try {
    const parsed = new URL(url)
    const path = parsed.pathname === '/' ? '' : parsed.pathname
    const text = `${parsed.host}${path}`
    return text.length > 52 ? `${text.slice(0, 52)}…` : text
  } catch {
    return url.length > 52 ? `${url.slice(0, 52)}…` : url
  }
}

function errorDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
    ?.detail
  return typeof detail === 'string' ? detail : fallback
}

export default function CompliancePage() {
  const [stats, setStats] = useState<StatsPayload | null>(null)
  const [verdicts, setVerdicts] = useState<VerdictItem[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // 补齐授权表单
  const [patchingId, setPatchingId] = useState<string | null>(null)
  const [basis, setBasis] = useState<string>('official')
  const [operator, setOperator] = useState('')
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [statsResp, listResp] = await Promise.allSettled([
        apiClient.get<StatsPayload>('/discover/verdicts/stats'),
        apiClient.get<{ items: VerdictItem[] }>('/discover/verdicts', {
          params: { limit: 100 },
        }),
      ])
      if (statsResp.status === 'fulfilled') setStats(statsResp.value.data)
      if (listResp.status === 'fulfilled') setVerdicts(listResp.value.data.items ?? [])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const gridCounts = useMemo(() => {
    const map: Record<string, number> = {}
    for (const cell of stats?.matrix ?? []) {
      map[`${cell.access}|${cell.authorization}`] = cell.count
    }
    return map
  }, [stats])

  const gridMax = useMemo(() => {
    const values = Object.values(gridCounts)
    return values.length ? Math.max(...values) : 1
  }, [gridCounts])

  const pendingList = useMemo(
    () => verdicts.filter((v) => v.decision === 'confirm_required'),
    [verdicts],
  )
  const blockedList = useMemo(
    () => verdicts.filter((v) => v.decision === 'blocked'),
    [verdicts],
  )

  function startPatch(verdict: VerdictItem) {
    setPatchingId(verdict.verdict_id)
    setBasis('official')
    setOperator('')
    setNote('')
    setMessage(null)
  }

  async function submitPatch(verdict: VerdictItem) {
    if (!operator.trim()) {
      setMessage('请填写操作者标识（用于审计留痕）')
      return
    }
    setSubmitting(true)
    setMessage(null)
    try {
      await apiClient.patch(
        `/discover/verdicts/${encodeURIComponent(verdict.verdict_id)}/authorization`,
        { basis, operator: operator.trim(), note: note.trim() || null },
      )
      setMessage(`已补齐授权并解锁：${shortUrl(verdict.target_url)}`)
      setPatchingId(null)
      void load()
    } catch (err) {
      setMessage(errorDetail(err, '补齐授权失败'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          四维判定的留痕与复核。每条判定可追溯到取证依据；补齐授权动作写入审计日志。
        </p>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          )}
          刷新
        </Button>
      </div>

      {message && (
        <div className="glass rounded-lg px-4 py-2.5 text-xs text-muted-foreground">
          {message}
        </div>
      )}

      {/* ---------------- 统计 ---------------- */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          index={0}
          icon={ShieldCheck}
          label="判定总数"
          value={<CountUp value={stats?.total ?? 0} />}
          hint="全部留痕记录"
        />
        <StatCard
          index={1}
          icon={ShieldCheck}
          label="可执行"
          value={<CountUp value={stats?.by_decision.proceed ?? 0} />}
          hint="proceed · 可进入采集"
        />
        <StatCard
          index={2}
          icon={ShieldQuestion}
          label="待确认"
          value={<CountUp value={stats?.by_decision.confirm_required ?? 0} />}
          hint="等待授权声明"
        />
        <StatCard
          index={3}
          icon={ShieldAlert}
          label="已阻断"
          value={<CountUp value={stats?.by_decision.blocked ?? 0} />}
          hint="附替代数据源"
        />
      </section>

      {/* ---------------- A×B 矩阵 ---------------- */}
      <Reveal delay={0.12} className="glass rounded-xl p-5">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold">可访问性 × 授权基础</h3>
          <span className="text-[0.68rem] text-muted-foreground">
            格子深浅 = 判定数量（点击下方列表查看取证）
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] border-separate border-spacing-1 text-center text-xs">
            <thead>
              <tr>
                <th className="w-14" />
                {AUTH_DIM.map((b) => (
                  <th key={b} className="pb-1 font-medium text-muted-foreground">
                    {b}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ACCESS_DIM.map((a) => (
                <tr key={a}>
                  <td className="pr-2 text-right font-medium text-muted-foreground">{a}</td>
                  {AUTH_DIM.map((b) => {
                    const count = gridCounts[`${a}|${b}`] ?? 0
                    return (
                      <td key={b}>
                        <div
                          className={cn(
                            'grid h-9 place-items-center rounded-md border text-[0.72rem] tabular-nums transition-colors',
                            count > 0
                              ? 'border-primary/30 text-foreground'
                              : 'border-border/40 text-muted-foreground/40',
                          )}
                          style={
                            count > 0
                              ? {
                                  backgroundColor: `hsl(var(--primary) / ${
                                    0.08 + 0.45 * (count / gridMax)
                                  })`,
                                }
                              : undefined
                          }
                          title={`${a} × ${b} · ${count} 条`}
                        >
                          {count > 0 ? count : '·'}
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Reveal>

      {/* ---------------- 待确认 ---------------- */}
      {pendingList.length > 0 && (
        <Reveal delay={0.16} className="space-y-3">
          <h3 className="section-title">待确认 · 需补齐授权（{pendingList.length}）</h3>
          {pendingList.map((verdict) => (
            <div key={verdict.verdict_id} className="glass rounded-xl p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="truncate text-sm font-medium">
                      {shortUrl(verdict.target_url)}
                    </span>
                    <span className="pill pill-warn">待确认</span>
                    <span className="mono-tag">
                      {verdict.dimensions.access}/{verdict.dimensions.authorization}
                    </span>
                    {verdict.has_token && (
                      <span className="text-[0.68rem] text-muted-foreground">
                        令牌有效期至 {formatDateTime(verdict.token_expires_at)}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    解锁条件：{verdict.conditions[0] ?? '声明授权基础并留痕'}
                  </p>
                </div>
                {patchingId !== verdict.verdict_id && (
                  <Button size="sm" variant="outline" onClick={() => startPatch(verdict)}>
                    补齐授权
                  </Button>
                )}
              </div>

              {patchingId === verdict.verdict_id && (
                <div className="mt-3 space-y-3 rounded-lg border border-border/60 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-muted-foreground">授权基础</span>
                    {BASIS_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setBasis(opt.value)}
                        className={cn(
                          'rounded-lg border px-2.5 py-1 text-xs transition-colors',
                          basis === opt.value
                            ? 'border-primary/50 bg-primary/10 font-medium text-primary'
                            : 'border-border/60 text-muted-foreground hover:text-foreground',
                        )}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input
                      value={operator}
                      onChange={(e) => setOperator(e.target.value)}
                      placeholder="操作者标识（必填，写入审计）"
                      className="h-9"
                    />
                    <Input
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      placeholder="授权依据说明（选填）"
                      className="h-9"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={submitting}
                      onClick={() => void submitPatch(verdict)}
                    >
                      {submitting && (
                        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                      )}
                      确认补齐并解锁
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setPatchingId(null)}
                      disabled={submitting}
                    >
                      取消
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </Reveal>
      )}

      {/* ---------------- 已阻断 ---------------- */}
      {blockedList.length > 0 && (
        <Reveal delay={0.2} className="space-y-3">
          <h3 className="section-title">已阻断 · 附替代数据源（{blockedList.length}）</h3>
          {blockedList.map((verdict) => (
            <div key={verdict.verdict_id} className="glass rounded-xl p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="truncate text-sm font-medium">
                  {shortUrl(verdict.target_url)}
                </span>
                <span className="pill pill-err">已阻断</span>
                <span className="mono-tag">
                  {verdict.dimensions.access}/{verdict.dimensions.authorization}
                </span>
              </div>
              {verdict.reasons[0] && (
                <p className="mt-1 text-xs text-muted-foreground">{verdict.reasons[0]}</p>
              )}
              {verdict.alternatives.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {verdict.alternatives.map((alt) => (
                    <span
                      key={alt.kind}
                      className="rounded-md border border-border/60 px-2 py-1 text-[0.68rem] text-muted-foreground"
                      title={alt.detail}
                    >
                      {alt.kind} · 覆盖率 {alt.coverage.toFixed(2)}
                    </span>
                  ))}
                  {verdict.coverage_estimate != null && (
                    <span className="rounded-md border border-primary/30 px-2 py-1 text-[0.68rem] text-primary">
                      综合可达率 {verdict.coverage_estimate.toFixed(2)}
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </Reveal>
      )}

      {/* ---------------- 全部判定 ---------------- */}
      <Reveal delay={0.24} className="glass overflow-hidden rounded-xl">
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-3.5">
          <h3 className="text-sm font-semibold">全部判定（{verdicts.length}）</h3>
          <span className="text-[0.68rem] text-muted-foreground">点击行展开四维取证</span>
        </div>

        {verdicts.length === 0 && !loading ? (
          <div className="px-5 py-12 text-center">
            <ShieldQuestion className="mx-auto mb-3 h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">暂无判定记录</p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              前往「站点分析」输入一个 URL，产生第一条判定留痕
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border/40">
            {verdicts.map((verdict) => {
              const expanded = expandedId === verdict.verdict_id
              return (
                <li key={verdict.verdict_id}>
                  <button
                    type="button"
                    onClick={() =>
                      setExpandedId(expanded ? null : verdict.verdict_id)
                    }
                    className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left transition-colors hover:bg-muted/40"
                  >
                    <div className="flex min-w-0 items-center gap-2.5">
                      <span
                        className={cn('pill shrink-0', DECISION_TONE[verdict.decision])}
                      >
                        {DECISION_LABEL[verdict.decision]}
                      </span>
                      <span className="truncate text-xs">{shortUrl(verdict.target_url)}</span>
                      <span className="mono-tag hidden shrink-0 sm:inline">
                        {verdict.dimensions.access}/{verdict.dimensions.authorization}/
                        {verdict.dimensions.behavior}/{verdict.dimensions.data}
                      </span>
                    </div>
                    <div className="flex shrink-0 items-center gap-3 text-[0.68rem] text-muted-foreground">
                      <span className="tabular-nums">
                        {formatDateTime(verdict.created_at)}
                      </span>
                      <ChevronDown
                        className={cn(
                          'h-3.5 w-3.5 transition-transform',
                          expanded && 'rotate-180',
                        )}
                      />
                    </div>
                  </button>

                  {expanded && (
                    <div className="space-y-2 border-t border-border/40 bg-muted/20 px-5 py-3 text-xs">
                      {verdict.reasons.length > 0 && (
                        <div>
                          <div className="section-title mb-1">取证依据</div>
                          <ul className="space-y-1 text-muted-foreground">
                            {verdict.reasons.map((reason, i) => (
                              <li key={i}>· {reason}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {verdict.operator && (
                        <div className="text-muted-foreground">
                          授权补齐：{verdict.operator} · {verdict.authorization_basis}
                        </div>
                      )}
                      {verdict.conditions.length > 0 && verdict.decision === 'confirm_required' && (
                        <div>
                          <div className="section-title mb-1">解锁条件</div>
                          <ul className="space-y-1 text-muted-foreground">
                            {verdict.conditions.map((condition, i) => (
                              <li key={i}>· {condition}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </Reveal>
    </div>
  )
}

function StatCard({
  index,
  icon: Icon,
  label,
  value,
  hint,
}: {
  index: number
  icon: typeof ShieldCheck
  label: string
  value: ReactNode
  hint: string
}) {
  return (
    <div
      className="glass glass-hover animate-rise rounded-xl p-4"
      style={{ ['--stagger' as string]: `${index * 60}ms` }}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="section-title">{label}</span>
        <Icon className="h-4 w-4 text-primary/70" />
      </div>
      <div className="text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
      <div className="mt-1 truncate text-[0.7rem] text-muted-foreground">{hint}</div>
    </div>
  )
}
