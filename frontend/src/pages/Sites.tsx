/**
 * 站点库
 * ======
 *
 * 把画像从「采集的副产品」变成「可复用的资产」：
 * 每个站点一张卡（判定 / 类型 / 置信 / 覆盖 / 时效），
 * 点击展开完整画像（访问状态 / 结构 / 字段 / 策略 / 判定）。
 */
import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  Compass,
  ExternalLink,
  Loader2,
  RefreshCw,
  Search,
} from 'lucide-react'

import apiClient from '@/api/client'
import CountUp from '@/components/motion/CountUp'
import Reveal from '@/components/motion/Reveal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { cn } from '@/lib/utils'

interface ProfileRow {
  profile_id: number
  domain: string
  url_pattern: string
  version: number
  site_type: string | null
  title: string | null
  confidence: number
  coverage: number
  field_count?: number
  decision: string | null
  last_verified: string | null
}

interface StatsPayload {
  total: number
  by_decision: {
    proceed: number
    confirm_required: number
    blocked: number
    unknown: number
  }
  by_type: Record<string, number>
  stale_count: number
}

interface ProfileDetail {
  profile_id: number
  domain: string
  url_pattern: string
  version: number
  sample_url: string | null
  site: Record<string, unknown>
  access: Record<string, unknown>
  structure: Record<string, unknown>
  fields: {
    name?: string
    type?: string
    source?: string
    path?: string
    coverage?: number
  }[]
  strategy: Record<string, unknown>
  compliance: Record<string, unknown>
  confidence: number
  coverage: number
  first_seen: string | null
  last_verified: string | null
}

// v5：判定列用实底 pill（参考图统一语言）
const DECISION_TONE: Record<string, string> = {
  proceed: 'pill-ok',
  confirm_required: 'pill-warn',
  blocked: 'pill-err',
}

const DECISION_LABEL: Record<string, string> = {
  proceed: '可采',
  confirm_required: '待确认',
  blocked: '不可采',
}

const DECISION_FILTERS = [
  { value: '', label: '全部' },
  { value: 'proceed', label: '可采' },
  { value: 'confirm_required', label: '待确认' },
  { value: 'blocked', label: '不可采' },
] as const

function timeAgo(iso: string | null): string {
  if (!iso) return '—'
  const time = new Date(iso).getTime()
  if (Number.isNaN(time)) return '—'
  const seconds = Math.max(0, Math.floor((Date.now() - time) / 1000))
  if (seconds < 60) return '刚刚'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`
  return `${Math.floor(seconds / 86400)} 天前`
}

function isStale(iso: string | null): boolean {
  if (!iso) return false
  return Date.now() - new Date(iso).getTime() > 14 * 86400 * 1000
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export default function SitesPage() {
  const [profiles, setProfiles] = useState<ProfileRow[]>([])
  const [stats, setStats] = useState<StatsPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('')
  const [search, setSearch] = useState('')
  const [message, setMessage] = useState<string | null>(null)

  const [detailId, setDetailId] = useState<number | null>(null)
  const [detail, setDetail] = useState<ProfileDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [reanalyzing, setReanalyzing] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [listResp, statsResp] = await Promise.allSettled([
        apiClient.get<{ items: ProfileRow[] }>('/discover/profiles', {
          params: { limit: 200 },
        }),
        apiClient.get<StatsPayload>('/discover/profiles/stats'),
      ])
      if (listResp.status === 'fulfilled') {
        setProfiles(listResp.value.data.items ?? [])
      }
      if (statsResp.status === 'fulfilled') setStats(statsResp.value.data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const openDetail = useCallback(async (profileId: number) => {
    setDetailId(profileId)
    setDetail(null)
    setDetailLoading(true)
    try {
      const { data } = await apiClient.get<ProfileDetail>(
        `/discover/profiles/${profileId}`,
      )
      setDetail(data)
    } catch {
      setMessage('画像详情加载失败')
    } finally {
      setDetailLoading(false)
    }
  }, [])

  async function reanalyze(profile: ProfileDetail) {
    if (!profile.sample_url) {
      setMessage('该画像没有记录样本 URL，无法自动重新探测')
      return
    }
    setReanalyzing(true)
    setMessage(null)
    try {
      const { data } = await apiClient.post<{ compliance?: { decision?: string } }>(
        '/discover/analyze',
        { url: profile.sample_url, force_refresh: true },
        { timeout: 120000 },
      )
      const decision = data.compliance?.decision
      setMessage(
        `已重新探测 ${profile.domain}${decision ? `（判定：${decision}）` : ''}`,
      )
      void openDetail(profile.profile_id)
      void load()
    } catch {
      setMessage('重新探测失败（目标可能不可达）')
    } finally {
      setReanalyzing(false)
    }
  }

  const filtered = profiles.filter((p) => {
    if (filter && p.decision !== filter) return false
    if (search && !p.domain.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          画像是可复用资产：同一站点再次采集时跳过完整探测；「重新探测」应对站点改版。
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

      {/* ---------------- 统计条 ---------------- */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          index={0}
          label="画像"
          value={<CountUp value={stats?.total ?? 0} />}
          hint={stats && stats.stale_count > 0 ? `${stats.stale_count} 个超 14 天建议重探测` : '全部新鲜'}
        />
        <StatCard
          index={1}
          label="可采"
          value={<CountUp value={stats?.by_decision.proceed ?? 0} />}
          hint="proceed"
        />
        <StatCard
          index={2}
          label="待确认"
          value={<CountUp value={stats?.by_decision.confirm_required ?? 0} />}
          hint="等待授权声明"
        />
        <StatCard
          index={3}
          label="不可采"
          value={<CountUp value={stats?.by_decision.blocked ?? 0} />}
          hint="附替代源（见合规中心）"
        />
      </section>

      {/* ---------------- 筛选 ---------------- */}
      <div className="glass flex flex-wrap items-center gap-3 rounded-xl px-4 py-3">
        <div className="flex flex-wrap items-center gap-1.5">
          {DECISION_FILTERS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setFilter(opt.value)}
              className={cn(
                'rounded-lg border px-2.5 py-1 text-xs transition-colors',
                filter === opt.value
                  ? 'border-primary/50 bg-primary/10 font-medium text-primary'
                  : 'border-border/60 text-muted-foreground hover:text-foreground',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="relative ml-auto">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索域名"
            className="h-8 w-52 pl-8 text-xs"
          />
        </div>
      </div>

      {/* ---------------- 卡片网格 ---------------- */}
      {filtered.length === 0 && !loading ? (
        <div className="glass rounded-xl px-5 py-14 text-center">
          <Compass className="mx-auto mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            {profiles.length === 0 ? '还没有站点画像' : '没有符合筛选条件的画像'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            {profiles.length === 0 ? (
              <>
                去
                <Link to="/discover" className="mx-1 text-primary hover:underline">
                  站点分析
                </Link>
                输入一个 URL，生成第一份画像
              </>
            ) : (
              '调整筛选条件或清空搜索'
            )}
          </p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((profile, index) => (
            <Reveal key={profile.profile_id} delay={Math.min(index * 0.03, 0.3)}>
              <button
                type="button"
                onClick={() => void openDetail(profile.profile_id)}
                className="glass glass-hover w-full rounded-xl p-4 text-left"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="truncate text-sm font-medium">{profile.domain}</span>
                  <span
                    className={cn(
                      'pill shrink-0',
                      DECISION_TONE[profile.decision ?? ''] ?? 'pill-info',
                    )}
                  >
                    {DECISION_LABEL[profile.decision ?? ''] ?? '未知'}
                  </span>
                </div>
                <div className="mt-1 truncate text-[0.7rem] text-muted-foreground">
                  {profile.site_type ?? '未分类'}
                  {profile.title ? ` · ${profile.title}` : ''}
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <MiniStat
                    label="置信"
                    value={`${Math.round((profile.confidence ?? 0) * 100)}%`}
                  />
                  <MiniStat
                    label="覆盖"
                    value={`${Math.round((profile.coverage ?? 0) * 100)}%`}
                  />
                  <MiniStat label="字段" value={String(profile.field_count ?? 0)} />
                </div>
                <div className="mt-2.5 flex items-center justify-between text-[0.66rem] text-muted-foreground">
                  <span>验证于 {timeAgo(profile.last_verified)}</span>
                  {isStale(profile.last_verified) && (
                    <span className="text-amber-500">建议重探测</span>
                  )}
                </div>
              </button>
            </Reveal>
          ))}
        </div>
      )}

      {/* ---------------- 详情抽屉 ---------------- */}
      <Sheet
        open={detailId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDetailId(null)
            setDetail(null)
          }
        }}
      >
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          {detailLoading || !detail ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-5 pt-1">
              <SheetHeader className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <SheetTitle className="truncate">{detail.domain}</SheetTitle>
                  <span
                    className={cn(
                      'pill shrink-0',
                      DECISION_TONE[
                        String((detail.compliance as { decision?: string }).decision ?? '')
                      ] ?? 'pill-info',
                    )}
                  >
                    {DECISION_LABEL[
                      String((detail.compliance as { decision?: string }).decision ?? '')
                    ] ?? '未知'}
                  </span>
                </div>
                <SheetDescription>
                  {detail.url_pattern} · v{detail.version} · 置信{' '}
                  {Math.round((detail.confidence ?? 0) * 100)}% · 覆盖{' '}
                  {Math.round((detail.coverage ?? 0) * 100)}%
                </SheetDescription>
              </SheetHeader>

              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void reanalyze(detail)}
                  disabled={reanalyzing}
                >
                  {reanalyzing ? (
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                  )}
                  重新探测
                </Button>
                {detail.sample_url && (
                  <a href={detail.sample_url} target="_blank" rel="noreferrer">
                    <Button size="sm" variant="ghost">
                      <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                      访问站点
                    </Button>
                  </a>
                )}
              </div>

              <Section title="访问状态">
                <KVList data={detail.access} />
              </Section>

              <Section title="结构识别">
                <KVList data={detail.structure} />
              </Section>

              <Section title={`可采字段（${detail.fields.length}）`}>
                {detail.fields.length === 0 ? (
                  <p className="text-xs text-muted-foreground">未识别到字段</p>
                ) : (
                  <div className="overflow-hidden rounded-lg border border-border/60">
                    <table className="w-full text-left text-[0.7rem]">
                      <thead className="bg-muted/40 text-muted-foreground">
                        <tr>
                          <th className="px-3 py-2 font-medium">字段</th>
                          <th className="px-2 py-2 font-medium">类型</th>
                          <th className="px-2 py-2 font-medium">来源</th>
                          <th className="px-2 py-2 font-medium">覆盖</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40">
                        {detail.fields.map((field, index) => (
                          <tr key={`${field.name}-${index}`}>
                            <td className="max-w-[140px] truncate px-3 py-1.5">
                              {field.name ?? '—'}
                            </td>
                            <td className="px-2 py-1.5 text-muted-foreground">
                              {field.type ?? '—'}
                            </td>
                            <td className="max-w-[150px] truncate px-2 py-1.5 text-muted-foreground">
                              {field.source ?? '—'}
                              {field.path ? `:${field.path}` : ''}
                            </td>
                            <td className="px-2 py-1.5 tabular-nums">
                              {field.coverage != null
                                ? `${Math.round(field.coverage * 100)}%`
                                : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Section>

              <Section title="推荐策略">
                <KVList data={detail.strategy} />
              </Section>

              <Section title="合规判定">
                <KVList data={detail.compliance} />
              </Section>

              <Section title="时间线">
                <div className="space-y-1 text-xs text-muted-foreground">
                  <div>首次见到 {formatDateTime(detail.first_seen)}</div>
                  <div>最近验证 {formatDateTime(detail.last_verified)}</div>
                </div>
              </Section>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}

function StatCard({
  index,
  label,
  value,
  hint,
}: {
  index: number
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
        <Compass className="h-4 w-4 text-primary/70" />
      </div>
      <div className="text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
      <div className="mt-1 truncate text-[0.7rem] text-muted-foreground">{hint}</div>
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted/30 py-1.5 text-center">
      <div className="text-[0.6rem] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="text-xs font-medium tabular-nums">{value}</div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <div className="section-title mb-2">{title}</div>
      {children}
    </div>
  )
}

function KVList({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data ?? {}).filter(
    ([, value]) => value !== null && value !== undefined && value !== '',
  )
  if (entries.length === 0) {
    return <p className="text-xs text-muted-foreground">—</p>
  }
  return (
    <dl className="space-y-1.5 text-xs">
      {entries.map(([key, value]) => (
        <div key={key} className="flex items-start justify-between gap-3">
          <dt className="shrink-0 text-muted-foreground">{key}</dt>
          <dd className="min-w-0 truncate text-right">{renderValue(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

function renderValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.length ? value.map(String).join('、') : '—'
  }
  if (typeof value === 'object' && value !== null) {
    try {
      const text = JSON.stringify(value)
      return text.length > 90 ? `${text.slice(0, 90)}…` : text
    } catch {
      return '…'
    }
  }
  return String(value)
}
