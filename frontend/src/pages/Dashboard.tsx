/**
 * 工作台
 * ======
 *
 * 平台的入口页：一屏之内回答三个问题——
 *   现在有什么（数据资产）、正在做什么（任务）、接下来能做什么（快捷入口）。
 */
import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  ArrowUpRight,
  Database,
  FileBarChart,
  Globe2,
  Layers,
  Radar,
  ServerCog,
  Table2,
} from 'lucide-react'

import apiClient from '@/api/client'
import CountUp from '@/components/motion/CountUp'
import Reveal from '@/components/motion/Reveal'
import Tilt from '@/components/motion/Tilt'
import { Button } from '@/components/ui/button'
import { useAppStore } from '@/stores/appStore'
import { cn } from '@/lib/utils'

interface JobRow {
  job_id: number
  plan_id: number
  status: string
  items_count: number
  quality_score: number
}

interface TableRow {
  name: string
  count?: number
}

interface OverviewPayload {
  total_tables?: number
  tables?: TableRow[]
}

const STATUS_TONE: Record<string, string> = {
  succeeded: 'badge-ok',
  partial: 'badge-warn',
  failed: 'badge-err',
  running: 'badge-info',
  waiting_human: 'badge-warn',
  pending: 'badge-info',
}

export default function DashboardPage() {
  const capabilities = useAppStore((s) => s.capabilities)
  const fetchCapabilities = useAppStore((s) => s.fetchCapabilities)

  const [overview, setOverview] = useState<OverviewPayload | null>(null)
  const [jobs, setJobs] = useState<JobRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    async function load() {
      const [overviewResult, jobsResult] = await Promise.allSettled([
        apiClient.get<OverviewPayload>('/data/overview'),
        apiClient.get<{ items: JobRow[] }>('/collect/jobs', { params: { limit: 6 } }),
      ])
      if (!alive) return
      if (overviewResult.status === 'fulfilled') setOverview(overviewResult.value.data)
      if (jobsResult.status === 'fulfilled') setJobs(jobsResult.value.data.items ?? [])
      setLoading(false)
    }
    void load()
    if (!capabilities) void fetchCapabilities()
    return () => {
      alive = false
    }
  }, [capabilities, fetchCapabilities])

  const datasetTables = (overview?.tables ?? []).filter((t) =>
    String(t.name).startsWith('ds_'),
  )
  const totalRows = (overview?.tables ?? []).reduce(
    (sum, t) => sum + (Number(t.count) || 0),
    0,
  )

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {/* ---------------- Hero：平台定位与快捷入口 ---------------- */}
      <section className="aurora grid-bg overflow-hidden rounded-2xl border border-border/60 px-6 py-7 sm:px-8">
        <div className="animate-rise relative z-10 flex flex-wrap items-end justify-between gap-5">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 text-[0.7rem] font-medium uppercase tracking-[0.16em] text-primary/85">
              <Radar className="h-3.5 w-3.5" strokeWidth={2.2} />
              WebInsight
            </div>
            <h2 className="mt-2 text-[1.45rem] font-semibold leading-snug tracking-tight sm:text-[1.65rem]">
              任意站点，从可采判定到洞察报告
            </h2>
            <p className="mt-1.5 text-xs text-muted-foreground">
              四维合规判定 · 定时采集与三级去重 · 数据物化与分析 · 全程审计留痕
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            <Link to="/discover">
              <Button size="sm">
                分析一个站点
                <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
              </Button>
            </Link>
            <Link to="/schedules">
              <Button size="sm" variant="outline">
                调度中心
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          index={0}
          icon={Database}
          label="数据表"
          value={loading ? '—' : <CountUp value={overview?.total_tables ?? 0} />}
          hint={`其中 ${datasetTables.length} 张为采集数据集`}
        />
        <StatCard
          index={1}
          icon={Layers}
          label="入库记录"
          value={loading ? '—' : <CountUp value={totalRows} />}
          hint="全部数据表行数合计"
        />
        <StatCard
          index={2}
          icon={Globe2}
          label="采集任务"
          value={loading ? '—' : <CountUp value={jobs.length} />}
          hint="最近 6 条"
        />
        <StatCard
          index={3}
          icon={ServerCog}
          label="服务能力"
          value={
            capabilities ? (
              <CountUp value={Object.keys(capabilities.capabilities).length} />
            ) : (
              '—'
            )
          }
          hint={capabilities ? `v${capabilities.version}` : '未连接'}
        />
      </section>

      <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <Reveal delay={0.1} className="glass overflow-hidden rounded-xl">
          <div className="flex items-center justify-between border-b border-border/60 px-5 py-3.5">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">最近采集任务</h3>
            </div>
            <Link
              to="/collect"
              className="flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary"
            >
              全部 <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>

          {jobs.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <p className="text-sm text-muted-foreground">还没有采集任务</p>
              <Link
                to="/discover"
                className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                从分析一个站点开始 <ArrowUpRight className="h-3 w-3" />
              </Link>
            </div>
          ) : (
            <ul className="divide-y divide-border/40">
              {jobs.map((job) => (
                <li
                  key={job.job_id}
                  className="flex items-center justify-between gap-3 px-5 py-3"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="mono-tag shrink-0">#{job.job_id}</span>
                    <span
                      className={cn(
                        'badge-dot shrink-0',
                        STATUS_TONE[job.status] ?? 'badge-info',
                      )}
                    >
                      {job.status}
                    </span>
                    <span className="truncate text-xs text-muted-foreground">
                      计划 #{job.plan_id}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-4 text-xs">
                    <span className="tabular-nums">{job.items_count} 条</span>
                    <span className="tabular-nums text-muted-foreground">
                      质量 {Math.round((job.quality_score ?? 0) * 100)}%
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Reveal>

        <Reveal delay={0.16} className="glass rounded-xl p-5">
          <h3 className="mb-3 text-sm font-semibold">开始使用</h3>
          <div className="space-y-2">
            <ActionLink
              to="/discover"
              icon={Radar}
              title="分析站点"
              desc="输入 URL，识别结构与可采字段"
            />
            <ActionLink
              to="/collect"
              icon={Globe2}
              title="查看采集任务"
              desc="进度、质量分与去重统计"
            />
            <ActionLink
              to="/datasets"
              icon={Table2}
              title="浏览数据集"
              desc="物化后的结构化数据"
            />
            <ActionLink
              to="/analytics"
              icon={Activity}
              title="执行分析"
              desc="EDA、统计、相关性与异常检测"
            />
            <ActionLink
              to="/reports"
              icon={FileBarChart}
              title="生成报告"
              desc="含血缘与隐私处理记录"
            />
          </div>
        </Reveal>
      </div>
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
  icon: typeof Database
  label: string
  value: ReactNode
  hint: string
}) {
  return (
    <div
      className="glass glass-hover animate-rise rounded-xl"
      style={{ ['--stagger' as string]: `${index * 60}ms` }}
    >
      <Tilt className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="section-title">{label}</span>
          <Icon className="h-4 w-4 text-primary/70" />
        </div>
        <div className="text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
        <div className="mt-1 truncate text-[0.7rem] text-muted-foreground">{hint}</div>
      </Tilt>
    </div>
  )
}

function ActionLink({
  to,
  icon: Icon,
  title,
  desc,
}: {
  to: string
  icon: typeof Radar
  title: string
  desc: string
}) {
  return (
    <Link
      to={to}
      className="group flex items-center gap-3 rounded-lg border border-border/60 px-3 py-2.5 transition-colors hover:border-primary/40 hover:bg-primary/5"
    >
      <Icon className="h-4 w-4 shrink-0 text-primary" />
      <div className="min-w-0 flex-1">
        <div className="text-[0.82rem] font-medium">{title}</div>
        <div className="truncate text-[0.7rem] text-muted-foreground">{desc}</div>
      </div>
      <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
    </Link>
  )
}
