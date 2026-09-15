import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // 与 scripts/run-dev.ps1 保持一致（该脚本也显式传 --port 5173）
    port: 5173,
    proxy: {
      // 后端根路径下的端点也要代理：新首页会 fetch('/capabilities')，
      // 只代理 /api 的话这个请求会打到 Vite 自己身上并 404
      '/capabilities': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/mcp': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 把体积大、更新频率低的依赖拆成独立 chunk：首屏只加载必要部分，
    // 且这些 chunk 的哈希不随业务代码变更，能稳定命中浏览器缓存。
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'motion-vendor': ['motion'],
        },
      },
    },
    chunkSizeWarningLimit: 700,
  },
})
