// vite.config.js
import { defineConfig } from 'vite';

export default defineConfig({
  base: '/wordnet/',

  // Dev server (local only)
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      // /api -> your Node server on 3001 in dev
      '/api': {
        target: 'http://127.0.0.1:3001',
        changeOrigin: true,
      },
    },
  },

  build: {
    outDir: 'dist',
    sourcemap: true, // handy for debugging the live site
  },
});