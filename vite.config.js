import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: true,           // allow network access to Vite
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:3001',
        changeOrigin: true,
      }
    }
  }
});