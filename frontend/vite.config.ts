import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api goes to FastAPI, so the browser only ever sees one origin.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
