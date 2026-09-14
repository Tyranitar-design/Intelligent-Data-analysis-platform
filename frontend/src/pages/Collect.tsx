/**
 * 采集任务
 * ========
 *
 * 计划 → 任务 → 条目 的三层视图。
 *
 * 信息密度优先：任务列表给的是"这条任务值不值得点进去"所需的全部判据
 * （状态、条目数、质量分、错误分布），点进去才展开分片细节。
 */
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import {
  Activity,
  ArrowUpRight,
  Loader2,
  PackageCheck,
  RefreshCw,
  TriangleAlert,
} from 'lucide-react'

import apiClient from '@/api/client'
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
  finished_at?: string | null
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

export default function CollectPage() {
  const [jobs, setJobs] = useState<JobRow[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [materializing, setMaterializing] = useState<number | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get<{ items: JobRow[] }>('/collect/jobs', {
        params: { limit: 50 },
      })
      setJobs(data.items ?? [])
    } catch {
      setJobs([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function materialize(jobId: number) {
    setMaterializing(jobId)
    setMessage(null)
    try {
      const { data } = await apiClient.post(`/collect/jobs/${jobId}/materialize`)
      setMessage(`数据集 #${data.id} 已创建：${data.row_count} 行 × ${data.column_count} 列`)
      void load()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response
        ?.data?.detail
      setMessage(typeof detail === 'string' ? detail : '物化失败')
    } finally {
      setMaterializing(null)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          采集任务由「站点分析 → 生成方案 → 执行」产生，也可通过 MCP 工具触发。
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

      {jobs.length === 0 && !loading ? (
        <div className="glass rounded-xl px-5 py-14 text-center">
          <PackageCheck className="mx-auto mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">暂无采集任务</p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            前往「站点分析」输入一个 URL 开始
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job, index) => (
            <motion.div
              key={job.job_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: Math.min(index * 0.04, 0.3) }}
              className="glass glass-hover overflow-hidden rounded-xl"
            >
              <div className="flex w-full items-center gap-2 px-5 py-3.5">
                <button
                  type="button"
                  onClick={() =>
                    setExpanded((current) => (current === job.job_id ? null : job.job_id))
                  }
                  className="flex min-w-0 flex-1 items-center justify-between gap-4 text-left"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="mono-tag shrink-0">#{job.job_id}</span>
                    <span
                      className={cn(
                        'badge-dot shrink-0',
                        STATUS_TONE[job.status] ?? 'badge-info',
                      )}
                    >
                      {STATUS_LABEL[job.status] ?? job.status}
                    </span>
                    <span className="truncate text-xs text-muted-foreground">
                      计划 #{job.plan_id} · 分片 {job.done_tasks}/{job.total_tasks}
                    </span>
                  </div>

                  <div className="flex shrink-0 items-center gap-5 text-xs">
                    <Stat label="条目" value={String(job.items_count)} />
                    <Stat
                      label="质量"
                      value={`${Math.round((job.quality_score ?? 0) * 100)}%`}
                    />
                    <Stat label="去重命中" value={String(dedupHits(job))} />
                  </div>
                </button>
                <Link
                  to={`/collect/${job.job_id}`}
                  className="grid h-7 w-7 shrink-0 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60 hover:text-primary"
                  aria-label={`查看任务 ${job.job_id} 详情`}
                  title="查看详情"
                >
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              </div>

              {expanded === job.job_id && (
                <div className="border-t border-border/60 px-5 py-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <div className="section-title mb-2">去重统计</div>
                      <dl className="space-y-1 text-xs">
                        {Object.entries(job.dedup_stats ?? {}).map(([key, value]) => (
                          <div key={key} className="flex justify-between">
                            <dt className="text-muted-foreground">{DEDUP_LABEL[key] ?? key}</dt>
                            <dd className="tabular-nums">{value}</dd>
                          </div>
                        ))}
                        {Object.keys(job.dedup_stats ?? {}).length === 0 && (
                          <div className="text-muted-foreground">无记录</div>
                        )}
                      </dl>
                    </div>

                    <div>
                      <div className="section-title mb-2">错误分布</div>
                      {Object.keys(job.error_dist ?? {}).length === 0 ? (
                        <div className="text-xs text-muted-foreground">无错误</div>
                      ) : (
                        <ul className="space-y-1 text-xs">
                          {Object.entries(job.error_dist).map(([key, value]) => (
                            <li key={key} className="flex items-start gap-2">
                              <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
                              <span className="flex-1 text-muted-foreground">{key}</span>
                              <span className="tabular-nums">{value}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 flex items-center gap-2 border-t border-border/60 pt-3.5">
                    <Button
                      size="sm"
                      onClick={() => void materialize(job.job_id)}
                      disabled={job.items_count === 0 || materializing === job.job_id}
                    >
                      {materializing === job.job_id && (
                        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                      )}
                      物化为数据集
                    </Button>
                    <span className="text-[0.7rem] text-muted-foreground">
                      规范化 + PII 最小化 + 血缘记录
                    </span>
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}

const DEDUP_LABEL: Record<string, string> = {
  inserted: '新增',
  updated: '内容更新',
  skipped: '跳过',
  content_hits: '内容命中',
  known_hits: '增量命中',
}

function dedupHits(job: JobRow): number {
  const stats = job.dedup_stats ?? {}
  return (stats.skipped ?? 0) + (stats.content_hits ?? 0) + (stats.known_hits ?? 0)
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-right">
      <div className="text-[0.62rem] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="tabular-nums font-medium">{value}</div>
    </div>
  )
}
