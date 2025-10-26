# Render Deployment Guide for RoomieRoster

**Last Updated:** 2025-10-25
**Version:** 2.0 (Includes Zeith Productivity Features)

This guide provides step-by-step instructions for deploying RoomieRoster (with Zeith productivity features) to Render.com.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Environment Configuration](#environment-configuration)
4. [First Deployment](#first-deployment)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Ongoing Deployments](#ongoing-deployments)
7. [Rollback Procedure](#rollback-procedure)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts
- ✅ GitHub account with repository access
- ✅ Render.com account (free tier available)
- ✅ Neon PostgreSQL database (free tier available)
- ✅ Google Cloud Console project (for OAuth)

### Required Tools (for local validation)
- Python 3.8+
- Node.js 16+
- Git

---

## Initial Setup

### Step 1: Create Neon PostgreSQL Database

1. **Sign up at [neon.tech](https://neon.tech)**

2. **Create a new project**
   - Project name: `roomieroster-prod`
   - Region: Choose closest to your users (e.g., `US East (Ohio)`)
   - PostgreSQL version: 16 (latest)

3. **Get connection string**
   - Go to project dashboard
   - Click "Connection Details"
   - Copy the connection string (should start with `postgresql://`)
   - **IMPORTANT:** Ensure it includes `?sslmode=require`

   Example:
   ```
   postgresql://neondb_owner:npg_XXXX@ep-XXXXX.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

### Step 2: Configure Google OAuth

1. **Go to [console.cloud.google.com](https://console.cloud.google.com)**

2. **Navigate to:** APIs & Services → Credentials

3. **Find your OAuth 2.0 Client ID**

4. **Add authorized redirect URIs:**
   - For development:
     - `http://localhost:5000/api/auth/callback`
     - `http://localhost:5001/api/auth/callback`

   - For production (add your Render URL):
     - `https://roomie-roster.onrender.com/api/auth/callback`
     - OR `https://your-custom-domain.com/api/auth/callback`

5. **Save changes**

### Step 3: Pre-Deployment Validation (Local)

Before deploying, validate your local setup:

```bash
# 1. Set environment variables locally
export DATABASE_URL="postgresql://..."
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export ROOMIE_WHITELIST="email1@gmail.com,email2@gmail.com"

# 2. Run pre-deployment checks
cd backend
python scripts/pre_deploy_check.py

# 3. Build frontend
cd ../frontend
npm install
npm run build

# 4. Run migrations (local test)
cd ../backend
python scripts/run_migrations.py
```

**Expected output:** All checks should pass ✅

---

## Environment Configuration

### Step 4: Create Render Web Service

1. **Log in to [dashboard.render.com](https://dashboard.render.com)**

2. **Click "New +" → "Web Service"**

3. **Connect GitHub repository:**
   - Select: `ah91648/roomie-roster` (or your fork)
   - Branch: `main`

4. **Configure service:**
   - Name: `roomie-roster`
   - Region: `Oregon` (or closest to your database)
   - Branch: `main`
   - Root Directory: Leave blank (uses project root)
   - Runtime: `Python 3`

5. **Build & Start Commands** (from render.yaml):
   - Build Command:
     ```bash
     cd backend && pip install -r requirements.txt && cd ../frontend && npm ci --production=false && npm run build
     ```

   - Start Command:
     ```bash
     cd backend && python scripts/run_migrations.py && gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
     ```

6. **Plan:** Select `Starter` (free tier) or `Standard` (recommended for production)

### Step 5: Set Environment Variables

In Render dashboard, go to **Environment** tab and add:

#### Required Variables

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `postgresql://neondb_owner:...` | From Neon dashboard, must include `?sslmode=require` |
| `GOOGLE_CLIENT_ID` | `1013918805389-...apps.googleusercontent.com` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-...` | From Google Cloud Console |
| `FLASK_SECRET_KEY` | Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"` | 64-character hex string |
| `ROOMIE_WHITELIST` | `email1@gmail.com,email2@gmail.com` | Comma-separated, no spaces |
| `FLASK_ENV` | `production` | Fixed value |

#### Optional Variables

| Variable | Value | Notes |
|----------|-------|-------|
| `APP_BASE_URL` | `https://your-domain.com` | Only if using custom domain |
| `OAUTHLIB_RELAX_TOKEN_SCOPE` | `1` | Prevents OAuth scope errors (recommended) |

#### Auto-Set Variables (DO NOT SET)

These are automatically set by Render:
- `PORT` - Automatically assigned
- `RENDER_SERVICE_NAME` - Your service name
- `RENDER` - Set to `true`

### Step 6: Configure Health Check

1. **In Render dashboard → Settings**

2. **Health Check Path:** `/api/health`

3. **Health Check Interval:** 30 seconds (default)

4. **Save changes**

---

## First Deployment

### Step 7: Trigger Initial Deploy

1. **Save environment variables**
   - This automatically triggers a deployment

2. **Monitor build logs:**
   - Click "Logs" tab
   - Watch for:
     ```
     📦 Installing backend dependencies...
     📦 Installing frontend dependencies...
     🏗️  Building frontend...
     ✅ Build complete
     ```

3. **Monitor start logs:**
   - Look for:
     ```
     🔄 Running database migrations...
     ✅ Migrations applied successfully
     🚀 Starting application...
     Starting gunicorn...
     ```

4. **Wait for deployment to complete**
   - Status should change to "Live" (green)
   - Initial deployment takes ~3-5 minutes

---

## Post-Deployment Verification

### Step 8: Verify Deployment

#### Check Health Endpoint

```bash
curl https://roomie-roster.onrender.com/api/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-25T...",
  "checks": {
    "database": {
      "status": "healthy",
      "type": "postgresql",
      "connected": true
    },
    "features": {
      "status": "healthy",
      "core_features": true,
      "productivity_features": true
    },
    "scheduler": {
      "status": "healthy",
      "running": true
    },
    "migrations": {
      "status": "healthy",
      "message": "Migration table exists"
    }
  }
}
```

#### Test OAuth Login

1. Open `https://roomie-roster.onrender.com` in browser

2. Click "Sign in with Google"

3. **If OAuth error occurs:**
   - Verify redirect URI in Google Console matches exactly
   - Check `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in Render

4. **After successful login:**
   - Verify your email is in `ROOMIE_WHITELIST`
   - You should see the main dashboard

#### Verify Zeith Features

Test all productivity features:

1. **Pomodoro Timer:**
   - Navigate to Pomodoro page
   - Start a focus session
   - Verify timer countdown works

2. **Todo List:**
   - Create a new todo item
   - Mark it as complete
   - Verify persistence after page reload

3. **Mood Journal:**
   - Create today's mood entry
   - Select mood level, energy, add notes
   - Verify entry appears

4. **Analytics Dashboard:**
   - View analytics page
   - Verify charts render (Recharts)
   - Switch time periods (7/14/30 days)

#### Check Database Persistence

1. Create a test roommate or chore

2. **Redeploy** (push a small change to GitHub)

3. **Verify data persists after redeploy**

---

## Ongoing Deployments

### Step 9: Continuous Deployment

**Auto-Deploy Setup:**

Render is configured to auto-deploy when you push to GitHub:

```bash
git add .
git commit -m "Add new feature"
git push origin main
```

**Deployment Process:**
1. Render detects push to `main` branch
2. Pulls latest code
3. Runs build command
4. **Runs database migrations automatically**
5. Starts new instance
6. **Health check validates deployment**
7. Routes traffic to new instance
8. Shuts down old instance

**Zero-Downtime Deployment:**
- Health check prevents traffic routing until app is ready
- Migrations run before app starts
- Old instance continues serving traffic until new one is healthy

### Manual Deployment

To manually trigger deployment:

1. Go to Render dashboard
2. Click "Manual Deploy"
3. Select branch: `main`
4. Click "Deploy latest commit"

---

## Rollback Procedure

### Step 10: Rollback to Previous Version

#### Application Rollback

1. **In Render dashboard:**
   - Go to "Events" or "Deploys" tab
   - Find the last known good deployment
   - Click "Redeploy" next to that deployment

2. **Monitor logs** to ensure successful rollback

#### Database Rollback (If Needed)

**Using Neon Point-in-Time Recovery:**

1. **Go to [console.neon.tech](https://console.neon.tech)**

2. **Select your project**

3. **Create branch from past state:**
   - Click "Branches"
   - Click "Create Branch"
   - Select timestamp (up to 7 days ago on free tier)
   - Name: `rollback-YYYY-MM-DD`

4. **Get connection string for rollback branch**

5. **Update `DATABASE_URL` in Render** with rollback branch URL

6. **Redeploy application**

7. **After verification:**
   - Either keep rollback branch as main
   - Or restore data manually and delete rollback branch

---

## Troubleshooting

### Common Issues

#### Issue: "Migration failed - aborting startup"

**Cause:** Database schema out of sync or migration error

**Fix:**
```bash
# Check migration status
cd backend
python scripts/check_pending_migrations.py

# Apply migrations manually
python scripts/run_migrations.py

# If error persists, check logs for specific migration error
```

#### Issue: Health check returns 503

**Cause:** Database connection failed or critical feature broken

**Fix:**
1. Check Render logs for error details
2. Verify `DATABASE_URL` is correct
3. Test database connection locally:
   ```bash
   python scripts/pre_deploy_check.py
   ```

#### Issue: OAuth redirect URI mismatch

**Cause:** Google Console redirect URI doesn't match Render URL

**Fix:**
1. Get current redirect URI from logs:
   ```
   https://roomie-roster.onrender.com/api/auth/callback
   ```
2. Add EXACT URL to Google Console
3. Wait 5 minutes for Google to propagate changes
4. Try login again

#### Issue: "Data lost after deployment"

**Cause:** Using JSON file storage instead of PostgreSQL

**Fix:**
1. Verify `DATABASE_URL` is set in Render environment variables
2. Check health endpoint - should show `"type": "postgresql"`
3. If showing `"type": "json_files"`:
   - DATABASE_URL is not configured correctly
   - Fix and redeploy

#### Issue: Frontend not loading

**Cause:** Build failed or static files missing

**Fix:**
1. Check build logs for errors
2. Verify frontend build command completed:
   ```
   🏗️  Building frontend...
   ```
3. Test local build:
   ```bash
   cd frontend
   npm run build
   ls -la build/
   ```

#### Issue: Render service won't start

**Cause:** Python dependencies or port binding issue

**Fix:**
1. Check logs for import errors
2. Verify `requirements.txt` includes all dependencies
3. Ensure start command uses `$PORT` variable:
   ```bash
   gunicorn --bind 0.0.0.0:$PORT app:app
   ```

### Getting Help

**Check Logs:**
- Render dashboard → Logs tab
- Filter by: Build, Deploy, Runtime

**Test Locally:**
```bash
# Replicate production environment
export FLASK_ENV=production
export DATABASE_URL="your-neon-url"
# ... other env vars ...

cd backend
python app.py
```

**Health Check Debug:**
```bash
curl -v https://roomie-roster.onrender.com/api/health | jq
```

**Contact Support:**
- Render community: https://community.render.com
- GitHub issues: https://github.com/ah91648/roomie-roster/issues

---

## Performance Optimization

### Scaling Up

**When to upgrade plan:**
- Response time > 2 seconds consistently
- Memory usage > 90%
- CPU usage > 80%

**Upgrade to Standard Plan:**
1. Render dashboard → Settings
2. Change plan to "Standard"
3. Benefits:
   - More memory (512MB → 2GB)
   - Better CPU allocation
   - No cold starts

### Database Optimization

**Monitor Neon usage:**
- [console.neon.tech](https://console.neon.tech) → Metrics
- Watch for:
  - Connection count (max 100 on free tier)
  - Storage usage (max 3GB on free tier)

**Optimize queries:**
- Check `backend/utils/database_data_handler.py`
- Add indexes for slow queries
- Use eager loading for relationships

---

## Success Checklist

- ✅ Health endpoint returns status 200
- ✅ Database type shows "postgresql"
- ✅ OAuth login works for whitelisted users
- ✅ All 4 Zeith features functional (Pomodoro, Todo, Mood, Analytics)
- ✅ Data persists across deployments
- ✅ No errors in Render logs
- ✅ Response time < 2 seconds

**Congratulations! Your RoomieRoster deployment is complete! 🎉**

---

## Quick Reference

**Render Dashboard:** https://dashboard.render.com
**Neon Dashboard:** https://console.neon.tech
**Health Check:** https://roomie-roster.onrender.com/api/health
**Application URL:** https://roomie-roster.onrender.com

**Local Commands:**
```bash
# Pre-deployment validation
python backend/scripts/pre_deploy_check.py

# Check migrations
python backend/scripts/check_pending_migrations.py

# Run migrations
python backend/scripts/run_migrations.py

# Build frontend
cd frontend && npm run build
```
