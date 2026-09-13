import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { LineChart, Play, Loader2 } from 'lucide-react'
import Plot from 'react-plotly.js'
import { dataBrowserApi } from '@/api/data'
import { extractApiError } from '@/api/crawl'
import { useAppStore } from '@/stores/appStore'

const CHART_TYPES = [
  { value: 'bar', label: '柱状图' },
  { value: 'line', label: '折线图' },
  { value: 'scatter', label: '散点图' },
  { value: 'pie', label: '饼图' },
  { value: 'histogram', label: '直方图' },
  { value: 'box', label: '箱线图' },
  { value: 'heatmap', label: '热力图' },
  { value: 'violin', label: '小提琴图' },
  { value: 'area', label: '面积图' },
  { value: 'treemap', label: '树图' },
]

export default function VisualizationPage() {
  const [searchParams] = useSearchParams()
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [chartType, setChartType] = useState('bar')
  const [tableName, setTableName] = useState(searchParams.get('table') || '')
  const [tableRows, setTableRows] = useState<any[]>([])
  const [columns, setColumns] = useState<string[]>([])
  const [xField, setXField] = useState('')
  const [yField, setYField] = useState('')
  const [result, setResult] = useState<any>(null)

  useEffect(() => {
    const table = searchParams.get('table')
    if (table) {
      setTableName(table)
      loadTableData(table)
    }
  }, [searchParams])

  const loadTableData = async (name: string) => {
    try {
      setLoading(true)
      const res = await dataBrowserApi.queryTable(name, { page: 1, size: 200 })
      const rows = res.data?.data || []
      const cols = res.data?.columns || []
      setTableRows(rows)
      setColumns(cols)
      if (cols.length > 0) {
        setXField((prev) => prev || cols[0])
      }
      if (cols.length > 1) {
        setYField((prev) => prev || cols[1])
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: '加载失败', description: extractApiError(e) })
    } finally {
      setLoading(false)
    }
  }

  const numericColumns = useMemo(() => {
    return columns.filter((col) =>
      tableRows.some((row) => {
        const value = row?.[col]
        return value !== null && value !== undefined && value !== '' && !Number.isNaN(Number(value))
      })
    )
  }, [columns, tableRows])

  const categoricalColumns = useMemo(() => columns.filter((col) => !numericColumns.includes(col)), [columns, numericColumns])

  const generate = async () => {
    if (!tableRows.length || !xField) {
      addNotification({ type: 'error', title: '生成失败', description: '请先加载真实数据并选择字段' })
      return
    }
    if (!yField && ['bar', 'line', 'scatter', 'area', 'pie'].includes(chartType)) {
      addNotification({ type: 'error', title: '生成失败', description: '当前图表类型需要选择一个数值型 Y 轴字段' })
      return
    }
    try {
      setLoading(true)
      const rows = tableRows.slice(0, 100)
      const xValues = rows.map((row) => row?.[xField])
      const yValues = yField ? rows.map((row) => Number(row?.[yField] ?? 0)) : []

      let data: any[] = []

      if (chartType === 'bar') {
        data = [{ type: 'bar', x: xValues, y: yValues }]
      } else if (chartType === 'line') {
        data = [{ type: 'scatter', mode: 'lines+markers', x: xValues, y: yValues }]
      } else if (chartType === 'scatter') {
        data = [{ type: 'scatter', mode: 'markers', x: xValues, y: yValues }]
      } else if (chartType === 'pie') {
        data = [{ type: 'pie', labels: xValues, values: yValues }]
      } else if (chartType === 'area') {
        data = [{ type: 'scatter', mode: 'lines', fill: 'tozeroy', x: xValues, y: yValues }]
      } else {
        data = [{ type: 'bar', x: xValues, y: yValues }]
      }

      setResult({
        data,
        layout: {
          title: `${tableName || '数据集'} · ${chartType}`,
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { color: '#cbd5e1' },
          margin: { l: 50, r: 20, t: 60, b: 60 },
        },
      })
      addNotification({
        type: 'success',
        title: '图表生成完成',
        description: rows.length < tableRows.length
          ? `已基于前 ${rows.length} 条记录生成图表预览`
          : '已基于当前真实数据生成图表',
      })
    } catch (e: any) {
      addNotification({ type: 'error', title: '生成失败', description: extractApiError(e) })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">可视化</h2>
        <p className="text-muted-foreground">真实数据集联动 · Plotly 渲染 · 图表快速生成</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LineChart className="h-5 w-5" /> 图表配置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-1.5 block">数据表</label>
              <div className="flex gap-2">
                <Input
                  placeholder="输入数据表名或从数据集页跳转"
                  value={tableName}
                  onChange={(e) => setTableName(e.target.value)}
                />
                <Button variant="outline" onClick={() => tableName.trim() && loadTableData(tableName.trim())} disabled={loading}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : '加载'}
                </Button>
              </div>
              {tableRows.length > 0 && (
                <p className="text-xs text-muted-foreground mt-2">
                  已加载 {tableRows.length} 条记录用于当前图表预览。
                </p>
              )}
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">图表类型</label>
              <Select value={chartType} onValueChange={setChartType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CHART_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {CHART_TYPES.map((t) => (
                <Badge
                  key={t.value}
                  variant={chartType === t.value ? 'default' : 'outline'}
                  className="cursor-pointer text-xs"
                  onClick={() => setChartType(t.value)}
                >
                  {t.label}
                </Badge>
              ))}
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">X 轴字段</label>
              <Select value={xField} onValueChange={setXField}>
                <SelectTrigger><SelectValue placeholder="选择 X 轴字段" /></SelectTrigger>
                <SelectContent>
                  {columns.map((col) => (
                    <SelectItem key={col} value={col}>{col}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Y 轴字段</label>
              <Select value={yField} onValueChange={setYField}>
                <SelectTrigger><SelectValue placeholder="选择 Y 轴字段" /></SelectTrigger>
                <SelectContent>
                  {numericColumns.map((col) => (
                    <SelectItem key={col} value={col}>{col}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {columns.map((col) => (
                <Badge key={col} variant={numericColumns.includes(col) ? 'default' : 'outline'} className="text-xs">
                  {col}
                </Badge>
              ))}
            </div>
            {columns.length > 0 && numericColumns.length === 0 && (
              <p className="text-xs text-amber-600">
                当前数据表缺少明显数值字段，建议先回到数据浏览页检查字段结构，或选择更适合分类展示的数据。
              </p>
            )}
            <Button onClick={generate} disabled={loading} className="w-full">
              {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
              生成图表
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>图表预览</CardTitle>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="space-y-3">
                <Plot
                  data={result.data}
                  layout={result.layout}
                  style={{ width: '100%', height: '420px' }}
                  config={{ responsive: true, displaylogo: false }}
                />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                <LineChart className="h-12 w-12 mb-2 opacity-30" />
                <p className="text-sm">从数据集页跳转，或先加载真实数据表</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
