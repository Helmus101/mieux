import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const here = (p: string) => path.resolve(__dirname, p);

/**
 * SEO: canonical, og:url and sitemap.xml must be absolute, and the domain is only known at build time.
 * Set VITE_SITE_URL (e.g. https://mieux.app) in the Vercel project; without it the page still ships,
 * with relative social image URLs and no sitemap, rather than pointing Google at a guessed domain.
 */
function seo(siteUrl: string) {
  const base = siteUrl.replace(/\/+$/, '');
  const abs = (p: string) => (base ? base + p : p);
  return {
    name: 'mieux-seo',
    transformIndexHtml(html: string) {
      const tags = [
        `<link rel="canonical" href="${abs('/')}" />`,
        `<meta property="og:url" content="${abs('/')}" />`,
      ].join('\n    ');
      return html.replace('%SEO_TAGS%', tags).replace(/%OG_IMAGE%/g, abs('/og-image.png'));
    },
    generateBundle() {
      if (!base) return;
      this.emitFile({
        type: 'asset',
        fileName: 'sitemap.xml',
        source: `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${base}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
</urlset>
`,
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, here('.'), 'VITE_');
  return {
    plugins: [react(), seo(env.VITE_SITE_URL || '')],
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
  };
});
