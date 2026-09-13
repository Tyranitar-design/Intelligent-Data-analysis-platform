import { create } from 'zustand'

interface Notification {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  title: string
  description?: string
  timestamp: number
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
}))
