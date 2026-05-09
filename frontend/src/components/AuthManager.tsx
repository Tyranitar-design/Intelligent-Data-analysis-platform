import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  LogIn, LogOut, CheckCircle, AlertCircle, Loader2, KeyRound,
  Globe, Cookie, Shield, Trash2, RefreshCw, Eye, EyeOff,
} from 'lucide-react'
import { crawlApi } from '@/api/crawl'
import { useAppStore } from '@/stores/appStore'

// 支持的平台列表
const SUPPORTED_PLATFORMS = [
  { value: 'zhihu', label: '知乎', icon: '📚' },
  { value: 'weibo', label: '微博', icon: '📱' },
  { value: 'douban', label: '豆瓣', icon: '🎬' },
  { value: 'bilibili', label: 'B站', icon: '📺' },
  { value: 'xiaohongshu', label: '小红书', icon: '📕' },
]

interface AuthSession {
  platform: string
  has_session: boolean
  cookies_count: number
  expires_at?: string
}

export default function AuthManager() {
  const { addNotification } = useAppStore()
  const [sessions, setSessions] = useState<AuthSession[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('login')

  // 登录表单
  const [selectedPlatform, setSelectedPlatform] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loggingIn, setLoggingIn] = useState(false)

  // Cookie 导入
  const [cookiePlatform, setCookiePlatform] = useState('')
  const [cookieJson, setCookieJson] = useState('')
  const [importingCookie, setImportingCookie] = useState(false)

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const res = await crawlApi.authSessions()
      if (res.data?.sessions) {
        setSessions(res.data.sessions)
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: '加载失败', description: e.message })
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async () => {
    if (!selectedPlatform || !username || !password) {
      addNotification({ type: 'warning', title: '请填写完整信息' })
      return
    }

    setLoggingIn(true)
    try {
      const res = await crawlApi.authLogin({
        platform: selectedPlatform,
        username,
        password,
      })

      if (res.data?.success) {
        addNotification({
          type: 'success',
          title: '登录成功',
          description: `${res.data.platform} | ${res.data.cookies_count} 个 Cookie`,
        })
        setUsername('')
        setPassword('')
        loadSessions()
      } else {
        addNotification({
          type: 'error',
          title: '登录失败',
          description: res.data?.error || '未知错误',
        })
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: '登录异常', description: e.message })
    } finally {
      setLoggingIn(false)
    }
  }

  const handleCookieImport = async () => {
    if (!cookiePlatform || !cookieJson.trim()) {
      addNotification({ type: 'warning', title: '请填写完整信息' })
      return
    }

    setImportingCookie(true)
    try {
      let cookies
      try {
        cookies = JSON.parse(cookieJson)
        if (!Array.isArray(cookies)) {
          // 可能是单个对象，包装成数组
          cookies = [cookies]
        }
      } catch {
        addNotification({ type: 'error', title: 'Cookie 格式错误', description: '请输入有效的 JSON' })
        return
      }

      const res = await crawlApi.authCookie({
        platform: cookiePlatform,
        cookies,
      })

      if (res.data?.success) {
        addNotification({
          type: 'success',
          title: 'Cookie 导入成功',
          description: `${cookiePlatform} | ${res.data.cookies_count} 个 Cookie`,
        })
        setCookieJson('')
        loadSessions()
      } else {
        addNotification({
          type: 'error',
          title: '导入失败',
          description: res.data?.error || '未知错误',
        })
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: '导入异常', description: e.message })
    } finally {
      setImportingCookie(false)
    }
  }

  const handleLogout = async (platform: string) => {
    try {
      const res = await crawlApi.authLogout(platform)
      if (res.data?.success) {
        addNotification({ type: 'success', title: '已登出', description: platform })
        loadSessions()
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: '登出失败', description: e.message })
    }
  }

  const handleCheckStatus = async (platform: string) => {
    try {
      setLoading(true)
      const res = await crawlApi.authStatus(platform)
      if (res.data?.is_logged_in) {
        addNotification({
          type: 'success',
          title: '登录状态有效',
          description: `${platform} | ${res.data.message}`,
        })
      } else {
        addNotification({
          type: 'warning',
          title: '登录状态无效',
          description: `${platform} | ${res.data.message || '请重新登录'}`,
        })
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: '检测失败', description: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-primary" />
          登录态管理
        </CardTitle>
        <CardDescription>
          管理各平台登录状态，支持自动登录和 Cookie 导入
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="login">
              <LogIn className="w-4 h-4 mr-1" /> 自动登录
            </TabsTrigger>
            <TabsTrigger value="cookie">
              <Cookie className="w-4 h-4 mr-1" /> Cookie 导入
            </TabsTrigger>
            <TabsTrigger value="sessions">
              <KeyRound className="w-4 h-4 mr-1" /> 会话管理
            </TabsTrigger>
          </TabsList>

          {/* 自动登录 */}
          <TabsContent value="login" className="space-y-4 mt-4">
            <div className="space-y-3">
              <div className="space-y-1">
                <Label>选择平台</Label>
                <div className="grid grid-cols-5 gap-2">
                  {SUPPORTED_PLATFORMS.map((p) => (
                    <button
                      key={p.value}
                      onClick={() => setSelectedPlatform(p.value)}
                      className={`
                        flex flex-col items-center gap-1 p-3 rounded-lg border text-sm cursor-pointer
                        transition-colors hover:bg-accent
                        ${selectedPlatform === p.value
                          ? 'border-primary bg-primary/10 text-primary font-medium'
                          : 'border-border hover:border-primary/50'
                        }
                      `}
                    >
                      <span className="text-xl">{p.icon}</span>
                      <span>{p.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1">
                <Label>用户名 / 手机号 / 邮箱</Label>
                <Input
                  placeholder="输入账号"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <Label>密码</Label>
                <div className="relative">
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="输入密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <Button
                className="w-full"
                onClick={handleLogin}
                disabled={loggingIn || !selectedPlatform || !username || !password}
              >
                {loggingIn ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <LogIn className="w-4 h-4 mr-2" />
                )}
                开始登录
              </Button>
            </div>
          </TabsContent>

          {/* Cookie 导入 */}
          <TabsContent value="cookie" className="space-y-4 mt-4">
            <div className="space-y-3">
              <div className="space-y-1">
                <Label>选择平台</Label>
                <div className="grid grid-cols-5 gap-2">
                  {SUPPORTED_PLATFORMS.map((p) => (
                    <button
                      key={p.value}
                      onClick={() => setCookiePlatform(p.value)}
                      className={`
                        flex flex-col items-center gap-1 p-3 rounded-lg border text-sm cursor-pointer
                        transition-colors hover:bg-accent
                        ${cookiePlatform === p.value
                          ? 'border-primary bg-primary/10 text-primary font-medium'
                          : 'border-border hover:border-primary/50'
                        }
                      `}
                    >
                      <span className="text-xl">{p.icon}</span>
                      <span>{p.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1">
                <Label>Cookie JSON</Label>
                <textarea
                  className="w-full h-40 p-3 rounded-md border bg-background text-sm font-mono"
                  placeholder={`[\n  {\n    "name": "session_id",\n    "value": "xxx",\n    "domain": ".zhihu.com",\n    "path": "/"\n  }\n]`}
                  value={cookieJson}
                  onChange={(e) => setCookieJson(e.target.value)}
                />
              </div>

              <Button
                className="w-full"
                onClick={handleCookieImport}
                disabled={importingCookie || !cookiePlatform || !cookieJson.trim()}
              >
                {importingCookie ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Cookie className="w-4 h-4 mr-2" />
                )}
                导入 Cookie
              </Button>
            </div>
          </TabsContent>

          {/* 会话管理 */}
          <TabsContent value="sessions" className="space-y-4 mt-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">已保存的会话</h4>
              <Button variant="outline" size="sm" onClick={loadSessions} disabled={loading}>
                <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </Button>
            </div>

            {sessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <KeyRound className="w-8 h-8 mb-2 opacity-30" />
                <p className="text-sm">暂无登录会话</p>
                <p className="text-xs">使用自动登录或 Cookie 导入添加</p>
              </div>
            ) : (
              <ScrollArea className="h-64">
                <div className="space-y-2">
                  {sessions.map((session) => (
                    <div
                      key={session.platform}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="text-xl">
                          {SUPPORTED_PLATFORMS.find((p) => p.value === session.platform)?.icon || '🌐'}
                        </div>
                        <div>
                          <p className="font-medium">
                            {SUPPORTED_PLATFORMS.find((p) => p.value === session.platform)?.label || session.platform}
                          </p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Badge variant={session.has_session ? 'default' : 'secondary'} className="text-xs">
                              {session.has_session ? (
                                <CheckCircle className="w-3 h-3 mr-1" />
                              ) : (
                                <AlertCircle className="w-3 h-3 mr-1" />
                              )}
                              {session.has_session ? '有效' : '无效'}
                            </Badge>
                            <span>{session.cookies_count} 个 Cookie</span>
                            {session.expires_at && (
                              <span>过期: {new Date(session.expires_at).toLocaleString()}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCheckStatus(session.platform)}
                        >
                          <RefreshCw className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleLogout(session.platform)}
                        >
                          <Trash2 className="w-4 h-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
