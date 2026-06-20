import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// M4: no personal/dev-machine hostnames committed here anymore. If you need to expose
// the dev server through a tunnel (LocalTunnel, ngrok, etc.), set VITE_ALLOWED_HOSTS as a
// comma-separated list in frontend/.env.local, e.g. VITE_ALLOWED_HOSTS=my-tunnel.loca.lt
const allowedHosts = (process.env.VITE_ALLOWED_HOSTS || '')
  .split(',')
  .map(h => h.trim())
  .filter(Boolean)

export default defineConfig({
  plugins: [react()],
  server: {
    ...(allowedHosts.length > 0 ? { allowedHosts } : {}),
    // M2: dev proxy for /api so the frontend can always call a relative `/api/...` URL,
    // matching frontend/nginx.conf in production, without needing CORS configured on the
    // backend or VITE_API_URL set per-developer.
    proxy: {
      '/api': {
        target: process.env.VITE_DEV_BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
