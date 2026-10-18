import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The app calls the relative /api/v1. In development Vite forwards /api to the local backend; in production the
// backend serves the built app (frontend/dist) itself, so everything runs on one local origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
