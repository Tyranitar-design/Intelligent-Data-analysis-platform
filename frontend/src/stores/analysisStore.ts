import { create } from 'zustand'

export interface EDAResult {
  dataset_name: string
  overview: any
  data_quality: any
  missing_values: any
  correlations: any
  suggestions: any[]
}

export interface MLModel {
  id: number
  algorithm: string
  task_type: string
  evaluation: Record<string, number>
  feature_importance?: Record<string, number>
  training_time_seconds?: number
  cv_mean?: number
  created_at: string
}

interface AnalysisStore {
  // EDA 结果
  edaResults: Map<string, EDAResult>
  setEdaResult: (key: string, result: EDAResult) => void
  clearEdaResults: () => void
  
  // ML 模型列表
  mlModels: MLModel[]
  setMlModels: (models: MLModel[]) => void
  addMlModel: (model: MLModel) => void
  removeMlModel: (id: number) => void
  
  // 当前分析数据
  currentDataset: any | null
  setCurrentDataset: (data: any | null) => void

  // 最近一次 EDA 来源
  latestEdaSourceTable: string | null
  setLatestEdaSourceTable: (tableName: string | null) => void
  
  // 数据概览
  overview: {
    total_records: number
    stock_records: number
    energy_records: number
    news_records: number
    ecom_products: number
  } | null
  setOverview: (ov: any) => void
  
  // 加载
  loading: boolean
  setLoading: (loading: boolean) => void
}

export const useAnalysisStore = create<AnalysisStore>((set) => ({
  edaResults: new Map(),
  setEdaResult: (key, result) =>
    set((s) => {
      const m = new Map(s.edaResults)
      m.set(key, result)
      return { edaResults: m }
    }),
  clearEdaResults: () => set({ edaResults: new Map() }),
  
  mlModels: [],
  setMlModels: (models) => set({ mlModels: models }),
  addMlModel: (model) => set((s) => ({ mlModels: [model, ...s.mlModels] })),
  removeMlModel: (id) => set((s) => ({ mlModels: s.mlModels.filter((m) => m.id !== id) })),
  
  currentDataset: null,
  setCurrentDataset: (data) => set({ currentDataset: data }),

  latestEdaSourceTable: null,
  setLatestEdaSourceTable: (tableName) => set({ latestEdaSourceTable: tableName }),
  
  overview: null,
  setOverview: (ov) => set({ overview: ov }),
  
  loading: false,
  setLoading: (loading) => set({ loading }),
}))
