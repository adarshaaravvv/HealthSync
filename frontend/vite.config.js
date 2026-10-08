import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // proxy keeps the browser talking to one origin, so no CORS surprises on demo day
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
