/**
 * 应用入口
 * ========
 *
 * 路由只保留六个核心页面——每个都对应采集链路里的一个真实环节。
 * 移除的页面（ML / DL / 挖掘 / 模型管理 / 旧数据浏览 / 验收中心）的能力
 * 已被后端新链路覆盖：分析与建模通过 /analytics 统一入口调用，
 * 界面上不再需要各自独立的页面。
 */
import { Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import MainLayout from '@/components/layout/MainLayout'
import DashboardPage from '@/pages/Dashboard'
import DiscoverPage from '@/pages/Discover'
import CollectPage from '@/pages/Collect'
import SchedulesPage from '@/pages/Schedules'
import DatasetsPage from '@/pages/Datasets'
import AnalyticsPage from '@/pages/Analytics'
import ReportsPage from '@/pages/Reports'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 30,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="discover" element={<DiscoverPage />} />
          <Route path="collect" element={<CollectPage />} />
          <Route path="schedules" element={<SchedulesPage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </QueryClientProvider>
  )
}
