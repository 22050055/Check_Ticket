import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api':  { target: 'https://check-ticket-1hyd.onrender.com', changeOrigin: true },
      '/ws':   { target: 'wss://check-ticket-1hyd.onrender.com',   ws: true, changeOrigin: true },
    }
  }
})
