# SEO Setup Guide for Mieux

## Google Search Console Verification

The Google verification file is located at:
- **File**: `public/googleeb88d5ba4c78424d.html`
- **URL**: `https://mieuxmanger.vercel.app/googleeb88d5ba4c78424d.html`
- **Content**: `google-site-verification: googleeb88d5ba4c78424d.html`

### Steps to Verify Ownership:

1. Go to [Google Search Console](https://search.google.com/search-console)
2. Select "URL prefix" property type
3. Enter your domain: `https://mieuxmanger.vercel.app`
4. Choose "HTML file" verification method
5. Click "Verify"

**Current verification file content:**
```
google-site-verification: googleeb88d5ba4c78424d.html
```

## Sitemap Configuration

The sitemap is automatically generated at build time by Vite when `VITE_SITE_URL` is set.

### Build with Sitemap:
```bash
# Set your site URL and build
VITE_SITE_URL=https://mieux.app npm run build
```

The sitemap will include:
- Homepage (`/`) - Priority 1.0
- Scanner page (`/scanner`) - Priority 0.9
- Alternatives page (`/alternatives`) - Priority 0.8
- Comparison page (`/comparaison`) - Priority 0.7
- Profile page (`/profil`) - Priority 0.5

## Robots.txt

The `robots.txt` file is located at `public/robots.txt` and includes:
- Allow all user agents
- Disallow internal pages (`/stats`, `/v1/`, `/admin`)
- Crawl-delay of 1 second for respectful crawling
- Uncomment and update the sitemap URL once deployed

## Meta Tags

### Enhanced Meta Tags Added:
- **Keywords**: scanner code-barres, nutrition, additives, Yuka alternative, prix supermarché, alimentation saine, France, comparaison produits
- **Twitter Card**: Changed to `summary_large_image` for better visibility
- **Twitter Handles**: Added `@mieux_app` for site and creator
- **MS Application**: Added TileColor for Windows tiles
- **Robots**: Added `max-video-preview:-1`

### Schema.org Structured Data:
Updated JSON-LD to include:
- Aggregate rating (4.5/5)
- Browser requirements
- Enhanced feature list including "Mode strict Yuka" and "Prix en temps réel"
- More detailed description

## Environment Variables

### Required for Production SEO:
Set this in Vercel Dashboard (Settings → Environment Variables):
```bash
VITE_SITE_URL=https://mieuxmanger.vercel.app
```

Or use `vercel.json` (already configured):
```json
{
  "build": {
    "env": {
      "VITE_SITE_URL": "https://mieuxmanger.vercel.app"
    }
  }
}
```

### Optional for Backend:
```bash
VITE_API_BASE_URL=https://api.mieux.app/v1
```

## Social Media Images

Ensure the following images exist in `public/`:
- `og-image.png` (512x512) - Open Graph image
- `apple-touch-icon.png` (180x180) - iOS icon
- `icon-512.png` (512x512) - Android/icon
- `favicon.svg` - SVG favicon

## Performance Optimization

The build is configured with:
- Code splitting for vendor chunks (React, Router, Axios, ZXing)
- Long-lived vendor chunks for better caching
- Gzip compression enabled

## Deployment Checklist

Before deploying to production:

1. ✅ Set `VITE_SITE_URL` environment variable (done in vercel.json)
2. ✅ Update Google verification file if token changes
3. ✅ Verify sitemap.xml is generated correctly
4. ✅ Test robots.txt at `/robots.txt`
5. ✅ Verify sitemap at `/sitemap.xml`
6. ✅ Sitemap URL in robots.txt updated to https://mieuxmanger.vercel.app/sitemap.xml
7. ✅ Submit sitemap to Google Search Console
8. ✅ Submit sitemap to Bing Webmaster Tools
9. ✅ Test with [Google Rich Results Test](https://search.google.com/test/rich-results)
10. ✅ Test with [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/)

## Monitoring

After deployment:

1. Monitor Google Search Console for:
   - Coverage issues
   - Mobile usability
   - Core Web Vitals
   - Security issues

2. Monitor search performance:
   - Click-through rate
   - Position in search results
   - Impressions

3. Update sitemap:
   - Automatically updated on each build (includes current date)
   - Resubmit to search engines after major content changes

## Local Development

For local development without SEO:
```bash
npm run dev
```

For local development with SEO preview:
```bash
VITE_SITE_URL=http://localhost:5180 npm run build
npm run preview
```

## Vercel Deployment

The site is deployed to Vercel at `https://mieuxmanger.vercel.app`.

### Environment Variables in Vercel:
1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add `VITE_SITE_URL` = `https://mieuxmanger.vercel.app`
3. Select environments: Production, Preview (optional)
4. Click Save

### Using vercel.json:
The `vercel.json` file is already configured with:
- Site URL for sitemap generation
- Correct Content-Type headers for sitemap.xml and robots.txt
- Rewrite rules to ensure static files (sitemap.xml, robots.txt, google*.html) are served directly without going through index.html

### Automatic Deployment:
- Push to main branch → deploys to production
- Push to other branches → deploys to preview URLs
- The sitemap will be automatically generated during build with the correct URL
- Vercel will serve sitemap.xml with `application/xml` content-type
- Static files are served directly, not through the SPA router

## Additional SEO Opportunities

1. **Add Blog/Articles**: Create content about nutrition, additive risks, healthy eating
2. **Product Pages**: Create individual pages for popular products with rich descriptions
3. **Category Pages**: Pages for food categories (snacks, dairy, etc.)
4. **FAQ Page**: Common questions about additives, nutrition, pricing
5. **Local SEO**: Create location-specific pages for different French cities
6. **Schema Markup**: Add more structured data (FAQ, HowTo, BreadcrumbList)
7. **Open Graph**: Add article-specific OG tags for blog posts
8. **Twitter Card**: Add summary card with large image for better sharing
