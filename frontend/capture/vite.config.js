import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  
  // Root directory for the capture app
  root: resolve(__dirname),
  
  // Public directory for static assets (manifest, sw, icons)
  publicDir: resolve(__dirname, 'public'),
  
  // Build configuration
  build: {
    outDir: resolve(__dirname, '../dist/capture'),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(__dirname, 'index.html'),
    },
  },
  
  // Dev server configuration
  server: {
    port: 5174, // Different port from main frontend (5173)
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  
  // Resolve aliases for shared code
  resolve: {
    alias: {
      '@shared': resolve(__dirname, '../src'),
      '@capture': resolve(__dirname, 'src'),
    },
  },
  
  // Base path for the PWA
  base: '/capture/',
});
