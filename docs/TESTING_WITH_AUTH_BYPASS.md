# Testing with Authentication Bypass

**Purpose:** Developer guide for using the development authentication bypass system to test RoomieRoster without configuring Google OAuth.

**Last Updated:** 2025-10-13
**Security Level:** DEVELOPMENT ONLY

---

## ⚠️ Security Warning

**CRITICAL:** The authentication bypass should **NEVER** be used in production!

The bypass system includes multiple security checks to prevent production use:
- Refuses to enable if `FLASK_ENV=production`
- Refuses to enable if running on Render (cloud platform)
- Refuses to enable with production DATABASE_URL
- Refuses to enable if `PORT` environment variable is set

**If you see bypass warnings in production logs, IMMEDIATELY:**
1. Remove `DEV_AUTH_BYPASS` from environment variables
2. Restart the application
3. Verify bypass is disabled via health endpoint

---

## 🎯 What is the Auth Bypass?

The authentication bypass is a development tool that allows you to:
- **Test protected endpoints** without Google OAuth setup
- **Develop locally** without internet connection (for OAuth)
- **Run automated tests** without authentication complexity
- **Debug issues** without authentication layer

### How It Works

When enabled, the bypass:
1. Intercepts authentication decorators (`@login_required`, etc.)
2. Provides a mock user session
3. Allows access to all protected endpoints
4. Logs all bypass usage for security awareness

---

## 🚀 Quick Start Guide

### Step 1: Enable Bypass

Edit your `.env` file:

```bash
# Development Auth Bypass
DEV_AUTH_BYPASS=true
FLASK_ENV=development
```

### Step 2: Start Application

```bash
python3 launch_app.py
```

### Step 3: Verify Bypass is Active

Check the startup logs:
```
⚠️  DEVELOPMENT AUTH BYPASS IS ENABLED - This should NEVER happen in production!
⚠️  All authentication checks will be bypassed
⚠️  Set DEV_AUTH_BYPASS=false or remove the variable to disable
```

### Step 4: Access Protected Endpoints

```bash
# Without bypass: Returns 401 Unauthorized
# With bypass: Returns data

curl http://localhost:5001/api/roommates
# Should return roommates list

curl http://localhost:5001/api/chores
# Should return chores list
```

### Step 5: Test in Browser

1. Open `http://localhost:3000`
2. You should be **automatically logged in** (no Google OAuth prompt)
3. All features should be accessible
4. You'll see bypass warnings in browser console (if configured)

---

## 🔧 Configuration Options

### Environment Variables

```bash
# Required for bypass
DEV_AUTH_BYPASS=true          # Enable bypass
FLASK_ENV=development         # Development mode

# Optional for bypass
# (If not set, uses sensible defaults)
```

### Mock User Configuration

The bypass provides a default mock user:

```python
{
    'google_id': 'dev_user_12345',
    'email': 'dev@roomieroster.local',
    'name': 'Dev User',
    'picture': None,
    'roommate_id': None,
    'roommate_name': None
}
```

To customize the mock user (advanced), edit `backend/utils/dev_auth_bypass.py`:

```python
class DevAuthBypass:
    # Customize mock user
    MOCK_USER = {
        'google_id': 'test_user_id',
        'email': 'test@example.com',
        'name': 'Test User',
        'picture': 'https://example.com/avatar.png',
        'roommate_id': 1,  # Link to specific roommate
        'roommate_name': 'Test Roommate'
    }
```

---

## 🧪 Testing Scenarios

### Scenario 1: Test API Endpoints

```bash
# Test GET endpoints
curl http://localhost:5001/api/roommates
curl http://localhost:5001/api/chores
curl http://localhost:5001/api/current-assignments

# Test POST endpoints
curl -X POST http://localhost:5001/api/roommates \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","current_cycle_points":0}'

# Test protected endpoints that normally require login
curl http://localhost:5001/api/auth/profile
# Should return mock user info
```

### Scenario 2: Test Frontend Features

1. **Enable bypass** in `.env`
2. **Start both servers**:
   ```bash
   python3 launch_app.py
   ```
3. **Open browser**: `http://localhost:3000`
4. **Test all features:**
   - View roommates
   - Create new chore
   - Assign chores
   - Manage shopping list
   - Test CRUD operations

### Scenario 3: Run Automated Tests

With bypass enabled, tests don't need to mock authentication:

```python
# tests/test_api.py

import pytest
import requests

BASE_URL = "http://localhost:5001"

def test_get_roommates():
    """Test getting roommates with auth bypass."""
    response = requests.get(f"{BASE_URL}/api/roommates")

    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_chore():
    """Test creating chore with auth bypass."""
    chore_data = {
        "name": "Test Chore",
        "description": "Test description",
        "frequency": "weekly",
        "type": "random",
        "points": 10
    }

    response = requests.post(
        f"{BASE_URL}/api/chores",
        json=chore_data
    )

    assert response.status_code in [200, 201]
```

### Scenario 4: Debug Authentication Issues

Enable bypass to isolate issues:

```bash
# 1. Enable bypass
DEV_AUTH_BYPASS=true python3 launch_app.py

# 2. Test endpoint works with bypass
curl http://localhost:5001/api/protected-endpoint

# 3. Disable bypass
DEV_AUTH_BYPASS=false python3 launch_app.py

# 4. Test endpoint with real auth
# If it fails now, issue is in authentication layer
# If it failed before, issue is in endpoint logic
```

---

## 🔍 Verifying Bypass Status

### Method 1: Check Logs

Look for these messages in startup logs:

**Bypass Enabled:**
```
⚠️  DEVELOPMENT AUTH BYPASS IS ENABLED - This should NEVER happen in production!
⚠️  All authentication checks will be bypassed
🔓 Auth bypass used for endpoint: get_roommates
```

**Bypass Disabled:**
```
✅ Dev auth bypass safety checks passed (but bypass flag not set)
```

### Method 2: Check Health Endpoint

```bash
curl http://localhost:5001/api/health | python3 -m json.tool
```

Look for:
```json
{
  "status": "healthy",
  "auth_bypass": true,  # <-- Should be true when bypass is enabled
  "database": "PostgreSQL"
}
```

### Method 3: Test Protected Endpoint

```bash
# This should work with bypass, fail without
curl http://localhost:5001/api/auth/profile

# With bypass: Returns mock user
# Without bypass: Returns 401 Unauthorized
```

### Method 4: Use Bypass Status Endpoint

```python
from utils.dev_auth_bypass import get_bypass_status

status = get_bypass_status()
print(f"Bypass enabled: {status['bypass_enabled']}")
print(f"FLASK_ENV: {status['flask_env']}")
print(f"Mock user: {status.get('mock_user_email')}")
```

---

## 🚫 Troubleshooting

### Issue: Bypass Not Working

**Symptoms:**
- Still getting 401 Unauthorized errors
- Google login still required
- Health endpoint shows `"auth_bypass": false`

**Solutions:**

1. **Check environment variables:**
   ```bash
   echo $DEV_AUTH_BYPASS  # Should print "true"
   echo $FLASK_ENV         # Should print "development"
   ```

2. **Verify .env file:**
   ```bash
   cat .env | grep -E "DEV_AUTH_BYPASS|FLASK_ENV"
   # Should show:
   # DEV_AUTH_BYPASS=true
   # FLASK_ENV=development
   ```

3. **Restart application:**
   ```bash
   pkill -f "python.*launch_app"
   python3 launch_app.py
   ```

4. **Check logs for rejection:**
   ```bash
   # Look for these messages:
   # ❌ AUTH BYPASS REJECTED: [reason]
   ```

### Issue: Bypass Enabled in Production

**Symptoms:**
- Bypass warnings in production logs
- Health endpoint shows `"auth_bypass": true` on production

**IMMEDIATE ACTION REQUIRED:**

1. **Remove bypass from production:**
   ```bash
   # In Render dashboard:
   # 1. Go to Environment variables
   # 2. DELETE DEV_AUTH_BYPASS variable
   # 3. Save (triggers redeploy)
   ```

2. **Verify disabled:**
   ```bash
   curl https://roomie-roster.onrender.com/api/health
   # Should show: "auth_bypass": false
   ```

3. **Review security:**
   ```bash
   python3 backend/scripts/production_security_audit.py
   ```

### Issue: Cannot Test Certain Features

**Problem:** Some features require specific roommate linking

**Solution:** Customize mock user with roommate_id:

```python
# In dev_auth_bypass.py
MOCK_USER = {
    'google_id': 'dev_user_12345',
    'email': 'dev@roomieroster.local',
    'name': 'Dev User',
    'picture': None,
    'roommate_id': 1,  # Link to roommate ID 1
    'roommate_name': 'Christine'
}
```

---

## 📋 Development Workflow

### Daily Development

```bash
# 1. Start day - enable bypass
echo "DEV_AUTH_BYPASS=true" >> .env

# 2. Start app
python3 launch_app.py

# 3. Develop and test
# - All endpoints accessible
# - No OAuth setup needed

# 4. End day - disable bypass (optional)
# Comment out or remove from .env
```

### Before Committing

```bash
# 1. Disable bypass
# Remove DEV_AUTH_BYPASS from .env

# 2. Test without bypass
python3 launch_app.py

# 3. Verify authentication works
# (or note that OAuth needs to be configured)

# 4. Run tests
python3 backend/scripts/verify_production_ready.py

# 5. Commit
git add .
git commit -m "Your changes"
```

### Before Deployment

```bash
# 1. Disable bypass locally
# Remove from .env

# 2. Run security audit
python3 backend/scripts/production_security_audit.py
# Should show: "Auth bypass properly disabled"

# 3. Verify in production config
# Ensure DEV_AUTH_BYPASS NOT in Render environment

# 4. Deploy
git push origin main
```

---

## 🔐 Security Best Practices

### DO ✅

- **Use bypass only for local development**
- **Enable bypass in `.env` file (not committed)**
- **Disable bypass before committing**
- **Run security audit before deployment**
- **Document any bypass usage in team**

### DON'T ❌

- **Never commit `.env` with bypass enabled**
- **Never set bypass in production environment**
- **Never use bypass with production database**
- **Never share credentials over bypass**
- **Never rely on bypass for security testing**

---

## 📊 Bypass Behavior Summary

| Environment | Bypass Flag | Result |
|-------------|-------------|--------|
| Local development | `true` | ✅ Enabled |
| Local development | `false` | ❌ Disabled |
| Production (Render) | `true` | ❌ Rejected |
| Production (Render) | `false` | ❌ Disabled |
| With production DB | `true` | ❌ Rejected |
| PORT env set | `true` | ❌ Rejected |

---

## 🧪 Testing Checklist

When using auth bypass for testing:

- [ ] Bypass enabled in `.env`
- [ ] App starts with bypass warning
- [ ] Health endpoint shows `"auth_bypass": true`
- [ ] Can access protected endpoints
- [ ] CRUD operations work
- [ ] All features accessible in UI
- [ ] Mock user appears in session
- [ ] Logs show bypass usage

When disabling bypass:

- [ ] Remove `DEV_AUTH_BYPASS` from `.env`
- [ ] Restart application
- [ ] Health endpoint shows `"auth_bypass": false`
- [ ] Protected endpoints return 401
- [ ] Google login required in browser
- [ ] Security audit passes

---

## 📚 Related Documentation

- **dev_auth_bypass.py** - Source code and implementation
- **session_manager.py** - Integration with decorators
- **PRODUCTION_DEPLOYMENT_CHECKLIST.md** - Deployment procedures
- **production_security_audit.py** - Security validation

---

## ✅ Quick Reference

**Enable Bypass:**
```bash
echo "DEV_AUTH_BYPASS=true" >> .env
echo "FLASK_ENV=development" >> .env
python3 launch_app.py
```

**Disable Bypass:**
```bash
# Remove from .env or set to false
DEV_AUTH_BYPASS=false python3 launch_app.py
```

**Check Status:**
```bash
curl http://localhost:5001/api/health | grep auth_bypass
```

**Security Audit:**
```bash
python3 backend/scripts/production_security_audit.py
```

**With proper bypass usage, you can develop and test efficiently while maintaining production security!**
