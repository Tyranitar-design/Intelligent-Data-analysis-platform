/**
 * 数据分析
 * ========
 *
 * 选数据集 → 选分析类型 → 出结果与图表。
 *
 * 图表直接用后端返回的 ECharts option 渲染——后端已经是可视化配置的生产者，
 * 前端不再做二次转换，避免两套图表逻辑各自演化。
 */
import { useEffect, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { Activity, Loader2, Play } from 'lucide-react'

import apiClient from '@/api/client'
import echarts, { CHART_MOTION, CHART_THEME, type EChartsOption } from '@/lib/echarts'
import { Button } from '@/components/ui/button'
import { SkeletonChart } from '@/components/visual/Skeleton'
import { cn } from '@/lib/utils'

interface TableRow {
  name: string
  count?: number
}

interface ChartSpec {
  id: string
  type: string
  title: string
  option: Record<string, unknown>
}

interface AnalysisPayload {
  dataset_id: number
  analysis_type: string
  result: Record<string, unknown>
  charts: ChartSpec[]
  summary: string
}

const ANALYSIS_TYPES = [
  { value: 'eda', label: '探索性分析', desc: '概况 · 质量 · 相关性 · 异常' },
  { value: 'stats', label: '描述统计', desc: '数值与分类字段的分布指标' },
  { value: 'correlation', label: '相关性', desc: '字段相关矩阵与显著相关对' },
  { value: 'outliers', label: '异常检测', desc: 'IQR 法识别可疑值' },
  { value: 'missing', label: '缺失分析', desc: '各字段缺失率' },
]

export default function AnalyticsPage() {
  const [datasets, setDatasets] = useState<TableRow[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [analysisType, setAnalysisType] = useState('eda')
  const [loading, setLoading] = useState(false)
  const [payload, setPayload] = useState<AnalysisPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const { data } = await apiClient.get<{ tables: TableRow[] }>('/data/tables')
        const rows = (data.tables ?? [])
          .filter((t) => String(t.name).startsWith('ds_'))
          .map((t) => ({ ...t, name: String(t.name) }))
        setDatasets(rows)
        if (rows.length > 0) {
          setSelected(Number(rows[0].name.replace(/^ds_/, '')))
        }
      } catch {
        setDatasets([])
      }
    }
    void load()
  }, [])

  async function run() {
    if (selected == null) return
    setLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.post<AnalysisPayload>('/analytics/run', {
        dataset_id: selected,
        analysis_type: analysisType,
      })
      setPayload(data)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response
        ?.data?.detail
      setError(typeof detail === 'string' ? detail : '分析失败')
      setPayload(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <section className="glass rounded-xl p-5">
        <div className="mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold">分析配置</h2>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
          <div>
            <div className="section-title mb-2">数据集</div>
            <div className="space-y-1.5">
              {datasets.length === 0 && (
                <p className="text-xs text-muted-foreground">暂无可用数据集</p>
              )}
              {datasets.map((table) => {
                const id = Number(table.name.replace(/^ds_/, ''))
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
            <div className="section-title mb-2">分析类型</div>
            <div className="grid gap-2 sm:grid-cols-2">
              {ANALYSIS_TYPES.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setAnalysisType(type.value)}
                  className={cn(
                    'rounded-lg border px-3 py-2 text-left transition-colors',
                    analysisType === type.value
                      ? 'border-primary/50 bg-primary/10'
                      : 'border-border/60 hover:border-primary/30 hover:bg-muted/50',
                  )}
                >
                  <div
                    className={cn(
                      'text-[0.8rem] font-medium',
                      analysisType === type.value && 'text-primary',
                    )}
                  >
                    {type.label}
                  </div>
                  <div className="mt-0.5 text-[0.68rem] text-muted-foreground">
                    {type.desc}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-3 border-t border-border/60 pt-4">
          <Button onClick={() => void run()} disabled={loading || selected == null}>
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            执行分析
          </Button>
          {payload && (
            <span className="text-xs text-muted-foreground">{payload.summary}</span>
          )}
          {error && <span className="text-xs text-destructive">{error}</span>}
        </div>
      </section>

      {loading && (
        <section className="grid gap-4 lg:grid-cols-2">
          <SkeletonChart />
          <SkeletonChart />
        </section>
      )}

      {payload && (
        <>
          {payload.charts?.length > 0 && (
            <section className="grid gap-4 lg:grid-cols-2">
              {payload.charts.map((chart, index) => (
                <motion.div
                  key={chart.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: index * 0.06 }}
                  className="glass overflow-hidden rounded-xl"
                >
                  <div className="border-b border-border/60 px-5 py-3">
                    <h3 className="text-sm font-semibold">{chart.title}</h3>
                  </div>
                  <div className="p-3">
                    <EChart option={chart.option} height={260} />
                  </div>
                </motion.div>
              ))}
            </section>
          )}

          <ResultTables payload={payload} />
        </>
      )}
    </div>
  )
}

// --------------------------------------------------------------------------- //

function EChart({
  option,
  height = 260,
}: {
  option: Record<string, unknown>
  height?: number
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    chartRef.current = echarts.init(containerRef.current, undefined, {
      renderer: 'canvas',
    })
    const handleResize = () => chartRef.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      chartRef.current?.dispose()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!chartRef.current) return
    chartRef.current.setOption(
      {
        ...CHART_THEME,
        ...CHART_MOTION,
        grid: { left: 44, right: 18, top: 28, bottom: 32 },
        ...option,
      } as EChartsOption,
      true,
    )
  }, [option])

  return <div ref={containerRef} style={{ height }} />
}

function ResultTables({ payload }: { payload: AnalysisPayload }) {
  const result = payload.result ?? {}
  const numeric = (result.numeric as Record<string, Record<string, number>>) ?? {}
  const strongPairs =
    (result.strong_pairs as { left: string; right: string; r: number; strength: string }[]) ??
    []
  const outliers = (result.fields as Record<string, Record<string, unknown>>) ?? {}

  const numericRows = Object.entries(numeric)
  const outlierRows =
    payload.analysis_type === 'outliers' ? Object.entries(outliers) : []

  if (numericRows.length === 0 && strongPairs.length === 0 && outlierRows.length === 0) {
    return null
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {numericRows.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass overflow-hidden rounded-xl"
        >
          <div className="border-b border-border/60 px-5 py-3">
            <h3 className="text-sm font-semibold">数值字段统计</h3>
          </div>
          <div className="max-h-[380px] overflow-auto">
            <table className="w-full min-w-[520px] text-left text-xs">
              <thead className="sticky top-0 bg-card/95 backdrop-blur">
                <tr className="text-muted-foreground">
                  <th className="px-4 py-2 font-medium">字段</th>
                  <th className="px-3 py-2 font-medium">均值</th>
                  <th className="px-3 py-2 font-medium">中位数</th>
                  <th className="px-3 py-2 font-medium">最小</th>
                  <th className="px-4 py-2 font-medium">最大</th>
                </tr>
              </thead>
              <tbody>
                {numericRows.map(([name, values]) => (
                  <tr key={name} className="border-t border-border/40">
                    <td className="px-4 py-2 font-medium">{name}</td>
                    <td className="px-3 py-2 tabular-nums text-muted-foreground">
                      {fmtNum(values.mean)}
                    </td>
                    <td className="px-3 py-2 tabular-nums text-muted-foreground">
                      {fmtNum(values.median)}
                    </td>
                    <td className="px-3 py-2 tabular-nums text-muted-foreground">
                      {fmtNum(values.min)}
                    </td>
                    <td className="px-4 py-2 tabular-nums text-muted-foreground">
                      {fmtNum(values.max)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.section>
      )}

      {strongPairs.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass overflow-hidden rounded-xl"
        >
          <div className="border-b border-border/60 px-5 py-3">
            <h3 className="text-sm font-semibold">显著相关字段对</h3>
          </div>
          <ul className="divide-y divide-border/40">
            {strongPairs.map((pair) => (
              <li
                key={`${pair.left}-${pair.right}`}
                className="flex items-center justify-between gap-3 px-5 py-2.5 text-xs"
              >
                <span>
                  <span className="mono-tag">{pair.left}</span>
                  <span className="mx-2 text-muted-foreground">↔</span>
                  <span className="mono-tag">{pair.right}</span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="tabular-nums text-muted-foreground">{pair.r}</span>
                  <span className="badge-dot badge-info">{pair.strength}</span>
                </span>
              </li>
            ))}
          </ul>
        </motion.section>
      )}

      {outlierRows.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass overflow-hidden rounded-xl"
        >
          <div className="border-b border-border/60 px-5 py-3">
            <h3 className="text-sm font-semibold">异常值分布（IQR 1.5 倍）</h3>
          </div>
          <ul className="divide-y divide-border/40">
            {outlierRows.map(([name, values]) => (
              <li
                key={name}
                className="flex items-center justify-between gap-3 px-5 py-2.5 text-xs"
              >
                <span className="font-medium">{name}</span>
                <span className="flex items-center gap-3 text-muted-foreground">
                  <span className="tabular-nums">{String(values.count)} 个</span>
                  <span className="tabular-nums">
                    {Math.round(Number(values.ratio ?? 0) * 100)}%
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </motion.section>
      )}
    </div>
  )
}

function fmtNum(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  if (Math.abs(value) >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  return String(Math.round(value * 100) / 100)
}
