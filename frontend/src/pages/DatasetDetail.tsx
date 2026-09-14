/**
 * 数据集详情
 * ==========
 *
 * 单个数据集的完整档案：schema、字段覆盖、PII 处理、字段级血缘、预览与导出。
 *
 * 回答"这份数据能不能信"——每一列都能回溯到提取规则与来源页面。
 */
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowUpRight,
  Database,
  Download,
  GitBranch,
  Loader2,
  RefreshCw,
  Table2,
} from 'lucide-react'

import apiClient from '@/api/client'
import Reveal from '@/components/motion/Reveal'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface LineageEntry {
  field: string
  item_field?: string
  extractor_rule: string
  coverage: number
  domain?: string | null
  source_sample?: string
  source_count?: number
}

interface FieldStat {
  type: string
  coverage: number
  null_count: number
  min?: number
  max?: number
  pii_action?: string
}

interface DatasetMeta {
  id: number
  name: string
  description: string | null
  source_type: string
  collect_job_id: number | null
  row_count: number
  column_count: number
  size_bytes: number
  created_at: string | null
  schema: Record<string, { column: string; type: string }> | null
  lineage: LineageEntry[] | null
  pii_policy: Record<string, string> | null
  statistics: { fields?: Record<string, FieldStat> } | null
}

interface PreviewPayload {
  dataset: DatasetMeta
  dataset_id: number
  columns: string[]
  rows: Record<string, unknown>[]
  total: number
  limit: number
  offset: number
  missing_table?: boolean
}

const PAGE_SIZE = 50

const PII_LABEL: Record<string, string> = {
  hashed: '哈希',
  masked: '打码',
  generalized: '泛化',
  binned: '分箱',
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

function formatBytes(bytes: number): string {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function DatasetDetailPage() {
  const { id } = useParams()
  const datasetId = Number(id)
  const [data, setData] = useState<PreviewPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)

  const load = useCallback(async () => {
    if (!Number.isFinite(datasetId)) {
      setError('无效的数据集 ID')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { data: payload } = await apiClient.get<PreviewPayload>(
        `/collect/datasets/${datasetId}/preview`,
        { params: { limit: PAGE_SIZE, offset } },
      )
      setData(payload)
    } catch {
      setError('数据集不存在或加载失败')
    } finally {
      setLoading(false)
    }
  }, [datasetId, offset])

  useEffect(() => {
    void load()
  }, [load])

  function download(format: 'csv' | 'json' | 'excel') {
    window.open(`/api/v1/analytics/export/${datasetId}?format=${format}`, '_blank')
  }

  if (loading && !data) {
    return (
      <div className="mx-auto max-w-6xl">
        <div className="glass flex items-center gap-3 rounded-xl px-5 py-10 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> 加载数据集…
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-6xl">
        <div className="glass rounded-xl px-5 py-12 text-center">
          <p className="text-sm text-muted-foreground">{error ?? '数据集不存在'}</p>
          <Link
            to="/datasets"
            className="mt-3 inline-flex items-center gap-1 text-xs text-primary hover:underline"
          >
            <ArrowLeft className="h-3 w-3" /> 返回数据集列表
          </Link>
        </div>
      </div>
    )
  }

  const meta = data.dataset
  const fieldStats = meta?.statistics?.fields ?? {}
  const lineage = meta?.lineage ?? []
  const schema = meta?.schema ?? {}
  const fieldNames = Object.keys(fieldStats).length
    ? Object.keys(fieldStats)
    : data.columns.filter((c) => c !== 'id' && c !== 'source_url')

  const canPrev = offset > 0
  const canNext = offset + PAGE_SIZE < (data.total ?? 0)

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {/* ---------------- 头部 ---------------- */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <Link
            to="/datasets"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
            aria-label="返回数据集列表"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-base font-semibold">
                {meta?.name ?? `数据集 #${datasetId}`}
              </h2>
              <span className="mono-tag">ds_{datasetId}</span>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {meta?.row_count ?? data.total} 行 × {meta?.column_count ?? data.columns.length} 列
              {meta?.collect_job_id ? ` · 来自采集任务 #${meta.collect_job_id}` : ''}
              {meta?.created_at ? ` · ${formatDateTime(meta.created_at)} 创建` : ''}
              {meta?.size_bytes ? ` · ${formatBytes(meta.size_bytes)}` : ''}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => download('csv')}>
            <Download className="mr-1.5 h-3.5 w-3.5" /> CSV
          </Button>
          <Button variant="outline" size="sm" onClick={() => download('json')}>
            <Download className="mr-1.5 h-3.5 w-3.5" /> JSON
          </Button>
          <Button variant="outline" size="sm" onClick={() => download('excel')}>
            <Download className="mr-1.5 h-3.5 w-3.5" /> Excel
          </Button>
          <Link to="/analytics">
            <Button size="sm">
              去分析 <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
            </Button>
          </Link>
        </div>
      </div>

      {/* ---------------- 字段概览 + 血缘 ---------------- */}
      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <Reveal delay={0.05} className="glass overflow-hidden rounded-xl">
          <div className="flex items-center gap-2 border-b border-border/60 px-5 py-3.5">
            <Table2 className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">字段概览（{fieldNames.length}）</h3>
          </div>
          {fieldNames.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-muted-foreground">
              暂无字段统计
            </div>
          ) : (
            <div className="max-h-[380px] overflow-auto">
              <table className="w-full min-w-[520px] text-left text-xs">
                <thead className="sticky top-0 bg-card/95 backdrop-blur">
                  <tr className="text-muted-foreground">
                    <th className="px-5 py-2.5 font-medium">字段</th>
                    <th className="px-3 py-2.5 font-medium">类型</th>
                    <th className="px-3 py-2.5 font-medium">覆盖</th>
                    <th className="px-3 py-2.5 font-medium">PII</th>
                    <th className="px-3 py-2.5 font-medium">范围</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {fieldNames.map((field) => {
                    const stat = fieldStats[field]
                    const range =
                      stat && stat.min != null && stat.max != null
                        ? `${stat.min} ~ ${stat.max}`
                        : '—'
                    return (
                      <tr key={field} className="transition-colors hover:bg-muted/30">
                        <td className="max-w-[220px] truncate px-5 py-2.5">
                          <div className="truncate font-medium">{field}</div>
                          {schema[field]?.column && schema[field].column !== field && (
                            <div className="truncate text-[0.64rem] text-muted-foreground">
                              列名 {schema[field].column}
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-muted-foreground">
                          {stat?.type ?? schema[field]?.type ?? '—'}
                        </td>
                        <td className="px-3 py-2.5 tabular-nums">
                          {stat ? `${Math.round((stat.coverage ?? 0) * 100)}%` : '—'}
                        </td>
                        <td className="px-3 py-2.5">
                          {stat?.pii_action ? (
                            <span className="badge-dot badge-warn">
                              {PII_LABEL[stat.pii_action] ?? stat.pii_action}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 tabular-nums text-muted-foreground">
                          {range}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Reveal>

        <Reveal delay={0.1} className="glass overflow-hidden rounded-xl">
          <div className="flex items-center gap-2 border-b border-border/60 px-5 py-3.5">
            <GitBranch className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">字段级血缘（{lineage.length}）</h3>
          </div>
          {lineage.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-muted-foreground">
              暂无血缘记录（数据集由接口导入或旧数据）
            </div>
          ) : (
            <ul className="max-h-[380px] divide-y divide-border/40 overflow-auto">
              {lineage.map((entry) => (
                <li key={entry.field} className="px-5 py-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs font-medium">{entry.field}</span>
                    <span className="shrink-0 text-[0.64rem] tabular-nums text-muted-foreground">
                      覆盖 {Math.round((entry.coverage ?? 0) * 100)}%
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-1.5 text-[0.68rem] text-muted-foreground">
                    <span className="shrink-0">←</span>
                    <span className="mono-tag truncate">{entry.extractor_rule}</span>
                    {entry.source_count != null && (
                      <span className="shrink-0">来源 {entry.source_count} 页</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Reveal>
      </div>

      {/* ---------------- 数据预览 ---------------- */}
      {data.missing_table ? (
        <div className="glass rounded-xl px-5 py-10 text-center text-sm text-muted-foreground">
          物理表缺失（可能已被清理）——元信息保留供审计
        </div>
      ) : (
        <Reveal delay={0.15} className="glass overflow-hidden rounded-xl">
          <div className="flex items-center justify-between border-b border-border/60 px-5 py-3.5">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">
                数据预览（{data.total.toLocaleString()}）
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[0.68rem] text-muted-foreground tabular-nums">
                {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="h-7"
                disabled={!canPrev || loading}
                onClick={() => setOffset((v) => Math.max(0, v - PAGE_SIZE))}
              >
                上一页
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-7"
                disabled={!canNext || loading}
                onClick={() => setOffset((v) => v + PAGE_SIZE)}
              >
                下一页
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={() => void load()}
                disabled={loading}
                aria-label="刷新预览"
              >
                <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
              </Button>
            </div>
          </div>

          {data.rows.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-muted-foreground">
              无可预览数据
            </div>
          ) : (
            <div className="max-h-[520px] overflow-auto">
              <table className="w-full min-w-[720px] text-left text-xs">
                <thead className="sticky top-0 bg-card/95 backdrop-blur">
                  <tr className="text-muted-foreground">
                    <th className="px-4 py-2 font-medium">#</th>
                    {data.columns.map((col) => (
                      <th key={col} className="whitespace-nowrap px-4 py-2 font-medium">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {data.rows.map((row, index) => (
                    <tr key={index} className="transition-colors hover:bg-muted/30">
                      <td className="px-4 py-2 tabular-nums text-muted-foreground">
                        {offset + index + 1}
                      </td>
                      {data.columns.map((col) => (
                        <td
                          key={col}
                          className="max-w-[320px] truncate px-4 py-2 text-muted-foreground"
                          title={String(row[col] ?? '')}
                        >
                          {row[col] == null ? '—' : String(row[col])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Reveal>
      )}
    </div>
  )
}
