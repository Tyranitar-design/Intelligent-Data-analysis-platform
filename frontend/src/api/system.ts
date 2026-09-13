import apiClient from './client'

export const systemApi = {
  capabilities: () => apiClient.get('/capabilities'),
}
