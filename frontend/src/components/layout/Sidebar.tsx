import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/stores/appStore'
import {
  LayoutDashboard,
  Database,
  Globe,
  Table,
  BarChart3,
  Brain,
  Network,
  Pickaxe,
  LineChart,
  FileText,
  Upload,
  Settings,
  ChevronLeft,
  Sparkles,
  ShieldCheck,
} from 'lucide-react'

const navigation = [
  { name: '工作台', href: '/', icon: LayoutDashboard, group: '核心' },
  { name: '数据源', href: '/sources', icon: Database, group: '数据' },
  { name: '数据采集', href: '/crawl', icon: Globe, group: '数据' },
  { name: '数据浏览', href: '/data', icon: Table, group: '数据', badge: 'NEW' },
  { name: '数据导入', href: '/import', icon: Upload, group: '数据', badge: 'NEW' },
  { name: '数据分析', href: '/analysis', icon: BarChart3, group: '分析', badge: 'EDA' },
  { name: '模型训练', href: '/ml', icon: Brain, group: '分析', badge: 'ML' },
  { name: '深度学习', href: '/dl', icon: Network, group: '分析', badge: 'DL' },
  { name: '数据挖掘', href: '/mining', icon: Pickaxe, group: '分析' },
  { name: '可视化', href: '/visualization', icon: LineChart, group: '输出' },
  { name: '报告中心', href: '/reports', icon: FileText, group: '输出' },
  { name: '验收中心', href: '/smoke', icon: ShieldCheck, group: '输出', badge: 'SMOKE' },
  { name: '设置', href: '/settings', icon: Settings, group: '系统' },
]

const groups = ['核心', '数据', '分析', '输出', '系统']

export function Sidebar() {
  const location = useLocation()
  const { sidebarOpen, toggleSidebar } = useAppStore()

  return (
    <div
      className={cn(
        'flex flex-col border-r bg-card transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-16',
      )}
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-4 border-b justify-between">
        {sidebarOpen && (
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary" />
            <span className="text-lg font-bold bg-gradient-to-r from-primary to-purple-500 bg-clip-text text-transparent">
              数据分析平台
            </span>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronLeft className={cn('w-4 h-4 transition-transform', !sidebarOpen && 'rotate-180')} />
        </button>
      </div>

      {/* 导航 */}
      <nav className="flex-1 px-2 py-4 space-y-4 overflow-auto">
        {groups.map((group) => {
          const items = navigation.filter((n) => n.group === group)
          if (items.length === 0) return null
          return (
            <div key={group}>
              {sidebarOpen && (
                <p className="px-3 mb-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
                  {group}
                </p>
              )}
              <div className="space-y-0.5">
                {items.map((item) => {
                  const isActive =
                    item.href === '/'
                      ? location.pathname === '/'
                      : location.pathname.startsWith(item.href)
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      title={!sidebarOpen ? item.name : undefined}
                      className={cn(
                        'flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                        isActive
                          ? 'bg-primary/10 text-primary border border-primary/20'
                          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                        !sidebarOpen && 'justify-center px-0',
                      )}
                    >
                      <item.icon className={cn('w-5 h-5 shrink-0', sidebarOpen && 'mr-3')} />
                      {sidebarOpen && (
                        <>
                          <span className="flex-1">{item.name}</span>
                          {item.badge && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-mono">
                              {item.badge}
                            </span>
                          )}
                        </>
                      )}
                    </Link>
                  )
                })}
              </div>
            </div>
          )
        })}
      </nav>

      {/* 底部信息 */}
      {sidebarOpen && (
        <div className="p-4 border-t">
          <p className="text-xs text-muted-foreground">v2.0.0 Enterprise</p>
        </div>
      )}
    </div>
  )
}
