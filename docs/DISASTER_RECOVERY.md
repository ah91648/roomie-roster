# Disaster Recovery Guide for RoomieRoster

**Purpose:** Comprehensive procedures for recovering from data loss, corruption, or system failures.

**Last Updated:** 2025-10-13

---

## 🚨 Emergency Response Process

### When to Use This Guide

Use this guide if you experience:
- Data loss or corruption
- Accidental deletion of critical data
- Database connection failures
- Application crashes with data integrity issues
- Need to rollback to previous state
- Container restart resulted in data loss (shouldn't happen with PostgreSQL!)

### Emergency Contact Information

- **Production URL:** https://roomie-roster.onrender.com
- **Health Check:** https://roomie-roster.onrender.com/api/health
- **Neon Dashboard:** https://console.neon.tech
- **Render Dashboard:** https://dashboard.render.com
- **GitHub Repository:** https://github.com/[your-repo]

---

## 🎯 Recovery Scenarios

### Scenario 1: Data Lost Recently (< 7 Days)

**Symptoms:**
- Recent data is missing
- Database shows older state
- Changes from last few days are gone

**Solution: Use Neon Point-in-Time Recovery**

#### Step 1: Determine Recovery Point

Find the last known good state:
```bash
# Check when data was last correct
# Look at application logs or user reports
```

#### Step 2: Create Recovery Branch via Neon Dashboard

1. Log into [console.neon.tech](https://console.neon.tech)
2. Select your `roomieroster` project
3. Go to "Branches" section
4. Click "Create Branch"
5. Select "Restore from history"
6. Choose date and time to restore to (e.g., "2 days ago at 3:00 PM")
7. Give the branch a name: `recovery-YYYY-MM-DD`
8. Click "Create Branch"

#### Step 3: Get New Connection String

1. In the new branch, click "Connection Details"
2. Copy the new DATABASE_URL
3. Note: This is a separate database branch

#### Step 4: Verify Recovery

Test the recovery branch before switching:

```bash
# Temporarily use recovery branch
export DATABASE_URL="postgresql://[recovery-branch-url]"

# Start app locally
python3 launch_app.py

# Check data at http://localhost:3000
# Verify data is correct
```

#### Step 5: Switch Production to Recovery Branch

**Option A: Update Render Environment Variable**
1. Go to Render dashboard
2. Update `DATABASE_URL` to the recovery branch URL
3. Save (triggers redeploy)

**Option B: Make Recovery Branch Primary (Permanent)**
1. In Neon console, go to branch settings
2. Promote recovery branch to primary
3. Original DATABASE_URL now points to recovered data

#### Step 6: Verify Production

```bash
curl https://roomie-roster.onrender.com/api/health
# Verify database is connected

# Test in browser
# Confirm data is correct
```

---

### Scenario 2: Restore from Emergency Backup (JSON Files)

**Symptoms:**
- PostgreSQL database corrupted or unavailable
- Need to restore from application-level backups
- Recent changes need to be recovered

**Solution: Use Emergency Recovery System**

#### Step 1: List Available Backups

```bash
cd backend

python3 -c "
from utils.emergency_recovery import emergency_recovery

backups = emergency_recovery.list_backups()
print(f'Found {len(backups)} backups:')
for i, backup in enumerate(backups):
    print(f'{i}: {backup[\"filename\"]}')
    print(f'   Created: {backup[\"created\"]}')
    print(f'   Size: {backup[\"size_mb\"]} MB')
    print(f'   Reason: {backup[\"reason\"]}')
    print()
"
```

#### Step 2: Select Backup to Restore

Choose the backup closest to the desired recovery point.

#### Step 3: Create Pre-Restore Backup

Safety measure before restoration:

```bash
python3 -c "
from utils.emergency_recovery import emergency_recovery
emergency_recovery.create_emergency_backup(reason='pre_restore_safety')
print('Safety backup created')
"
```

#### Step 4: Restore from Backup

```bash
# Restore from most recent backup
python3 -c "
from utils.emergency_recovery import emergency_recovery
success = emergency_recovery.restore_from_backup()
print(f'Restoration: {\"SUCCESS\" if success else \"FAILED\"}')
"

# OR restore from specific backup file
python3 -c "
from utils.emergency_recovery import emergency_recovery
backup_path = 'backend/emergency_backups/emergency_backup_YYYYMMDD_HHMMSS_reason.json.gz'
success = emergency_recovery.restore_from_backup(backup_path)
print(f'Restoration: {\"SUCCESS\" if success else \"FAILED\"}')
"
```

#### Step 5: Restart Application

```bash
# If running locally
pkill -f "python.*launch_app"
python3 launch_app.py

# If on Render
# Go to Render dashboard → Manual Deploy → Deploy latest commit
```

#### Step 6: Verify Restoration

1. Check health endpoint
2. Verify data in UI
3. Test CRUD operations
4. Confirm data matches expected state

---

### Scenario 3: Restore from pg_dump Backup (S3 or Local)

**Symptoms:**
- Need to restore from scheduled backup
- Emergency backups not available
- Restoring to new database instance

**Solution: Use PostgreSQL Dump Files**

#### Step 1: List Available Backups

**From S3:**
```bash
aws s3 ls s3://roomieroster-backups-[unique-id]/backups/
```

**From Local:**
```bash
ls -lh backend/backups/
```

#### Step 2: Download Backup (if from S3)

```bash
# Download latest backup
aws s3 cp s3://roomieroster-backups-[unique-id]/backups/roomieroster_backup_YYYY-MM-DD_HH-MM-SS.sql.gz ./

# Decompress
gunzip roomieroster_backup_YYYY-MM-DD_HH-MM-SS.sql.gz
```

#### Step 3: Restore to Database

**Important:** This will REPLACE all data in the target database!

```bash
# Set target database URL
export DATABASE_URL="postgresql://..."

# Restore from backup
psql $DATABASE_URL < roomieroster_backup_YYYY-MM-DD_HH-MM-SS.sql
```

#### Step 4: Verify Restoration

```bash
# Check database connection
psql $DATABASE_URL -c "SELECT COUNT(*) FROM roommates;"

# Start application
python3 launch_app.py

# Verify in UI
```

---

### Scenario 4: Complete Database Corruption

**Symptoms:**
- Database is completely corrupted
- Cannot connect to database
- Data is inconsistent or invalid
- Need complete rebuild

**Solution: Reset and Restore from Backup**

#### Step 1: Create Final Backup of Corrupted Data

For forensic analysis:

```bash
cd backend
python3 -c "
from utils.emergency_recovery import emergency_recovery
emergency_recovery.create_emergency_backup(reason='pre_complete_reset')
print('Corrupted state backed up for analysis')
"
```

#### Step 2: Reset Database

**Option A: Create New Neon Branch**
1. Go to Neon console
2. Create fresh branch from main
3. Get new DATABASE_URL
4. Use this for clean slate

**Option B: Reset Existing Database**
```bash
# DANGER: This deletes ALL data!
python3 -c "
from utils.database_init import database_initializer
from flask import Flask
app = Flask(__name__)
with app.app_context():
    database_initializer.reset_database(app)
print('Database reset complete')
"
```

#### Step 3: Restore from Backup

Choose one of the recovery methods from Scenarios 1-3 above.

#### Step 4: Validate Data Integrity

```bash
python3 backend/scripts/verify_production_ready.py
# Should pass all checks
```

---

## 🔍 Troubleshooting Common Issues

### Issue: "Database connection failed"

**Causes:**
- DATABASE_URL incorrect
- Database server down
- Network issues
- SSL certificate problems

**Solutions:**
```bash
# Test connection manually
psql $DATABASE_URL -c "SELECT version();"

# Check SSL configuration
# DATABASE_URL should contain: ?sslmode=require

# Verify Neon database is running
# Check Neon dashboard for status
```

### Issue: "Migration failed"

**Causes:**
- Schema mismatch
- Data type conflicts
- Foreign key violations

**Solutions:**
```bash
# Check migration logs
cat backend/logs/*.log | grep -i "migration"

# Run data integrity validator
python3 -c "
from utils.data_integrity_validator import validate_data
from flask import Flask
app = Flask(__name__)
success, report = validate_data(mode='database', app=app)
print(report)
"
```

### Issue: "Restored data is incomplete"

**Causes:**
- Backup was partial
- Wrong backup restored
- Data wasn't committed before backup

**Solutions:**
1. Check backup timestamp vs. when data was created
2. Try a different backup (older one might be more complete)
3. Combine data from multiple sources:
   - Neon point-in-time recovery
   - Emergency backups
   - S3 backups

### Issue: "Cannot access Neon dashboard"

**Solutions:**
1. Reset password at [neon.tech](https://neon.tech)
2. Check email for 2FA codes
3. Contact Neon support if locked out
4. Use local backups in the meantime

---

## 📋 Recovery Verification Checklist

After any recovery procedure, verify:

- [ ] Database connection successful
  ```bash
  curl https://roomie-roster.onrender.com/api/health
  # Should return: "database": "PostgreSQL"
  ```

- [ ] All data types present:
  - [ ] Roommates (expected count: 4+)
  - [ ] Chores (expected count: 4+)
  - [ ] Assignments
  - [ ] Shopping items
  - [ ] Requests
  - [ ] Laundry slots

- [ ] CRUD operations work:
  - [ ] Can create new item
  - [ ] Can read existing items
  - [ ] Can update items
  - [ ] Can delete items

- [ ] User authentication works:
  - [ ] Google login functional
  - [ ] Sessions persist
  - [ ] Whitelisted users can access

- [ ] No errors in logs:
  ```bash
  # Check Render logs
  # No database errors
  # No authentication errors
  ```

- [ ] Monitoring shows healthy:
  - [ ] UptimeRobot shows "Up"
  - [ ] Response times normal
  - [ ] No alerts triggered

---

## 🛡️ Prevention Best Practices

### Regular Backup Verification

**Weekly:**
- Check that Neon backups are running
- Verify emergency backup count
- Test backup download from S3 (if configured)

**Monthly:**
- Perform full disaster recovery drill
- Time the recovery process
- Update documentation with learnings

### Monitoring and Alerts

- Monitor UptimeRobot for downtime
- Set up Slack/email alerts for database errors
- Review logs weekly for warnings

### Database Maintenance

- Keep DATABASE_URL secure
- Rotate credentials periodically
- Monitor database size (Neon free tier: 3GB)
- Archive old data if approaching limits

---

## 📞 Emergency Support

### If All Recovery Methods Fail

1. **Contact Neon Support:**
   - Email: support@neon.tech
   - Dashboard: console.neon.tech (support chat)
   - Include: Project ID, approximate time of issue

2. **Contact Render Support:**
   - Dashboard: dashboard.render.com (support chat)
   - Include: Service name, deployment logs

3. **Manual Data Reconstruction:**
   - Use any available data sources
   - Export from Google Calendar (if synced)
   - Roommates re-enter critical data
   - Start fresh if necessary

### Post-Incident Actions

1. **Document the incident:**
   - What happened?
   - When did it occur?
   - What was the root cause?
   - How was it resolved?

2. **Update procedures:**
   - Modify recovery docs if needed
   - Add prevention measures
   - Improve monitoring

3. **Team debrief:**
   - Share learnings
   - Update training
   - Review backup strategy

---

## 🔐 Security Considerations

### During Recovery

- **Never share DATABASE_URL publicly**
- **Use secure channels** for credentials
- **Verify backup integrity** before restoring
- **Create safety backup** before any destructive operation

### After Recovery

- **Rotate credentials** if breach suspected
- **Audit access logs** for unauthorized access
- **Review security audit:**
  ```bash
  python3 backend/scripts/production_security_audit.py
  ```

---

## ✅ Recovery Success Criteria

Recovery is successful when:

1. ✅ Application is accessible
2. ✅ Database connection established
3. ✅ All expected data is present
4. ✅ CRUD operations functional
5. ✅ Authentication working
6. ✅ No errors in logs
7. ✅ Monitoring shows healthy status
8. ✅ Users can perform normal operations

**Remember: With PostgreSQL and multiple backup layers, your data is safe!**

---

## 📚 Related Documentation

- **DATA_LOSS_PREVENTION.md** - Overall protection strategy
- **PRODUCTION_DEPLOYMENT_CHECKLIST.md** - Deployment procedures
- **MONITORING_GUIDE.md** - Monitoring and alerting setup
- **DATABASE_SETUP_GUIDE.md** - Database configuration details
