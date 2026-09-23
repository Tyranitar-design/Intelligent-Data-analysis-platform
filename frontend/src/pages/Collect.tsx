/**
 * 采集任务（v4 · 对标"数据采集平台"目标图）
 * ========
 *
 * v4 布局：
 *   KPI 读数行（总采集条目 / 任务成功率 / 合规通过率 / 数据集）
 *   → 任务表（进度条 + 状态徽章 + 时长）· 数据管道（四态分布）· 实时活动流。
 *
 * 数据真实性：所有读数来自 /collect/jobs、/discover/verdicts/stats、
 * /collect/datasets 的实时聚合——无历史采样的图表不做假曲线。
 */
import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import {
  ArrowUpRight,
  ChevronRight,
  Globe2,
  ListChecks,
  Loader2,
  RefreshCw,
} from 'lucide-react'

import apiClient from '@/api/client'
import CountUp from '@/components/motion/CountUp'
import { RingProgress } from '@/components/visual/MiniCharts'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface JobRow {
  job_id: number
  plan_id: number
  status: string
  total_tasks: number
  done_tasks: number
  items_count: number
  quality_score: number
  dedup_stats: Record<string, number>
  error_dist: Record<string, number>
  created_at?: string | null
  started_at?: string | null
  finished_at?: string | null
}

interface VerdictStats {
  total: number
  by_decision: { proceed: number; confirm_required: number; blocked: number }
}

// v5：任务状态列用实底 pill（参考图统一语言）
const STATUS_TONE: Record<string, string> = {
  succeeded: 'pill-ok',
  partial: 'pill-warn',
  failed: 'pill-err',
  running: 'pill-info',
  waiting_human: 'pill-warn',
  pending: 'pill-info',
}

const STATUS_LABEL: Record<string, string> = {
  succeeded: '已完成',
  partial: '部分成功',
  failed: '失败',
  running: '运行中',
  waiting_human: '等待人工',
  pending: '等待中',
}

const STATUS_DOT: Record<string, string> = {
  succeeded: 'bg-[hsl(158_74%_52%)]',
  partial: 'bg-[hsl(38_92%_58%)]',
  failed: 'bg-[hsl(0_74%_60%)]',
  running: 'bg-primary',
  pending: 'bg-muted-foreground/40',
}

function progressOf(job: JobRow): number {
  if (job.status === 'succeeded') return 100
  if (!job.total_tasks) return job.status === 'failed' ? 100 : 0
  return Math.round((job.done_tasks / job.total_tasks) * 100)
}

function formatDuration(from?: string | null, to?: string | null): string {
  if (!from || !to) return '—'
  const seconds = Math.max(
    0,
    Math.round((new Date(to).getTime() - new Date(from).getTime()) / 1000),
  )
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

function timeAgo(iso?: string | null): string {
  if (!iso) return '—'
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000))
  if (seconds < 60) return '刚刚'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`
  return `${Math.floor(seconds / 86400)} 天前`
}

export default function CollectPage() {
  const [jobs, setJobs] = useState<JobRow[]>([])
  const [verdicts, setVerdicts] = useState<VerdictStats | null>(null)
  const [datasetCount, setDatasetCount] = useState(0)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [jobsResp, verdictResp, datasetResp] = await Promise.allSettled([
        apiClient.get<{ items: JobRow[] }>('/collect/jobs', { params: { limit: 50 } }),
        apiClient.get<VerdictStats>('/discover/verdicts/stats'),
        apiClient.get<{ total?: number }>('/collect/datasets', { params: { limit: 1 } }),
      ])
      if (jobsResp.status === 'fulfilled') setJobs(jobsResp.value.data.items ?? [])
      if (verdictResp.status === 'fulfilled') setVerdicts(verdictResp.value.data)
      if (datasetResp.status === 'fulfilled') setDatasetCount(datasetResp.value.data.total ?? 0)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  // ---- KPI 聚合（全部真实） ----
  const totalItems = jobs.reduce((sum, job) => sum + (Number(job.items_count) || 0), 0)
  const finished = jobs.filter((job) =>
    ['succeeded', 'partial', 'failed'].includes(job.status),
  )
  const successRate = finished.length
    ? finished.filter((job) => job.status === 'succeeded').length / finished.length
    : null
  const complianceRate =
    verdicts && verdicts.total > 0 ? verdicts.by_decision.proceed / verdicts.total : null

  // ---- 管道四态 ----
  const pipe = [
    { key: 'pending', label: '等待中', count: jobs.filter((j) => j.status === 'pending').length },
    { key: 'running', label: '运行中', count: jobs.filter((j) => j.status === 'running').length },
    {
      key: 'succeeded',
      label: '已完成',
      count: jobs.filter((j) => ['succeeded', 'partial'].includes(j.status)).length,
    },
    { key: 'failed', label: '失败', count: jobs.filter((j) => j.status === 'failed').length },
  ]
  const pipelineTotal = pipe.reduce((sum, node) => sum + node.count, 0)

  // ---- 活动流（最近 8 条任务事件） ----
  const activity = [...jobs].slice(0, 8)

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          采集任务由「站点分析 → 生成方案 → 执行」产生，也可通过 MCP 工具或调度中心触发。
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

      {/* ---- KPI 读数行 ---- */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          index={0}
          label="总采集条目"
          featured
          value={<CountUp value={totalItems} />}
          hint={`来自 ${jobs.length} 个任务 · ${pipelineTotal} 条管道记录`}
        />
        <KpiCard
          index={1}
          label="任务成功率"
          value={
            successRate == null ? (
              '—'
            ) : (
              <span>
                <CountUp value={Math.round(successRate * 100)} decimals={0} />
                <span className="text-base">%</span>
              </span>
            )
          }
          hint={`已完成 ${finished.filter((j) => j.status === 'succeeded').length} / ${finished.length}`}
          ring={
            successRate == null ? undefined : (
              <RingProgress
                value={successRate}
                label={`${Math.round(successRate * 100)}%`}
                sub="成功"
              />
            )
          }
        />
        <KpiCard
          index={2}
          label="合规通过率"
          value={
            complianceRate == null ? (
              '—'
            ) : (
              <span>
                <CountUp value={Math.round(complianceRate * 100)} decimals={0} />
                <span className="text-base">%</span>
              </span>
            )
          }
          hint={verdicts ? `判定记录 ${verdicts.total} 条` : '—'}
          ring={
            complianceRate == null ? undefined : (
              <RingProgress
                value={complianceRate}
                label={`${Math.round(complianceRate * 100)}%`}
                sub="合规"
              />
            )
          }
        />
        <KpiCard
          index={3}
          label="数据集"
          value={<CountUp value={datasetCount} />}
          hint="已物化的结构化资产"
        />
      </section>

      <div className="grid items-start gap-4 lg:grid-cols-[1.5fr_1fr]">
        {/* ---- 任务表 ---- */}
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.06 }}
          className="panel overflow-hidden"
        >
          <div className="flex items-center justify-between px-5 pb-2 pt-4">
            <div className="flex items-center gap-2">
              <ListChecks className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">采集任务</h3>
              <span className="text-xs text-muted-foreground">共 {jobs.length} 个</span>
            </div>
            <span className="text-[0.66rem] text-muted-foreground">点击行打开详情</span>
          </div>

          {jobs.length === 0 && !loading ? (
            <div className="px-5 py-12 text-center">
              <Globe2 className="mx-auto mb-3 h-7 w-7 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">暂无采集任务</p>
              <Link
                to="/discover"
                className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                从分析一个站点开始 <ArrowUpRight className="h-3 w-3" />
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-xs">
                <thead className="text-muted-foreground">
                  <tr className="border-b border-border/40">
                    <th className="px-5 py-2 font-medium">任务</th>
                    <th className="px-3 py-2 font-medium">状态</th>
                    <th className="px-3 py-2 font-medium">进度</th>
                    <th className="px-3 py-2 text-right font-medium">条目</th>
                    <th className="px-3 py-2 text-right font-medium">质量</th>
                    <th className="px-3 py-2 text-right font-medium">时长</th>
                    <th className="w-8 px-3 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {jobs.map((job) => {
                    const progress = progressOf(job)
                    return (
                      <tr key={job.job_id} className="group transition-colors hover:bg-muted/30">
                        <td className="px-5 py-2.5">
                          <Link
                            to={`/collect/${job.job_id}`}
                            className="num font-medium text-foreground group-hover:text-primary"
                          >
                            #{job.job_id}
                          </Link>
                          <span className="ml-2 text-[0.66rem] text-muted-foreground">
                            计划 #{job.plan_id}
                          </span>
                        </td>
                        <td className="px-3 py-2.5">
                          <span
                            className={cn(
                              'pill',
                              STATUS_TONE[job.status] ?? 'pill-info',
                            )}
                          >
                            {STATUS_LABEL[job.status] ?? job.status}
                          </span>
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <div className="bar-track w-20">
                              <div
                                className={cn(
                                  'bar-fill',
                                  job.status === 'failed' && 'bg-[hsl(0_74%_60%)]',
                                )}
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                            <span className="num text-[0.66rem] text-muted-foreground">
                              {progress}%
                            </span>
                          </div>
                        </td>
                        <td className="num px-3 py-2.5 text-right">
                          {(Number(job.items_count) || 0).toLocaleString()}
                        </td>
                        <td className="num px-3 py-2.5 text-right text-muted-foreground">
                          {Number(job.items_count) > 0
                            ? `${Math.round((job.quality_score ?? 0) * 100)}%`
                            : '—'}
                        </td>
                        <td className="num px-3 py-2.5 text-right text-muted-foreground">
                          {formatDuration(job.started_at ?? job.created_at, job.finished_at)}
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          <Link
                            to={`/collect/${job.job_id}`}
                            className="text-muted-foreground transition-colors hover:text-primary"
                            aria-label={`打开任务 ${job.job_id} 详情`}
                          >
                            <ChevronRight className="h-3.5 w-3.5" />
                          </Link>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </motion.section>

        {/* ---- 右列：管道 + 活动流 ---- */}
        <div className="space-y-4">
          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.12 }}
            className="panel p-5"
          >
            <h3 className="mb-4 text-sm font-semibold">数据管道</h3>
            <div className="flex items-center justify-between gap-1">
              {pipe.map((node, index) => (
                <div key={node.key} className="flex items-center gap-1">
                  <div className="flex w-[58px] flex-col items-center gap-1.5">
                    <span
                      className={cn(
                        'grid h-7 w-7 place-items-center rounded-full border text-[0.62rem] font-medium',
                        node.count > 0
                          ? node.key === 'failed'
                            ? 'border-[hsl(0_74%_60%)] text-[hsl(0_74%_66%)]'
                            : 'border-[hsl(var(--primary)/0.5)] text-primary ring-2 ring-[hsl(var(--primary)/0.12)]'
                          : 'border-border/70 text-muted-foreground/60',
                      )}
                    >
                      {node.count}
                    </span>
                    <span className="text-[0.62rem] text-muted-foreground">{node.label}</span>
                  </div>
                  {index < pipe.length - 1 && (
                    <ChevronRight className="mb-4 h-3 w-3 shrink-0 text-muted-foreground/40" />
                  )}
                </div>
              ))}
            </div>
          </motion.section>

          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.18 }}
            className="panel p-5"
          >
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">实时活动</h3>
              <Link
                to="/audit"
                className="inline-flex items-center gap-0.5 text-[0.68rem] text-primary hover:underline"
              >
                审计日志 <ArrowUpRight className="h-3 w-3" />
              </Link>
            </div>
            {activity.length === 0 ? (
              <p className="text-xs text-muted-foreground">暂无活动记录</p>
            ) : (
              <ul className="space-y-2.5">
                {activity.map((job) => (
                  <li key={job.job_id} className="flex items-center gap-2.5 text-xs">
                    <span
                      className={cn(
                        'h-1.5 w-1.5 shrink-0 rounded-full',
                        STATUS_DOT[job.status] ?? 'bg-muted-foreground/40',
                      )}
                    />
                    <span className="num shrink-0 text-[0.66rem] text-muted-foreground">
                      {timeAgo(job.finished_at ?? job.created_at)}
                    </span>
                    <span className="min-w-0 flex-1 truncate">
                      任务 #{job.job_id} ·{' '}
                      {STATUS_LABEL[job.status] ?? job.status}
                      {Number(job.items_count) > 0 && ` · ${job.items_count} 条`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </motion.section>
        </div>
      </div>
    </div>
  )
}

function KpiCard({
  index,
  label,
  value,
  hint,
  featured = false,
  ring,
}: {
  index: number
  label: string
  value: ReactNode
  hint: string
  featured?: boolean
  /** 右侧环形进度（v5，传真实比例） */
  ring?: ReactNode
}) {
  return (
    <div
      className={cn('panel animate-rise', featured && 'sm:col-span-2 lg:col-span-1')}
      style={{ ['--stagger' as string]: `${index * 60}ms` }}
    >
      <div className={cn(featured ? 'p-5' : 'p-4')}>
        <div className="label-xs mb-1.5">{label}</div>
        <div className="flex items-end justify-between gap-3">
          <div className="min-w-0">
            <div
              className={cn(
                'num font-semibold tracking-tight',
                featured ? 'text-[2rem] leading-none text-primary' : 'text-[1.6rem] leading-none',
              )}
            >
              {value}
            </div>
            <div className="mt-2 truncate text-[0.68rem] text-muted-foreground">{hint}</div>
          </div>
          {ring && <div className="shrink-0">{ring}</div>}
        </div>
      </div>
    </div>
  )
}
