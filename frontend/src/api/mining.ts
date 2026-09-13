import apiClient from './client'

// ==================== 数据挖掘 ====================
export const miningApi = {
  // 关联规则
  associationRules: (data: any) => apiClient.post('/mining/association', data),
  
  // 异常检测
  anomalyDetection: (data: any) => apiClient.post('/mining/anomaly', data),
  
  // 降维
  dimensionalityReduction: (data: any) => apiClient.post('/mining/reduction', data),
  
  // 方法列表
  listMethods: () => apiClient.get('/mining/methods'),
}
