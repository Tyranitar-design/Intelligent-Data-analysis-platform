import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import {
  Activity,
  ChevronLeft,
  Database,
  FileBarChart,
  Globe2,
  LayoutDashboard,
  Menu,
  Moon,
  Radar,
  RefreshCw,
  Sun,
  X,
} from 'lucide-react'

import { Toaster } from '@/components/ui/sonner'
import ParticleField from '@/components/visual/ParticleField'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/stores/appStore'
import { useThemeStore } from '@/stores/themeStore'

type NavItem = {
  to: string
  label: string
  icon: typeof LayoutDashboard
  hint: string
}

type NavGroup = {
  title: string
  items: NavItem[]
}

/**
 * 导航按"用户在做什么"分组，而不是按后端模块名。
 * 用户想的是"我要把这个站点采下来"，不是"我要用 crawl 模块"。
 */
const NAV_GROUPS: NavGroup[] = [
  {
    title: '总览',
    items: [{ to: '/', label: '工作台', icon: LayoutDashboard, hint: '平台概览' }],
  },
  {
    title: '采集链路',
    items: [
      { to: '/discover', label: '站点分析', icon: Radar, hint: '输入 URL 判别可采性' },
      { to: '/collect', label: '采集任务', icon: Globe2, hint: '方案、任务与进度' },
    ],
  },
  {
    title: '数据资产',
    items: [{ to: '/datasets', label: '数据集', icon: Database, hint: '物化后的数据集' }],
  },
  {
    title: '分析与交付',
    items: [
      { to: '/analytics', label: '数据分析', icon: Activity, hint: 'EDA 与挖掘' },
      { to: '/reports', label: '分析报告', icon: FileBarChart, hint: '报告与导出' },
    ],
  },
]

const COLLAPSE_KEY = 'webinsight.sidebar.collapsed'

export default function MainLayout() {
  const location = useLocation()
  const { theme, setTheme } = useThemeStore()
  const capabilities = useAppStore((s) => s.capabilities)
  const capabilitiesError = useAppStore((s) => s.capabilitiesError)
  const fetchCapabilities = useAppStore((s) => s.fetchCapabilities)

  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(COLLAPSE_KEY) === '1',
  )
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0')
  }, [collapsed])

  useEffect(() => {
    if (!capabilities && !capabilitiesError) void fetchCapabilities()
  }, [capabilities, capabilitiesError, fetchCapabilities])

  // 路由切换时收起抽屉，避免"点了链接抽屉还开着"的割裂感
  useEffect(() => {
    setDrawerOpen(false)
  }, [location.pathname])

  // 抽屉打开时锁定页面滚动
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [drawerOpen])

  const allItems = NAV_GROUPS.flatMap((g) => g.items)
  const activeItem = allItems.find(
    (item) =>
      item.to === location.pathname ||
      (item.to !== '/' && location.pathname.startsWith(item.to)),
  )

  const online = Boolean(capabilities)
  const isDark = theme === 'dark'

  return (
    <div className="relative flex min-h-screen bg-background text-foreground">
      <ParticleField />

      {/* ---------------- 侧边栏（lg 及以上常驻） ---------------- */}
      <aside
        className={cn(
          'glass sticky top-0 z-30 hidden h-screen shrink-0 flex-col border-r transition-[width] duration-300 lg:flex',
          collapsed ? 'w-[68px]' : 'w-[232px]',
        )}
      >
        <Brand collapsed={collapsed} />

        <nav className="no-scrollbar flex-1 overflow-y-auto overflow-x-hidden px-2.5 py-3">
          <NavGroups collapsed={collapsed} />
        </nav>

        <div className="border-t border-border/60 p-2.5">
          {!collapsed && <ServiceBadge online={online} error={capabilitiesError} />}
          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            className="flex w-full items-center justify-center gap-2 rounded-lg px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
            aria-label={collapsed ? '展开侧边栏' : '折叠侧边栏'}
          >
            <ChevronLeft
              className={cn('h-4 w-4 transition-transform', collapsed && 'rotate-180')}
            />
            {!collapsed && <span>折叠</span>}
          </button>
        </div>
      </aside>

      {/* ---------------- 移动端抽屉 ---------------- */}
      <AnimatePresence>
        {drawerOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="absolute inset-0 bg-background/70 backdrop-blur-sm"
              onClick={() => setDrawerOpen(false)}
            />
            <motion.aside
              initial={{ x: -260 }}
              animate={{ x: 0 }}
              exit={{ x: -260 }}
              transition={{ type: 'spring', stiffness: 400, damping: 36 }}
              className="glass absolute inset-y-0 left-0 flex w-[248px] flex-col border-r"
            >
              <div className="relative">
                <Brand collapsed={false} />
                <button
                  type="button"
                  onClick={() => setDrawerOpen(false)}
                  className="absolute right-3 top-5 grid h-7 w-7 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
                  aria-label="关闭导航"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <nav className="no-scrollbar flex-1 overflow-y-auto px-2.5 py-3">
                <NavGroups collapsed={false} />
              </nav>
              <div className="border-t border-border/60 p-2.5">
                <ServiceBadge online={online} error={capabilitiesError} />
              </div>
            </motion.aside>
          </div>
        )}
      </AnimatePresence>

      {/* ---------------- 主区 ---------------- */}
      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        <header className="glass sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b px-4 sm:px-5">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground lg:hidden"
              aria-label="打开导航"
            >
              <Menu className="h-4 w-4" />
            </button>
            <h1 className="truncate text-[0.95rem] font-semibold tracking-tight">
              {activeItem?.label ?? '工作台'}
            </h1>
            {activeItem && (
              <span className="hidden truncate text-xs text-muted-foreground md:inline">
                {activeItem.hint}
              </span>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              onClick={() => setTheme(isDark ? 'light' : 'dark')}
              className="grid h-8 w-8 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
              aria-label="切换主题"
            >
              {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <button
              type="button"
              onClick={() => void fetchCapabilities()}
              className="grid h-8 w-8 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
              aria-label="刷新服务状态"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </header>

        <main className="min-w-0 flex-1 px-4 py-4 sm:px-5 sm:py-5">
          <Outlet />
        </main>
      </div>

      <Toaster />
    </div>
  )
}

function Brand({ collapsed }: { collapsed: boolean }) {
  return (
    <div className="flex h-16 items-center gap-2.5 border-b border-border/60 px-4">
      <div className="relative grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary/15 text-primary">
        <Radar className="h-4 w-4" strokeWidth={2.2} />
        <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-primary animate-pulse-soft" />
      </div>
      {!collapsed && (
        <div className="min-w-0 leading-tight">
          <div className="truncate text-[0.9rem] font-semibold tracking-tight">
            WebInsight
          </div>
          <div className="truncate text-[0.68rem] text-muted-foreground">
            智能数据采集与分析
          </div>
        </div>
      )}
    </div>
  )
}

function NavGroups({ collapsed }: { collapsed: boolean }) {
  return (
    <>
      {NAV_GROUPS.map((group) => (
        <div key={group.title} className="mb-4">
          {!collapsed && (
            <div className="section-title px-2.5 pb-1.5">{group.title}</div>
          )}
          <ul className="space-y-0.5">
            {group.items.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  title={collapsed ? item.label : item.hint}
                  className={({ isActive }) =>
                    cn(
                      'group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[0.83rem] transition-colors',
                      isActive
                        ? 'bg-primary/10 font-medium text-primary'
                        : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <motion.span
                          layoutId="nav-active-bar"
                          className="absolute bottom-1.5 left-0 top-1.5 w-[3px] rounded-r bg-primary"
                          transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                        />
                      )}
                      <item.icon className="h-4 w-4 shrink-0" strokeWidth={2} />
                      {!collapsed && <span className="truncate">{item.label}</span>}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </>
  )
}

function ServiceBadge({ online, error }: { online: boolean; error: string | null }) {
  return (
    <div className="mb-2 flex items-center justify-between rounded-lg bg-muted/40 px-2.5 py-1.5">
      <span className="section-title">服务</span>
      <span
        className={cn('badge-dot', online ? 'badge-ok' : 'badge-warn')}
        title={error ?? undefined}
      >
        {online ? '在线' : '离线'}
      </span>
    </div>
  )
}
