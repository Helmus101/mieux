import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { execSync } from 'child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs';
import { BLOG, BLOG_DESC } from './src/blogMeta';

const here = (p: string) => path.resolve(__dirname, p);

/** "1.0.0+31e0d0e": shown in the profile and sent with error reports, so a report can be matched to a build. */
function appVersion(): string {
  const v = JSON.parse(readFileSync(here('package.json'), 'utf8')).version as string;
  const sha = process.env.VERCEL_GIT_COMMIT_SHA || process.env.GITHUB_SHA || (() => { try { return execSync('git rev-parse HEAD', { stdio: ['ignore', 'pipe', 'ignore'] }).toString(); } catch { return ''; } })();
  return sha ? `${v}+${sha.trim().slice(0, 7)}` : v;
}

/**
 * SEO: canonical, og:url and sitemap.xml must be absolute, and the domain is only known at build time.
 * Set VITE_SITE_URL (e.g. https://mieux.app) in the Vercel project; without it the page still ships,
 * with relative social image URLs and no sitemap, rather than pointing Google at a guessed domain.
 */
function seo(siteUrl: string) {
  const base = siteUrl.replace(/\/+$/, '');
  const abs = (p: string) => (base ? base + p : p);
  const esc = (x: string) => x.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  const ld = (o: unknown) => `<script type="application/ld+json">${JSON.stringify(o).replace(/</g, '\\u003c')}</script>`;
  const ORG = { '@type': 'Organization', name: 'Mieux', url: abs('/'), logo: abs('/icon-512.png') };
  /** The shell with one page's own head: what a crawler reads before any script runs. */
  const pageHtml = (html: string, o: { title: string; desc: string; path: string; type: string; ld: unknown }) => html
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(o.title)}</title>`)
    .replace(/(<meta name="description" content=")[^"]*(")/, `$1${esc(o.desc)}$2`)
    .replace(/<link rel="canonical" href="[^"]*" \/>/, `<link rel="canonical" href="${abs(o.path)}" />`)
    .replace(/<meta property="og:url" content="[^"]*" \/>/, `<meta property="og:url" content="${abs(o.path)}" />`)
    .replace(/<meta property="og:type" content="[^"]*" \/>/, `<meta property="og:type" content="${o.type}" />`)
    .replace(/(<meta (?:property="og:title"|name="twitter:title") content=")[^"]*(")/g, `$1${esc(o.title)}$2`)
    .replace(/(<meta (?:property="og:description"|name="twitter:description") content=")[^"]*(")/g, `$1${esc(o.desc)}$2`)
    .replace('</head>', `${ld(o.ld)}\n  </head>`);
  const blogPosts = BLOG;

  return {
    name: 'mieux-seo',
    transformIndexHtml(html: string) {
      const tags = [
        `<link rel="canonical" href="${abs('/')}" />`,
        `<meta property="og:url" content="${abs('/')}" />`,
      ].join('\n    ');
      const home = ld({ '@context': 'https://schema.org', '@graph': [
        { '@type': 'WebSite', name: 'Mieux', url: abs('/'), inLanguage: 'fr' },
        { ...ORG },
        { '@type': 'SoftwareApplication', name: 'Mieux', applicationCategory: 'LifestyleApplication', operatingSystem: 'Web', url: abs('/'), offers: { '@type': 'Offer', price: '0', priceCurrency: 'EUR' } },
      ] });
      return html.replace('%SEO_TAGS%', tags + '\n    ' + home).replace(/%OG_IMAGE%/g, abs('/og-image.png'));
    },
    generateBundle() {
      if (!base) return;

      const urls = [
        `<url><loc>${base}/</loc><lastmod>${blogPosts[0].iso}</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>`,
        `<url><loc>${base}/blog</loc><lastmod>${blogPosts[0].iso}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>`,
        ...['mentions-legales', 'confidentialite', 'cgu'].map(s => `<url><loc>${base}/${s}</loc><changefreq>yearly</changefreq><priority>0.2</priority></url>`),
        ...blogPosts.map(post => `<url><loc>${base}/blog/${post.slug}</loc><lastmod>${post.iso}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>`),
      ];
      this.emitFile({
        type: 'asset',
        fileName: 'sitemap.xml',
        source: `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join('\n  ')}
</urlset>
`,
      });
    },
    closeBundle() {
      if (!base) return;
      const shellPath = here('dist/index.html');
      if (!existsSync(shellPath)) return;
      const shell = readFileSync(shellPath, 'utf8');
      const emit = (rel: string, source: string) => { const f = here('dist/' + rel); mkdirSync(path.dirname(f), { recursive: true }); writeFileSync(f, source); };
      emit('blog/index.html', pageHtml(shell, { title: 'Blog · Mieux', desc: BLOG_DESC, path: '/blog', type: 'website', ld: { '@context': 'https://schema.org', '@type': 'Blog', name: 'Blog Mieux', url: abs('/blog'), inLanguage: 'fr', publisher: ORG } }));
      for (const b of blogPosts) {
        emit(`blog/${b.slug}/index.html`, pageHtml(shell, { title: `${b.title} · Mieux`, desc: b.excerpt, path: `/blog/${b.slug}`, type: 'article', ld: { '@context': 'https://schema.org', '@type': 'BlogPosting', headline: b.title, description: b.excerpt, datePublished: b.iso, dateModified: b.iso, inLanguage: 'fr', mainEntityOfPage: abs(`/blog/${b.slug}`), image: abs('/og-image.png'), author: ORG, publisher: ORG } }));
      }
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, here('.'), 'VITE_');
  return {
    plugins: [react(), seo(env.VITE_SITE_URL || '')],
    define: { __APP_VERSION__: JSON.stringify(appVersion()) },
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
            if (id.includes('zustand')) return 'zustand';
          },
        },
      },
      chunkSizeWarningLimit: 600,
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
