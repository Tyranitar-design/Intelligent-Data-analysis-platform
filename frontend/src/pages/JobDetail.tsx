/**
 * 任务详情
 * ========
 *
 * 把一次采集从「一行摘要」展开成可诊断的执行报告：
 * 管道状态 · 执行时间线 · 降级链 · 去重统计 · 条目表。
 *
 * 所有状态都来自真实任务数据——不做与结果无关的装饰动画。
 */
import { Fragment, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowUpRight,
  CircleDashed,
  Loader2,
  PackageCheck,
  RefreshCw,
  RotateCcw,
} from 'lucide-react'

import apiClient from '@/api/client'
import CountUp from '@/components/motion/CountUp'
import Reveal from '@/components/motion/Reveal'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface TaskItem {
  task_id: number
  status: string
  capability: string | null
  attempts: number
  last_error: string | null
}

interface JobDetail {
  job_id: number
  plan_id: number
  status: string
  total_tasks: number
  done_tasks: number
  items_count: number
  dedup_stats: Record<string, number>
  quality_score: number
  error_dist: Record<string, number>
  started_at: string | null
  finished_at: string | null
  created_at: string | null
  tasks: TaskItem[]
}

interface CollectItemRow {
  item_id: number
  job_id: number
  source_url: string | null
  completeness: number
  version: number
  payload: Record<string, unknown> | null
}

const STATUS_TONE: Record<string, string> = {
  succeeded: 'badge-ok',
  partial: 'badge-warn',
  failed: 'badge-err',
  running: 'badge-info',
  waiting_human: 'badge-warn',
  pending: 'badge-info',
}

const STATUS_LABEL: Record<string, string> = {
  succeeded: '已完成',
  partial: '部分成功',
  failed: '失败',
  running: '执行中',
  waiting_human: '等待人工',
  pending: '排队中',
}

type NodeState = 'done' | 'active' | 'failed' | 'pending'

interface PipeNode {
  key: string
  label: string
  state: NodeState
  detail: string
}

const NODE_DOT: Record<NodeState, string> = {
  done: 'bg-primary',
  active: 'bg-primary animate-pulse-soft',
  failed: 'bg-destructive',
  pending: 'bg-muted-foreground/30',
}

function buildPipeline(job: JobDetail): PipeNode[] {
  const collectState: NodeState =
    job.status === 'succeeded' || job.status === 'partial'
      ? 'done'
      : job.status === 'failed'
        ? 'failed'
        : job.status === 'running'
          ? 'active'
          : 'pending'

  const dedup = job.dedup_stats ?? {}
  const dedupDone = Object.keys(dedup).length > 0
  const inserted = Number(dedup.inserted ?? 0)
  const skipped = Number(dedup.skipped ?? 0)

  return [
    { key: 'judge', label: '判别', state: 'done', detail: '判定留痕' },
    { key: 'collect', label: '采集', state: collectState, detail: STATUS_LABEL[job.status] ?? job.status },
    {
      key: 'dedup',
      label: '去重',
      state: dedupDone ? 'done' : 'pending',
      detail: dedupDone ? `新增 ${inserted} · 跳过 ${skipped}` : '待运行',
    },
    {
      key: 'store',
      label: '入库',
      state: job.items_count > 0 ? 'done' : 'pending',
      detail: `${job.items_count} 条`,
    },
  ]
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function formatDuration(from: string | null, to: string | null): string {
  if (!from || !to) return '—'
  const start = new Date(from).getTime()
  const end = new Date(to).getTime()
  if (Number.isNaN(start) || Number.isNaN(end)) return '—'
  const seconds = Math.max(0, Math.round((end - start) / 1000))
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

function shortValue(value: unknown): string {
  if (value == null) return '—'
  if (typeof value === 'string') return value.length > 60 ? `${value.slice(0, 60)}…` : value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    const text = JSON.stringify(value)
    return text.length > 60 ? `${text.slice(0, 60)}…` : text
  } catch {
    return '…'
  }
}

export default function JobDetailPage() {
  const { jobId } = useParams()
  const [job, setJob] = useState<JobDetail | null>(null)
  const [items, setItems] = useState<CollectItemRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [materializing, setMaterializing] = useState(false)
  const [resuming, setResuming] = useState(false)

  const load = useCallback(async () => {
    if (!jobId) return
    setLoading(true)
    setError(null)
    try {
      const [jobResp, itemsResp] = await Promise.allSettled([
        apiClient.get<JobDetail>(`/collect/jobs/${jobId}`),
        apiClient.get<{ items: CollectItemRow[] }>('/collect/items', {
          params: { job_id: jobId, limit: 100 },
        }),
      ])
      if (jobResp.status === 'fulfilled') {
        setJob(jobResp.value.data)
      } else {
        setError('任务不存在或加载失败')
      }
      if (itemsResp.status === 'fulfilled') setItems(itemsResp.value.data.items ?? [])
    } finally {
      setLoading(false)
    }
  }, [jobId])

  useEffect(() => {
    void load()
  }, [load])

  const pipeline = useMemo(() => (job ? buildPipeline(job) : []), [job])

  const columns = useMemo(() => {
    const keys: string[] = []
    for (const item of items) {
      for (const key of Object.keys(item.payload ?? {})) {
        if (!keys.includes(key) && keys.length < 4) keys.push(key)
      }
      if (keys.length >= 4) break
    }
    return keys
  }, [items])

  async function materialize() {
    if (!jobId) return
    setMaterializing(true)
    setMessage(null)
    try {
      const { data } = await apiClient.post<{
        id: number
        row_count: number
        column_count: number
      }>(`/collect/jobs/${jobId}/materialize`)
      setMessage(`数据集 #${data.id} 已创建：${data.row_count} 行 × ${data.column_count} 列`)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response
        ?.data?.detail
      setMessage(typeof detail === 'string' ? detail : '物化失败')
    } finally {
      setMaterializing(false)
    }
  }

  async function resumeJob() {
    if (!jobId) return
    setResuming(true)
    setMessage(null)
    try {
      const { data } = await apiClient.post<{ job: JobDetail; error?: string }>(
        `/collect/jobs/${jobId}/resume`,
        undefined,
        { timeout: 180000 },
      )
      setMessage(
        data.error
          ? `重试完成但仍有错误：${data.error}`
          : `重试完成——当前状态：${STATUS_LABEL[data.job.status] ?? data.job.status}`,
      )
      void load()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response
        ?.data?.detail
      setMessage(typeof detail === 'string' ? detail : '重试失败')
    } finally {
      setResuming(false)
    }
  }

  if (loading && !job) {
    return (
      <div className="mx-auto max-w-6xl">
        <div className="glass flex items-center gap-3 rounded-xl px-5 py-10 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> 加载任务详情…
        </div>
      </div>
    )
  }

  if (error || !job) {
    return (
      <div className="mx-auto max-w-6xl">
        <div className="glass rounded-xl px-5 py-12 text-center">
          <p className="text-sm text-muted-foreground">{error ?? '任务不存在'}</p>
          <Link
            to="/collect"
            className="mt-3 inline-flex items-center gap-1 text-xs text-primary hover:underline"
          >
            <ArrowLeft className="h-3 w-3" /> 返回采集任务
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {/* ---------------- 头部 ---------------- */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to="/collect"
            className="grid h-8 w-8 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
            aria-label="返回采集任务"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <h2 className="text-base font-semibold">任务 #{job.job_id}</h2>
          <span className={cn('badge-dot', STATUS_TONE[job.status] ?? 'badge-info')}>
            {STATUS_LABEL[job.status] ?? job.status}
          </span>
          <span className="text-xs text-muted-foreground">计划 #{job.plan_id}</span>
        </div>
        <div className="flex gap-2">
          {(job.status === 'failed' ||
            job.status === 'partial' ||
            job.status === 'running') && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => void resumeJob()}
              disabled={resuming}
            >
              {resuming ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              )}
              重试失败分片
            </Button>
          )}
          {job.status === 'succeeded' || job.status === 'partial' ? (
            <Button size="sm" onClick={() => void materialize()} disabled={materializing}>
              {materializing ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <PackageCheck className="mr-1.5 h-3.5 w-3.5" />
              )}
              物化为数据集
            </Button>
          ) : null}
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={cn('mr-1.5 h-3.5 w-3.5', loading && 'animate-spin')} />
            刷新
          </Button>
        </div>
      </div>

      {message && (
        <div className="glass rounded-lg px-4 py-2.5 text-xs text-muted-foreground">
          {message}
        </div>
      )}

      {/* ---------------- 摘要 ---------------- */}
      <Reveal className="glass rounded-xl p-5">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <SummaryCell label="条目" value={<CountUp value={job.items_count} />} hint="本次入库条数" />
          <SummaryCell
            label="质量分"
            value={<CountUp value={Math.round((job.quality_score ?? 0) * 100)} />}
            hint="完整度 × 有效占比（100 分制）"
          />
          <SummaryCell
            label="分片"
            value={
              <span className="tabular-nums">
                {job.done_tasks} / {job.total_tasks}
              </span>
            }
            hint="完成 / 总数"
          />
          <SummaryCell
            label="用时"
            value={<span className="tabular-nums">{formatDuration(job.started_at, job.finished_at)}</span>}
            hint="started → finished"
          />
        </div>
      </Reveal>

      {/* ---------------- 管道 ---------------- */}
      <Reveal delay={0.08} className="glass rounded-xl p-5">
        <h3 className="mb-4 text-sm font-semibold">执行管道</h3>
        <div className="flex flex-wrap items-start gap-y-4">
          {pipeline.map((node, index) => (
            <Fragment key={node.key}>
              <div className="flex w-24 flex-col items-center gap-1.5">
                <span className={cn('h-2.5 w-2.5 rounded-full', NODE_DOT[node.state])} />
                <span className="text-xs font-medium">{node.label}</span>
                <span className="text-center text-[0.64rem] leading-tight text-muted-foreground">
                  {node.detail}
                </span>
              </div>
              {index < pipeline.length - 1 && (
                <div
                  className={cn(
                    'mt-[4px] h-px w-8 sm:w-14',
                    pipeline[index + 1].state === 'pending' ? 'bg-border' : 'bg-primary/50',
                  )}
                />
              )}
            </Fragment>
          ))}
        </div>
      </Reveal>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* ---------------- 时间线 ---------------- */}
        <Reveal delay={0.12} className="glass rounded-xl p-5">
          <h3 className="mb-3 text-sm font-semibold">执行时间线</h3>
          <ul className="space-y-3">
            <TimelineRow label="创建" time={formatDateTime(job.created_at)} />
            <TimelineRow
              label="开始"
              time={formatDateTime(job.started_at)}
              delta={formatDuration(job.created_at, job.started_at)}
            />
            <TimelineRow
              label="完成"
              time={formatDateTime(job.finished_at)}
              delta={formatDuration(job.started_at, job.finished_at)}
              last
            />
          </ul>
        </Reveal>

        {/* ---------------- 去重统计 ---------------- */}
        <Reveal delay={0.16} className="glass rounded-xl p-5">
          <h3 className="mb-3 text-sm font-semibold">去重统计</h3>
          {Object.keys(job.dedup_stats ?? {}).length === 0 ? (
            <p className="text-xs text-muted-foreground">本任务暂无去重记录</p>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(job.dedup_stats).map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2"
                >
                  <span className="text-xs text-muted-foreground">{key}</span>
                  <span className="text-sm font-medium tabular-nums">{value}</span>
                </div>
              ))}
            </div>
          )}
          {Object.keys(job.error_dist ?? {}).length > 0 && (
            <div className="mt-3">
              <div className="section-title mb-1">错误分布</div>
              {Object.entries(job.error_dist).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between text-xs">
                  <span className="truncate text-muted-foreground">{key}</span>
                  <span className="tabular-nums text-destructive">{value}</span>
                </div>
              ))}
            </div>
          )}
        </Reveal>
      </div>

      {/* ---------------- 分片 / 降级链 ---------------- */}
      <Reveal delay={0.2} className="glass rounded-xl p-5">
        <h3 className="mb-3 text-sm font-semibold">分片与降级链（{job.tasks.length}）</h3>
        {job.tasks.length === 0 ? (
          <p className="text-xs text-muted-foreground">暂无分片记录</p>
        ) : (
          <div className="space-y-2">
            {job.tasks.map((task) => (
              <div
                key={task.task_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/60 px-3 py-2"
              >
                <div className="flex min-w-0 items-center gap-2">
                  {task.status === 'done' ? (
                    <span className="h-2 w-2 rounded-full bg-primary" />
                  ) : task.status === 'failed' ? (
                    <span className="h-2 w-2 rounded-full bg-destructive" />
                  ) : (
                    <CircleDashed className="h-3 w-3 text-muted-foreground" />
                  )}
                  <span className="mono-tag shrink-0">分片 #{task.task_id}</span>
                  <span className="text-xs">
                    {task.capability ? `能力：${task.capability}` : '未使用采集能力'}
                  </span>
                  {task.attempts > 1 && (
                    <span className="badge-dot badge-warn shrink-0">
                      尝试 {task.attempts} 次
                    </span>
                  )}
                </div>
                {task.last_error && (
                  <span
                    className="max-w-[46%] truncate text-xs text-destructive"
                    title={task.last_error}
                  >
                    {task.last_error}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </Reveal>

      {/* ---------------- 条目表 ---------------- */}
      <Reveal delay={0.24} className="glass overflow-hidden rounded-xl">
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-3.5">
          <h3 className="text-sm font-semibold">采集条目（{job.items_count}）</h3>
          <span className="text-[0.68rem] text-muted-foreground">最多显示最近 100 条</span>
        </div>
        {items.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-muted-foreground">
            本任务暂未入库条目
          </div>
        ) : (
          <div className="max-h-[460px] overflow-auto">
            <table className="w-full min-w-[680px] text-left text-xs">
              <thead className="sticky top-0 bg-card">
                <tr className="text-muted-foreground">
                  <th className="px-5 py-2.5 font-medium">来源</th>
                  {columns.map((column) => (
                    <th key={column} className="px-3 py-2.5 font-medium">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {items.map((item) => (
                  <tr key={item.item_id} className="transition-colors hover:bg-muted/30">
                    <td className="max-w-[280px] px-5 py-2.5">
                      {item.source_url ? (
                        <a
                          href={item.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 truncate text-primary hover:underline"
                          title={item.source_url}
                        >
                          <span className="truncate">
                            {item.source_url.replace(/^https?:\/\//, '')}
                          </span>
                          <ArrowUpRight className="h-3 w-3 shrink-0" />
                        </a>
                      ) : (
                        '—'
                      )}
                    </td>
                    {columns.map((column) => (
                      <td key={column} className="max-w-[220px] truncate px-3 py-2.5">
                        {shortValue(item.payload?.[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Reveal>
    </div>
  )
}

function SummaryCell({
  label,
  value,
  hint,
}: {
  label: string
  value: React.ReactNode
  hint: string
}) {
  return (
    <div>
      <div className="section-title mb-1">{label}</div>
      <div className="text-xl font-semibold tracking-tight">{value}</div>
      <div className="mt-0.5 truncate text-[0.66rem] text-muted-foreground">{hint}</div>
    </div>
  )
}

function TimelineRow({
  label,
  time,
  delta,
  last,
}: {
  label: string
  time: string
  delta?: string
  last?: boolean
}) {
  return (
    <li className="flex items-start gap-3">
      <div className="flex flex-col items-center">
        <span className="mt-0.5 h-2 w-2 rounded-full bg-primary/70" />
        {!last && <span className="mt-1 h-6 w-px bg-border" />}
      </div>
      <div className="flex flex-1 items-center justify-between">
        <span className="text-xs font-medium">{label}</span>
        <div className="text-right">
          <div className="text-xs tabular-nums">{time}</div>
          {delta && delta !== '—' && (
            <div className="text-[0.64rem] text-muted-foreground">+{delta}</div>
          )}
        </div>
      </div>
    </li>
  )
}
