import apiClient from './client'

// ==================== ML Pipeline ====================
export const mlApi = {
  // 算法
  listAlgorithms: () => apiClient.get('/ml/algorithms'),
  getAlgorithmInfo: (name: string) => apiClient.get(`/ml/algorithms/${name}`),
  
  // 训练
  train: (data: MLTrainRequest) => apiClient.post('/ml/train', data),
  
  // 模型管理
  listModels: () => apiClient.get('/ml/models'),
  getModel: (id: number) => apiClient.get(`/ml/models/${id}`),
  deleteModel: (id: number) => apiClient.delete(`/ml/models/${id}`),
  
  // 预测
  predict: (modelId: number, data: any[]) => apiClient.post('/ml/predict', { model_id: modelId, data }),
  
  // 评估
  evaluate: (modelId: number, data: any) => apiClient.post(`/ml/models/${modelId}/evaluate`, data),
}

// ==================== 类型定义 ====================
export interface MLTrainRequest {
  data?: any[]           // 内联数据
  dataset_id?: number    // 数据集ID
  target_column: string
  algorithm: string
  task_type: 'classification' | 'regression' | 'clustering'
  test_size?: number
  tuning?: {
    method: 'grid' | 'random' | 'optuna'
    n_trials?: number
  }
  cv_folds?: number
}

export interface MLModel {
  id: number
  algorithm: string
  task_type: string
  metrics: Record<string, number>
  created_at: string
  feature_importance?: Record<string, number>
}
