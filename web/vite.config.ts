import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

const here = (p: string) => path.resolve(__dirname, p);

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@shared': here('../shared'),
      // shared/ has no node_modules of its own: resolve its dependencies from web/
      zustand: here('node_modules/zustand'),
      axios: here('node_modules/axios'),
    },
  },
  test: { environment: 'node', include: ['src/**/*.test.ts'] },
  build: {
    rollupOptions: {
      output: {
        // Long-lived vendor chunks: a new app build does not invalidate React/the router/the API client in the cache.
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return;
          if (id.includes('@zxing')) return 'zxing';
          if (id.includes('react-router')) return 'router';
          if (id.includes('axios')) return 'axios';
          if (/\/node_modules\/(react|react-dom|scheduler)\//.test(id)) return 'react';
        },
      },
    },
  },
  server: {
    port: 5180,
    fs: { allow: [here('..')] },
    proxy: {
      '/v1': {
        target: 'http://localhost:8010',
        changeOrigin: true,
      },
    },
  },
});
