import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Network, Play, Loader2, TrendingUp, MessageSquare } from 'lucide-react'
import { dlApi } from '@/api/dl'
import { useAppStore } from '@/stores/appStore'

export default function DLPage() {
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [dlTask, setDlTask] = useState<'prophet' | 'lstm' | 'sentiment' | 'keywords'>('prophet')
  const [inputData, setInputData] = useState('')
  const [result, setResult] = useState<any>(null)

  const runDL = async () => {
    try {
      setLoading(true)
      let res: any
      if (dlTask === 'prophet' || dlTask === 'lstm') {
        const data = JSON.parse(inputData)
        res = dlTask === 'prophet'
          ? await dlApi.prophetForecast({ data })
          : await dlApi.lstmForecast({ data })
      } else if (dlTask === 'sentiment') {
        const texts = JSON.parse(inputData)
        res = await dlApi.sentimentAnalysis({ texts })
      } else {
        const texts = JSON.parse(inputData)
        res = await dlApi.extractKeywords({ texts })
      }
      setResult(res.data)
      addNotification({ type: 'success', title: '分析完成' })
    } catch (e: any) {
      addNotification({ type: 'error', title: '分析失败', description: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">深度学习</h2>
        <p className="text-muted-foreground">Prophet/LSTM 时序预测 · NLP 情感分析 · 关键词提取</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" /> 任务配置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-1.5 block">任务类型</label>
              <Select value={dlTask} onValueChange={(v: any) => setDlTask(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="prophet">Prophet 时序预测</SelectItem>
                  <SelectItem value="lstm">LSTM 时序预测</SelectItem>
                  <SelectItem value="sentiment">情感分析</SelectItem>
                  <SelectItem value="keywords">关键词提取</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">输入数据 (JSON)</label>
              <Textarea
                placeholder={
                  dlTask === 'sentiment' || dlTask === 'keywords'
                    ? '["这个产品很好用", "太差了"]'
                    : '[{"date": "2024-01-01", "value": 100}, ...]'
                }
                value={inputData}
                onChange={(e) => setInputData(e.target.value)}
                className="min-h-[200px] font-mono text-xs"
              />
            </div>
            <Button onClick={runDL} disabled={loading} className="w-full">
              {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
              运行分析
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>分析结果</CardTitle>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="space-y-3">
                {result.positive !== undefined && (
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg bg-green-500/10 text-center">
                      <p className="text-2xl font-bold text-green-500">{result.positive}</p>
                      <p className="text-xs text-muted-foreground">正面</p>
                    </div>
                    <div className="p-3 rounded-lg bg-yellow-500/10 text-center">
                      <p className="text-2xl font-bold text-yellow-500">{result.neutral}</p>
                      <p className="text-xs text-muted-foreground">中性</p>
                    </div>
                    <div className="p-3 rounded-lg bg-red-500/10 text-center">
                      <p className="text-2xl font-bold text-red-500">{result.negative}</p>
                      <p className="text-xs text-muted-foreground">负面</p>
                    </div>
                  </div>
                )}
                {result.keywords && (
                  <div className="flex flex-wrap gap-2">
                    {result.keywords.map((kw: any, i: number) => (
                      <Badge key={i} variant="secondary">{kw.word || kw} ({kw.score?.toFixed(2) || ''})</Badge>
                    ))}
                  </div>
                )}
                {result.forecast && (
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-sm font-medium">预测期数: {result.forecast.length}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      首期: {result.forecast[0]?.toFixed(2)} · 末期: {result.forecast[result.forecast.length - 1]?.toFixed(2)}
                    </p>
                  </div>
                )}
                <pre className="p-3 rounded-lg bg-muted/50 text-xs font-mono overflow-auto max-h-64">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Network className="h-10 w-10 mb-2 opacity-30" />
                <p className="text-sm">选择任务类型并输入数据</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
