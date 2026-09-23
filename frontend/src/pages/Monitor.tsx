/**
 * 运行监视
 * ========
 *
 * 平台自身的健康度：服务状态、任务队列、采集限速（跨请求的实时节奏）、存储用量。
 *
 * 限速表展示的是"正在进行"的自适应状态——被 429/503 降速的域名会在这里
 * 显示当前速率与原基准的差距。
 */
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import {
  Activity,
  Archive,
  Gauge,
  Loader2,
  RefreshCw,
  ServerCog,
  ShieldCheck,
  Timer,
} from 'lucide-react'

import apiClient from '@/api/client'
import CountUp from '@/components/motion/CountUp'
import Reveal from '@/components/motion/Reveal'
import { Button } from '@/components/ui/button'
import { DualStatBar, SectionHead, Sparkline, StatusStrip, StripItem } from '@/components/visual/console'
import { cn } from '@/lib/utils'

interface DomainRate {
  base_per_second: number
  current_per_second: number
  min_per_second: number
  max_concurrency: number
  success_streak: number
  total_requests: number
  throttle_events: number
  throttled: boolean
}

interface MonitorStats {
  service: { app_name: string; version: string; database: string }
  queue: {
    pending_jobs: number
    running_jobs: number
    total_jobs: number
    job_status: Record<string, number>
    schedules_total: number
    schedules_enabled: number
  }
  rate: {
    tracked_domains: number
    throttled_domains: string[]
    domains: Record<string, DomainRate>
  }
  storage: {
    datasets: number
    items: number
    profiles: number
    tables: number | null
    db_file: string | null
    db_bytes: number | null
  }
}

interface RetentionEntry {
  count: number
  oldest: string | null
  newest: string | null
}

interface RetentionPayload {
  generated_at: string
  tables: Record<string, RetentionEntry>
  total_rows: number
}

const AUTO_REFRESH_MS = 30_000

const RETENTION_LABELS: [string, string][] = [
  ['collect_items', '采集条目'],
  ['datasets', '数据集'],
  ['audit_logs', '审计日志'],
  ['compliance_verdicts', '合规判定'],
]

function formatBytes(bytes: number | null): string {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatShort(iso: string | null): string {
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

export default function MonitorPage() {
  const [stats, setStats] = useState<MonitorStats | null>(null)
  const [retention, setRetention] = useState<RetentionPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [auto, setAuto] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  /* v3 NOC 走势：每次轮询把真实读数推进环形缓冲（最多 60 个采样点 ≈ 30 分钟）。
     时序不是假数据——它就是本页轮询到的真实队列深度与限速域数的进程内历史。 */
  const MAX_POINTS = 60
  const queueHist = useRef<number[]>([])
  const domainHist = useRef<number[]>([])
  const [historyTick, setHistoryTick] = useState(0)

  const pushSample = useCallback((s: MonitorStats) => {
    const q = s.queue.pending_jobs + s.queue.running_jobs
    const d = s.rate.tracked_domains
    queueHist.current = [...queueHist.current, q].slice(-MAX_POINTS)
    domainHist.current = [...domainHist.current, d].slice(-MAX_POINTS)
    setHistoryTick((t) => t + 1) // 触发依赖历史数组的重渲染
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [{ data }, retentionResponse] = await Promise.all([
        apiClient.get<MonitorStats>('/monitor/stats'),
        apiClient
          .get<RetentionPayload>('/monitor/retention')
          .catch(() => null),
      ])
      setStats(data)
      pushSample(data)
      if (retentionResponse) setRetention(retentionResponse.data)
      setLastUpdated(new Date())
    } catch {
      // 保持上次快照
    } finally {
      setLoading(false)
    }
  }, [pushSample])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!auto) return
    const timer = window.setInterval(() => void load(), AUTO_REFRESH_MS)
    return () => window.clearInterval(timer)
  }, [auto, load])

  const domains = Object.entries(stats?.rate.domains ?? {})

  // 走势数据（historyTick 仅用于触发重渲染，读取走 ref）
  void historyTick
  const queueSeries = queueHist.current
  const domainSeries = domainHist.current

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {/* ---------------- 控制台抬头（v3）：标识 + 实时状态条 + 操作 ---------------- */}
      <section className="panel px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-[1.05rem] font-semibold leading-tight text-foreground">运行监视</h2>
            <p className="mt-1 text-[0.72rem] text-muted-foreground">
              服务健康 · 任务队列 · 采集限速（进程级实时节奏）
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setAuto((v) => !v)}
              className={cn(
                'rounded-lg border px-2.5 py-1 text-xs transition-colors',
                auto
                  ? 'border-primary/50 bg-primary/10 font-medium text-primary'
                  : 'border-border/60 text-muted-foreground hover:text-foreground',
              )}
            >
              自动刷新 {auto ? '开' : '关'}
            </button>
            <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
              {loading ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
              )}
              刷新
            </Button>
          </div>
        </div>

        {/* 实时读数条：全部来自真实接口 */}
        <StatusStrip className="hairline-t mt-3.5 pt-3">
          <StripItem
            label="服务"
            value={stats ? '在线' : '—'}
            tone={stats ? 'ok' : 'off'}
          />
          <StripItem label="版本" value={stats ? `v${stats.service.version}` : '—'} />
          <StripItem label="队列深度" value={stats ? (stats.queue.pending_jobs + stats.queue.running_jobs) : '—'} />
          <StripItem label="运行中" value={stats ? stats.queue.running_jobs : '—'} />
          <StripItem
            label="限速域"
            value={stats ? stats.rate.throttled_domains.length : '—'}
            tone={stats && stats.rate.throttled_domains.length > 0 ? 'warn' : undefined}
          />
          <StripItem label="跟踪域" value={stats ? stats.rate.tracked_domains : '—'} />
          <span className="ml-auto flex items-center gap-1.5">
            读取于
            <span className="num font-medium text-foreground/90">
              {lastUpdated ? lastUpdated.toLocaleTimeString('zh-CN', { hour12: false }) : '—'}
            </span>
          </span>
        </StatusStrip>
      </section>

      {/* ---------------- 走势双卡（v3 NOC）：真实轮询采样积累 ---------------- */}
      <section className="grid gap-3 lg:grid-cols-2">
        <Reveal className="panel overflow-hidden">
          <SectionHead
            icon={<Activity className="h-4 w-4" />}
            title="队列深度走势"
            meta={`最近 ${queueSeries.length} 次采样`}
            action={
              <Sparkline data={queueSeries} width={120} height={32} className="text-primary" />
            }
          />
          <div className="flex items-end justify-between gap-4 px-4 pb-4 pt-3">
            <div>
              <div className="label-xs">当前深度（排队 + 运行）</div>
              <div className="num mt-1.5 text-[2rem] font-semibold leading-none text-foreground">
                {stats ? stats.queue.pending_jobs + stats.queue.running_jobs : '—'}
              </div>
              <div className="mt-2 text-[0.7rem] text-muted-foreground">
                {stats
                  ? `排队 ${stats.queue.pending_jobs} · 运行 ${stats.queue.running_jobs} · 总任务 ${stats.queue.total_jobs}`
                  : '—'}
              </div>
            </div>
            <Sparkline data={queueSeries} width={220} height={64} className="text-primary" />
          </div>
        </Reveal>

        <Reveal className="panel overflow-hidden">
          <SectionHead
            icon={<Gauge className="h-4 w-4" />}
            title="限速域走势"
            meta={`最近 ${domainSeries.length} 次采样`}
            action={
              <Sparkline data={domainSeries} width={120} height={32} className="text-primary" />
            }
          />
          <div className="flex items-end justify-between gap-4 px-4 pb-4 pt-3">
            <div>
              <div className="label-xs">跟踪域名（进程级共享限速）</div>
              <div className="num mt-1.5 text-[2rem] font-semibold leading-none text-foreground">
                {stats ? stats.rate.tracked_domains : '—'}
              </div>
              <div
                className={cn(
                  'mt-2 text-[0.7rem]',
                  stats && stats.rate.throttled_domains.length > 0 ? 'text-warn' : 'text-muted-foreground',
                )}
              >
                {stats
                  ? stats.rate.throttled_domains.length > 0
                    ? `⚠ 限速中：${stats.rate.throttled_domains.slice(0, 3).join('、')}${stats.rate.throttled_domains.length > 3 ? ' 等' : ''}`
                    : '全部域名节奏正常'
                  : '—'}
              </div>
            </div>
            <Sparkline data={domainSeries} width={220} height={64} className="text-primary" />
          </div>
        </Reveal>
      </section>

      {/* ---------------- 四卡 ---------------- */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          index={0}
          icon={ShieldCheck}
          label="服务状态"
          value={
            <span className="flex items-center gap-2">
              <span className="badge-dot badge-ok">健康</span>
            </span>
          }
          hint={stats ? `v${stats.service.version} · ${stats.service.database}` : '—'}
        />
        <StatCard
          index={1}
          icon={ServerCog}
          label="任务队列"
          value={
            <CountUp
              value={(stats?.queue.pending_jobs ?? 0) + (stats?.queue.running_jobs ?? 0)}
            />
          }
          hint={
            stats
              ? `排队 ${stats.queue.pending_jobs} · 运行 ${stats.queue.running_jobs} · 调度 ${stats.queue.schedules_enabled}/${stats.queue.schedules_total} 启用`
              : '—'
          }
        />
        <StatCard
          index={2}
          icon={Gauge}
          label="采集限速"
          value={<CountUp value={stats?.rate.tracked_domains ?? 0} />}
          hint={
            stats
              ? stats.rate.throttled_domains.length > 0
                ? `限速中 ${stats.rate.throttled_domains.length} 个域名`
                : '全部域名节奏正常'
              : '—'
          }
        />
        <StatCard
          index={3}
          icon={Timer}
          label="存储用量"
          value={
            <span className="tabular-nums text-xl">
              {formatBytes(stats?.storage.db_bytes ?? null)}
            </span>
          }
          hint={
            stats
              ? `表 ${stats.storage.tables ?? '—'} · 数据集 ${stats.storage.datasets} · 条目 ${stats.storage.items}`
              : '—'
          }
        />
      </section>

      {/* ---------------- 域名限速 · Worker 卡矩阵（v3） ----------------
          参考图的「Worker Nodes」在本平台的对应物就是采集域名：每个域名一张卡，
          等宽主机名 + 速率对比条（当前 vs 基准）+ 状态点 + 请求数。数据全部真实。 */}
      {domains.length > 0 && (
        <section>
          <SectionHead
            icon={<ServerCog className="h-4 w-4" />}
            title="采集通道"
            meta={`${domains.length} 个域名`}
            action={
              <span className="label-xs">
                {stats && stats.rate.throttled_domains.length > 0
                  ? `${stats.rate.throttled_domains.length} 个限速中`
                  : '全部正常'}
              </span>
            }
          />
          <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {domains.slice(0, 12).map(([domain, snap]) => {
              const throttled = snap.throttled
              const ratio = snap.base_per_second > 0 ? snap.current_per_second / snap.base_per_second : 1
              return (
                <div key={domain} className="panel px-3.5 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="num truncate text-[0.78rem] text-foreground/90" title={domain}>
                      {domain}
                    </span>
                    <span className={cn('status-dot', throttled ? 'bg-amber-400' : 'bg-emerald-400')} aria-hidden="true" />
                  </div>
                  <div className="mt-2.5">
                    <DualStatBar current={snap.current_per_second} base={snap.base_per_second} max={Math.max(snap.base_per_second, snap.current_per_second) || 1} />
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[0.68rem] text-muted-foreground">
                    <span className="num">
                      {snap.current_per_second.toFixed(1)}/s
                      <span className="ml-1 opacity-60">/ 基准 {snap.base_per_second.toFixed(1)}</span>
                    </span>
                    <span className={cn('num', throttled && 'text-amber-400')}>
                      {snap.total_requests.toLocaleString()} 次
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[0.66rem] text-muted-foreground">
                    <span>并发 {snap.max_concurrency}</span>
                    <span>
                      {throttled ? (
                        <span className="text-amber-400">限速中 · 连续成功 {snap.success_streak}</span>
                      ) : (
                        <span>连续成功 {snap.success_streak}</span>
                      )}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* ---------------- 域名限速表 ---------------- */}
      <Reveal delay={0.1} className="glass overflow-hidden rounded-xl">
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">域名限速状态（{domains.length}）</h3>
          </div>
          {lastUpdated && (
            <span className="text-[0.68rem] text-muted-foreground tabular-nums">
              更新于{' '}
              {lastUpdated.toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false,
              })}
            </span>
          )}
        </div>

        {domains.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-muted-foreground">
            暂无活动域名——发起一次采集后，各域名的实时节奏会出现在这里
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-xs">
              <thead className="text-muted-foreground">
                <tr className="border-b border-border/40">
                  <th className="px-5 py-2.5 font-medium">域名</th>
                  <th className="px-3 py-2.5 font-medium">基准 → 当前</th>
                  <th className="px-3 py-2.5 font-medium">请求数</th>
                  <th className="px-3 py-2.5 font-medium">被限速</th>
                  <th className="px-3 py-2.5 font-medium">连续成功</th>
                  <th className="px-3 py-2.5 font-medium">状态</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {domains.map(([domain, snap]) => (
                  <tr key={domain} className="transition-colors hover:bg-muted/30">
                    <td className="max-w-[260px] truncate px-5 py-2.5 font-medium">
                      {domain}
                    </td>
                    <td className="px-3 py-2.5 tabular-nums">
                      {snap.base_per_second.toFixed(1)} →{' '}
                      <span
                        className={cn(
                          snap.throttled ? 'text-amber-500' : 'text-foreground',
                        )}
                      >
                        {snap.current_per_second.toFixed(1)}
                      </span>{' '}
                      /s
                    </td>
                    <td className="px-3 py-2.5 tabular-nums text-muted-foreground">
                      {snap.total_requests}
                    </td>
                    <td className="px-3 py-2.5 tabular-nums text-muted-foreground">
                      {snap.throttle_events > 0 ? (
                        <span className="text-amber-500">{snap.throttle_events} 次</span>
                      ) : (
                        '0'
                      )}
                    </td>
                    <td className="px-3 py-2.5 tabular-nums text-muted-foreground">
                      {snap.success_streak}
                    </td>
                    <td className="px-3 py-2.5">
                      <span
                        className={cn(
                          'badge-dot',
                          snap.throttled ? 'badge-warn' : 'badge-ok',
                        )}
                      >
                        {snap.throttled ? '限速中' : '正常'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Reveal>

      {/* ---------------- 存储明细 ---------------- */}
      <Reveal delay={0.15} className="glass rounded-xl p-5">
        <h3 className="mb-3 text-sm font-semibold">存储与资产明细</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Detail label="数据库文件" value={stats?.storage.db_file ?? '—'} />
          <Detail label="文件大小" value={formatBytes(stats?.storage.db_bytes ?? null)} />
          <Detail label="数据表" value={String(stats?.storage.tables ?? '—')} />
          <Detail label="站点画像" value={String(stats?.storage.profiles ?? '—')} />
          <Detail label="数据集" value={String(stats?.storage.datasets ?? '—')} />
          <Detail label="采集条目" value={String(stats?.storage.items ?? '—')} />
          <Detail label="任务总数" value={String(stats?.queue.total_jobs ?? '—')} />
          <Detail
            label="调度规则"
            value={`${stats?.queue.schedules_enabled ?? '—'} 启用 / ${stats?.queue.schedules_total ?? '—'}`}
          />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg border border-border/60 px-3 py-2.5 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">指标导出</span>
          <span className="mono-tag">GET /api/v1/monitor/metrics</span>
          Prometheus 文本格式 —— 可接入 scrape，或用于人工诊断
        </div>
      </Reveal>

      {/* ---------------- 数据保留（只读报告） ---------------- */}
      <Reveal delay={0.2} className="glass overflow-hidden rounded-xl">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <Archive className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">数据保留（只读）</h3>
          </div>
          <span className="text-[0.68rem] tabular-nums text-muted-foreground">
            共 {retention?.total_rows.toLocaleString() ?? '—'} 行 · 报告不做自动删除
          </span>
        </div>
        {retention ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-xs">
              <thead className="text-muted-foreground">
                <tr className="border-b border-border/40">
                  <th className="px-5 py-2.5 font-medium">资产</th>
                  <th className="px-3 py-2.5 font-medium">条数</th>
                  <th className="px-3 py-2.5 font-medium">最早</th>
                  <th className="px-3 py-2.5 font-medium">最新</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {RETENTION_LABELS.map(([key, label]) => {
                  const entry = retention.tables[key]
                  if (!entry) return null
                  return (
                    <tr key={key} className="transition-colors hover:bg-muted/30">
                      <td className="px-5 py-2.5 font-medium">{label}</td>
                      <td className="px-3 py-2.5 tabular-nums">
                        {entry.count.toLocaleString()}
                      </td>
                      <td className="px-3 py-2.5 tabular-nums text-muted-foreground">
                        {formatShort(entry.oldest)}
                      </td>
                      <td className="px-3 py-2.5 tabular-nums text-muted-foreground">
                        {formatShort(entry.newest)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-5 py-6 text-center text-sm text-muted-foreground">
            保留报告暂不可用
          </div>
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
  icon: typeof Gauge
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

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/60 px-3 py-2.5">
      <div className="text-[0.62rem] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-0.5 truncate text-sm font-medium tabular-nums">{value}</div>
    </div>
  )
}
