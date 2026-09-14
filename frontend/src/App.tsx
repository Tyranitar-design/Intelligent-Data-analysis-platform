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
import SitesPage from '@/pages/Sites'
import CollectPage from '@/pages/Collect'
import JobDetailPage from '@/pages/JobDetail'
import SchedulesPage from '@/pages/Schedules'
import CompliancePage from '@/pages/Compliance'
import AuditPage from '@/pages/Audit'
import MonitorPage from '@/pages/Monitor'
import IntegrationsPage from '@/pages/Integrations'
import DatasetsPage from '@/pages/Datasets'
import DatasetDetailPage from '@/pages/DatasetDetail'
import ComparePage from '@/pages/Compare'
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
          <Route path="sites" element={<SitesPage />} />
          <Route path="collect" element={<CollectPage />} />
          <Route path="collect/:jobId" element={<JobDetailPage />} />
          <Route path="schedules" element={<SchedulesPage />} />
          <Route path="compliance" element={<CompliancePage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="monitor" element={<MonitorPage />} />
          <Route path="integrations" element={<IntegrationsPage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="datasets/:id" element={<DatasetDetailPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </QueryClientProvider>
  )
}
