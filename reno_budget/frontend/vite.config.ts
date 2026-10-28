import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// Home Assistant ingress serves the app under a per-install path, so every asset URL must be
// relative ('./'), the router uses hash history and API calls never start with '/'.
export default defineConfig({
  base: './',
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: { '/api': 'http://127.0.0.1:8099' },
  },
  build: {
    chunkSizeWarningLimit: 1500,
  },
})
