import apiClient from './client'

// ==================== DL Pipeline ====================
export const dlApi = {
  // 时序预测
  prophetForecast: (data: any) => apiClient.post('/dl/prophet', data),
  lstmForecast: (data: any) => apiClient.post('/dl/lstm', data),
  
  // NLP
  sentimentAnalysis: (data: any) => apiClient.post('/dl/sentiment', data),
  extractKeywords: (data: any) => apiClient.post('/dl/keywords', data),
  
  // 模型
  listModels: () => apiClient.get('/dl/models'),
}
