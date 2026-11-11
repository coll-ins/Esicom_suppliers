import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// In development, /ledger-api goes to the local Django server. In production the
// Vercel rewrite in vercel.json does the same job, so cookies stay first-party.
export default defineConfig({
  // Served from the website's Vercel project at /dashboard/.
  base: '/dashboard/',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/ledger-api': {
        target: 'http://127.0.0.1:8000',
        rewrite: (path) => path.replace(/^\/ledger-api/, '/api/ledger'),
      },
    },
  },
  test: { environment: 'node', include: ['src/**/*.test.js'] },
})
