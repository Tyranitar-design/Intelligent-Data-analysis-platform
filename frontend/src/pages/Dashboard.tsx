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
  Sparkles,
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
  // 状态条用的真实读取时刻（不造假数据）
  const [loadedAt, setLoadedAt] = useState('—')

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
      setLoadedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
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

  // 任务卡的汇总读数（v3）：用真实数据填满卡片留白，避免出现大片空区
  const jobsSucceeded = jobs.filter((j) => j.status === 'succeeded').length
  const jobsFailed = jobs.filter((j) => j.status === 'failed').length
  const jobsItems = jobs.reduce((sum, j) => sum + (Number(j.items_count) || 0), 0)

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {/* ---------------- 控制台抬头：页面标识 + 实时状态条 + 快捷操作 ----------------
          v3 调整：原「营销式 hero」（大标语 + 副标题 + 三个 CTA）与参考图的设计意图冲突——
          参考图的抬头区只有「面包屑 + 状态读数 + 操作」，首屏主角应当是数据本身。
          此处把 hero 降级为控制台抬头，并补一条全部由真实接口驱动的状态条。 */}
      <section className="panel px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-[1.05rem] font-semibold leading-tight text-foreground">平台概览</h2>
            <p className="mt-1 text-[0.72rem] text-muted-foreground">
              站点采集 · 数据物化 · 合规审计
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Link to="/discover">
              <Button size="sm" className="btn-glow">
                分析一个站点
                <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
              </Button>
            </Link>
            <Link to="/schedules">
              <Button size="sm" variant="outline">
                调度中心
              </Button>
            </Link>
            <Link to="/showcase">
              <Button size="sm" variant="ghost">
                <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                展示视图
              </Button>
            </Link>
          </div>
        </div>

        {/* 工程状态条：读数全部来自真实接口（服务能力 + 概览 + 本次读取时刻） */}
        <div className="status-strip hairline-t mt-3.5 pt-3">
          <span className="flex items-center gap-1.5">
            <span className={cn('status-dot', capabilities ? 'dot-ok' : 'dot-off')} />
            服务
            <span className="num text-foreground/85">{capabilities ? '在线' : '离线'}</span>
          </span>
          <span className="flex items-center gap-1.5">
            版本
            <span className="num text-foreground/85">
              {capabilities ? `v${capabilities.version}` : '—'}
            </span>
          </span>
          <span className="flex items-center gap-1.5">
            能力
            <span className="num text-foreground/85">
              {capabilities ? `${Object.keys(capabilities.capabilities).length} 项` : '—'}
            </span>
          </span>
          <span className="flex items-center gap-1.5">
            数据表
            <span className="num text-foreground/85">{overview?.total_tables ?? 0}</span>
          </span>
          <span className="ml-auto flex items-center gap-1.5">
            读取于
            <span className="num text-foreground/85">{loadedAt}</span>
          </span>
        </div>
      </section>

      {/* KPI Bento（v3）：首卡为主指标——跨 2 列 + featured 字号，
          取代 v2 的四宫格等宽排布，主次一眼可辨 */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          featured
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

      {/* v3：items-start 让两卡各自随内容收底——避免左卡被强行撑高后
          在列表与页脚之间留下大片空洞（参考图终审指出的唯一硬伤） */}
      <div className="grid items-start gap-5 lg:grid-cols-[1.3fr_1fr]">
        <Reveal delay={0.1} className="glass flex flex-col overflow-hidden rounded-xl">
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
                      质量 {Number(job.items_count) > 0 ? `${Math.round((job.quality_score ?? 0) * 100)}%` : '—'}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {/* 汇总读数条（v3）：真实聚合数据 + 语义色 + 容器底衬，
              从"卡内脚注"升级为"控制台读数条" */}
          <div className="status-strip hairline-t mt-auto bg-muted/25 px-5 py-2.5">
            <span className="flex items-center gap-1.5">
              本次显示
              <span className="num font-medium text-foreground/90">{jobs.length}</span>
            </span>
            <span className="flex items-center gap-1.5">
              成功
              <span className="num font-medium text-ok">{jobsSucceeded}</span>
            </span>
            <span className="flex items-center gap-1.5">
              失败
              <span
                className={cn(
                  'num font-medium',
                  jobsFailed > 0 ? 'text-err' : 'text-muted-foreground',
                )}
              >
                {jobsFailed}
              </span>
            </span>
            <span className="ml-auto flex items-center gap-1.5">
              采集记录
              <span className="num font-medium text-foreground/90">
                {jobsItems.toLocaleString()}
              </span>
            </span>
          </div>
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
  featured = false,
}: {
  index: number
  icon: typeof Database
  label: string
  value: ReactNode
  hint: string
  /** 主指标卡：更大字号与留白，用于建立 Bento 主次层级（v3） */
  featured?: boolean
}) {
  return (
    <div
      className={cn('panel relative overflow-hidden', featured && 'sm:col-span-2 lg:col-span-2')}
      style={{ ['--stagger' as string]: `${index * 60}ms` }}
    >
      <Tilt className={featured ? 'p-5' : 'p-4'}>
        <div className={cn('flex items-center justify-between', featured ? 'mb-3' : 'mb-2.5')}>
          <span className="section-title">{label}</span>
          <Icon
            className={cn('shrink-0 text-muted-foreground', featured ? 'h-4 w-4' : 'h-3.5 w-3.5')}
            strokeWidth={2}
          />
        </div>
        <div
          className={cn(
            'num animate-value-pop font-semibold leading-none tracking-tight text-foreground',
            featured ? 'text-[2.15rem]' : 'text-[1.5rem]',
          )}
        >
          {value}
        </div>
        <div
          className={cn(
            'mt-2 truncate text-muted-foreground',
            featured ? 'text-[0.72rem]' : 'text-[0.7rem]',
          )}
        >
          {hint}
        </div>
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
