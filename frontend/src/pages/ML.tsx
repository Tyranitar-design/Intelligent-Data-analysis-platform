import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import {
  Brain, Play, Loader2, TrendingUp, Target, BarChart3,
  Trash2, Eye, Zap,
} from 'lucide-react'
import { mlApi, type MLModel } from '@/api/ml'
import { useAnalysisStore } from '@/stores/analysisStore'
import { useAppStore } from '@/stores/appStore'

const ALGORITHMS = {
  classification: [
    { value: 'logistic_regression', label: '逻辑回归' },
    { value: 'decision_tree', label: '决策树' },
    { value: 'random_forest', label: '随机森林' },
    { value: 'gradient_boosting', label: '梯度提升' },
    { value: 'svm', label: 'SVM' },
  ],
  regression: [
    { value: 'linear_regression', label: '线性回归' },
    { value: 'ridge', label: 'Ridge' },
    { value: 'lasso', label: 'Lasso' },
    { value: 'random_forest_reg', label: '随机森林' },
    { value: 'gradient_boosting_reg', label: '梯度提升' },
    { value: 'svr', label: 'SVR' },
  ],
  clustering: [
    { value: 'kmeans', label: 'K-Means' },
    { value: 'dbscan', label: 'DBSCAN' },
  ],
}

export default function MLPage() {
  const { mlModels, setMlModels, addMlModel, removeMlModel } = useAnalysisStore()
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [taskType, setTaskType] = useState<'classification' | 'regression' | 'clustering'>('classification')
  const [algorithm, setAlgorithm] = useState('random_forest')
  const [targetColumn, setTargetColumn] = useState('target')
  const [trainData, setTrainData] = useState('')
  const [tuningMethod, setTuningMethod] = useState<'none' | 'grid' | 'random' | 'optuna'>('none')
  const [trainResult, setTrainResult] = useState<any>(null)
  const [modelsLoading, setModelsLoading] = useState(false)

  useEffect(() => {
    fetchModels()
  }, [])

  const fetchModels = async () => {
    try {
      setModelsLoading(true)
      const res = await mlApi.listModels()
      setMlModels(res.data?.models || res.data || [])
    } catch (e) {
      console.error(e)
    } finally {
      setModelsLoading(false)
    }
  }

  const train = async () => {
    if (!trainData.trim()) {
      addNotification({ type: 'warning', title: '请输入训练数据' })
      return
    }
    try {
      setLoading(true)
      const data = JSON.parse(trainData)
      const res = await mlApi.train({
        data,
        target_column: targetColumn,
        algorithm,
        task_type: taskType,
        tuning: tuningMethod !== 'none' ? { method: tuningMethod, n_trials: 20 } : undefined,
        cv_folds: 5,
      })
      setTrainResult(res.data)
      addMlModel(res.data)
      addNotification({ type: 'success', title: '训练完成', description: `模型 ID: ${res.data.model_id}` })
    } catch (e: any) {
      addNotification({ type: 'error', title: '训练失败', description: e.message })
    } finally {
      setLoading(false)
    }
  }

  const deleteModel = async (id: number) => {
    try {
      await mlApi.deleteModel(id)
      removeMlModel(id)
      addNotification({ type: 'info', title: '模型已删除' })
    } catch (e: any) {
      addNotification({ type: 'error', title: '删除失败' })
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">模型训练</h2>
        <p className="text-muted-foreground">13 种算法 · Optuna 调优 · 交叉验证 · SHAP 解释</p>
      </div>

      <Tabs defaultValue="train">
        <TabsList>
          <TabsTrigger value="train">训练模型</TabsTrigger>
          <TabsTrigger value="models">模型列表</TabsTrigger>
        </TabsList>

        {/* 训练 */}
        <TabsContent value="train" className="space-y-4">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5" /> 训练配置
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium mb-1.5 block">任务类型</label>
                    <Select value={taskType} onValueChange={(v: any) => setTaskType(v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="classification">分类</SelectItem>
                        <SelectItem value="regression">回归</SelectItem>
                        <SelectItem value="clustering">聚类</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-1.5 block">算法</label>
                    <Select value={algorithm} onValueChange={setAlgorithm}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {(ALGORITHMS[taskType] || []).map((a) => (
                          <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium mb-1.5 block">目标列</label>
                    <Input value={targetColumn} onChange={(e) => setTargetColumn(e.target.value)} />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-1.5 block">调优方式</label>
                    <Select value={tuningMethod} onValueChange={(v: any) => setTuningMethod(v)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">不调优</SelectItem>
                        <SelectItem value="grid">Grid Search</SelectItem>
                        <SelectItem value="random">Random Search</SelectItem>
                        <SelectItem value="optuna">Optuna 贝叶斯</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium mb-1.5 block">训练数据 (JSON)</label>
                  <Textarea
                    placeholder='[{"x1": 1, "x2": 2, "target": 0}, ...]'
                    value={trainData}
                    onChange={(e) => setTrainData(e.target.value)}
                    className="min-h-[180px] font-mono text-xs"
                  />
                </div>

                <Button onClick={train} disabled={loading} className="w-full">
                  {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
                  开始训练
                </Button>
              </CardContent>
            </Card>

            {/* 训练结果 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5" /> 训练结果
                </CardTitle>
              </CardHeader>
              <CardContent>
                {trainResult ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 rounded-lg bg-muted/50">
                        <p className="text-xs text-muted-foreground">算法</p>
                        <p className="font-bold">{trainResult.algorithm}</p>
                      </div>
                      <div className="p-3 rounded-lg bg-muted/50">
                        <p className="text-xs text-muted-foreground">训练时间</p>
                        <p className="font-bold">{trainResult.training_time_seconds?.toFixed(1)}s</p>
                      </div>
                      <div className="p-3 rounded-lg bg-muted/50">
                        <p className="text-xs text-muted-foreground">CV 均值</p>
                        <p className="font-bold text-primary">{trainResult.cv_mean?.toFixed(4)}</p>
                      </div>
                      <div className="p-3 rounded-lg bg-muted/50">
                        <p className="text-xs text-muted-foreground">模型 ID</p>
                        <p className="font-bold font-mono">{trainResult.model_id}</p>
                      </div>
                    </div>

                    {/* 评估指标 */}
                    {trainResult.evaluation && (
                      <div>
                        <h4 className="font-semibold mb-2 text-sm text-muted-foreground">评估指标</h4>
                        <div className="space-y-1.5">
                          {Object.entries(trainResult.evaluation)
                            .filter(([k]) => !['confusion_matrix'].includes(k) && typeof trainResult.evaluation[k] !== 'object')
                            .map(([key, value]) => (
                              <div key={key} className="flex items-center justify-between text-sm p-2 rounded bg-muted/30">
                                <span>{key}</span>
                                <span className="font-bold font-mono">{typeof value === 'number' ? value.toFixed(4) : String(value)}</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                    {/* 特征重要性 */}
                    {trainResult.feature_importance && (
                      <div>
                        <h4 className="font-semibold mb-2 text-sm text-muted-foreground">特征重要性</h4>
                        <div className="space-y-1.5">
                          {Object.entries(trainResult.feature_importance)
                            .sort(([,a],[,b]) => (b as number) - (a as number))
                            .slice(0, 8)
                            .map(([feat, imp]) => (
                              <div key={feat} className="flex items-center gap-2 text-sm">
                                <span className="w-24 truncate">{feat}</span>
                                <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                                  <div className="h-full bg-primary rounded-full" style={{ width: `${(imp as number) * 100}%` }} />
                                </div>
                                <span className="font-mono text-xs w-12 text-right">{(imp as number).toFixed(3)}</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Brain className="h-10 w-10 mb-2 opacity-30" />
                    <p className="text-sm">配置参数后开始训练</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 模型列表 */}
        <TabsContent value="models">
          {mlModels.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Brain className="h-10 w-10 text-muted-foreground/30 mb-2" />
                <p className="text-muted-foreground">暂无训练模型</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {mlModels.map((model) => (
                <Card key={model.id}>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <p className="font-semibold">{model.algorithm}</p>
                        <Badge variant="outline" className="text-xs mt-1">{model.task_type}</Badge>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => deleteModel(model.id)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                    {model.evaluation && (
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {Object.entries(model.evaluation).slice(0, 4).map(([k, v]) => (
                          <div key={k} className="p-1.5 rounded bg-muted/50">
                            <span className="text-muted-foreground">{k}: </span>
                            <span className="font-mono">{typeof v === 'number' ? v.toFixed(3) : String(v)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
