import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Globe, Play, Square, RefreshCw, Loader2, CheckCircle, Search,
  AlertCircle, Clock, Database, Link, ArrowRight, Zap, Eye,
  ChevronDown, Table, List, FileJson, Sparkles, ExternalLink,
  Shield, KeyRound,
} from 'lucide-react'
import DynamicForm from '@/components/DynamicForm'
import AuthManager from '@/components/AuthManager'
import { crawlApi, extractApiError } from '@/api/crawl'
import { dataBrowserApi } from '@/api/data'
import { useTaskStore } from '@/stores/taskStore'
import { useAppStore } from '@/stores/appStore'

// 状态常量
const STATUS_MAP: Record<string, { icon: any; class: string }> = {
  completed: { icon: CheckCircle, class: 'bg-green-500/10 text-green-600' },
  running: { icon: Loader2, class: 'bg-blue-500/10 text-blue-500' },
  failed: { icon: AlertCircle, class: 'bg-red-500/10 text-red-500' },
  pending: { icon: Clock, class: 'bg-yellow-500/10 text-yellow-600' },
  stopped: { icon: Square, class: 'bg-gray-500/10 text-gray-500' },
}

export default function CrawlPage() {
  const navigate = useNavigate()
  const { tasks, setTasks, updateTask, adapters, setAdapters } = useTaskStore()
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('smart')

  // ==================== 智能采集 ====================
  const [smartUrl, setSmartUrl] = useState('')
  const [smartRequirement, setSmartRequirement] = useState('我想要标题、评分、上映时间')
  const [smartDynamic, setSmartDynamic] = useState(false)
  const [smartWaitFor, setSmartWaitFor] = useState('')
  const [smartAutoScroll, setSmartAutoScroll] = useState(false)
  const [smartScrollCount, setSmartScrollCount] = useState(3)
  const [smartClickSelector, setSmartClickSelector] = useState('')
  const [smartClickCount, setSmartClickCount] = useState(1)
  const [smartLoading, setSmartLoading] = useState(false)
  const [smartResult, setSmartResult] = useState<any>(null)
  const [savingDataset, setSavingDataset] = useState(false)
  const [datasetName, setDatasetName] = useState('')
  const [datasetDesc, setDatasetDesc] = useState('')

  // ==================== URL 自由爬取 ====================
  const [urlInput, setUrlInput] = useState('')
  const [urlProbing, setUrlProbing] = useState(false)
  const [urlProbeResult, setUrlProbeResult] = useState<any>(null)
  const [urlCrawling, setUrlCrawling] = useState(false)
  const [urlCrawlResult, setUrlCrawlResult] = useState<any>(null)
  const [useSmartV2, setUseSmartV2] = useState(true)
  const [urlDatasetName, setUrlDatasetName] = useState('')
  const [urlDatasetDesc, setUrlDatasetDesc] = useState('')
  const [savingUrlDataset, setSavingUrlDataset] = useState(false)

  // 分页爬取
  const [paginatedUrl, setPaginatedUrl] = useState('')
  const [startPage, setStartPage] = useState(1)
  const [endPage, setEndPage] = useState(5)
  const [paginationConcurrency, setPaginationConcurrency] = useState(3)
  const [paginatedResult, setPaginatedResult] = useState<any>(null)

  // ==================== 适配器参数表单 ====================
  const [selectedAdapter, setSelectedAdapter] = useState('')
  const [adapterSchema, setAdapterSchema] = useState<Record<string, any> | null>(null)
  const [adapterValues, setAdapterValues] = useState<Record<string, any>>({})
  const [submitting, setSubmitting] = useState(false)
  const [adapterResult, setAdapterResult] = useState<any>(null)

  // ==================== JustOneAPI ====================
  const [justoneSchema, setJustoneSchema] = useState<Record<string, any> | null>(null)
  const [justoneValues, setJustoneValues] = useState<Record<string, any>>({})
  const [justonePlatforms, setJustonePlatforms] = useState<any[]>([])
  const [justoneSelectedPlatform, setJustoneSelectedPlatform] = useState('')
  const [justoneApis, setJustoneApis] = useState<any[]>([])
  const [justoneCrawling, setJustoneCrawling] = useState(false)
  const [justoneResult, setJustoneResult] = useState<any>(null)

  // ==================== Day 3: 登录态配置 ====================
  const [authSessions, setAuthSessions] = useState<any[]>([])
  const [selectedAuthPlatform, setSelectedAuthPlatform] = useState('')
  const [useAuth, setUseAuth] = useState(false)
  const [showAuthManager, setShowAuthManager] = useState(false)

  useEffect(() => {
    initData()
  }, [])

  const initData = async () => {
    try {
      setLoading(true)
      await Promise.all([
        loadTasks(),
        loadSchemas(),
      ])
    } finally {
      setLoading(false)
    }
  }

  const loadTasks = async () => {
    try {
      const res = await crawlApi.listTasks()
      setTasks(res.data?.tasks || res.data?.data || res.data || [])
    } catch {
      // 静默处理
    }
  }

  const loadSchemas = async () => {
    try {
      const res = await crawlApi.paramSchemas()
      const schemas = res.data?.schemas || []
      const mapped: Record<string, any> = {}
      for (const s of schemas) {
        mapped[s.adapter] = s
      }
      // 载入 JustOneAPI schema
      try {
        const j1Res = await crawlApi.paramSchema('justoneapi')
        if (j1Res.data?.params) {
          setJustoneSchema(j1Res.data.params)
        }
      } catch {}
    } catch {}
  }

  // ==================== Day 3: 加载登录态 ====================
  const loadAuthSessions = async () => {
    try {
      const res = await crawlApi.authSessions()
      if (res.data?.sessions) {
        setAuthSessions(res.data.sessions)
      }
    } catch {
      // 静默处理
    }
  }

  // ==================== URL 探测 ====================
  const probeUrl = async () => {
    if (!urlInput.trim()) return
    setUrlProbing(true)
    setUrlProbeResult(null)
    try {
      const res = useSmartV2
        ? await crawlApi.smartProbeV2(urlInput.trim())
        : await crawlApi.urlProbe(urlInput.trim())
      setUrlProbeResult(res.data)
    } catch (e: any) {
      addNotification({ type: 'error', title: '探测失败', description: extractApiError(e) })
    } finally {
      setUrlProbing(false)
    }
  }

  // ==================== URL 爬取 ====================
  const crawlUrl = async () => {
    if (!urlInput.trim()) return
    setUrlCrawling(true)
    setUrlCrawlResult(null)
    try {
      const payload: any = { url: urlInput.trim() }
      // Day 3: 添加登录态
      if (useAuth && selectedAuthPlatform) {
        payload.use_auth = true
        payload.auth_platform = selectedAuthPlatform
        payload.require_auth = true
      }
      const res = useSmartV2
        ? await crawlApi.smartCrawlV2(payload)
        : await crawlApi.urlCrawl(payload)
      setUrlCrawlResult(res.data)
      setUrlDatasetName(`URL采集_${new Date().toISOString().slice(0, 10)}`)
      setUrlDatasetDesc(`从 ${urlInput.trim()} 采集`)
      addNotification({
        type: res.data?.success ? 'success' : 'error',
        title: res.data?.success ? '爬取成功' : '爬取失败',
        description: res.data?.message || res.data?.error || '',
      })
    } catch (e: any) {
      addNotification({ type: 'error', title: '爬取失败', description: extractApiError(e) })
    } finally {
      setUrlCrawling(false)
    }
  }

  const normalizedUrlRows = useMemo(() => {
    const data = urlCrawlResult?.data
    if (Array.isArray(data)) return data
    if (data && typeof data === 'object') return [data]
    return []
  }, [urlCrawlResult])

  const normalizedUrlColumns = useMemo(() => {
    if (!normalizedUrlRows.length) return []
    const firstRow = normalizedUrlRows[0]
    return Object.keys(firstRow)
  }, [normalizedUrlRows])

  const saveUrlDataset = async () => {
    if (!normalizedUrlRows.length || !urlDatasetName.trim()) return
    setSavingUrlDataset(true)
    try {
      const res = await crawlApi.saveDataset({
        name: urlDatasetName,
        description: urlDatasetDesc,
        columns: normalizedUrlColumns,
        data: normalizedUrlRows,
        source_url: urlInput.trim(),
        source_type: useSmartV2 ? 'smart_crawl_v2' : 'crawl',
      })
      if (res.data?.success) {
        addNotification({
          type: 'success',
          title: '保存成功',
          description: `${res.data.message}，现在可以在“数据集”或“数据浏览”中继续查看`,
        })
        navigate('/datasets')
      } else {
        addNotification({ type: 'error', title: '保存失败', description: res.data?.error || '保存失败' })
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: '保存失败', description: extractApiError(e) })
    } finally {
      setSavingUrlDataset(false)
    }
  }

  // ==================== 分页爬取 ====================
  const crawlPaginated = async () => {
    if (!paginatedUrl.trim()) return
    setUrlCrawling(true)
    setPaginatedResult(null)
    try {
      const res = await crawlApi.urlCrawlPaginated({
        url: paginatedUrl.trim(),
        start_page: startPage,
        end_page: endPage,
        concurrency: paginationConcurrency,
      })
      setPaginatedResult(res.data)
      addNotification({
        type: 'success',
        title: '分页爬取完成',
        description: `共 ${res.data?.pages?.total || 0} 页,获取 ${res.data?.count || 0} 条数据`,
      })
    } catch (e: any) {
      addNotification({ type: 'error', title: '分页爬取失败', description: extractApiError(e) })
    } finally {
      setUrlCrawling(false)
    }
  }

  // ==================== 适配器参数表单 ====================
  const selectAdapter = async (name: string) => {
    setSelectedAdapter(name)
    setAdapterValues({})
    setAdapterResult(null)
    try {
      const res = await crawlApi.paramSchema(name)
      if (res.data?.params) {
        setAdapterSchema(res.data.params)
      }
    } catch {
      setAdapterSchema(null)
    }
  }

  const submitAdapter = async () => {
    if (!selectedAdapter) return
    setSubmitting(true)
    setAdapterResult(null)
    try {
      const res = await crawlApi.crawlAdapter(selectedAdapter, adapterValues)
      setAdapterResult(res.data)
      addNotification({
        type: res.data?.success ? 'success' : 'error',
        title: '采集完成',
        description: `获取 ${res.data?.count || 0} 条数据`,
      })
    } catch (e: any) {
      addNotification({ type: 'error', title: '采集失败', description: extractApiError(e) })
    } finally {
      setSubmitting(false)
    }
  }

  // ==================== JustOneAPI ====================
  const selectJustonePlatform = (platform: string) => {
    setJustoneSelectedPlatform(platform)
    setJustoneValues((prev) => ({ ...prev, platform }))
  }

  const submitJustone = async () => {
    setJustoneCrawling(true)
    setJustoneResult(null)
    try {
      const res = await crawlApi.crawlAdapter('justoneapi', justoneValues)
      setJustoneResult(res.data)
      addNotification({
        type: res.data?.success ? 'success' : 'error',
        title: 'JustOneAPI 采集完成',
        description: `获取 ${res.data?.count || 0} 条数据`,
      })
    } catch (e: any) {
      addNotification({ type: 'error', title: '采集失败', description: extractApiError(e) })
    } finally {
      setJustoneCrawling(false)
    }
  }

  const submitSmartExtract = async () => {
    if (!smartUrl.trim() || !smartRequirement.trim()) return
    setSmartLoading(true)
    setSmartResult(null)
    try {
      const payload: any = {
        url: smartUrl.trim(),
        requirement: smartRequirement.trim(),
        dynamic: smartDynamic,
        wait_for: smartWaitFor || undefined,
        auto_scroll: smartAutoScroll,
        scroll_count: smartScrollCount,
        click_selector: smartClickSelector || undefined,
        click_count: smartClickCount,
      }
      // Day 3: 添加登录态
      if (useAuth && selectedAuthPlatform) {
        payload.use_auth = true
        payload.auth_platform = selectedAuthPlatform
      }
      const res = await crawlApi.smartExtract(payload)
      setSmartResult(res.data)
      addNotification({
        type: res.data?.success ? 'success' : 'error',
        title: res.data?.success ? '智能抽取完成' : '智能抽取失败',
        description: res.data?.message || '',
      })
    } catch (e: any) {
      addNotification({ type: 'error', title: '智能抽取失败', description: extractApiError(e) })
    } finally {
      setSmartLoading(false)
    }
  }

  // ==================== 状态徽章 ====================
  const statusBadge = (status: string) => {
    const cfg = STATUS_MAP[status] || STATUS_MAP.pending
    const Icon = cfg.icon
    return (
      <Badge variant="outline" className={`${cfg.class} gap-1`}>
        <Icon className={`w-3 h-3 ${status === 'running' ? 'animate-spin' : ''}`} />
        {status}
      </Badge>
    )
  }

  // ==================== JustOneAPI 平台网格 ====================
  const JUSTONE_PLATFORMS = [
    { value: 'xiaohongshu', label: '小红书', icon: '🔴' },
    { value: 'douyin', label: '抖音', icon: '🎵' },
    { value: 'weibo', label: '微博', icon: '📱' },
    { value: 'taobao', label: '淘宝', icon: '🛒' },
    { value: 'bilibili', label: 'B站', icon: '📺' },
    { value: 'jd', label: '京东', icon: '🛍️' },
    { value: 'zhihu', label: '知乎', icon: '💡' },
    { value: 'kuaishou', label: '快手', icon: '📸' },
    { value: 'pdd', label: '拼多多', icon: '🎯' },
    { value: 'meituan', label: '美团', icon: '🍜' },
    { value: 'dianping', label: '大众点评', icon: '⭐' },
    { value: 'toutiao', label: '头条', icon: '📰' },
  ]

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">数据采集</h2>
          <p className="text-muted-foreground">URL 自由爬取 · 参数表单化 · 分页采集 · JustOneAPI 可视化</p>
        </div>
        <Button variant="outline" onClick={initData} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} /> 刷新
        </Button>
      </div>

      {/* Day 3: 登录态配置栏 */}
      <Card className="bg-primary/5 border-primary/20">
        <CardContent className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">登录态</span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="use-auth"
                  type="checkbox"
                  checked={useAuth}
                  onChange={(e) => {
                    setUseAuth(e.target.checked)
                    if (e.target.checked) loadAuthSessions()
                  }}
                  className="rounded border-gray-300"
                />
                <Label htmlFor="use-auth" className="text-sm cursor-pointer">
                  使用登录态采集
                </Label>
              </div>
              {useAuth && (
                <Select value={selectedAuthPlatform} onValueChange={setSelectedAuthPlatform}>
                  <SelectTrigger className="w-40 h-8 text-sm">
                    <SelectValue placeholder="选择平台..." />
                  </SelectTrigger>
                  <SelectContent>
                    {authSessions.filter((s: any) => s.has_session).map((s: any) => (
                      <SelectItem key={s.platform} value={s.platform}>
                        {s.platform} ({s.cookies_count} cookies)
                      </SelectItem>
                    ))}
                    {authSessions.filter((s: any) => s.has_session).length === 0 && (
                      <SelectItem value="" disabled>暂无有效会话</SelectItem>
                    )}
                  </SelectContent>
                </Select>
              )}
            </div>
            <Button variant="ghost" size="sm" onClick={() => setShowAuthManager(!showAuthManager)}>
              <KeyRound className="w-4 h-4 mr-1" />
              {showAuthManager ? '隐藏' : '管理'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {showAuthManager && <AuthManager />}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-5 w-full max-w-3xl">
          <TabsTrigger value="smart" className="gap-2">
            <Sparkles className="w-4 h-4" /> 智能采集
          </TabsTrigger>
          <TabsTrigger value="url" className="gap-2">
            <Link className="w-4 h-4" /> URL 爬取
          </TabsTrigger>
          <TabsTrigger value="adapter" className="gap-2">
            <Zap className="w-4 h-4" /> 适配器采集
          </TabsTrigger>
          <TabsTrigger value="justoneapi" className="gap-2">
            <Globe className="w-4 h-4" /> JustOneAPI
          </TabsTrigger>
          <TabsTrigger value="tasks" className="gap-2">
            <Database className="w-4 h-4" /> 任务管理
          </TabsTrigger>
        </TabsList>

        {/* ==================== Tab 0: 智能采集 ==================== */}
        <TabsContent value="smart" className="space-y-4 mt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-primary" />
                  智能字段采集
                </CardTitle>
                <CardDescription>
                  输入 URL 和你想要的字段,系统自动抽取结构化数据
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>目标 URL</Label>
                  <Input
                    placeholder="https://movie.douban.com/top250"
                    value={smartUrl}
                    onChange={(e) => setSmartUrl(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>想提取的内容</Label>
                  <Textarea
                    rows={4}
                    placeholder="例如:我要电影排名、电影名、评分、上映时间、导演"
                    value={smartRequirement}
                    onChange={(e) => setSmartRequirement(e.target.value)}
                  />
                </div>
                <div className="border rounded-lg p-3 space-y-3 bg-muted/30">
                  <div className="flex items-center gap-2">
                    <input
                      id="smart-dynamic"
                      type="checkbox"
                      checked={smartDynamic}
                      onChange={(e) => setSmartDynamic(e.target.checked)}
                    />
                    <Label htmlFor="smart-dynamic">动态页面增强模式</Label>
                  </div>
                  {smartDynamic && (
                    <div className="space-y-3 pl-6">
                      <div className="space-y-1">
                        <Label className="text-xs">等待元素出现 (CSS 选择器)</Label>
                        <Input
                          size={1}
                          placeholder="例如: .content-loaded"
                          value={smartWaitFor}
                          onChange={(e) => setSmartWaitFor(e.target.value)}
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          id="smart-auto-scroll"
                          type="checkbox"
                          checked={smartAutoScroll}
                          onChange={(e) => setSmartAutoScroll(e.target.checked)}
                        />
                        <Label htmlFor="smart-auto-scroll" className="text-sm">自动滚动加载</Label>
                      </div>
                      {smartAutoScroll && (
                        <div className="space-y-1">
                          <Label className="text-xs">滚动次数</Label>
                          <Input
                            type="number"
                            min={1}
                            max={20}
                            value={smartScrollCount}
                            onChange={(e) => setSmartScrollCount(Number(e.target.value))}
                          />
                        </div>
                      )}
                      <div className="space-y-1">
                        <Label className="text-xs">点击加载更多 (CSS 选择器)</Label>
                        <Input
                          size={1}
                          placeholder="例如: .load-more"
                          value={smartClickSelector}
                          onChange={(e) => setSmartClickSelector(e.target.value)}
                        />
                      </div>
                      {smartClickSelector && (
                        <div className="space-y-1">
                          <Label className="text-xs">点击次数</Label>
                          <Input
                            type="number"
                            min={1}
                            max={10}
                            value={smartClickCount}
                            onChange={(e) => setSmartClickCount(Number(e.target.value))}
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <Button className="w-full" onClick={submitSmartExtract} disabled={smartLoading || !smartUrl.trim()}>
                  {smartLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
                  开始智能抽取
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Table className="w-5 h-5 text-primary" />
                  抽取结果
                  {smartResult?.rows && <Badge className="ml-2">{smartResult.rows.length} 条</Badge>}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!smartResult ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Sparkles className="w-8 h-8 mb-2 opacity-30" />
                    <p className="text-sm">试试：豆瓣 Top250 + "排名、评分、上映时间"</p>
                  </div>
                ) : (
                  <ScrollArea className="h-96">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-muted-foreground">{smartResult.message}</p>
                        {smartResult.success && smartResult.rows?.length > 0 && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setDatasetName(`采集数据_${new Date().toISOString().slice(0, 10)}`)
                              setDatasetDesc(`从 ${smartUrl} 采集`)
                            }}
                          >
                            <Database className="w-3 h-3 mr-1" /> 保存为数据集
                          </Button>
                        )}
                      </div>
                      {datasetName && (
                        <div className="border rounded-lg p-3 space-y-2 bg-muted/30">
                          <div className="space-y-1">
                            <Label className="text-xs">数据集名称</Label>
                            <Input
                              size={1}
                              value={datasetName}
                              onChange={(e) => setDatasetName(e.target.value)}
                              placeholder="输入数据集名称"
                            />
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs">描述</Label>
                            <Input
                              size={1}
                              value={datasetDesc}
                              onChange={(e) => setDatasetDesc(e.target.value)}
                              placeholder="输入描述"
                            />
                          </div>
                          <Button
                            size="sm"
                            className="w-full"
                            disabled={savingDataset || !datasetName.trim()}
                            onClick={async () => {
                              setSavingDataset(true)
                              try {
                                const res = await crawlApi.saveDataset({
                                  name: datasetName,
                                  description: datasetDesc,
                                  columns: smartResult.fields?.map((f: any) => f.name) || Object.keys(smartResult.rows[0]),
                                  data: smartResult.rows,
                                  source_url: smartUrl,
                                  source_type: 'crawl',
                                })
                                if (res.data?.success) {
                                  addNotification({
                                    type: 'success',
                                    title: '保存成功',
                                    description: `${res.data.message}，现在可以在“数据集”中查看真实数据`,
                                  })
                                  setDatasetName('')
                                  setDatasetDesc('')
                                  navigate('/datasets')
                                } else {
                                  addNotification({ type: 'error', title: '保存失败', description: res.data?.error || '' })
                                }
                              } catch (e: any) {
                                addNotification({ type: 'error', title: '保存失败', description: extractApiError(e) })
                              } finally {
                                setSavingDataset(false)
                              }
                            }}
                          >
                            {savingDataset ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Database className="w-3 h-3 mr-1" />}
                            确认保存
                          </Button>
                        </div>
                      )}
                      {smartResult.quality && (
                        <div className="text-xs text-muted-foreground">
                          质量分: {smartResult.quality.score} · 命中率: {smartResult.quality.filled_ratio}
                        </div>
                      )}
                      <Separator />
                      {smartResult.rows?.slice(0, 50).map((row: any, i: number) => (
                        <div key={i} className="border rounded p-3 text-sm bg-muted/20">
                          {Object.entries(row).map(([k, v]) => (
                            <div key={k} className="flex gap-2 py-0.5">
                              <span className="font-medium text-muted-foreground min-w-[80px]">{k}:</span>
                              <span className="truncate">{String(v)}</span>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ==================== Tab 1: URL 自由爬取 ==================== */}
        <TabsContent value="url" className="space-y-4 mt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* 输入区 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Link className="w-5 h-5 text-primary" />
                  URL 自由爬取
                </CardTitle>
                <CardDescription>
                  输入网址,自动识别类型,智能选择爬取策略
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* URL 输入 */}
                <div className="space-y-2">
                  <Label>目标 URL</Label>
                  <div className="flex gap-2">
                    <Input
                      placeholder="https://example.com/data"
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && probeUrl()}
                    />
                    <Button
                      variant="outline"
                      onClick={probeUrl}
                      disabled={!urlInput.trim() || urlProbing}
                    >
                      {urlProbing ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Search className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>

                {/* 探测结果 */}
                {urlProbeResult && (
                  <div className="border rounded-lg p-4 space-y-3 bg-muted/30">
                    <h4 className="text-sm font-semibold flex items-center gap-2">
                      <Eye className="w-4 h-4" /> 探测结果
                    </h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">
                          {urlProbeResult.status_code > 0 ? `${urlProbeResult.status_code}` : 'N/A'}
                        </Badge>
                        <span className="text-muted-foreground">状态码</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">
                          {urlProbeResult.content_type?.split(';')[0] || 'unknown'}
                        </Badge>
                        <span className="text-muted-foreground">Content-Type</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={urlProbeResult.is_api ? 'default' : 'secondary'} className="text-xs">
                          {urlProbeResult.is_api ? 'API' : '网页'}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={urlProbeResult.is_protected ? 'destructive' : 'secondary'}
                          className="text-xs"
                        >
                          {urlProbeResult.is_protected ? '有反爬' : '无保护'}
                        </Badge>
                      </div>
                    </div>
                    {urlProbeResult.suggested_strategy && (
                      <div className="flex items-center gap-2 text-sm">
                        <Sparkles className="w-4 h-4 text-primary" />
                        <span className="text-muted-foreground">建议策略:</span>
                        <Badge>{urlProbeResult.suggested_strategy}</Badge>
                      </div>
                    )}
                    {urlProbeResult.intent && (
                      <div className="flex items-center gap-2 text-sm">
                        <Sparkles className="w-4 h-4 text-primary" />
                        <span className="text-muted-foreground">识别意图:</span>
                        <Badge variant="outline">{urlProbeResult.intent}</Badge>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex items-center justify-between rounded-lg border px-3 py-2">
                  <div className="space-y-0.5">
                    <p className="text-sm font-medium">智能爬虫 v2</p>
                    <p className="text-xs text-muted-foreground">
                      使用新的智能探测、自适应策略和质量评分链路
                    </p>
                  </div>
                  <input
                    id="use-smart-v2"
                    type="checkbox"
                    checked={useSmartV2}
                    onChange={(e) => setUseSmartV2(e.target.checked)}
                    className="h-4 w-4"
                  />
                </div>

                {/* 爬取按钮 */}
                <Button
                  className="w-full"
                  onClick={crawlUrl}
                  disabled={!urlInput.trim() || urlCrawling}
                >
                  {urlCrawling ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  开始爬取
                </Button>
              </CardContent>
            </Card>

            {/* 结果区 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Table className="w-5 h-5 text-primary" />
                  爬取结果
                  {urlCrawlResult && (
                    <Badge variant={urlCrawlResult.success ? 'default' : 'destructive'} className="ml-2">
                      {urlCrawlResult.count || 0} 条
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!urlCrawlResult ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <ArrowRight className="w-8 h-8 mb-2 opacity-30" />
                    <p className="text-sm">输入 URL 并探测,然后开始爬取</p>
                  </div>
                ) : (
                  <ScrollArea className="h-80">
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">
                        {urlCrawlResult.message || urlCrawlResult.error || '爬取完成'}
                      </p>
                      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                        {typeof urlCrawlResult.elapsed === 'number' && (
                          <span>耗时 {urlCrawlResult.elapsed.toFixed(2)}s</span>
                        )}
                        {typeof urlCrawlResult.duration_ms === 'number' && (
                          <span>耗时 {(urlCrawlResult.duration_ms / 1000).toFixed(2)}s</span>
                        )}
                        {urlCrawlResult.strategy_used && (
                          <span>策略 {urlCrawlResult.strategy_used}</span>
                        )}
                        {typeof urlCrawlResult.quality_score === 'number' && (
                          <span>质量 {(urlCrawlResult.quality_score * 100).toFixed(0)}%</span>
                        )}
                      </div>
                      {urlCrawlResult.success && normalizedUrlRows.length > 0 && (
                        <div className="border rounded-lg p-3 space-y-2 bg-muted/30">
                          <div className="space-y-1">
                            <Label className="text-xs">数据集名称</Label>
                            <Input
                              value={urlDatasetName}
                              onChange={(e) => setUrlDatasetName(e.target.value)}
                              placeholder="输入数据集名称"
                            />
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs">描述</Label>
                            <Input
                              value={urlDatasetDesc}
                              onChange={(e) => setUrlDatasetDesc(e.target.value)}
                              placeholder="输入描述"
                            />
                          </div>
                          <Button
                            size="sm"
                            className="w-full"
                            disabled={savingUrlDataset || !urlDatasetName.trim()}
                            onClick={saveUrlDataset}
                          >
                            {savingUrlDataset ? (
                              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                            ) : (
                              <Database className="w-3 h-3 mr-1" />
                            )}
                            保存为数据集并查看
                          </Button>
                          {normalizedUrlRows.length >= 100 && (
                            <p className="text-xs text-muted-foreground">
                              当前仅展示部分采集结果，保存后可在数据浏览页分页查看完整内容。
                            </p>
                          )}
                        </div>
                      )}
                      <Separator />
                      {normalizedUrlRows
                        .filter(Boolean)
                        .slice(0, 50)
                        .map((item: any, i: number) => (
                        <div key={i} className="border rounded p-3 text-sm bg-muted/20">
                          {Object.entries(item).map(([k, v]) => (
                            <div key={k} className="flex gap-2 py-0.5">
                              <span className="font-medium text-muted-foreground min-w-[80px]">{k}:</span>
                              <span className="truncate">{String(v).substring(0, 200)}</span>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          </div>

          {/* 分页爬取 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ChevronDown className="w-5 h-5 text-primary" />
                分页爬取
              </CardTitle>
              <CardDescription>
                输入第 1 页 URL,自动识别分页规律并翻页采集
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-5">
                <div className="md:col-span-2 space-y-2">
                  <Label>第 1 页 URL</Label>
                  <Input
                    placeholder="https://example.com/list?page=1"
                    value={paginatedUrl}
                    onChange={(e) => setPaginatedUrl(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>起始页</Label>
                  <Input
                    type="number"
                    min={1}
                    value={startPage}
                    onChange={(e) => setStartPage(Number(e.target.value))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>结束页</Label>
                  <Input
                    type="number"
                    min={1}
                    max={50}
                    value={endPage}
                    onChange={(e) => setEndPage(Number(e.target.value))}
                  />
                </div>
                <div className="flex items-end">
                  <Button
                    className="w-full"
                    onClick={crawlPaginated}
                    disabled={!paginatedUrl.trim() || urlCrawling}
                  >
                    {urlCrawling ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4 mr-2" />
                    )}
                    分页采集
                  </Button>
                </div>
              </div>
              {paginatedResult && (
                <div className="border rounded-lg p-4 bg-muted/30">
                  <p className="text-sm font-medium">{paginatedResult.message}</p>
                  <div className="flex gap-3 mt-2 text-sm text-muted-foreground">
                    <span>总页数: {paginatedResult.pages?.total}</span>
                    <span>成功: {paginatedResult.pages?.success}</span>
                    <span>失败: {paginatedResult.pages?.failed}</span>
                    <span>数据: {paginatedResult.count} 条</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ==================== Tab 2: 适配器参数表单化 ==================== */}
        <TabsContent value="adapter" className="space-y-4 mt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* 表单区 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-primary" />
                  适配器采集
                </CardTitle>
                <CardDescription>
                  选择适配器,填表单,不用写 JSON
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* 适配器选择 */}
                <div className="space-y-2">
                  <Label>选择适配器</Label>
                  <Select value={selectedAdapter} onValueChange={selectAdapter}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择数据源..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="eastmoney">📈 东方财富 - 股票K线/行情</SelectItem>
                      <SelectItem value="exchangerate">💱 汇率查询</SelectItem>
                      <SelectItem value="openweather">🌤️ 天气查询</SelectItem>
                      <SelectItem value="wikipedia">📚 维基百科</SelectItem>
                      <SelectItem value="justoneapi">🌐 JustOneAPI - 社交数据</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* 动态表单 */}
                {adapterSchema && (
                  <div className="border rounded-lg p-4 space-y-2">
                    <h4 className="text-sm font-semibold">填写参数</h4>
                    <DynamicForm
                      schema={adapterSchema}
                      values={adapterValues}
                      onChange={setAdapterValues}
                      disabled={submitting}
                    />
                  </div>
                )}

                <Button
                  className="w-full"
                  onClick={submitAdapter}
                  disabled={!selectedAdapter || submitting}
                >
                  {submitting ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  开始采集
                </Button>
              </CardContent>
            </Card>

            {/* 结果区 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileJson className="w-5 h-5 text-primary" />
                  采集结果
                  {adapterResult && (
                    <Badge variant={adapterResult.success ? 'default' : 'destructive'} className="ml-2">
                      {adapterResult.count || 0} 条
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!adapterResult ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Database className="w-8 h-8 mb-2 opacity-30" />
                    <p className="text-sm">选择适配器并填写参数后开始采集</p>
                  </div>
                ) : (
                  <ScrollArea className="h-80">
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">{adapterResult.message}</p>
                      {adapterResult.data?.slice(0, 50).map((item: any, i: number) => (
                        <div key={i} className="border rounded p-3 text-sm bg-muted/20">
                          {Object.entries(item).map(([k, v]) => (
                            <div key={k} className="flex gap-2 py-0.5">
                              <span className="font-medium text-muted-foreground min-w-[80px]">{k}:</span>
                              <span className="truncate">{String(v).substring(0, 200)}</span>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ==================== Tab 3: JustOneAPI 可视化选择 ==================== */}
        <TabsContent value="justoneapi" className="space-y-4 mt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* 选择区 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Globe className="w-5 h-5 text-primary" />
                  JustOneAPI
                </CardTitle>
                <CardDescription>
                  27 个社交媒体平台 · 200+ API · 可视化三步选择
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Step 1: 选平台 */}
                <div className="space-y-3">
                  <Label className="text-base font-semibold">📌 第一步:选择平台</Label>
                  <div className="grid grid-cols-4 gap-2">
                    {JUSTONE_PLATFORMS.map((p) => (
                      <button
                        key={p.value}
                        onClick={() => selectJustonePlatform(p.value)}
                        className={`
                          flex items-center gap-1.5 p-2 rounded-lg border text-sm cursor-pointer
                          transition-colors hover:bg-accent
                          ${justoneSelectedPlatform === p.value
                            ? 'border-primary bg-primary/10 text-primary font-medium'
                            : 'border-border hover:border-primary/50'
                          }
                        `}
                      >
                        <span className="text-base">{p.icon}</span>
                        <span>{p.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Step 2: 选 API */}
                {justoneSelectedPlatform && (
                  <div className="space-y-3">
                    <Label className="text-base font-semibold">⚙️ 第二步:选择功能</Label>
                    {justoneSchema?.api && (
                      <DynamicForm
                        schema={{ api: justoneSchema.api }}
                        values={{ api: justoneValues.api || '' }}
                        onChange={(v) => setJustoneValues({ ...justoneValues, ...v })}
                      />
                    )}
                  </div>
                )}

                {/* Step 3: 填参数 */}
                {justoneSelectedPlatform && justoneSchema && (
                  <div className="space-y-3">
                    <Label className="text-base font-semibold">📝 第三步:填写参数</Label>
                    <div className="border rounded-lg p-4">
                      <DynamicForm
                        schema={Object.fromEntries(
                          Object.entries(justoneSchema).filter(([k]) => !['platform', 'api'].includes(k))
                        )}
                        values={justoneValues}
                        onChange={setJustoneValues}
                        disabled={justoneCrawling}
                      />
                    </div>
                  </div>
                )}

                <Button
                  className="w-full"
                  onClick={submitJustone}
                  disabled={!justoneSelectedPlatform || justoneCrawling}
                >
                  {justoneCrawling ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Search className="w-4 h-4 mr-2" />
                  )}
                  开始采集
                </Button>
              </CardContent>
            </Card>

            {/* 结果区 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileJson className="w-5 h-5 text-primary" />
                  采集结果
                  {justoneResult && (
                    <Badge variant={justoneResult.success ? 'default' : 'destructive'} className="ml-2">
                      {justoneResult.count || 0} 条
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!justoneResult ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Globe className="w-8 h-8 mb-2 opacity-30" />
                    <p className="text-sm">选择平台 → 选择 API → 填写参数 → 开始采集</p>
                  </div>
                ) : (
                  <ScrollArea className="h-96">
                    <div className="space-y-2">
                      <p className="text-sm">{justoneResult.message}</p>
                      {justoneResult.data?.slice(0, 50).map((item: any, i: number) => (
                        <div key={i} className="border rounded p-3 text-sm bg-muted/20">
                          {Object.entries(item).slice(0, 6).map(([k, v]) => (
                            <div key={k} className="flex gap-2 py-0.5">
                              <span className="font-medium text-muted-foreground min-w-[80px]">{k}:</span>
                              <span className="truncate">{String(v).substring(0, 150)}</span>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ==================== Tab 4: 任务管理 ==================== */}
        <TabsContent value="tasks" className="space-y-4 mt-4">
          {(!tasks || tasks.length === 0) ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Globe className="h-12 w-12 text-muted-foreground/30 mb-3" />
                <p className="text-muted-foreground">暂无采集任务</p>
                <p className="text-sm text-muted-foreground/60">使用 URL 爬取、适配器采集或 JustOneAPI 创建任务</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {tasks.map((task: any) => (
                <Card key={task.id}>
                  <CardContent className="flex items-center justify-between py-4">
                    <div className="flex items-center gap-4">
                      <Database className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium">{task.source_name || task.source || '采集任务'}</p>
                        <p className="text-xs text-muted-foreground">{task.created_at}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {statusBadge(task.status)}
                      {task.status === 'pending' && (
                        <Button size="sm" variant="outline">
                          <Play className="h-3 w-3 mr-1" /> 启动
                        </Button>
                      )}
                      {task.status === 'running' && (
                        <Button size="sm" variant="outline">
                          <Square className="h-3 w-3 mr-1" /> 停止
                        </Button>
                      )}
                    </div>
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
