import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';

export default defineConfig(() => {
  const backendHost = process.env.BACKEND_HOST || '127.0.0.1';
  const backendPort = process.env.BACKEND_PORT || '8000';
  const apiTarget = process.env.VITE_BACKEND_URL || `http://${backendHost}:${backendPort}`;

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/output': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/temp': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/jobs': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
