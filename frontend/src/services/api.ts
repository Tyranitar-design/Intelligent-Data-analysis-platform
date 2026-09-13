import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

// ==================== Data Source API ====================
export const sourceApi = {
  list: () => api.get('/crawl/sources'),
  create: (data: any) => api.post('/crawl/sources', data),
  get: (id: number) => api.get(`/crawl/sources/${id}`),
  delete: (id: number) => api.delete(`/crawl/sources/${id}`),
}

// ==================== Crawler API ====================
export const crawlApi = {
  listTasks: () => api.get('/crawl/tasks'),
  createTask: (data: any) => api.post('/crawl/tasks', data),
  getTask: (id: number) => api.get(`/crawl/tasks/${id}`),
  startTask: (id: number) => api.post(`/crawl/tasks/${id}/start`),
  stopTask: (id: number) => api.post(`/crawl/tasks/${id}/stop`),
}

// ==================== Analysis API ====================
export const analysisApi = {
  eda: (sourceType: string) => api.post(`/analysis/eda/${sourceType}`),
  statistics: (sourceType: string, columns?: string) =>
    api.post(`/analysis/statistics/${sourceType}${columns ? `?columns=${columns}` : ''}`),
  chart: (sourceType: string, chartType: string, x: string, y?: string) =>
    api.post(`/analysis/chart/${sourceType}?chart_type=${chartType}&x=${encodeURIComponent(x)}${y ? `&y=${encodeURIComponent(y)}` : ''}`),
  listDatasets: () => api.get('/analysis/datasets'),
  createDataset: (data: any) => api.post('/analysis/datasets', data),
  deleteDataset: (id: number) => api.delete(`/analysis/datasets/${id}`),
  getVisualizations: () => api.get('/analysis/visualizations'),
}

// ==================== ML API ====================
export const mlApi = {
  listAlgorithms: () => api.get('/ml/algorithms'),
  listModels: () => api.get('/ml/models'),
  getModel: (id: number) => api.get(`/ml/models/${id}`),
  deleteModel: (id: number) => api.delete(`/ml/models/${id}`),
  train: (data: any) => api.post('/ml/train/enhanced', data),
  trainFromDb: (data: any) => api.post('/ml/train/db', data),
  predict: (modelId: number, data: any[]) => api.post('/ml/predict', { model_id: modelId, data }),
}

// ==================== Local Data API ====================
export const localDataApi = {
  listFiles: (platform?: string, keyword?: string) => 
    api.get('/data/files', { params: { platform, keyword } }),
  previewFile: (filename: string) => api.get(`/data/preview/${filename}`),
  loadFile: (filename: string, config?: any) => api.post(`/data/load/${filename}`, config),
  getSample: (filename: string, limit?: number) => api.get(`/data/sample/${filename}`, { params: { limit } }),
}

// ==================== DL API ====================
export const dlApi = {
  listModels: () => api.get('/dl/models'),
  train: (data: any) => api.post('/dl/train', data),
}

// ==================== Mining API ====================
export const miningApi = {
  listMethods: () => api.get('/mining/methods'),
  analyze: (data: any) => api.post('/mining/analyze', data),
}

// ==================== Reports API ====================
export const reportApi = {
  list: () => api.get('/reports/'),
  generate: (sourceType: string, reportType: string, modelId?: number) =>
    api.post(`/reports/generate?source_type=${sourceType}&report_type=${reportType}${modelId ? `&model_id=${modelId}` : ''}`),
  get: (id: number) => api.get(`/reports/${id}`),
  delete: (id: number) => api.delete(`/reports/${id}`),
}

export default api