import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

const uiPort = Number(process.env.AGENTS_MEMORY_UI_PORT ?? '10000')
const apiProxyTarget =
  process.env.AGENTS_MEMORY_API_PROXY_TARGET ??
  `http://localhost:${process.env.AGENTS_MEMORY_API_PORT ?? '10100'}`

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: uiPort,
    strictPort: true,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
})
