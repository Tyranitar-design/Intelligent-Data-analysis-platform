import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  BarChart3, Upload, Loader2, AlertCircle, CheckCircle, TrendingUp,
  FileSpreadsheet, Sparkles, ArrowRight,
} from 'lucide-react'
import { edaApi, featureApi } from '@/api/analysis'
import { dataBrowserApi } from '@/api/data'
import { extractApiError } from '@/api/crawl'
import { useAnalysisStore } from '@/stores/analysisStore'
import { useAppStore } from '@/stores/appStore'

export default function AnalysisPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const {
    edaResults,
    setEdaResult,
    currentDataset,
    setCurrentDataset,
    latestEdaSourceTable,
    setLatestEdaSourceTable,
  } = useAnalysisStore()
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [dataType, setDataType] = useState('csv')
  const [rawData, setRawData] = useState('')
  const [datasets, setDatasets] = useState<any[]>([])
  const [selectedTable, setSelectedTable] = useState(searchParams.get('table') || '')
  const [selectedTableColumns, setSelectedTableColumns] = useState<string[]>([])
  const [selectedTableRowCount, setSelectedTableRowCount] = useState(0)
  const [featureTask, setFeatureTask] = useState<'classification' | 'regression'>('classification')
  const [featureResult, setFeatureResult] = useState<any>(null)

  useEffect(() => {
    loadDatasets()
  }, [])

  useEffect(() => {
    const table = searchParams.get('table')
    if (table) {
      setSelectedTable(table)
      loadTableData(table)
    }
  }, [searchParams])

  const loadDatasets = async () => {
    try {
      const res = await edaApi.listDatasets()
      setDatasets(res.data || [])
    } catch (e: any) {
      addNotification({ type: 'error', title: '加载数据集失败', description: extractApiError(e) })
    }
  }

  const loadTableData = async (tableName: string) => {
    try {
      setLoading(true)
      const res = await dataBrowserApi.queryTable(tableName, { page: 1, size: 500 })
      const rows = res.data?.data || []
      const columns = res.data?.columns || []
      setCurrentDataset({
        tableName,
        rows,
        columns,
        total: res.data?.total || rows.length,
      })
      setSelectedTableColumns(columns)
      setSelectedTableRowCount(res.data?.total || rows.length)
      setRawData(JSON.stringify(rows, null, 2))
    } catch (e: any) {
      addNotification({ type: 'error', title: '加载真实数据失败', description: extractApiError(e) })
    } finally {
      setLoading(false)
    }
  }

  const runEDA = async () => {
    if (!rawData.trim()) {
      addNotification({ type: 'warning', title: '请输入数据' })
      return
    }
    try {
      setLoading(true)
      const parsed = JSON.parse(rawData)
      const res = await edaApi.analyze({
        data: parsed,
        dataset_name: selectedTable || currentDataset?.tableName || 'analysis',
      })
      setEdaResult('latest', res.data)
      setLatestEdaSourceTable(selectedTable || currentDataset?.tableName || null)
      addNotification({
        type: 'success',
        title: 'EDA 分析完成',
        description: selectedTable ? `已基于真实数据表 ${selectedTable} 生成分析结果` : undefined,
      })
    } catch (e: any) {
      addNotification({ type: 'error', title: '分析失败', description: extractApiError(e) })
    } finally {
      setLoading(false)
    }
  }

  const runFeature = async () => {
    if (!rawData.trim()) return
    try {
      setLoading(true)
      const parsed = JSON.parse(rawData)
      const res = await featureApi.engineer({ data: parsed, target_column: 'target', task_type: featureTask })
      setFeatureResult(res.data)
      addNotification({ type: 'success', title: '特征工程完成' })
    } catch (e: any) {
      addNotification({ type: 'error', title: '特征工程失败', description: extractApiError(e) })
    } finally {
      setLoading(false)
    }
  }

  const latestEDA = edaResults.get('latest')
  const selectedDatasetMeta = useMemo(
    () => datasets.find((dataset: any) => dataset.table_name === selectedTable),
    [datasets, selectedTable],
  )

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">数据分析</h2>
        <p className="text-muted-foreground">真实数据集驱动的 EDA · 特征工程 · 数据质量评估</p>
      </div>

      <Tabs defaultValue="eda">
        <TabsList>
          <TabsTrigger value="eda">EDA 分析</TabsTrigger>
          <TabsTrigger value="feature">特征工程</TabsTrigger>
        </TabsList>

        {/* EDA 分析 */}
        <TabsContent value="eda" className="space-y-4">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* 数据输入 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="h-5 w-5" /> 数据输入
                </CardTitle>
                <CardDescription>优先选择真实数据集，也支持手动输入 JSON</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium mb-1.5 block">真实数据集</label>
                  <div className="flex gap-2">
                    <Select value={selectedTable} onValueChange={(value) => { setSelectedTable(value); loadTableData(value) }}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择已保存的数据表" />
                      </SelectTrigger>
                      <SelectContent>
                        {datasets.map((dataset: any) => (
                          <SelectItem key={dataset.id} value={dataset.table_name}>
                            {dataset.name} ({dataset.table_name})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button variant="outline" onClick={loadDatasets} disabled={loading}>
                      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : '刷新'}
                    </Button>
                  </div>
                  {selectedDatasetMeta && (
                    <p className="text-xs text-muted-foreground mt-2">
                      当前数据集：{selectedDatasetMeta.name} · {selectedTableRowCount || selectedDatasetMeta.row_count || 0} 行 · {selectedTableColumns.length || selectedDatasetMeta.column_count || 0} 列
                    </p>
                  )}
                </div>
                <div>
                  <label className="text-sm font-medium mb-1.5 block">数据格式</label>
                  <Select value={dataType} onValueChange={setDataType}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="csv">CSV</SelectItem>
                      <SelectItem value="json">JSON</SelectItem>
                      <SelectItem value="excel">Excel</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Textarea
                  placeholder='[{"price": 100, "category": "A"}, {"price": 200, "category": "B"}]'
                  value={rawData}
                  onChange={(e) => setRawData(e.target.value)}
                  className="min-h-[200px] font-mono text-xs"
                />
                {currentDataset?.rows?.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    当前文本框已同步所选真实数据表的前 {currentDataset.rows.length} 条记录，可直接运行 EDA。
                  </p>
                )}
                <Button onClick={runEDA} disabled={loading} className="w-full">
                  {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <BarChart3 className="h-4 w-4 mr-2" />}
                  运行 EDA 分析
                </Button>
              </CardContent>
            </Card>

            {/* EDA 结果 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5" /> 分析结果
                </CardTitle>
              </CardHeader>
              <CardContent>
                {latestEDA ? (
                  <div className="space-y-4">
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!latestEdaSourceTable}
                        onClick={() => latestEdaSourceTable && navigate(`/visualization?table=${encodeURIComponent(latestEdaSourceTable)}`)}
                      >
                        <BarChart3 className="h-4 w-4 mr-2" />
                        去可视化
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!latestEdaSourceTable}
                        onClick={() => latestEdaSourceTable && navigate(`/reports?sourceTable=${encodeURIComponent(latestEdaSourceTable)}`)}
                      >
                        <FileSpreadsheet className="h-4 w-4 mr-2" />
                        去报告中心
                      </Button>
                    </div>

                    {/* 数据概览 */}
                    <div>
                      <h4 className="font-semibold mb-2 text-sm text-muted-foreground">数据概览</h4>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="p-2 rounded bg-muted/50 text-sm">
                          行数: <span className="font-bold">{latestEDA.overview?.row_count || 'N/A'}</span>
                        </div>
                        <div className="p-2 rounded bg-muted/50 text-sm">
                          列数: <span className="font-bold">{latestEDA.overview?.column_count || 'N/A'}</span>
                        </div>
                      </div>
                    </div>

                    {/* 质量评分 */}
                    {latestEDA.data_quality && (
                      <div>
                        <h4 className="font-semibold mb-2 text-sm text-muted-foreground">数据质量</h4>
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                          <div className={`text-3xl font-bold ${
                            latestEDA.data_quality.grade === 'A' ? 'text-green-500' :
                            latestEDA.data_quality.grade === 'B' ? 'text-blue-500' :
                            latestEDA.data_quality.grade === 'C' ? 'text-yellow-500' : 'text-red-500'
                          }`}>
                            {latestEDA.data_quality.grade}
                          </div>
                          <div>
                            <p className="font-medium">{latestEDA.data_quality.overall_score}/100</p>
                            <p className="text-xs text-muted-foreground">{latestEDA.data_quality.grade_description}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 缺失值 */}
                    {latestEDA.missing_values?.columns_detail?.length > 0 && (
                      <div>
                        <h4 className="font-semibold mb-2 text-sm text-muted-foreground">缺失值</h4>
                        <div className="space-y-1.5">
                          {latestEDA.missing_values.columns_detail.slice(0, 5).map((col: any) => (
                            <div key={col.column} className="flex items-center justify-between text-sm p-2 rounded bg-muted/30">
                              <span>{col.column}</span>
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-xs">{col.missing_pct}%</Badge>
                                <span className="text-xs text-muted-foreground">{col.suggestion?.action}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 建议 */}
                    {latestEDA.suggestions?.length > 0 && (
                      <div>
                        <h4 className="font-semibold mb-2 text-sm text-muted-foreground">分析建议</h4>
                        <div className="space-y-1.5">
                          {latestEDA.suggestions.slice(0, 5).map((s: any, i: number) => (
                            <div key={i} className="flex items-start gap-2 text-sm p-2 rounded bg-muted/30">
                              <span className={`shrink-0 ${
                                s.priority === 'high' ? 'text-red-500' :
                                s.priority === 'medium' ? 'text-yellow-500' : 'text-green-500'
                              }`}>●</span>
                              <span>{s.title || s.description || s.action}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <BarChart3 className="h-10 w-10 mb-2 opacity-30" />
                    <p className="text-sm">输入数据后运行 EDA 分析</p>
                    <p className="text-xs mt-2">也可以先从真实数据集选择一个数据表再分析</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 特征工程 */}
        <TabsContent value="feature" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>特征工程 Pipeline</CardTitle>
              <CardDescription>缺失值处理 → 编码 → 缩放 → 特征选择</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <Select value={featureTask} onValueChange={(v: any) => setFeatureTask(v)}>
                  <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="classification">分类任务</SelectItem>
                    <SelectItem value="regression">回归任务</SelectItem>
                  </SelectContent>
                </Select>
                <Button onClick={runFeature} disabled={loading}>
                  {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <TrendingUp className="h-4 w-4 mr-2" />}
                  运行特征工程
                </Button>
              </div>
              {featureResult && (
                <div className="p-4 rounded-lg bg-muted/50 space-y-2">
                  <p className="text-sm font-medium">原始维度: {featureResult.original_shape?.join('×')}</p>
                  <p className="text-sm font-medium">处理后维度: {featureResult.final_shape?.join('×')}</p>
                  <p className="text-sm text-muted-foreground">处理步骤: {featureResult.steps?.length || 0}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
