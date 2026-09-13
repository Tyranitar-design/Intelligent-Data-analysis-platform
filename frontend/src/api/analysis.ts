import apiClient from './client'

// ==================== EDA 分析 ====================
export const edaApi = {
  analyze: (data: any) => apiClient.post('/analysis/eda', data),
  statistics: (data: any) => apiClient.post('/analysis/statistics', data),
  overview: () => apiClient.get('/analysis/overview'),
  
  // Phase 2: 数据库数据
  dbData: (sourceType: string, params?: any) => apiClient.get(`/analysis/db/data/${sourceType}`, { params }),
  listDatasets: () => apiClient.get('/analysis/datasets'),
}

// ==================== 特征工程 ====================
export const featureApi = {
  engineer: (data: any) => apiClient.post('/analysis/feature-engineering', data),
  selectFeatures: (data: any) => apiClient.post('/analysis/feature-selection', data),
}

// ==================== 可视化 ====================
export const chartApi = {
  generate: (data: any) => apiClient.post('/analysis/chart', data),
  listTypes: () => apiClient.get('/analysis/chart/types'),
}

// ==================== 报告 ====================
export const reportApi = {
  generate: (params: { source_type: string; report_type?: string }) =>
    apiClient.post(`/reports/generate?source_type=${encodeURIComponent(params.source_type)}&report_type=${encodeURIComponent(params.report_type || 'eda')}`),
  generateFromTable: (params: { table_name: string; report_type?: string }) =>
    apiClient.post(`/reports/generate-from-table?table_name=${encodeURIComponent(params.table_name)}&report_type=${encodeURIComponent(params.report_type || 'eda')}`),
  list: () => apiClient.get('/reports'),
  get: (id: number) => apiClient.get(`/reports/${id}`),
  delete: (id: number) => apiClient.delete(`/reports/${id}`),
  exportHtml: (id: number) => apiClient.get(`/reports/${id}/export/html`),
}
