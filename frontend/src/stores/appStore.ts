import { create } from 'zustand'

interface Notification {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  title: string
  description?: string
  timestamp: number
}

export interface CapabilityEntry {
  enabled: boolean
  category: string
  label: string
  path?: string
  reason?: string
}

export interface CapabilitiesPayload {
  status: string
  service: string
  version: string
  capabilities: Record<string, CapabilityEntry>
}

interface AppStore {
  // 侧边栏
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void

  // 通知
  notifications: Notification[]
  addNotification: (n: Omit<Notification, 'id' | 'timestamp'>) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void

  // 全局加载
  globalLoading: boolean
  setGlobalLoading: (loading: boolean) => void

  // 平台能力状态（后端 /capabilities，用于顶栏在线指示与系统页）
  capabilities: CapabilitiesPayload | null
  capabilitiesError: string | null
  fetchCapabilities: () => Promise<void>
}

let notifId = 0

export const useAppStore = create<AppStore>((set) => ({
  // 侧边栏
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  // 通知
  notifications: [],
  addNotification: (n) =>
    set((s) => ({
      notifications: [...s.notifications, { ...n, id: String(++notifId), timestamp: Date.now() }],
    })),
  removeNotification: (id) =>
    set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) })),
  clearNotifications: () => set({ notifications: [] }),

  // 全局加载
  globalLoading: false,
  setGlobalLoading: (loading) => set({ globalLoading: loading }),

  // 平台能力状态
  capabilities: null,
  capabilitiesError: null,
  fetchCapabilities: async () => {
    try {
      // 注意：/capabilities 挂在根路径而非 /api/v1 下
      const response = await fetch('/capabilities')
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const payload = (await response.json()) as CapabilitiesPayload
      set({ capabilities: payload, capabilitiesError: null })
    } catch (error) {
      set({
        capabilities: null,
        capabilitiesError: error instanceof Error ? error.message : '无法连接后端',
      })
    }
  },
}))
