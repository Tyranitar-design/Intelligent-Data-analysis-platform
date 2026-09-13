import apiClient from './client'

export interface SmokeScenario {
  scenario_id: string
  title: string
  description: string
  mode: 'local' | 'live-public' | 'live-assisted'
  requires_robots_check: boolean
  requires_auth: boolean
  requires_human: boolean
  preferred_strategy?: string | null
  platform?: string | null
  required_inputs: string[]
  post_steps: string[]
}

export interface SmokeRunResult {
  success: boolean
  scenario_id: string
  status: string
  stage: string
  requires_human: boolean
  dataset_saved: boolean
  analysis_passed: boolean
  report_passed: boolean
  crawl_strategy?: string | null
  robots: Record<string, any>
  artifacts: Record<string, any>
  memory_capture: {
    captured?: boolean
    capture_path?: string | null
    synced?: boolean
    sync_path?: string | null
    error?: string | null
  }
  notes: string[]
  error?: string | null
}

export interface AssistedSmokeRunResult extends SmokeRunResult {
  assisted_auth_state: string
  platform?: string | null
  continuation_token?: string | null
}

export const smokeApi = {
  scenarios: () => apiClient.get('/smoke/scenarios'),
  contracts: () => apiClient.get('/smoke/contracts'),
  run: (data: {
    scenario_id: string
    url?: string
    dataset_name?: string
    dataset_description?: string
    rows?: Array<Record<string, any>>
  }) => apiClient.post('/smoke/run', data),
  assistedStart: (data: { scenario_id: string; url: string }) => apiClient.post('/smoke/assisted/start', data),
  assistedContinue: (data: { continuation_token: string }) => apiClient.post('/smoke/assisted/continue', data),
}
