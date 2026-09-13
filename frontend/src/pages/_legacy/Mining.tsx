import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Pickaxe, Play, Loader2, AlertTriangle, Link2, Minimize2 } from 'lucide-react'
import { miningApi } from '@/api/mining'
import { useAppStore } from '@/stores/appStore'

export default function MiningPage() {
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [task, setTask] = useState<'association' | 'anomaly' | 'reduction'>('anomaly')
  const [inputData, setInputData] = useState('')
  const [result, setResult] = useState<any>(null)

  const runMining = async () => {
    try {
      setLoading(true)
      const data = JSON.parse(inputData)
      let res: any
      switch (task) {
        case 'association':
          res = await miningApi.associationRules({ data, min_support: 0.05, min_confidence: 0.5 })
          break
        case 'anomaly':
          res = await miningApi.anomalyDetection({ data, method: 'isolation_forest', contamination: 0.05 })
          break
        case 'reduction':
          res = await miningApi.dimensionalityReduction({ data, method: 'pca', n_components: 2 })
          break
      }
      setResult(res.data)
      addNotification({ type: 'success', title: '挖掘完成' })
    } catch (e: any) {
      addNotification({ type: 'error', title: '挖掘失败', description: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">数据挖掘</h2>
        <p className="text-muted-foreground">关联规则 · 异常检测 · 降维可视化</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Pickaxe className="h-5 w-5" /> 挖掘配置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-1.5 block">挖掘方法</label>
              <Select value={task} onValueChange={(v: any) => setTask(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="anomaly">异常检测 (Isolation Forest)</SelectItem>
                  <SelectItem value="association">关联规则 (Apriori)</SelectItem>
                  <SelectItem value="reduction">降维可视化 (PCA/t-SNE/UMAP)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">数据 (JSON)</label>
              <Textarea
                placeholder='[{"value": 1.2, "feature": 3.4}, ...]'
                value={inputData}
                onChange={(e) => setInputData(e.target.value)}
                className="min-h-[200px] font-mono text-xs"
              />
            </div>
            <Button onClick={runMining} disabled={loading} className="w-full">
              {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
              运行挖掘
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>挖掘结果</CardTitle>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="space-y-3">
                {/* 异常检测 */}
                {result.anomaly_count !== undefined && (
                  <div className="space-y-3">
                    <div className="p-4 rounded-lg bg-red-500/5 border border-red-200">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-5 w-5 text-red-500" />
                        <span className="font-semibold">异常检测</span>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="text-center p-2 rounded bg-muted/50">
                          <p className="text-xl font-bold">{result.anomaly_count}</p>
                          <p className="text-xs text-muted-foreground">异常样本</p>
                        </div>
                        <div className="text-center p-2 rounded bg-muted/50">
                          <p className="text-xl font-bold">{result.total_samples}</p>
                          <p className="text-xs text-muted-foreground">总样本</p>
                        </div>
                        <div className="text-center p-2 rounded bg-muted/50">
                          <p className="text-xl font-bold">{result.anomaly_pct}%</p>
                          <p className="text-xs text-muted-foreground">异常率</p>
                        </div>
                      </div>
                    </div>
                    {result.comparison && (
                      <div>
                        <h4 className="text-sm font-semibold mb-2">异常 vs 正常对比</h4>
                        <div className="space-y-1.5">
                          {Object.entries(result.comparison).slice(0, 5).map(([col, info]: [string, any]) => (
                            <div key={col} className="flex items-center justify-between text-sm p-2 rounded bg-muted/30">
                              <span>{col}</span>
                              <Badge variant="outline" className="text-xs">差 {info.diff_pct}%</Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 关联规则 */}
                {result.rules && (
                  <div>
                    <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <Link2 className="h-4 w-4" /> 关联规则 ({result.rules.length} 条)
                    </h4>
                    <div className="space-y-1.5 max-h-64 overflow-auto">
                      {result.rules.slice(0, 10).map((rule: any, i: number) => (
                        <div key={i} className="p-2 rounded bg-muted/30 text-sm">
                          <span className="font-mono">{rule.antecedents.join(',')}</span>
                          <span className="mx-2 text-primary">→</span>
                          <span className="font-mono">{rule.consequents.join(',')}</span>
                          <div className="flex gap-2 mt-1">
                            <Badge variant="outline" className="text-[10px]">支持 {rule.support}</Badge>
                            <Badge variant="outline" className="text-[10px]">置信 {rule.confidence}</Badge>
                            <Badge variant="outline" className="text-[10px]">提升 {rule.lift}</Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 降维 */}
                {result.points && (
                  <div className="p-4 rounded-lg bg-muted/50">
                    <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <Minimize2 className="h-4 w-4" /> {result.method} 降维
                    </h4>
                    <p className="text-sm">样本数: {result.sample_size}</p>
                    {result.explained_variance && (
                      <p className="text-sm">解释方差: {result.total_variance_explained}</p>
                    )}
                  </div>
                )}

                <pre className="p-3 rounded-lg bg-muted/50 text-xs font-mono overflow-auto max-h-48">
                  {JSON.stringify(result, null, 2).slice(0, 2000)}
                </pre>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Pickaxe className="h-10 w-10 mb-2 opacity-30" />
                <p className="text-sm">选择方法并输入数据</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
