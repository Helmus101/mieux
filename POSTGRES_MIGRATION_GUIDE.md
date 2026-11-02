# PostgreSQL Migration Guide

## Current Status
- ✅ Security secrets set on Fly.io (JWT_SECRET_KEY, ADMIN_KEY, USAGE_SALT)
- ✅ Fly.io resources upgraded to shared-cpu-2x/2GB
- ✅ CORS restricted to specific domains
- ✅ JWT token expiry reduced to 7 days
- ⚠️ Still using SQLite (not production-ready)

## PostgreSQL Setup Options

### Option 1: Fly.io Managed PostgreSQL (Recommended)

**Run these commands manually in your terminal:**

```bash
cd backend
flyctl pg create --name mieux-db --region cdg
```

This will create a managed PostgreSQL database. Fly.io will prompt for:
- Organization selection
- Plan selection (Starter or Professional)
- Confirm creation

After creation, Fly.io will provide a connection URL. Set it as a secret:

```bash
flyctl secrets set DATABASE_URL=<provided-connection-url>
```

### Option 2: Supabase (Easier Alternative)

1. Go to https://supabase.com
2. Create a new project
3. Get the connection string from Settings → Database
4. Set it as a Fly.io secret:

```bash
flyctl secrets set DATABASE_URL="postgresql://postgres:[password]@[host]:5432/postgres"
```

### Option 3: Railway PostgreSQL

1. Go to https://railway.app
2. New Project → Add PostgreSQL
3. Get the connection URL
4. Set it as a Fly.io secret

## Migration Steps

### 1. Install PostgreSQL Client
```bash
# macOS
brew install postgresql

# Or use libpq
brew install libpq
```

### 2. Export SQLite Data
```bash
cd backend
python -c "
from app import db, engine
from sqlalchemy import create_engine
import pandas as pd

# Read from SQLite
sqlite_engine = create_engine('sqlite:///foodiq.db')
users = pd.read_sql('SELECT * FROM users', sqlite_engine)
products = pd.read_sql('SELECT * FROM products', sqlite_engine)
# Add other tables as needed

print('Export complete')
"
```

### 3. Import to PostgreSQL
```bash
# After DATABASE_URL is set as a Fly.io secret
python -c "
from app import db, engine
from sqlalchemy import create_engine
import pandas as pd

# Connect to PostgreSQL
pg_engine = create_engine(os.getenv('DATABASE_URL'))

# Import data
users.to_sql('users', pg_engine, if_exists='replace', index=False)
products.to_sql('products', pg_engine, if_exists='replace', index=False)

print('Import complete')
"
```

### 4. Run Migrations
```bash
# Set DATABASE_URL as environment variable first
export DATABASE_URL="postgresql://..."
alembic upgrade head
```

### 5. Verify
```bash
# Test the backend
python -c "
from app import db, engine
s = engine()
users = s.query(db.User).all()
print(f'Users: {len(users)}')
s.close()
"
```

## Quick Start (Supabase - Fastest)

If you want the fastest path to production:

1. **Create Supabase project** (2 minutes)
   - Go to https://supabase.com
   - Sign up/create project
   - Wait for setup (30 seconds)

2. **Get connection string** (30 seconds)
   - Settings → Database
   - Copy the connection string

3. **Set as Fly.io secret** (30 seconds)
   ```bash
   flyctl secrets set DATABASE_URL="postgresql://postgres:[password]@[host]:5432/postgres"
   ```

4. **Deploy** (automatic)
   ```bash
   git add .
   git commit -m "Configure PostgreSQL"
   git push
   ```

**Total time: ~5 minutes**

## Database Schema

The following tables need to be migrated:
- users
- products
- product_overrides
- product_prices
- price_observations
- receipts
- receipt_items
- comparisons
- product_substitutions
- budget_config
- savings_events
- visits

## Important Notes

1. **SQLite will still work for development** - don't delete foodiq.db
2. **Test locally with PostgreSQL first** before deploying
3. **Backup your SQLite data** before migration
4. **The app will automatically use DATABASE_URL if set**
5. **If DATABASE_URL is not set, it falls back to SQLite**

## Testing Checklist

- [ ] PostgreSQL database created
- [ ] DATABASE_URL set as Fly.io secret
- [ ] Data exported from SQLite
- [ ] Data imported to PostgreSQL
- [ ] Migrations run successfully
- [ ] Backend starts without errors
- [ ] Product lookup works
- [ ] User authentication works
- [ ] Receipt parsing works
- [ ] All tests pass

## Alternative: Stay on SQLite for Now

If you're starting with fewer than 100 users, SQLite might be acceptable for a while. But be aware:
- Write-locking issues under concurrent writes
- No horizontal scaling
- Manual backups required
- Not recommended for production

**Recommendation:** Start with PostgreSQL now to avoid migration pain later.
