import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AlertCircle, CheckCircle2, Loader2, PlayCircle, ShieldCheck, Sparkles, Wrench } from 'lucide-react'
import { smokeApi, type AssistedSmokeRunResult, type SmokeRunResult, type SmokeScenario } from '@/api/smoke'
import { extractApiError } from '@/api/crawl'
import { useAppStore } from '@/stores/appStore'

const DEFAULT_LOCAL_ROWS = [
  { date: '2026-05-10', value: 12.5, category: 'A' },
  { date: '2026-05-11', value: 18.0, category: 'B' },
]

export default function SmokeCenterPage() {
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [scenarios, setScenarios] = useState<SmokeScenario[]>([])
  const [contracts, setContracts] = useState<{ run_statuses: string[]; run_stages: string[]; assisted_auth_states: string[] } | null>(null)
  const [runResult, setRunResult] = useState<SmokeRunResult | null>(null)
  const [assistedResult, setAssistedResult] = useState<AssistedSmokeRunResult | null>(null)
  const [localDatasetName, setLocalDatasetName] = useState('smoke_center_local')
  const [localRows, setLocalRows] = useState(JSON.stringify(DEFAULT_LOCAL_ROWS, null, 2))
  const [publicStaticUrl, setPublicStaticUrl] = useState('https://example.com')
  const [publicDynamicUrl, setPublicDynamicUrl] = useState('https://example.com')
  const [assistedUrl, setAssistedUrl] = useState('https://www.bilibili.com')

  useEffect(() => {
    void loadSmokeMetadata()
  }, [])

  const loadSmokeMetadata = async () => {
    try {
      setLoading(true)
      const [scenarioRes, contractsRes] = await Promise.all([
        smokeApi.scenarios(),
        smokeApi.contracts(),
      ])
      setScenarios(scenarioRes.data?.scenarios || [])
      setContracts(contractsRes.data || null)
    } catch (e: any) {
      addNotification({ type: 'error', title: '验收中心加载失败', description: extractApiError(e) })
    } finally {
      setLoading(false)
    }
  }

  const localScenario = useMemo(
    () => scenarios.find((item) => item.scenario_id === 'local-upload-basic') || null,
    [scenarios],
  )
  const publicStaticScenario = useMemo(
    () => scenarios.find((item) => item.scenario_id === 'live-public-static') || null,
    [scenarios],
  )
  const publicDynamicScenario = useMemo(
    () => scenarios.find((item) => item.scenario_id === 'live-public-dynamic-js') || null,
    [scenarios],
  )
  const assistedScenario = useMemo(
    () => scenarios.find((item) => item.scenario_id === 'live-assisted-bilibili') || null,
    [scenarios],
  )

  const runLocalSmoke = async () => {
    try {
      setRunning(true)
      const rows = JSON.parse(localRows)
      const res = await smokeApi.run({
        scenario_id: 'local-upload-basic',
        dataset_name: localDatasetName,
        dataset_description: 'Smoke Center local run',
        rows,
      })
      setRunResult(res.data)
      addNotification({ type: 'success', title: '本地 Smoke 完成', description: `状态：${res.data.status}` })
    } catch (e: any) {
      addNotification({ type: 'error', title: '本地 Smoke 失败', description: extractApiError(e) })
    } finally {
      setRunning(false)
    }
  }

  const runPublicSmoke = async (scenarioId: string, url: string) => {
    try {
      setRunning(true)
      const res = await smokeApi.run({
        scenario_id: scenarioId,
        url,
      })
      setRunResult(res.data)
      addNotification({ type: 'success', title: '公开 Smoke 已执行', description: `状态：${res.data.status}` })
    } catch (e: any) {
      addNotification({ type: 'error', title: '公开 Smoke 失败', description: extractApiError(e) })
    } finally {
      setRunning(false)
    }
  }

  const startAssistedSmoke = async () => {
    try {
      setRunning(true)
      const res = await smokeApi.assistedStart({
        scenario_id: 'live-assisted-bilibili',
        url: assistedUrl,
      })
      setAssistedResult(res.data)
      addNotification({ type: 'success', title: '人机协同已启动', description: '请完成登录/验证码后点击继续校验。' })
    } catch (e: any) {
      addNotification({ type: 'error', title: '启动协同失败', description: extractApiError(e) })
    } finally {
      setRunning(false)
    }
  }

  const continueAssistedSmoke = async () => {
    if (!assistedResult?.continuation_token) {
      addNotification({ type: 'warning', title: '缺少 continuation token' })
      return
    }
    try {
      setRunning(true)
      const res = await smokeApi.assistedContinue({
        continuation_token: assistedResult.continuation_token,
      })
      setAssistedResult(res.data)
      addNotification({ type: 'success', title: '协同校验已执行', description: `状态：${res.data.status}` })
    } catch (e: any) {
      addNotification({ type: 'error', title: '继续协同失败', description: extractApiError(e) })
    } finally {
      setRunning(false)
    }
  }

  const renderMemoryCapture = (memoryCapture?: SmokeRunResult['memory_capture']) => {
    if (!memoryCapture) return null

    return (
      <div className="rounded-lg border bg-muted/30 p-3 text-xs space-y-1">
        <div className="flex items-center justify-between gap-3">
          <span className="font-medium">Little C 记忆写入</span>
          <Badge variant={memoryCapture.captured ? 'default' : 'outline'}>
            {memoryCapture.captured ? 'captured' : 'skipped'}
          </Badge>
        </div>
        {memoryCapture.capture_path && <p className="break-all">capture: {memoryCapture.capture_path}</p>}
        {memoryCapture.sync_path && <p className="break-all">sync: {memoryCapture.sync_path}</p>}
        {memoryCapture.error && <p className="break-all text-destructive">error: {memoryCapture.error}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">验收中心</h2>
          <p className="text-muted-foreground">Smoke Center · 主链验收 · robots 合规 · 人机协同采集</p>
        </div>
        <Button variant="outline" onClick={() => void loadSmokeMetadata()} disabled={loading || running}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
          刷新元数据
        </Button>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <Tabs defaultValue="local">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="local">Local Smoke</TabsTrigger>
              <TabsTrigger value="public">Live Public</TabsTrigger>
              <TabsTrigger value="assisted">Live Assisted</TabsTrigger>
            </TabsList>

            <TabsContent value="local" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PlayCircle className="h-5 w-5" /> 本地数据主链验收
                  </CardTitle>
                  <CardDescription>{localScenario?.description || '使用本地结构化数据验证数据集、分析与报告主链。'}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="mb-1.5 block text-sm font-medium">数据集名称</label>
                    <Input value={localDatasetName} onChange={(e) => setLocalDatasetName(e.target.value)} />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium">本地样例数据（JSON）</label>
                    <Textarea
                      value={localRows}
                      onChange={(e) => setLocalRows(e.target.value)}
                      className="min-h-[220px] font-mono text-xs"
                    />
                  </div>
                  <Button onClick={() => void runLocalSmoke()} disabled={running} className="w-full">
                    {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlayCircle className="mr-2 h-4 w-4" />}
                    运行 Local Smoke
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="public" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5" /> 公开静态 URL 验收
                  </CardTitle>
                  <CardDescription>{publicStaticScenario?.description || 'robots 先行，静态页面优先 URL crawl。'}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Input value={publicStaticUrl} onChange={(e) => setPublicStaticUrl(e.target.value)} placeholder="输入公开静态 URL" />
                  <Button variant="outline" onClick={() => void runPublicSmoke('live-public-static', publicStaticUrl)} disabled={running} className="w-full">
                    {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlayCircle className="mr-2 h-4 w-4" />}
                    运行 Static Smoke
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5" /> 公开动态 JS URL 验收
                  </CardTitle>
                  <CardDescription>{publicDynamicScenario?.description || 'robots 先行，动态页面优先 smart v2 / 动态方案。'}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Input value={publicDynamicUrl} onChange={(e) => setPublicDynamicUrl(e.target.value)} placeholder="输入公开动态 URL" />
                  <Button variant="outline" onClick={() => void runPublicSmoke('live-public-dynamic-js', publicDynamicUrl)} disabled={running} className="w-full">
                    {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlayCircle className="mr-2 h-4 w-4" />}
                    运行 Dynamic Smoke
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="assisted" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Wrench className="h-5 w-5" /> 人机协同登录验收
                  </CardTitle>
                  <CardDescription>{assistedScenario?.description || '首个平台为 Bilibili，后续扩展到更多登录态站点。'}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Input value={assistedUrl} onChange={(e) => setAssistedUrl(e.target.value)} placeholder="输入需要人机协同的目标 URL" />
                  {assistedScenario && (
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span>平台</span>
                        <Badge variant="outline">{assistedScenario.platform || 'custom'}</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>人工协同</span>
                        <Badge variant="outline">必需</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>后续目标</span>
                        <Badge variant="outline">session reuse + crawl</Badge>
                      </div>
                    </div>
                  )}
                  <div className="flex gap-3">
                    <Button onClick={() => void startAssistedSmoke()} disabled={running} className="flex-1">
                      {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wrench className="mr-2 h-4 w-4" />}
                      启动协同登录
                    </Button>
                    <Button variant="outline" onClick={() => void continueAssistedSmoke()} disabled={running || !assistedResult?.continuation_token} className="flex-1">
                      {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlayCircle className="mr-2 h-4 w-4" />}
                      我已完成，继续校验
                    </Button>
                  </div>

                  {assistedResult && (
                    <div className="rounded-lg border p-4 text-sm">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="font-medium">{assistedResult.platform || 'assisted-auth'}</p>
                          <p className="text-muted-foreground">
                            stage: {assistedResult.stage} · state: {assistedResult.assisted_auth_state}
                          </p>
                        </div>
                        <Badge variant={assistedResult.status === 'completed' ? 'default' : 'outline'}>
                          {assistedResult.status}
                        </Badge>
                      </div>

                      {assistedResult.continuation_token && (
                        <p className="mt-3 break-all text-xs text-muted-foreground">
                          continuation token: {assistedResult.continuation_token}
                        </p>
                      )}

                      {assistedResult.artifacts?.login_url && (
                        <div className="mt-3 rounded bg-muted/50 p-3 text-xs">
                          <p>登录入口：{assistedResult.artifacts.login_url}</p>
                          <p>状态检查：{assistedResult.artifacts.check_url}</p>
                        </div>
                      )}

                      <div className="mt-3">
                        {renderMemoryCapture(assistedResult.memory_capture)}
                      </div>

                      {assistedResult.notes?.length > 0 && (
                        <ul className="mt-3 space-y-1 text-muted-foreground">
                          {assistedResult.notes.map((note) => (
                            <li key={note}>- {note}</li>
                          ))}
                        </ul>
                      )}

                      {assistedResult.error && (
                        <div className="mt-3 rounded border border-destructive/30 bg-destructive/5 p-3 text-destructive">
                          {assistedResult.error}
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>后端 Contracts</CardTitle>
              <CardDescription>当前 Smoke Center 后端已固定的状态 vocabulary</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div>
                <p className="mb-2 font-medium">Run Statuses</p>
                <div className="flex flex-wrap gap-2">
                  {(contracts?.run_statuses || []).map((item) => (
                    <Badge key={item} variant="outline">{item}</Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-2 font-medium">Assisted Auth States</p>
                <div className="flex flex-wrap gap-2">
                  {(contracts?.assisted_auth_states || []).map((item) => (
                    <Badge key={item} variant="outline">{item}</Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>最近一次运行结果</CardTitle>
              <CardDescription>结构化展示当前 smoke run 的状态、合规与主链结果</CardDescription>
            </CardHeader>
            <CardContent>
              {!runResult ? (
                <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
                  还没有执行 smoke。先从 Local 或 Live Public 场景开始。
                </div>
              ) : (
                <div className="space-y-4 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{runResult.scenario_id}</p>
                      <p className="text-muted-foreground">stage: {runResult.stage}</p>
                    </div>
                    {runResult.status === 'passed' ? (
                      <Badge className="bg-green-500/10 text-green-600">
                        <CheckCircle2 className="mr-1 h-3 w-3" /> {runResult.status}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-amber-600">
                        <AlertCircle className="mr-1 h-3 w-3" /> {runResult.status}
                      </Badge>
                    )}
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-lg bg-muted/50 p-3">
                      <p className="text-muted-foreground">采集策略</p>
                      <p className="font-medium">{runResult.crawl_strategy || 'N/A'}</p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-3">
                      <p className="text-muted-foreground">robots</p>
                      <p className="font-medium">
                        {runResult.robots?.checked ? (runResult.robots?.allowed ? 'allowed' : 'blocked') : 'not checked'}
                      </p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-3">
                      <p className="text-muted-foreground">数据集保存</p>
                      <p className="font-medium">{runResult.dataset_saved ? 'passed' : 'not passed'}</p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-3">
                      <p className="text-muted-foreground">Analysis / Report</p>
                      <p className="font-medium">{`${runResult.analysis_passed ? 'analysis ok' : 'analysis no'} · ${runResult.report_passed ? 'report ok' : 'report no'}`}</p>
                    </div>
                  </div>

                  {runResult.artifacts?.dataset && (
                    <div className="rounded-lg border p-3">
                      <p className="mb-1 font-medium">Dataset Artifact</p>
                      <p className="text-muted-foreground break-all">
                        {runResult.artifacts.dataset.name} · {runResult.artifacts.dataset.table_name}
                      </p>
                    </div>
                  )}

                  {renderMemoryCapture(runResult.memory_capture)}

                  {runResult.notes?.length > 0 && (
                    <div className="rounded-lg border p-3">
                      <p className="mb-1 font-medium">Notes</p>
                      <ul className="space-y-1 text-muted-foreground">
                        {runResult.notes.map((note) => (
                          <li key={note}>- {note}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {runResult.error && (
                    <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-destructive">
                      {runResult.error}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
