# Production Readiness Audit Report
**Date:** November 2, 2026
**Project:** Mieux (FoodIQ)
**Status:** ⚠️ CRITICAL ISSUES FOUND - NOT READY FOR PRODUCTION

---

## 🔴 CRITICAL SECURITY ISSUES

### 1. **JWT Secret Key Hardcoded Default**
**Severity:** CRITICAL
**Location:** `backend/app/auth.py:10`
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
```
**Issue:** Default secret key is hardcoded and weak. If JWT_SECRET_KEY is not set, the app uses an insecure default.
**Risk:** Any attacker can forge JWT tokens and impersonate users.
**Fix Required:**
- MUST set strong JWT_SECRET_KEY in Fly.io environment variables
- Minimum 32 characters, random, stored securely
- No deployment without this set

### 2. **CORS Configuration Too Permissive**
**Severity:** HIGH
**Location:** `backend/fly.toml:11`
```toml
ALLOWED_ORIGINS = '*'
```
**Issue:** Wildcard CORS allows any origin to access the API.
**Risk:** Cross-origin attacks, CSRF vulnerabilities.
**Fix Required:**
```toml
ALLOWED_ORIGINS = 'https://mieuxmanger.vercel.app,https://mieux.app'
```

### 3. **Admin Endpoint Unprotected in Default Config**
**Severity:** HIGH
**Location:** `backend/app/main.py:917-925`
**Issue:** `/v1/people` endpoint exposes user data. Only protected by ADMIN_KEY header, but if ADMIN_KEY is not set, the endpoint returns 404 (hides the endpoint but doesn't properly secure data).
**Risk:** If ADMIN_KEY is leaked or weak, user data is exposed.
**Fix Required:**
- Set strong ADMIN_KEY in Fly.io environment
- Consider removing this endpoint entirely if not needed
- Add IP whitelist for admin access

### 4. **Usage Tracking Salt Default**
**Severity:** MEDIUM
**Location:** `backend/app/main.py:255,265`
```python
salt = os.getenv("USAGE_SALT") or os.getenv("JWT_SECRET_KEY") or "mieux-usage"
```
**Issue:** Falls back to hardcoded "mieux-usage" if no salt set.
**Risk:** Weak hashing of visitor tracking data.
**Fix Required:**
- Set USAGE_SALT in environment
- Or ensure JWT_SECRET_KEY is always set

---

## 🟡 SECURITY CONCERNS

### 5. **Rate Limiting - Good But Could Be Tighter**
**Status:** ✅ IMPLEMENTED
**Details:**
- All endpoints have rate limiting (5-60/minute)
- Uses slowapi with IP-based limiting
- **Concern:** Some endpoints allow 60/minute which might be high for sensitive operations
**Recommendation:**
- Reduce sensitive endpoints to 10-20/minute
- Consider user-based rate limiting in addition to IP-based
- Add rate limit headers to responses

### 6. **Authentication - Basic Implementation**
**Status:** ⚠️ PLACEHOLDER
**Details:**
- No password hashing (login is email-only placeholder)
- No password verification
- JWT tokens valid for 30 days (ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60)
**Risk:** If real auth is added without password hashing, passwords stored in plaintext
**Fix Required:**
- Implement proper password hashing (bcrypt/argon2)
- Reduce token expiry to 7 days or less
- Add refresh token mechanism
- Add password reset flow

### 7. **SQL Injection - Protected by ORM**
**Status:** ✅ SAFE
**Details:**
- Uses SQLAlchemy ORM (parameterized queries)
- No raw SQL string concatenation found
- Good practice using ORM methods

### 8. **XSS Protection - Basic**
**Status:** ⚠️ NEEDS REVIEW
**Details:**
- Backend returns data as JSON (safe)
- Frontend uses React (built-in XSS protection)
- **Concern:** Blog content uses `dangerouslySetInnerHTML` in BlogPost.tsx
**Risk:** If blog content is ever user-generated, XSS vulnerability
**Fix Required:**
- Sanitize HTML content (use DOMPurify)
- Or use markdown instead of raw HTML

---

## 🟢 GOOD SECURITY PRACTICES

### ✅ Environment Variables
- `.env` in `.gitignore` (not committed)
- `.env.example` provided
- Uses `python-dotenv` for local development

### ✅ Rate Limiting
- All endpoints rate-limited
- Uses slowapi library
- IP-based tracking

### ✅ HTTPS Enforcement
- Fly.io config: `force_https = true`
- Good practice

### ✅ Database
- Uses ORM (SQLAlchemy)
- No raw SQL injection risk
- Connection pooling (implied by SQLAlchemy)

---

## 📊 SCALABILITY ANALYSIS

### Current Architecture
```
Web (Vercel) → Backend (Fly.io shared-cpu-1x, 1GB RAM) → Database
```

### Database
- Current: SQLite (single file)
- **Issue:** SQLite is NOT suitable for production with hundreds of users
- **Concurrency:** SQLite has write-locking issues
- **Performance:** No connection pooling benefits
- **Backup:** Manual file-based (not robust)

**CRITICAL FIX REQUIRED:**
```toml
# fly.toml or environment
DATABASE_URL = postgresql://user:pass@host:port/dbname
```

### Backend Resources
- Fly.io: `shared-cpu-1x`, `1GB` memory
- **Capacity:** ~100-200 concurrent users max
- **Issue:** Not enough for "hundreds of users"
- **Recommendation:** Upgrade to `shared-cpu-2x` or `dedicated-cpu-1x` with 2GB RAM

### API Performance
- Single-instance deployment
- No load balancing
- No caching layer
- **Recommendation:**
  - Add Redis for caching (product lookups, session data)
  - Consider CDN for static assets (already using Vercel)
  - Add database connection pooling

### Database Indexing
- Quick index exists (`off_quick.db`) for alternatives
- **Good:** Optimized for category-based searches
- **Concern:** May need indexes on frequently queried columns in user data

---

## 🔍 SEO AUDIT

### ✅ Good SEO Practices
1. **Meta Tags:** Comprehensive (title, description, keywords, author)
2. **Open Graph:** Complete (title, type, image, url)
3. **Twitter Cards:** Implemented (summary_large_image)
4. **Structured Data:** JSON-LD Schema.org
5. **Sitemap:** Generated dynamically with blog URLs
6. **Robots.txt:** Configured
7. **Canonical URLs:** Set correctly
8. **Blog Content:** 5 French articles with rich content

### ⚠️ SEO Improvements Needed
1. **Blog Content:**
   - ❌ No schema.org markup for blog posts (BlogPosting)
   - ❌ No meta descriptions per blog post
   - ❌ No internal linking between blog posts
   - ❌ No breadcrumb navigation

2. **Performance:**
   - ⚠️ Need Lighthouse audit
   - ⚠️ Need Core Web Vitals monitoring
   - ⚠️ Need image optimization (use WebP, lazy loading)

3. **Social:**
   - ❌ No social sharing buttons
   - ❌ No Open Graph images per blog post

### Recommendations
```typescript
// Add to BlogPost.tsx
useEffect(() => {
  document.title = `${post.title} | Mieux`;
  document.querySelector('meta[name="description"]')?.setAttribute('content', post.excerpt);
  // Add BlogPosting schema
}, [post]);
```

---

## 🚀 PRODUCTION READINESS CHECKLIST

### Critical (Must Fix Before Launch)
- [ ] Set strong JWT_SECRET_KEY in Fly.io environment
- [ ] Set proper ALLOWED_ORIGINS (not wildcard)
- [ ] Set strong ADMIN_KEY or remove admin endpoint
- [ ] Migrate from SQLite to PostgreSQL
- [ ] Upgrade Fly.io resources (min shared-cpu-2x, 2GB RAM)
- [ ] Add proper password hashing if authentication is real
- [ ] Reduce JWT token expiry to 7 days

### High Priority
- [ ] Add Redis caching layer
- [ ] Add database connection pooling configuration
- [ ] Add monitoring (Sentry, error tracking)
- [ ] Add uptime monitoring (Pingdom, UptimeRobot)
- [ ] Add database backup automation
- [ ] Add CDN for product images (if any)
- [ ] Implement proper password reset flow
- [ ] Add email service for auth (SendGrid/Mailgun)

### Medium Priority
- [ ] Add blog post schema.org markup
- [ ] Add social sharing buttons
- [ ] Add Open Graph images per blog post
- [ ] Add internal linking between blog posts
- [ ] Add breadcrumb navigation
- [ ] Run Lighthouse audit and fix issues
- [ ] Add Core Web Vitals monitoring
- [ ] Add analytics (Google Analytics 4)
- [ ] Add GDPR compliance banner
- [ ] Add privacy policy page
- [ ] Add terms of service page

### Low Priority
- [ ] Add A/B testing framework
- [ ] Add feature flags
- [ ] Add analytics dashboard
- [ ] Add user feedback system
- [ ] Add notification system

---

## 📈 SCALABILITY RECOMMENDATIONS

### For Hundreds of Users
**Current Stack Upgrade:**
1. **Database:** PostgreSQL (managed on Fly.io or Railway)
2. **Backend:** Fly.io `shared-cpu-2x` with 2GB RAM
3. **Caching:** Redis (Fly.io Redis)
4. **Monitoring:** Sentry for errors, New Relic for performance
5. **Load Testing:** Use k6 or Locust to test with 500+ concurrent users

### Architecture Improvements
```
Current:
Vercel → Fly.io (single instance) → SQLite

Recommended:
Vercel → Fly.io (2 instances, load balanced) → PostgreSQL + Redis
```

### Expected Capacity
- **Current:** ~100 concurrent users
- **With PostgreSQL:** ~500 concurrent users
- **With PostgreSQL + Redis:** ~1000+ concurrent users
- **With load balancing:** 2000+ concurrent users

---

## 🔐 SECURITY SCORE: 4/10

### Critical Issues: 4
### High Issues: 2
### Medium Issues: 2
### Good Practices: 5

**Overall Assessment:** NOT READY FOR PRODUCTION

---

## 📝 IMMEDIATE ACTION ITEMS

### Before Launch (Required)
1. Set environment variables in Fly.io:
   ```bash
   flyctl secrets set JWT_SECRET_KEY=<strong-32-char-random>
   flyctl secrets set ADMIN_KEY=<strong-32-char-random>
   flyctl secrets set USAGE_SALT=<strong-32-char-random>
   flyctl secrets set DATABASE_URL=postgresql://...
   ```

2. Update fly.toml:
   ```toml
   [env]
     ALLOWED_ORIGINS = 'https://mieuxmanger.vercel.app'
   
   [[vm]]
     size = 'shared-cpu-2x'
     memory = '2gb'
   ```

3. Update backend auth:
   - Implement password hashing (bcrypt)
   - Reduce token expiry to 7 days
   - Add rate limit headers

4. Migrate database:
   ```bash
   # Create PostgreSQL database
   # Run migrations
   # Import data from SQLite
   # Test thoroughly
   ```

### After Launch (Within 1 Week)
1. Add monitoring (Sentry)
2. Add uptime monitoring
3. Set up database backups
4. Run load testing
5. Add analytics

---

## ✅ CONCLUSION

**The app is NOT ready for production with hundreds of users.**

**Critical blockers:**
1. Weak JWT secret key
2. Wildcard CORS
3. SQLite database (not production-ready)
4. Insufficient backend resources
5. Basic authentication implementation

**Time to production-ready:** 2-3 days of focused work on critical issues.

**Recommended approach:**
1. Fix all critical security issues (4 hours)
2. Migrate to PostgreSQL (4 hours)
3. Upgrade Fly.io resources (10 minutes)
4. Add monitoring (2 hours)
5. Load test and optimize (4 hours)

**Total estimated time:** 14-16 hours of focused work.
