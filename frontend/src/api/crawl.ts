import apiClient from './client'

// ==================== 数据源 ====================
export const sourceApi = {
  list: () => apiClient.get('/crawl/sources'),
  create: (data: any) => apiClient.post('/crawl/sources', data),
  get: (id: number) => apiClient.get(`/crawl/sources/${id}`),
  delete: (id: number) => apiClient.delete(`/crawl/sources/${id}`),
}

// ==================== 采集任务 ====================
export const crawlApi = {
  listTasks: () => apiClient.get('/crawl/tasks'),
  createTask: (data: any) => apiClient.post('/crawl/tasks', data),
  getTask: (id: number) => apiClient.get(`/crawl/tasks/${id}`),
  startTask: (id: number) => apiClient.post(`/crawl/tasks/${id}/start`),
  stopTask: (id: number) => apiClient.post(`/crawl/tasks/${id}/stop`),
  deleteTask: (id: number) => apiClient.delete(`/crawl/tasks/${id}`),
  
  // Phase 2 新端点
  adapters: () => apiClient.get('/crawl/adapters'),
  adapterInfo: (name: string) => apiClient.get(`/crawl/adapters/${name}/info`),
  crawlAdapter: (name: string, params?: any) => apiClient.post(`/crawl/adapters/${name}/fetch`, params),
  
  // JustOneAPI
  justoneapiPlatforms: () => apiClient.get('/crawl/justoneapi/platforms'),
  justoneapiApis: (platform: string) => apiClient.get(`/crawl/justoneapi/platforms/${platform}/apis`),
  justoneapiCall: (data: any) => apiClient.post('/crawl/justoneapi/call', data),
  
  // 自定义爬虫
  customCrawl: (data: any) => apiClient.post('/crawl/custom', data),
  
  // Celery 任务
  celeryStatus: (taskId: string) => apiClient.get(`/crawl/celery/status/${taskId}`),
  celerySubmit: (source_type: string, priority: string = 'normal', config?: any) =>
    apiClient.post(`/crawl/celery/submit?source_type=${encodeURIComponent(source_type)}&priority=${encodeURIComponent(priority)}`, config || {}),
  celeryResult: (taskId: string) => apiClient.get(`/crawl/celery/result/${taskId}`),
  
  // robots.txt
  robotsCheck: (url: string) => apiClient.get(`/crawl/robots-check?url=${encodeURIComponent(url)}`),

  
  // 文件解析
  parseFile: (file_path: string, config?: any) => apiClient.post('/crawl/local/parse', config || {}, {
    params: { file_path },
  }),

  // ==================== Phase 4.6: 智能采集 ====================
  smartExtract: (data: { url: string; requirement: string; dynamic?: boolean; mode?: string; wait_for?: string; auto_scroll?: boolean; scroll_count?: number; click_selector?: string; click_count?: number }) =>
    apiClient.post('/crawl/smart/extract', data),

  // ==================== Phase 4.6: 多格式导入 ====================
  importFile: (data: { file_path: string; file_type?: string; sheet_name?: any; encoding?: string; delimiter?: string; table_index?: number }) =>
    apiClient.post('/crawl/import/file', data),

  // ==================== Phase 4.6: 数据集管理 ====================
  saveDataset: (data: { name: string; description?: string; columns: string[]; data: any[]; source_url?: string; source_type?: string }) =>
    apiClient.post('/crawl/smart/save', data),
  listDatasets: (limit?: number) => apiClient.get('/crawl/datasets', { params: { limit } }),
  getDatasetData: (table_name: string, limit?: number) =>
    apiClient.get(`/crawl/datasets/${table_name}/data`, { params: { limit } }),

  // ==================== Phase 4.5: URL 自由爬取 ====================
  urlProbe: (url: string) => apiClient.post('/crawl/url/probe', { url }),
  urlCrawl: (data: any) => apiClient.post('/crawl/url/crawl', data),
  urlCrawlPaginated: (data: any) => apiClient.post('/crawl/url/crawl/paginated', data),

  // ==================== Day 3: 登录态管理 ====================
  authPlatforms: () => apiClient.get('/crawl/auth/platforms'),
  authSessions: () => apiClient.get('/crawl/auth/sessions'),
  authLogin: (data: { platform: string; username: string; password: string; custom_url?: string; custom_selectors?: Record<string, string> }) =>
    apiClient.post('/crawl/auth/login', data),
  authCookie: (data: { platform: string; cookies: any[] }) => apiClient.post('/crawl/auth/cookie', data),
  authStatus: (platform: string, check_url?: string) => apiClient.get(`/crawl/auth/status/${platform}`, { params: { check_url } }),
  authLogout: (platform: string) => apiClient.delete(`/crawl/auth/logout/${platform}`),
  authHeaders: (platform: string) => apiClient.get(`/crawl/auth/headers/${platform}`),

  // ==================== Phase 4.5: 参数 Schema ====================
  paramSchemas: () => apiClient.get('/crawl/param-schemas'),
  paramSchema: (adapter: string) => apiClient.get(`/crawl/param-schemas/${adapter}`),
  validateParams: (adapter: string, params: any) => apiClient.post(`/crawl/param-schemas/${adapter}/validate`, params),
}

// ==================== 数据集 ====================
export const datasetApi = {
  list: () => apiClient.get('/analysis/datasets'),
  create: (data: any) => apiClient.post('/analysis/datasets', data),
  get: (id: number) => apiClient.get(`/analysis/datasets/${id}`),
  delete: (id: number) => apiClient.delete(`/analysis/datasets/${id}`),
  preview: (id: number, limit?: number) => apiClient.get(`/analysis/datasets/${id}/preview`, { params: { limit } }),
}
