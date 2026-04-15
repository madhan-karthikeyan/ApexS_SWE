import { defineConfig, loadEnv, type ConfigEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig(({ mode }: ConfigEnv) => {
  const env = loadEnv(mode, __dirname, '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000'
  const allowedHosts = env.VITE_ALLOWED_HOSTS
    ? env.VITE_ALLOWED_HOSTS.split(',').map((host: string) => host.trim()).filter(Boolean)
    : true

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      allowedHosts,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
        '/health': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
  }
})