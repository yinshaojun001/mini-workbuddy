import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    host: '127.0.0.1',
    port: 5174,
    proxy: { '/api': process.env.FORTUNE_API_TARGET || 'http://127.0.0.1:8001' },
  },
  test: { exclude: ['tests/e2e/**', 'node_modules/**'] },
})
