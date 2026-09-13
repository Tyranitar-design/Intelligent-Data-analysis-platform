import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  AlertCircle, CheckCircle2, Database, Globe, Key, Loader2, Moon, RefreshCw, ServerCog, Sun,
} from 'lucide-react'
import { useTheme } from '@/components/theme-provider'
import { systemApi } from '@/api/system'
import { extractApiError } from '@/api/crawl'
import { useAppStore } from '@/stores/appStore'

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(true)
  const [capabilities, setCapabilities] = useState<Record<string, any>>({})
  const [environment, setEnvironment] = useState<Record<string, any>>({})
  const [serviceName, setServiceName] = useState('智能数据分析平台')
  const [serviceVersion, setServiceVersion] = useState('v2.0.0')

  useEffect(() => {
    loadCapabilities()
  }, [])

  const loadCapabilities = async () => {
    try {
      setLoading(true)
      const res = await systemApi.capabilities()
      setCapabilities(res.data?.capabilities || {})
      setEnvironment(res.data?.environment || {})
      setServiceName(res.data?.service || '智能数据分析平台')
      setServiceVersion(res.data?.version ? `v${res.data.version}` : 'v2.0.0')
    } catch (e: any) {
      addNotification({ type: 'error', title: '系统状态加载失败', description: extractApiError(e) })
    } finally {
      setLoading(false)
    }
  }

  const coreCapabilities = useMemo(
    () => Object.entries(capabilities).filter(([, value]: any) => value?.category === 'core'),
    [capabilities],
  )

  const optionalCapabilities = useMemo(
    () => Object.entries(capabilities).filter(([, value]: any) => value?.category === 'optional'),
    [capabilities],
  )

  const envItems = useMemo(() => ([
    {
      key: 'database',
      label: '数据库',
      description: environment.database?.driver ? `${environment.database.driver} · ${environment.database.url_kind === 'local' ? '本地' : '远程'}` : '未检测',
      configured: Boolean(environment.database?.configured),
    },
    {
      key: 'queue',
      label: '任务队列',
      description: environment.queue?.host ? `${environment.queue.provider} · ${environment.queue.host}` : '未检测',
      configured: Boolean(environment.queue?.configured),
    },
    {
      key: 'storage',
      label: '对象存储',
      description: environment.storage?.endpoint ? `${environment.storage.provider} · ${environment.storage.endpoint}` : '未检测',
      configured: Boolean(environment.storage?.configured),
    },
    {
      key: 'integration',
      label: '外部集成',
      description: environment.integrations?.justoneapi_configured ? 'JustOneAPI 已配置' : 'JustOneAPI 未配置',
      configured: Boolean(environment.integrations?.justoneapi_configured),
    },
  ]), [environment])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">设置</h2>
          <p className="text-muted-foreground">平台配置 · API Key · 主题 · 系统状态</p>
        </div>
        <Button variant="outline" onClick={loadCapabilities} disabled={loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          刷新状态
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* 主题 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {theme === 'dark' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
              外观主题
            </CardTitle>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button variant={theme === 'light' ? 'default' : 'outline'} onClick={() => setTheme('light')}>
              <Sun className="h-4 w-4 mr-2" /> 浅色
            </Button>
            <Button variant={theme === 'dark' ? 'default' : 'outline'} onClick={() => setTheme('dark')}>
              <Moon className="h-4 w-4 mr-2" /> 深色
            </Button>
            <Button variant={theme === 'system' ? 'default' : 'outline'} onClick={() => setTheme('system')}>
              系统
            </Button>
          </CardContent>
        </Card>

        {/* API Keys */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" /> API 配置
            </CardTitle>
            <CardDescription>后端 .env 文件管理</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">JustOneAPI Token</span>
              <Badge variant="outline" className="text-xs">已配置</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Brave Search</span>
              <Badge variant="outline" className="text-xs">已配置</Badge>
            </div>
            <Separator />
            <p className="text-xs text-muted-foreground">
              API Key 在后端 .env 文件中管理，修改后需重启后端
            </p>
          </CardContent>
        </Card>

        {/* 核心能力 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ServerCog className="h-5 w-5" /> 核心能力
            </CardTitle>
            <CardDescription>当前主链默认启用的系统能力</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {coreCapabilities.length === 0 ? (
              <p className="text-sm text-muted-foreground">{loading ? '正在读取系统能力...' : '暂无能力状态数据'}</p>
            ) : (
              coreCapabilities.map(([name, item]: any) => (
                <div key={name} className="flex items-center justify-between text-sm">
                  <div>
                    <p>{item.label || name}</p>
                    <p className="text-xs text-muted-foreground">{item.path}</p>
                  </div>
                  <Badge variant="default" className="text-[10px] bg-green-500/10 text-green-600">
                    已启用
                  </Badge>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* 可选重模块 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" /> 可选高级能力
            </CardTitle>
            <CardDescription>按当前环境可用性动态挂载的重模块</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {optionalCapabilities.length === 0 ? (
              <p className="text-sm text-muted-foreground">{loading ? '正在读取高级能力...' : '暂无高级能力数据'}</p>
            ) : (
              optionalCapabilities.map(([name, item]: any) => (
                <div key={name} className="flex items-center justify-between text-sm">
                  <div>
                    <p>{item.label || name}</p>
                    <p className="text-xs text-muted-foreground">{item.path}</p>
                  </div>
                  {item.enabled ? (
                    <Badge variant="default" className="text-[10px] bg-green-500/10 text-green-600">
                      <CheckCircle2 className="mr-1 h-3 w-3" />
                      可用
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-[10px] text-amber-600">
                      <AlertCircle className="mr-1 h-3 w-3" />
                      按环境关闭
                    </Badge>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* 系统环境 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" /> 运行环境
            </CardTitle>
            <CardDescription>当前主线依赖配置的就绪情况</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {envItems.map((item) => (
              <div key={item.key} className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="text-xs text-muted-foreground">{item.description}</p>
                </div>
                {item.configured ? (
                  <Badge variant="default" className="bg-green-500/10 text-green-600">已配置</Badge>
                ) : (
                  <Badge variant="outline" className="text-amber-600">待配置</Badge>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* 系统信息 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" /> 系统信息
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-muted-foreground">服务</span><span>{serviceName}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">版本</span><span>{serviceVersion}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">前端</span><span>React 18 + shadcn/ui + Tailwind</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">后端</span><span>FastAPI + Celery + 数据主链</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">ML/DL/挖掘</span><span>按环境动态挂载</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">爬虫</span><span>适配器 + Smart v2 + 登录态</span></div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
