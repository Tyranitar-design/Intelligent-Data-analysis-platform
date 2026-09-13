import apiClient from './client'

// ==================== Phase 4.5: 数据浏览 API ====================
export const dataBrowserApi = {
  // 列出所有数据表
  listTables: () => apiClient.get('/data/tables'),

  // 获取表结构
  tableSchema: (tableName: string) => apiClient.get(`/data/tables/${tableName}/schema`),

  // 查询数据（分页 + 搜索 + 筛选 + 排序）
  queryTable: (tableName: string, params: {
    page?: number
    size?: number
    search?: string
    sort?: string
    order?: string
    filter_column?: string
    filter_value?: string
  }) => apiClient.get(`/data/tables/${tableName}/rows`, { params }),

  // 导出数据
  exportTable: (tableName: string, params: {
    format?: string
    search?: string
    filter_column?: string
    filter_value?: string
    max_rows?: number
  }) => apiClient.get(`/data/tables/${tableName}/export`, {
    params,
    responseType: 'blob',
  }),

  // 获取表统计
  tableStats: (tableName: string) => apiClient.get(`/data/tables/${tableName}/stats`),

  // 数据概览
  overview: () => apiClient.get('/data/overview'),
}
