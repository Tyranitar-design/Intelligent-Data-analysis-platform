/**
 * 数据集
 * ======
 *
 * 采集结果物化后的结构化资产。
 * 列表回答"有哪些数据、多大、什么时候来的"，预览回答"里面长什么样"。
 */
import { useCallback, useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { Database, Loader2, RefreshCw, Table2 } from 'lucide-react'

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
          {tables.map((table, index) => (
            <motion.button
              key={table.name}
              type="button"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: Math.min(index * 0.05, 0.3) }}
              onClick={() => void openPreview(table.name)}
              className={cn(
                'glass glass-hover rounded-xl p-4 text-left',
                previewId === Number(String(table.name).replace(/^ds_/, '')) &&
                  'border-primary/45',
              )}
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
            </motion.button>
          ))}
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
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-card/95 backdrop-blur">
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
