import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true, proxy: { '/api': process.env.API_TARGET || 'http://127.0.0.1:8000' } },
  build: { rollupOptions: { output: { manualChunks(id) {
    if (!id.includes('node_modules')) return
    if (id.includes('/echarts/') || id.includes('/zrender/')) return 'charts'
    if (/\/(react|react-dom|scheduler|react-router|react-router-dom)\//.test(id)) return 'vendor'
    if (/\/(motion|framer-motion|motion-dom|motion-utils)\//.test(id)) return 'motion'
  } } } },
})
