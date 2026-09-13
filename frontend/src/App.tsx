import { Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/components/theme-provider'
import { Toaster } from '@/components/ui/toaster'

import MainLayout from '@/components/layout/MainLayout'
import Dashboard from '@/pages/Dashboard'
import DataSourcePage from '@/pages/DataSource'
import CrawlPage from '@/pages/Crawl'
import DataBrowserPage from '@/pages/DataBrowser'
import DatasetPage from '@/pages/Dataset'
import AnalysisPage from '@/pages/Analysis'
import MLPage from '@/pages/ML'
import DLPage from '@/pages/DL'
import MiningPage from '@/pages/Mining'
import ModelPage from '@/pages/Model'
import VisualizationPage from '@/pages/Visualization'
import ReportsPage from '@/pages/Reports'
import ReportPage from '@/pages/Report'
import ImportPage from '@/pages/ImportPage'
import SettingsPage from '@/pages/Settings'
import SmokeCenterPage from '@/pages/SmokeCenter'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="system" storageKey="idp-theme">
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="sources" element={<DataSourcePage />} />
            <Route path="crawl" element={<CrawlPage />} />
            <Route path="data" element={<DataBrowserPage />} />
            <Route path="datasets" element={<DatasetPage />} />
            <Route path="analysis" element={<AnalysisPage />} />
            <Route path="ml" element={<MLPage />} />
            <Route path="dl" element={<DLPage />} />
            <Route path="mining" element={<MiningPage />} />
            <Route path="models" element={<ModelPage />} />
            <Route path="visualization" element={<VisualizationPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="report" element={<ReportPage />} />
            <Route path="import" element={<ImportPage />} />
            <Route path="smoke" element={<SmokeCenterPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster />
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
