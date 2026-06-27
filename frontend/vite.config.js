/**
 * frontend/vite.config.js  (security-hardened revision)
 *
 * Security fixes applied
 * ----------------------
 * M6  – The personal LocalTunnel hostname "opthalmoai.loca.lt" (note: also
 *        misspelled) was hard-coded in allowedHosts, committing a developer's
 *        private tunnel URL to source control. It has been removed.
 *        Tunnel hostnames are now injected via the VITE_ALLOWED_HOSTS env var
 *        and documented in .env.example so no real hostnames are ever committed.
 *
 * +   – The /api proxy is retained (fixes the missing dev-proxy documented in
 *        ISSUES.md M2) so developers never need to set VITE_API_URL manually.
 *
 * +   – Proxy rewrite strips /api prefix, matching frontend/nginx.conf exactly,
 *        so dev and prod behaviour are identical.
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  /**
   * Allowed tunnel / custom hosts injected via environment variable.
   *
   * Usage in frontend/.env.local:
   *   VITE_ALLOWED_HOSTS=my-tunnel.loca.lt,another-host.ngrok.io
   *
   * Never commit real tunnel hostnames to this file.
   */
  const allowedHosts = (process.env.VITE_ALLOWED_HOSTS || '')
    .split(',')
    .map(h => h.trim())
    .filter(Boolean)

  /**
   * Backend target for the /api proxy in development.
   * Override in frontend/.env.local:
   *   VITE_DEV_BACKEND_URL=http://localhost:8000
   */
  const backendTarget = process.env.VITE_DEV_BACKEND_URL || 'http://localhost:8000'

  return {
    plugins: [react()],

    server: {
      // Only expose allowed hosts when explicitly configured
      ...(allowedHosts.length > 0 ? { allowedHosts } : {}),

      proxy: {
        /**
         * Dev proxy: /api/* → http://localhost:8000/*
         *
         * This mirrors frontend/nginx.conf exactly so there is no
         * divergence between development and production request paths.
         * Developers should call /api/predict etc., not the backend
         * directly, so CORS is never needed in development.
         */
        '/api': {
          target:      backendTarget,
          changeOrigin: true,
          rewrite:     path => path.replace(/^\/api/, ''),
          // Log proxy errors clearly instead of swallowing them
          configure:   (proxy) => {
            proxy.on('error', (err) => {
              console.error('[vite-proxy] Backend unreachable:', err.message)
            })
          },
        },
      },
    },

    build: {
      // Produce a source map only in non-production builds
      // (prevents exposing application logic in the browser in production)
      sourcemap: mode !== 'production',
      // Raise the chunk-size warning threshold for the ML-related deps
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        output: {
          // Split vendor code into a separate chunk for better caching
          manualChunks: {
            react:   ['react', 'react-dom'],
            ui:      ['lucide-react'],
            pdf:     ['jspdf', 'jspdf-autotable'],
          },
        },
      },
    },

    // Prevent Vite from leaking env vars that don't start with VITE_
    envPrefix: 'VITE_',
  }
})
