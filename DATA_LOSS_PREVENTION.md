# Data Loss Prevention Guide for RoomieRoster

## 🚨 Critical Issue: Why You're Losing Data

### Root Cause Analysis

Your RoomieRoster application is currently **losing data on container restarts** because:

1. **JSON File Storage Mode**: Your `.env` file has `DATABASE_URL` commented out
2. **Ephemeral Filesystem**: Cloud platforms like Render use temporary storage for containers
3. **Container Restarts**: Every deployment, crash, or platform restart wipes the filesystem
4. **No Persistent Database**: Without PostgreSQL, all data exists only in memory/temp files

**Evidence from your configuration**:
```bash
# Your .env file (LINE 21):
# For local development, leave DATABASE_URL commented out to use JSON files
# DATABASE_URL=postgresql://...   ← THIS IS COMMENTED OUT!
```

**What happens when DATABASE_URL is not configured**:
- App falls back to JSON file storage (`backend/data/state.json`, etc.)
- On Render, these files are stored in `/app/backend/data/` (ephemeral)
- Container restart → Files deleted → **ALL DATA LOST**

---

## ✅ Comprehensive Solution Implemented

I've created a **5-layer protection system** to ensure your data is never lost again:

### Layer 1: Automated PostgreSQL Setup
**File**: `backend/scripts/setup_production_persistence.py`

One-command setup that:
- ✅ Guides you through Neon PostgreSQL setup (free tier, 3GB storage)
- ✅ Tests database connectivity
- ✅ Auto-configures `.env` file
- ✅ Migrates existing JSON data to PostgreSQL
- ✅ Validates data integrity
- ✅ Verifies backup system

**Usage**:
```bash
python3 backend/scripts/setup_production_persistence.py
```

### Layer 2: Data Integrity Validation
**File**: `backend/utils/data_integrity_validator.py`

Comprehensive validation system that:
- ✅ Validates foreign key relationships
- ✅ Detects orphaned records
- ✅ Checks date formats and ranges
- ✅ Validates required fields
- ✅ Compares JSON vs Database consistency
- ✅ Generates detailed integrity reports

**Usage**:
```python
from utils.data_integrity_validator import validate_data

# Validate JSON files
success, report = validate_data(mode='json', data_dir='backend/data')

# Validate database
success, report = validate_data(mode='database', app=app)
```

### Layer 3: Emergency Recovery System
**File**: `backend/utils/emergency_recovery.py`

Automatic safety net that:
- ✅ Creates JSON snapshots before every write operation
- ✅ Keeps last 10 backups automatically (compressed)
- ✅ Emergency restore from any backup
- ✅ Database-to-JSON sync for hybrid resilience
- ✅ Rollback capability if migration fails

**Usage**:
```python
from utils.emergency_recovery import emergency_recovery

# Create manual backup
backup_path = emergency_recovery.create_emergency_backup(reason="before_deployment")

# List all backups
backups = emergency_recovery.list_backups()

# Restore from most recent backup
success = emergency_recovery.restore_from_backup()

# Sync database to JSON (safety backup)
emergency_recovery.sync_database_to_json(app)
```

### Layer 4: Existing Automated Backups
**Files**: `backend/scripts/backup_database.sh`, `backup_to_s3.sh`

Already implemented:
- ✅ Daily pg_dump backups (local or S3)
- ✅ Compression and retention management
- ✅ Neon's built-in point-in-time restore (7-30 days)
- ✅ GitHub Actions workflow (in `.github/workflows/`)

### Layer 5: Enhanced Monitoring
**Enhanced**: `/api/health` endpoint

Now includes:
- ✅ Database connection status
- ✅ Storage mode (PostgreSQL vs JSON)
- ✅ Data integrity validation
- ✅ Last successful write timestamp
- ✅ Backup status

---

## 🚀 Quick Fix (15 Minutes)

### Step 1: Sign Up for Neon PostgreSQL (FREE)

1. Go to [neon.tech](https://neon.tech)
2. Create free account (no credit card required)
3. Create a new project named `roomieroster`
4. Copy the connection string (looks like):
   ```
   postgresql://username:password@ep-xxx-pooler.us-east-2.aws.neon.tech/dbname?sslmode=require
   ```

   postgresql://neondb_owner:npg_G3wnBmtv5lPJ@ep-restless-band-aeejy267-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require

### Step 2: Run Automated Setup Script

```bash
cd /path/to/your/roomieroster/project
python3 backend/scripts/setup_production_persistence.py
```

**The script will**:
1. Prompt you for the database URL
2. Test the connection
3. Update your `.env` file
4. Migrate all your existing data
5. Validate data integrity
6. Verify backup system

**Expected output**:
```
======================================================================
          RoomieRoster Production Persistence Setup
======================================================================

[Step 1/6] Configure PostgreSQL Database
Enter your database URL: postgresql://...

✅ Database URL format is valid

[Step 2/6] Test Database Connection
ℹ️  Testing database connection...
✅ Connected successfully!
ℹ️  PostgreSQL version: PostgreSQL 15.3

[Step 3/6] Update Environment Configuration
✅ Updated /path/to/.env

[Step 4/6] Migrate Data from JSON to PostgreSQL
⚠️  Proceed with migration? (yes/no): yes
✅ Migration completed successfully!

[Step 5/6] Validate Data Integrity
ℹ️  Found 4 roommates, 4 chores, 4 assignments
✅ Data integrity validation passed!

[Step 6/6] Verify Backup System
✅ Backup system is ready

======================================================================
                        Setup Complete!
======================================================================
```

### Step 3: Verify PostgreSQL is Active

```bash
# Start your application
python3 launch_app.py

# In another terminal, check health
curl http://localhost:5001/api/health
```

**Expected response**:
```json
{
  "status": "healthy",
  "database": "postgresql",  ← MUST BE "postgresql" NOT "json"
  "database_connected": true,
  "version": "1.0.0"
}
```

### Step 4: Deploy to Production

**On Render Dashboard**:
1. Go to your service → Environment
2. Add environment variable:
   ```
   DATABASE_URL = postgresql://username:password@...?sslmode=require
   ```
3. Redeploy your application
4. Verify with: `curl https://your-app.onrender.com/api/health`

---

## 🛡️ Long-Term Protection Strategy

### Daily Automated Backups

Set up cron job for daily backups:

```bash
crontab -e

# Add this line (runs daily at 2 AM):
0 2 * * * /path/to/backend/scripts/backup_database.sh >> /var/log/roomieroster_backup.log 2>&1
```

**For cloud backups** (recommended for production):
```bash
# Setup AWS S3 bucket
aws s3 mb s3://roomieroster-backups-YOUR_UNIQUE_ID
aws s3api put-bucket-versioning --bucket roomieroster-backups-YOUR_UNIQUE_ID --versioning-configuration Status=Enabled

# Update cron for S3
0 2 * * * /path/to/backend/scripts/backup_to_s3.sh >> /var/log/roomieroster_backup_s3.log 2>&1
```

### Monitoring Setup

**Option 1: Simple Uptime Monitoring** (free, 5 minutes)
1. Sign up at [UptimeRobot](https://uptimerobot.com)
2. Add monitor for: `https://your-app.onrender.com/api/health`
3. Set check interval: 5 minutes
4. Add email alerts

**Option 2: Advanced Monitoring with Sentry** (optional)
```bash
cd backend
pip install sentry-sdk[flask]
echo "sentry-sdk[flask]==1.40.0" >> requirements.txt

# Set environment variable
echo "SENTRY_DSN=your_sentry_dsn_here" >> .env
```

### Weekly Data Integrity Checks

Add to cron or run manually:
```bash
# Run weekly integrity validation
cd backend
python3 -c "
from flask import Flask
from utils.data_integrity_validator import validate_data

app = Flask(__name__)
app.config.from_object('config.ProductionConfig')

success, report = validate_data(mode='database', app=app)
if not success:
    print('⚠️ Data integrity issues found!')
    print(report)
"
```

---

## 🚑 Emergency Recovery Procedures

### Scenario 1: Data Lost Recently (< 7 Days)

Use Neon's built-in point-in-time restore:

1. **Via Neon Dashboard**:
   - Log into [console.neon.tech](https://console.neon.tech)
   - Select your project
   - Go to "Branches" → "Restore"
   - Choose the date/time to restore to
   - Update your `DATABASE_URL` to new branch

2. **Via Neon CLI** (faster):
   ```bash
   npm install -g neonctl
   neonctl branch create --restore-to-parent='2 days ago'
   ```

### Scenario 2: Restore from Emergency Backup

```bash
cd backend
python3 -c "
from utils.emergency_recovery import emergency_recovery

# List available backups
backups = emergency_recovery.list_backups()
for i, backup in enumerate(backups):
    print(f'{i}: {backup[\"filename\"]} - {backup[\"created\"]} ({backup[\"size_mb\"]} MB)')

# Restore from most recent
success = emergency_recovery.restore_from_backup()
print(f'Restoration: {\"Success\" if success else \"Failed\"}')
"
```

### Scenario 3: Restore from pg_dump Backup

```bash
# List available backups
ls -lh backend/backups/

# Or from S3
aws s3 ls s3://roomieroster-backups-YOUR_ID/

# Download from S3 (if needed)
aws s3 cp s3://roomieroster-backups-YOUR_ID/backup_2025-10-12.sql.gz ./

# Decompress and restore
gunzip backup_2025-10-12.sql.gz
psql $DATABASE_URL < backup_2025-10-12.sql

# Verify restoration
python3 launch_app.py
```

### Scenario 4: Complete Database Corruption

```bash
cd backend

# 1. Create final backup of corrupted data (for analysis)
python3 -c "
from utils.emergency_recovery import emergency_recovery
emergency_recovery.create_emergency_backup(reason='pre_reset')
"

# 2. Reset database completely
python3 -c "
from utils.database_init import database_initializer
from flask import Flask
app = Flask(__name__)
database_initializer.reset_database(app)
"

# 3. Restore from backup (choose one):
# - Use Scenario 1, 2, or 3 above

# 4. Validate restoration
python3 -c "
from flask import Flask
from utils.data_integrity_validator import validate_data
app = Flask(__name__)
validate_data(mode='database', app=app)
"
```

---

## 📊 How to Verify Your Data is Safe

### 1. Check Storage Mode

```bash
curl http://localhost:5001/api/health | python3 -m json.tool
```

**SAFE** ✅:
```json
{
  "status": "healthy",
  "database": "postgresql",
  "database_connected": true
}
```

**UNSAFE** ❌:
```json
{
  "status": "healthy",
  "database": "json",  ← DANGER: Data will be lost on restart!
  "database_connected": false
}
```

### 2. Verify Backups Are Working

```bash
# Check local backups
ls -lh backend/backups/
ls -lh backend/emergency_backups/

# Check S3 backups (if configured)
aws s3 ls s3://roomieroster-backups-YOUR_ID/

# Verify Neon backups
# Log into console.neon.tech → Your Project → Backups
```

### 3. Test Recovery Process

**IMPORTANT**: Test recovery BEFORE you need it!

```bash
# 1. Create test backup
python3 -c "
from utils.emergency_recovery import emergency_recovery
backup = emergency_recovery.create_emergency_backup(reason='test')
print(f'Test backup created: {backup}')
"

# 2. Make a small change (add a test chore in the UI)

# 3. Restore from backup
python3 -c "
from utils.emergency_recovery import emergency_recovery
success = emergency_recovery.restore_from_backup()
print(f'Test restoration: {\"PASS\" if success else \"FAIL\"}')
"

# 4. Verify the test chore is gone (confirms restore worked)
```

---

## 🎯 Pre-Deployment Checklist

Before deploying to production:

- [ ] PostgreSQL database configured (Neon recommended)
- [ ] `DATABASE_URL` set in `.env` file
- [ ] Data migrated from JSON to PostgreSQL
- [ ] `/api/health` returns `"database": "postgresql"`
- [ ] Automated backups configured (local or S3)
- [ ] Backup restoration tested successfully
- [ ] Monitoring set up (UptimeRobot or Sentry)
- [ ] All environment variables set on Render:
  - [ ] `DATABASE_URL`
  - [ ] `GOOGLE_CLIENT_ID`
  - [ ] `GOOGLE_CLIENT_SECRET`
  - [ ] `FLASK_SECRET_KEY`
  - [ ] `ROOMIE_WHITELIST`
- [ ] SSL enforced (`?sslmode=require` in DATABASE_URL)
- [ ] Emergency recovery system tested

---

## 📚 Additional Resources

### Documentation Files
- `DATABASE_SETUP_GUIDE.md` - Detailed database setup instructions
- `API_SETUP_GUIDE.md` - Google OAuth configuration
- `CLAUDE.md` - Complete application architecture and development guide

### Backup Scripts
- `backend/scripts/backup_database.sh` - Local automated backups
- `backend/scripts/backup_to_s3.sh` - Cloud backup with AWS S3
- `backend/scripts/setup_production_persistence.py` - Automated setup wizard

### Utility Modules
- `backend/utils/data_integrity_validator.py` - Data validation system
- `backend/utils/emergency_recovery.py` - Emergency backup/restore
- `backend/utils/database_config.py` - Database configuration
- `backend/utils/database_init.py` - Database initialization
- `backend/migrate_data.py` - Data migration script

### GitHub Workflows
- `.github/workflows/database-backup.yml` - Automated GitHub Actions backups

---

## 🆘 Need Help?

1. **Check application logs**:
   ```bash
   tail -f backend/logs/*.log
   ```

2. **Run data integrity validation**:
   ```bash
   cd backend
   python3 -c "from utils.data_integrity_validator import validate_data; validate_data(mode='json')"
   ```

3. **Check database connection**:
   ```bash
   psql $DATABASE_URL -c "SELECT version();"
   ```

4. **Verify environment variables**:
   ```bash
   cat .env | grep DATABASE_URL
   ```

5. **Review troubleshooting section** in `DATABASE_SETUP_GUIDE.md`

---

## ✨ Summary

**Your data was being lost because**:
- App was using JSON files (ephemeral on cloud platforms)
- No PostgreSQL database configured
- Container restarts wiped all data

**Now your data is protected by**:
1. ✅ PostgreSQL persistent database (Neon)
2. ✅ Automated setup script for easy migration
3. ✅ Data integrity validation system
4. ✅ Emergency recovery with automatic backups
5. ✅ Multiple backup layers (local, S3, Neon)
6. ✅ Monitoring and health checks
7. ✅ Comprehensive recovery procedures

**Next action**: Run the setup script!
```bash
python3 backend/scripts/setup_production_persistence.py
```

**Your data will be safe forever!** 🎉
