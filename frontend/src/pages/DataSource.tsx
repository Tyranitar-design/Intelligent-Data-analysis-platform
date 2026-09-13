import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  TrendingUp, Newspaper, Cloud, BookOpen, MessageSquare,
  RefreshCw, Search, Globe, Loader2, CheckCircle, XCircle,
  Zap, ExternalLink,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { crawlApi } from '@/api/crawl'
import { useAppStore } from '@/stores/appStore'

interface Adapter {
  name: string
  description: string
  category: string
  available: boolean
  icon: any
  color: string
  platforms?: string[]
  free: boolean
}

// 静态适配器信息 (后端可能不返回图标等 UI 信息)
const adapterMeta: Record<string, Partial<Adapter>> = {
  eastmoney: { icon: TrendingUp, color: 'text-red-500', category: '金融', description: '东方财富 — 股票/基金/行情数据', free: true },
  exchangerate: { icon: TrendingUp, color: 'text-green-500', category: '金融', description: 'ExchangeRate — 汇率数据', free: true },
  kr36: { icon: Newspaper, color: 'text-blue-500', category: '新闻', description: '36氪 — 科技创投资讯', free: true },
  cls: { icon: Newspaper, color: 'text-orange-500', category: '新闻', description: '财联社 — 金融快讯', free: true },
  justoneapi: { icon: MessageSquare, color: 'text-pink-500', category: '社交/电商', description: 'JustOneAPI — 27平台200+API (小红书/抖音/微博/淘宝等)', free: false, platforms: ['小红书', '抖音', '微博', '淘宝', 'B站', '京东', '知乎'] },
  openweather: { icon: Cloud, color: 'text-sky-500', category: '天气', description: 'OpenWeather — 全球天气预报', free: true },
  wikipedia: { icon: BookOpen, color: 'text-amber-500', category: '研究', description: 'Wikipedia — 百科知识', free: true },
}

export default function DataSourcePage() {
  const [adapters, setAdapters] = useState<Adapter[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const { addNotification } = useAppStore()

  useEffect(() => {
    fetchAdapters()
  }, [])

  const fetchAdapters = async () => {
    try {
      setLoading(true)
      const res = await crawlApi.adapters()
      const data = res.data?.adapters || res.data || []
      
      // 合并后端状态 + 前端元数据
      const merged: Adapter[] = Object.keys(adapterMeta).map((name) => {
        const backend = data.find((a: any) => a.name === name)
        return {
          name,
          description: adapterMeta[name]?.description || backend?.description || name,
          category: adapterMeta[name]?.category || backend?.category || '其他',
          available: backend?.available ?? true,
          icon: adapterMeta[name]?.icon || Globe,
          color: adapterMeta[name]?.color || 'text-gray-500',
          platforms: adapterMeta[name]?.platforms,
          free: adapterMeta[name]?.free ?? true,
        }
      })
      
      setAdapters(merged)
    } catch (e) {
      console.error('Failed to fetch adapters:', e)
      // 降级: 仅用前端元数据
      const fallback: Adapter[] = Object.entries(adapterMeta).map(([name, meta]) => ({
        name,
        description: meta.description || name,
        category: meta.category || '其他',
        available: false,
        icon: meta.icon || Globe,
        color: meta.color || 'text-gray-500',
        platforms: meta.platforms,
        free: meta.free ?? true,
      }))
      setAdapters(fallback)
      addNotification({ type: 'warning', title: '后端未启动', description: '使用静态数据源信息' })
    } finally {
      setLoading(false)
    }
  }

  const filtered = adapters.filter((a) =>
    a.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    a.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    a.category.includes(searchTerm),
  )

  const categories = [...new Set(adapters.map((a) => a.category))]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">数据源</h2>
          <p className="text-muted-foreground">7 个适配器 · 覆盖金融/新闻/社交/电商/天气/研究</p>
        </div>
        <Button variant="outline" onClick={fetchAdapters} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      {/* 搜索 */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="搜索数据源..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* 按分类展示 */}
      {categories.map((cat) => {
        const catAdapters = filtered.filter((a) => a.category === cat)
        if (catAdapters.length === 0) return null
        return (
          <div key={cat}>
            <h3 className="text-lg font-semibold mb-3">{cat}</h3>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {catAdapters.map((adapter) => (
                <Card key={adapter.name} className="relative overflow-hidden">
                  <div className={`absolute top-0 right-0 w-20 h-20 opacity-5 ${adapter.color}`}>
                    <adapter.icon className="w-full h-full" />
                  </div>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-muted">
                          <adapter.icon className={`h-5 w-5 ${adapter.color}`} />
                        </div>
                        <div>
                          <CardTitle className="text-base">{adapter.name}</CardTitle>
                          <CardDescription className="text-xs">{adapter.category}</CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {adapter.available ? (
                          <Badge variant="default" className="bg-green-500/10 text-green-600 border-green-200">
                            <CheckCircle className="w-3 h-3 mr-1" /> 可用
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-red-500/10 text-red-500 border-red-200">
                            <XCircle className="w-3 h-3 mr-1" /> 离线
                          </Badge>
                        )}
                        {adapter.free && (
                          <Badge variant="outline" className="text-xs">免费</Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3">{adapter.description}</p>
                    {adapter.platforms && (
                      <div className="flex flex-wrap gap-1">
                        {adapter.platforms.map((p) => (
                          <Badge key={p} variant="secondary" className="text-xs">{p}</Badge>
                        ))}
                      </div>
                    )}
                    <Link to="/crawl" className="block mt-3">
                      <Button variant="outline" size="sm" className="w-full">
                        <ExternalLink className="h-3 w-3 mr-1" /> 开始采集
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

