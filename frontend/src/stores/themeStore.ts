import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'dark' | 'light'

interface ThemeState {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

/**
 * 主题应用：同时设置 `.dark` 类与 `data-theme` 属性。
 *
 * 必须设类——Tailwind 的 `darkMode: ["class"]` 靠 `.dark` 选择器生效；
 * 只设 data-theme 属性的话，`dark:` 变体和深色 CSS 变量都不会被应用，
 * 表现为"切到深色却还是白底"。属性保留用于兼容按
 * `[data-theme="dark"]` 写的历史样式。
 */
function applyTheme(theme: Theme) {
  const root = document.documentElement
  root.classList.toggle('dark', theme === 'dark')
  root.setAttribute('data-theme', theme)
  root.style.colorScheme = theme
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'dark',
      toggleTheme: () =>
        set((state) => {
          const newTheme = state.theme === 'dark' ? 'light' : 'dark'
          applyTheme(newTheme)
          return { theme: newTheme }
        }),
      setTheme: (theme) => {
        applyTheme(theme)
        set({ theme })
      },
    }),
    {
      name: 'theme-storage',
      onRehydrateStorage: () => (state) => {
        if (state) applyTheme(state.theme)
      },
    }
  )
)
