import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Database, Globe, BarChart3, Brain, ArrowRight, Activity, 
  TrendingUp, Zap, Newspaper, ShoppingCart, Clock, CheckCircle,
  AlertCircle, Loader2,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { edaApi } from '@/api/analysis'
import { useAnalysisStore } from '@/stores/analysisStore'
import { useTaskStore } from '@/stores/taskStore'

const statCards = [
  { key: 'total_records', name: '数据总量', icon: Database, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  { key: 'stock_records', name: '股票数据', icon: TrendingUp, color: 'text-green-500', bg: 'bg-green-500/10' },
  { key: 'energy_records', name: '能源数据', icon: Zap, color: 'text-purple-500', bg: 'bg-purple-500/10' },
  { key: 'news_records', name: '新闻数据', icon: Newspaper, color: 'text-orange-500', bg: 'bg-orange-500/10' },
  { key: 'ecom_products', name: '电商数据', icon: ShoppingCart, color: 'text-red-500', bg: 'bg-red-500/10' },
]

const quickActions = [
  { name: '新建采集', href: '/crawl', icon: Globe, desc: '采集数据到平台' },
  { name: '数据分析', href: '/analysis', icon: BarChart3, desc: 'EDA 探索性分析' },
  { name: '训练模型', href: '/ml', icon: Brain, desc: '机器学习 Pipeline' },
  { name: '生成报告', href: '/reports', icon: Activity, desc: '自动分析报告' },
]

export default function Dashboard() {
  const { overview, setOverview } = useAnalysisStore()
  const { tasks } = useTaskStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        setLoading(true)
        const res = await edaApi.overview()
        setOverview(res.data)
      } catch (e) {
        console.error('Failed to fetch overview:', e)
      } finally {
        setLoading(false)
      }
    }
    fetchOverview()
  }, [setOverview])

  const formatNumber = (n: number | undefined) => {
    if (!n) return '0'
    if (n >= 10000) return (n / 10000).toFixed(1) + '万'
    return n.toLocaleString()
  }

  const statusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'running': return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
      case 'failed': return <AlertCircle className="w-4 h-4 text-red-500" />
      default: return <Clock className="w-4 h-4 text-yellow-500" />
    }
  }

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div>
        <h2 className="text-3xl font-bold tracking-tight">工作台</h2>
        <p className="text-muted-foreground">数据概览 · 任务管理 · 快捷操作</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {statCards.map((card) => {
          const value = overview?.[card.key as keyof typeof overview] || 0
          return (
            <Card key={card.key}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {card.name}
                </CardTitle>
                <div className={`p-1.5 rounded-md ${card.bg}`}>
                  <card.icon className={`h-4 w-4 ${card.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {loading ? <span className="text-muted-foreground">--</span> : formatNumber(value)}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* 快捷操作 + 最近任务 */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* 快捷操作 */}
        <Card>
          <CardHeader>
            <CardTitle>快捷操作</CardTitle>
            <CardDescription>一键进入常用功能</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {quickActions.map((action) => (
              <Link key={action.name} to={action.href}>
                <Button variant="outline" className="w-full justify-start h-auto py-3">
                  <div className={`p-1.5 rounded-md bg-primary/10 mr-3`}>
                    <action.icon className="h-4 w-4 text-primary" />
                  </div>
                  <div className="text-left">
                    <div className="font-medium">{action.name}</div>
                    <div className="text-xs text-muted-foreground">{action.desc}</div>
                  </div>
                  <ArrowRight className="h-4 w-4 ml-auto text-muted-foreground" />
                </Button>
              </Link>
            ))}
          </CardContent>
        </Card>

        {/* 最近任务 */}
        <Card>
          <CardHeader>
            <CardTitle>最近任务</CardTitle>
            <CardDescription>采集与分析任务状态</CardDescription>
          </CardHeader>
          <CardContent>
            {tasks.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <Globe className="h-10 w-10 mb-2 opacity-30" />
                <p className="text-sm">暂无任务</p>
                <Link to="/crawl">
                  <Button variant="link" size="sm" className="mt-1">创建第一个采集任务</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {tasks.slice(0, 5).map((task) => (
                  <div key={task.id} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div className="flex items-center gap-3">
                      {statusIcon(task.status)}
                      <span className="text-sm font-medium">{task.source_name}</span>
                    </div>
                    <Badge variant={task.status === 'completed' ? 'default' : 'secondary'} className="text-xs">
                      {task.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 系统信息 */}
      <Card>
        <CardHeader>
          <CardTitle>平台能力</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold text-primary">7</div>
              <div className="text-xs text-muted-foreground">数据适配器</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold text-primary">13</div>
              <div className="text-xs text-muted-foreground">ML 算法</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold text-primary">10</div>
              <div className="text-xs text-muted-foreground">图表类型</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold text-primary">3</div>
              <div className="text-xs text-muted-foreground">挖掘方法</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
