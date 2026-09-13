/**
 * 分析报告
 * ========
 *
 * 生成 → 预览 → 导出。
 *
 * 报告里包含数据血缘与隐私处理记录——这两项让报告本身就能回答
 * "数据从哪来、隐私怎么处理的"，不必再去翻别的页面。
 */
import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import {
  Check,
  Copy,
  Download,
  FileBarChart,
  Loader2,
  Sparkles,
} from 'lucide-react'

import apiClient from '@/api/client'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface TableRow {
  name: string
  count?: number
}

interface ReportPayload {
  dataset_id: number
  analysis_type: string
  format: string
  title: string
  content: string
  sections: string[]
}

const FORMATS = [
  { value: 'markdown', label: 'Markdown' },
  { value: 'html', label: 'HTML' },
  { value: 'json', label: 'JSON' },
] as const

export default function ReportsPage() {
  const [datasets, setDatasets] = useState<TableRow[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [format, setFormat] = useState<'markdown' | 'html' | 'json'>('markdown')
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<ReportPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const { data } = await apiClient.get<{ tables: TableRow[] }>('/data/tables')
        const rows = (data.tables ?? []).filter((t) => String(t.name).startsWith('ds_'))
        setDatasets(rows)
        if (rows.length > 0) setSelected(Number(String(rows[0].name).replace(/^ds_/, '')))
      } catch {
        setDatasets([])
      }
    }
    void load()
  }, [])

  async function generate() {
    if (selected == null) return
    setLoading(true)
    setError(null)
    setCopied(false)
    try {
      const { data } = await apiClient.post<ReportPayload>('/analytics/report', {
        dataset_id: selected,
        analysis_type: 'eda',
        format,
      })
      setReport(data)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response
        ?.data?.detail
      setError(typeof detail === 'string' ? detail : '报告生成失败')
      setReport(null)
    } finally {
      setLoading(false)
    }
  }

  async function downloadExport(kind: 'csv' | 'json' | 'excel') {
    if (selected == null) return
    try {
      const response = await apiClient.get(`/analytics/export/${selected}`, {
        params: { format: kind },
        responseType: 'blob',
      })
      const url = URL.createObjectURL(response.data as Blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `dataset_${selected}.${kind === 'excel' ? 'xlsx' : kind}`
      anchor.click()
      URL.revokeObjectURL(url)
    } catch {
      setError('导出失败')
    }
  }

  async function copyContent() {
    if (!report) return
    await navigator.clipboard.writeText(report.content)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <section className="glass rounded-xl p-5">
        <div className="mb-4 flex items-center gap-2">
          <FileBarChart className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold">报告生成</h2>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <div className="section-title mb-2">选择数据集</div>
            <div className="space-y-1.5">
              {datasets.length === 0 && (
                <p className="text-xs text-muted-foreground">暂无可选数据集</p>
              )}
              {datasets.map((table) => {
                const id = Number(String(table.name).replace(/^ds_/, ''))
                return (
                  <button
                    key={table.name}
                    type="button"
                    onClick={() => setSelected(id)}
                    className={cn(
                      'flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-xs transition-colors',
                      selected === id
                        ? 'border-primary/50 bg-primary/10 text-primary'
                        : 'border-border/60 hover:border-primary/30 hover:bg-muted/50',
                    )}
                  >
                    <span className="mono-tag">{table.name}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {(Number(table.count) || 0).toLocaleString()} 行
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <div className="section-title mb-2">报告格式</div>
            <div className="flex gap-2">
              {FORMATS.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  onClick={() => setFormat(item.value)}
                  className={cn(
                    'flex-1 rounded-lg border px-3 py-2 text-xs transition-colors',
                    format === item.value
                      ? 'border-primary/50 bg-primary/10 text-primary'
                      : 'border-border/60 hover:border-primary/30 hover:bg-muted/50',
                  )}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="section-title mb-2 mt-4">导出原始数据</div>
            <div className="flex gap-2">
              {(['csv', 'json', 'excel'] as const).map((kind) => (
                <Button
                  key={kind}
                  variant="outline"
                  size="sm"
                  onClick={() => void downloadExport(kind)}
                  disabled={selected == null}
                >
                  <Download className="mr-1.5 h-3.5 w-3.5" />
                  {kind.toUpperCase()}
                </Button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-3 border-t border-border/60 pt-4">
          <Button onClick={() => void generate()} disabled={loading || selected == null}>
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="mr-2 h-4 w-4" />
            )}
            生成报告
          </Button>
          {error && <span className="text-xs text-destructive">{error}</span>}
        </div>
      </section>

      {report && (
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass overflow-hidden rounded-xl"
        >
          <div className="flex items-center justify-between gap-3 border-b border-border/60 px-5 py-3.5">
            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold">{report.title}</h3>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {report.sections.map((section) => (
                  <span key={section} className="mono-tag">
                    {section}
                  </span>
                ))}
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => void copyContent()}>
              {copied ? (
                <Check className="mr-1.5 h-3.5 w-3.5 text-emerald-500" />
              ) : (
                <Copy className="mr-1.5 h-3.5 w-3.5" />
              )}
              {copied ? '已复制' : '复制'}
            </Button>
          </div>

          <div className="max-h-[620px] overflow-auto p-5">
            {report.format === 'html' ? (
              <iframe
                title="分析报告"
                srcDoc={report.content}
                className="h-[560px] w-full rounded-lg border border-border/60 bg-white"
                sandbox=""
              />
            ) : (
              <pre className="whitespace-pre-wrap break-words font-mono text-[0.76rem] leading-relaxed text-muted-foreground">
                {report.content}
              </pre>
            )}
          </div>
        </motion.section>
      )}
    </div>
  )
}
