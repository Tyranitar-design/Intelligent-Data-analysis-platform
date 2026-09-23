/**
 * 数据集
 * ======
 *
 * 采集结果物化后的结构化资产。
 * 列表回答"有哪些数据、多大、什么时候来的"，预览回答"里面长什么样"。
 */
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { ArrowUpRight, Database, Loader2, RefreshCw, Table2 } from 'lucide-react'

import apiClient from '@/api/client'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/visual/Skeleton'
import { cn } from '@/lib/utils'

interface TableRow {
  name: string
  count?: number
  columns?: { name: string; type: string }[]
}

interface PreviewPayload {
  dataset_id: number
  columns: string[]
  rows: Record<string, unknown>[]
  total: number
}

export default function DatasetsPage() {
  const [tables, setTables] = useState<TableRow[]>([])
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<PreviewPayload | null>(null)
  const [previewId, setPreviewId] = useState<number | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get<{ tables: TableRow[] }>('/data/tables')
      // 采集物化出的表以 ds_ 前缀命名
      setTables((data.tables ?? []).filter((t) => String(t.name).startsWith('ds_')))
    } catch {
      setTables([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function openPreview(tableName: string) {
    const datasetId = Number(String(tableName).replace(/^ds_/, ''))
    if (!Number.isFinite(datasetId)) return
    setPreviewId(datasetId)
    setPreviewLoading(true)
    try {
      const { data } = await apiClient.get<PreviewPayload>(
        `/collect/datasets/${datasetId}/preview`,
        { params: { limit: 30 } },
      )
      setPreview(data)
    } catch {
      setPreview(null)
    } finally {
      setPreviewLoading(false)
    }
  }

  // KPI 聚合（真实数据）
  const totalRows = tables.reduce((sum, t) => sum + (Number(t.count) || 0), 0)
  const avgColumns = tables.length
    ? Math.round(
        tables.reduce((sum, t) => sum + (t.columns?.length ?? 0), 0) / tables.length,
      )
    : 0

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          由采集任务物化而来：规范化字段类型、执行 PII 最小化、记录字段级血缘。
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

      {/* ---------------- KPI 读数行 ---------------- */}
      <section className="grid gap-3 sm:grid-cols-3">
        {[
          {
            label: '数据集',
            value: String(tables.length),
            hint: '已物化的结构化资产',
            tone: '',
          },
          {
            label: '总行数据',
            value: totalRows.toLocaleString(),
            hint: '全部数据集行数合计',
            tone: 'text-primary',
          },
          {
            label: '平均字段数',
            value: String(avgColumns),
            hint: '每个数据集的列数均值',
            tone: '',
          },
        ].map((item, index) => (
          <div
            key={item.label}
            className="panel animate-rise p-4"
            style={{ ['--stagger' as string]: `${index * 60}ms` }}
          >
            <div className="label-xs mb-1.5">{item.label}</div>
            <div className={cn('num text-[1.6rem] font-semibold leading-none', item.tone)}>
              {item.value}
            </div>
            <div className="mt-2 truncate text-[0.68rem] text-muted-foreground">
              {item.hint}
            </div>
          </div>
        ))}
      </section>

      {loading && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="glass rounded-xl p-4">
              <div className="mb-3 flex items-center justify-between">
                <Skeleton className="h-5 w-20" />
                <Skeleton className="h-4 w-4 rounded" />
              </div>
              <Skeleton className="mb-2 h-6 w-16" />
              <Skeleton className="h-2.5 w-24" />
            </div>
          ))}
        </div>
      )}

      {tables.length === 0 && !loading ? (
        <div className="glass rounded-xl px-5 py-14 text-center">
          <Database className="mx-auto mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">暂无物化的数据集</p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            在「采集任务」里选择一条已完成的任务，点击「物化为数据集」
          </p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {tables.map((table, index) => {
            const datasetId = Number(String(table.name).replace(/^ds_/, ''))
            return (
              <motion.div
                key={table.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: Math.min(index * 0.05, 0.3) }}
                className={cn(
                  'glass glass-hover overflow-hidden rounded-xl',
                  previewId === datasetId && 'border-primary/45',
                )}
              >
                <button
                  type="button"
                  onClick={() => void openPreview(table.name)}
                  className="w-full p-4 text-left"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="mono-tag">{table.name}</span>
                    <Table2 className="h-4 w-4 text-primary/70" />
                  </div>
                  <div className="text-xl font-semibold tabular-nums">
                    {(Number(table.count) || 0).toLocaleString()}
                  </div>
                  <div className="mt-0.5 text-[0.7rem] text-muted-foreground">
                    行数据
                    {table.columns?.length ? ` · ${table.columns.length} 列` : ''}
                  </div>
                </button>
                <div className="flex items-center justify-between border-t border-border/50 px-4 py-2">
                  <span className="text-[0.66rem] text-muted-foreground">点击卡片预览</span>
                  <span className="flex items-center gap-3">
                    <Link
                      to={`/compare?a=${datasetId}`}
                      className="inline-flex items-center gap-0.5 text-[0.7rem] text-muted-foreground hover:text-primary"
                    >
                      对比
                    </Link>
                    <Link
                      to={`/datasets/${datasetId}`}
                      className="inline-flex items-center gap-0.5 text-[0.7rem] text-primary hover:underline"
                    >
                      详情 <ArrowUpRight className="h-3 w-3" />
                    </Link>
                  </span>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}

      {/* ---- 预览 ---- */}
      {(previewLoading || preview) && (
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass overflow-hidden rounded-xl"
        >
          <div className="flex items-center justify-between border-b border-border/60 px-5 py-3.5">
            <div className="flex items-center gap-2">
              <Table2 className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">
                数据预览
                {preview && <span className="mono-tag ml-2">ds_{preview.dataset_id}</span>}
              </h3>
            </div>
            {preview && (
              <span className="text-xs text-muted-foreground">
                共 {preview.total.toLocaleString()} 行
              </span>
            )}
          </div>

          {previewLoading ? (
            <div className="px-5 py-10 text-center">
              <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : preview && preview.rows.length > 0 ? (
            <div className="max-h-[440px] overflow-auto">
              <table className="w-full min-w-[640px] text-left text-xs">
                <thead className="sticky top-0 bg-card">
                  <tr className="text-muted-foreground">
                    {preview.columns.map((col) => (
                      <th key={col} className="whitespace-nowrap px-4 py-2 font-medium">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((row, index) => (
                    <tr key={index} className="border-t border-border/40">
                      {preview.columns.map((col) => (
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
          ) : (
            <div className="px-5 py-10 text-center text-sm text-muted-foreground">
              无可预览数据
            </div>
          )}
        </motion.section>
      )}
    </div>
  )
}
