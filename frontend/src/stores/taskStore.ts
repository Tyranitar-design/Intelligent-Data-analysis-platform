import { create } from 'zustand'

export interface CrawlTask {
  id: number
  source_name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
  created_at: string
  progress?: number
  result?: any
}

export interface AdapterInfo {
  name: string
  description: string
  available: boolean
  category: string
}

interface TaskStore {
  // 采集任务
  tasks: CrawlTask[]
  setTasks: (tasks: CrawlTask[]) => void
  addTask: (task: CrawlTask) => void
  updateTask: (id: number, patch: Partial<CrawlTask>) => void
  removeTask: (id: number) => void
  
  // 适配器
  adapters: AdapterInfo[]
  setAdapters: (adapters: AdapterInfo[]) => void
  
  // Celery
  celeryAvailable: boolean
  setCeleryAvailable: (available: boolean) => void
  
  // 加载状态
  loading: boolean
  setLoading: (loading: boolean) => void
}

export const useTaskStore = create<TaskStore>((set) => ({
  tasks: [],
  setTasks: (tasks) => set({ tasks }),
  addTask: (task) => set((s) => ({ tasks: [task, ...s.tasks] })),
  updateTask: (id, patch) =>
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === id ? { ...t, ...patch } : t)),
    })),
  removeTask: (id) => set((s) => ({ tasks: s.tasks.filter((t) => t.id !== id) })),
  
  adapters: [],
  setAdapters: (adapters) => set({ adapters }),
  
  celeryAvailable: false,
  setCeleryAvailable: (available) => set({ celeryAvailable: available }),
  
  loading: false,
  setLoading: (loading) => set({ loading }),
}))
