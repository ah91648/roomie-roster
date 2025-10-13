# Production Deployment Checklist for RoomieRoster

**Version:** 1.0
**Last Updated:** 2025-10-13
**Purpose:** Comprehensive checklist to ensure RoomieRoster is production-ready with zero data loss risk

---

## 📋 Pre-Deployment Checks

### Development Environment Testing

- [ ] **Auth Bypass Created and Tested**
  - `backend/utils/dev_auth_bypass.py` exists
  - `DEV_AUTH_BYPASS=true` in local `.env`
  - Can access protected endpoints without Google login
  - Logs show "⚠️  DEVELOPMENT AUTH BYPASS IS ENABLED" warning

- [ ] **Local Testing Passed**
  - App starts successfully: `python3 launch_app.py`
  - Health endpoint returns PostgreSQL: `curl http://localhost:5001/api/health`
  - UI loads at `http://localhost:3000`
  - All data displays correctly:
    - [ ] 4+ Roommates visible
    - [ ] 4+ Chores visible
    - [ ] Shopping list accessible
    - [ ] Assignments display correctly
  - No errors in backend logs

- [ ] **Database Connection Verified**
  - `DATABASE_URL` active in `.env`
  - Health endpoint shows: `"database": "postgresql"`
  - Not using JSON file fallback

- [ ] **CRUD Operations Work**
  - Can create new chore
  - Can edit existing chore
  - Can delete test data
  - Changes persist after app restart

- [ ] **Validation Script Passed**
  ```bash
  python3 backend/scripts/verify_production_ready.py
  # Expected: All checks pass
  ```

- [ ] **Security Audit Passed**
  ```bash
  python3 backend/scripts/production_security_audit.py
  # Expected: No critical issues
  ```

- [ ] **Auth Bypass Disabled for Production Build**
  - Remove `DEV_AUTH_BYPASS=true` from `.env`
  - Verify bypass is disabled: health endpoint shows `"auth_bypass": false`
  - Google login is required to access app

---

## 🚀 Render Deployment Configuration

### Environment Variables Setup

- [ ] **Log into Render Dashboard**
  - Navigate to your RoomieRoster service
  - Go to "Environment" tab

- [ ] **Database Configuration**
  ```bash
  DATABASE_URL=postgresql://neondb_owner:npg_G3wnBmtv5lPJ@ep-restless-band-aeejy267-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
  ```
  - [ ] DATABASE_URL contains `?sslmode=require`
  - [ ] Connection string is from Neon dashboard

- [ ] **Google OAuth Credentials**
  ```bash
  GOOGLE_CLIENT_ID=[from .env file]
  GOOGLE_CLIENT_SECRET=[from .env file]
  ```
  - [ ] Client ID ends with `.apps.googleusercontent.com`
  - [ ] Client secret is 24+ characters

- [ ] **Flask Security**
  ```bash
  FLASK_SECRET_KEY=[32+ character hex string]
  ```
  - [ ] Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
  - [ ] NOT a placeholder value like "dev" or "secret"

- [ ] **Access Control**
  ```bash
  ROOMIE_WHITELIST=email1@example.com,email2@example.com,email3@example.com
  ```
  - [ ] All roommate emails listed
  - [ ] Comma-separated with no spaces

- [ ] **Environment Mode**
  ```bash
  FLASK_ENV=production
  ```
  - [ ] Set to "production" (not "development")

- [ ] **CRITICAL: Security Variables NOT Set**
  - [ ] `DEV_AUTH_BYPASS` does NOT exist in Render env vars
  - [ ] `FLASK_DEBUG` is NOT set (or set to false)

- [ ] **Auto-Set Variables (DO NOT SET MANUALLY)**
  - PORT (set by Render automatically)
  - RENDER_SERVICE_NAME (set by Render automatically)

### Google OAuth Redirect URIs

- [ ] **Update Google Cloud Console**
  - Go to [console.cloud.google.com](https://console.cloud.google.com)
  - Navigate to: APIs & Services → Credentials
  - Edit OAuth 2.0 Client ID
  - Add authorized redirect URI:
    ```
    https://roomie-roster.onrender.com/api/auth/callback
    ```
    (Replace with your actual production URL)
  - [ ] Save changes

- [ ] **Verify OAuth Configuration**
  - Test app name shows correctly in consent screen
  - Authorized domains include your Render domain
  - Required scopes are listed:
    - [ ] email
    - [ ] profile
    - [ ] calendar
    - [ ] calendar.events

### Deployment Execution

- [ ] **Verify Environment Variables**
  - All required vars shown above are set
  - No typos in variable names or values
  - DEV_AUTH_BYPASS is NOT present

- [ ] **Save and Deploy**
  - Click "Save Changes" (triggers auto-deploy)
  - OR manually deploy via "Manual Deploy" button

- [ ] **Monitor Deployment Logs**
  - Watch for "Starting gunicorn" message
  - No "DEV_AUTH_BYPASS" warnings in logs
  - No database connection errors
  - Deployment status shows "Live"

- [ ] **Post-Deployment Verification**
  ```bash
  curl https://roomie-roster.onrender.com/api/health
  ```
  Expected response:
  ```json
  {
    "status": "healthy",
    "database": "PostgreSQL",
    "database_connected": true,
    "auth_bypass": false
  }
  ```

- [ ] **Test Production Access**
  - Open production URL in browser
  - Google login is required (no bypass)
  - Can log in with whitelisted email
  - All features work:
    - [ ] View roommates
    - [ ] View chores
    - [ ] View assignments
    - [ ] Shopping list loads
    - [ ] Can create/edit/delete items

---

## 📊 Monitoring Setup

### UptimeRobot Configuration

- [ ] **Sign Up for UptimeRobot**
  - Visit [uptimerobot.com](https://uptimerobot.com)
  - Create free account
  - Verify email address

- [ ] **Create Primary Health Monitor**
  - Click "Add New Monitor"
  - Monitor Type: `HTTP(s)`
  - Friendly Name: `RoomieRoster Health Check`
  - URL: `https://roomie-roster.onrender.com/api/health`
  - Monitoring Interval: `5 minutes`
  - Monitor Timeout: `30 seconds`
  - Monitor HTTP(s) Type: `HEAD`

- [ ] **Configure Alert Settings**
  - Alert Threshold: `Alert when down for 2 consecutive checks`
  - Alert Contacts: Add email address(es)
  - Alert When: `Down` and `Back up`
  - Get Notifications: `Immediately`

- [ ] **Create Secondary Monitors (Optional)**
  - Frontend Monitor:
    - URL: `https://roomie-roster.onrender.com/`
    - Friendly Name: `RoomieRoster Frontend`
  - API Monitor:
    - URL: `https://roomie-roster.onrender.com/api/roommates`
    - Friendly Name: `RoomieRoster API`

- [ ] **Test Monitors**
  - All monitors show "Up" status
  - Response time < 2 seconds
  - Receive test notification (pause monitor briefly to test alerts)

### Alternative: Render Built-in Monitoring

- [ ] **Configure Health Check in Render**
  - Go to service settings
  - Health Check Path: `/api/health`
  - Check for HTTP 200 status

- [ ] **Set Up Notifications**
  - Add notification emails in Render dashboard
  - Enable deploy notifications
  - Enable downtime notifications

---

## 💾 Backup Strategy Configuration

### Layer 1: Neon Built-in Backups (PRIMARY) ✅

- [ ] **Verify Neon Backups Active**
  - Log into [console.neon.tech](https://console.neon.tech)
  - Navigate to your project
  - Go to "Backups" or "Branches" section
  - Verify: "Point-in-time recovery available"

- [ ] **Understand Backup Features**
  - Free tier: 7-day point-in-time recovery
  - Paid plans: 30-day recovery
  - Automatic snapshots every few hours
  - No manual setup required

- [ ] **Test Restore Procedure (Optional)**
  - Create test branch from 1 day ago
  - Verify data is correct
  - Delete test branch after verification

### Layer 2: GitHub Actions + S3 Backups (OPTIONAL)

- [ ] **Create AWS S3 Bucket**
  ```bash
  aws s3 mb s3://roomieroster-backups-[unique-id]
  aws s3api put-bucket-versioning \
    --bucket roomieroster-backups-[unique-id] \
    --versioning-configuration Status=Enabled
  ```

- [ ] **Configure GitHub Secrets**
  - Go to GitHub repository → Settings → Secrets → Actions
  - Add these secrets:
    - `DATABASE_URL` - Your Neon connection string
    - `AWS_ACCESS_KEY_ID` - AWS access key
    - `AWS_SECRET_ACCESS_KEY` - AWS secret key
    - `S3_BUCKET_NAME` - Your bucket name (e.g., `roomieroster-backups-unique-id`)

- [ ] **Verify Workflow File Exists**
  - File: `.github/workflows/database-backup.yml`
  - Scheduled: Daily at 2 AM UTC
  - Can be triggered manually

- [ ] **Test Backup Workflow**
  - Go to GitHub → Actions tab
  - Select "Database Backup" workflow
  - Click "Run workflow"
  - Monitor execution (should complete in < 5 minutes)
  - Verify backup appears in S3:
    ```bash
    aws s3 ls s3://roomieroster-backups-[unique-id]/backups/
    ```

### Layer 3: Emergency Recovery System ✅

- [ ] **Verify Emergency Backups Work**
  ```bash
  cd backend
  python3 -c "
  from utils.emergency_recovery import emergency_recovery
  backup = emergency_recovery.create_emergency_backup(reason='pre_deployment')
  print(f'Backup created: {backup}')
  "
  ```

- [ ] **List Existing Backups**
  ```bash
  ls -lh backend/emergency_backups/
  # Should show .json.gz files
  ```

### Backup Verification and Testing

- [ ] **Test Disaster Recovery** (CRITICAL)
  1. Create backup:
     ```bash
     cd backend
     python3 -c "
     from utils.emergency_recovery import emergency_recovery
     emergency_recovery.create_emergency_backup(reason='test')
     "
     ```
  2. Make small test change (add test roommate in UI)
  3. Restore from backup:
     ```bash
     python3 -c "
     from utils.emergency_recovery import emergency_recovery
     emergency_recovery.restore_from_backup()
     "
     ```
  4. Verify test change is gone (confirms restore worked)

- [ ] **Document Backup Procedures**
  - Know how to restore from Neon (see docs/DISASTER_RECOVERY.md)
  - Know how to restore from S3 (if configured)
  - Know how to use emergency recovery system

---

## 🔒 Security Verification

### Security Audit

- [ ] **Run Security Audit**
  ```bash
  python3 backend/scripts/production_security_audit.py
  ```
  Expected: No critical issues

- [ ] **Verify Critical Security Settings**
  - [ ] Auth bypass disabled (Render env vars)
  - [ ] SSL enforced in DATABASE_URL (`?sslmode=require`)
  - [ ] FLASK_SECRET_KEY is secure (64+ char hex)
  - [ ] CSRF protection active
  - [ ] Session cookies secure (HTTPOnly, SameSite=Lax)
  - [ ] FLASK_DEBUG is false or not set
  - [ ] FLASK_ENV is "production"

- [ ] **Test Security Features**
  - Cannot access API without authentication
  - CSRF token required for mutations
  - Rate limiting active (test by rapid requests)
  - Only whitelisted emails can log in

### Access Control

- [ ] **Verify Whitelist Works**
  - Try logging in with whitelisted email → Success
  - Try logging in with non-whitelisted email → Rejected

- [ ] **Test Session Management**
  - Session persists across page reloads
  - Session expires after 30 days (or configured lifetime)
  - Logout clears session completely

---

## 📚 Documentation Verification

- [ ] **All Documentation Complete**
  - [ ] `PRODUCTION_DEPLOYMENT_CHECKLIST.md` (this file)
  - [ ] `DATA_LOSS_PREVENTION.md` (complete guide)
  - [ ] `DATABASE_SETUP_GUIDE.md` (setup instructions)
  - [ ] `docs/DISASTER_RECOVERY.md` (recovery procedures)
  - [ ] `docs/MONITORING_GUIDE.md` (monitoring setup)
  - [ ] `docs/TESTING_WITH_AUTH_BYPASS.md` (developer guide)

- [ ] **Team Training**
  - Team knows how to access production app
  - Team knows monitoring dashboards (UptimeRobot/Render)
  - Team knows disaster recovery procedures
  - Team knows how to check backup status

---

## ✅ Final Production Checklist

### Pre-Launch Verification

- [ ] All local tests passed
- [ ] All security checks passed
- [ ] Database migrated to PostgreSQL
- [ ] Auth bypass disabled in production
- [ ] All environment variables set correctly
- [ ] Google OAuth configured for production URL
- [ ] Monitoring active and alerting
- [ ] Backup systems verified and tested
- [ ] Documentation complete
- [ ] Team trained

### Launch Execution

- [ ] Deploy to Render
- [ ] Verify production health endpoint
- [ ] Test Google login flow
- [ ] Verify all features work
- [ ] Check monitoring shows "Up"
- [ ] Confirm no errors in logs

### Post-Launch Monitoring (First 24 Hours)

- [ ] Monitor UptimeRobot dashboard
- [ ] Check Render logs for errors
- [ ] Verify backup jobs running
- [ ] Test app functionality periodically
- [ ] Confirm users can access successfully

---

## 🆘 Rollback Procedure

If critical issues occur after deployment:

1. **Immediate Action:**
   ```
   # In Render dashboard:
   - Go to "Manual Deploy"
   - Select previous successful deployment
   - Click "Redeploy"
   ```

2. **Restore Database (if needed):**
   - See `docs/DISASTER_RECOVERY.md` for detailed procedures
   - Use Neon point-in-time recovery
   - Or restore from S3/emergency backups

3. **Notify Team:**
   - Alert all stakeholders
   - Document issues encountered
   - Create post-mortem after resolution

---

## 📞 Support Resources

- **Documentation:** `docs/` directory
- **Health Check:** `https://roomie-roster.onrender.com/api/health`
- **Monitoring:** UptimeRobot dashboard
- **Logs:** Render dashboard → Logs tab
- **Database:** [Neon Console](https://console.neon.tech)
- **Backups:** S3 bucket or Neon branches

---

## 🎉 Success Criteria

Deployment is successful when:

- ✅ Health endpoint returns "healthy" with PostgreSQL
- ✅ Users can log in with Google OAuth
- ✅ All features accessible and functional
- ✅ Monitoring shows "Up" status
- ✅ No critical errors in logs
- ✅ Backups verified and working
- ✅ Auth bypass confirmed disabled
- ✅ Data persists across container restarts

**Your data is now safe forever! 🎊**
