# Database Setup Guide for RoomieRoster

## Critical Issue: Current Data Loss Risk

**Your application is currently using JSON file storage, which means:**
- ❌ All data will be lost on container restarts in production
- ❌ No automated backups
- ❌ No audit trail for changes
- ❌ No transaction safety

**This guide will set up a production-ready PostgreSQL database with:**
- ✅ Persistent storage that survives restarts
- ✅ Automated daily backups
- ✅ Complete audit logging
- ✅ Data integrity constraints
- ✅ Point-in-time recovery
- ✅ Health monitoring

---

## Part 1: PostgreSQL Setup with Neon (Recommended)

### Why Neon PostgreSQL?

Neon is the recommended database provider for RoomieRoster because:
- **Free tier**: 3GB storage, enough for most households
- **Built-in backups**: Point-in-time restore for up to 7 days (30 days on paid plans)
- **Serverless**: Automatic scaling and sleep when inactive
- **Zero maintenance**: No server management required
- **Production-ready**: Enterprise-grade reliability

### Step 1: Create Neon Account and Database

1. **Sign up for Neon**:
   - Visit [neon.tech](https://neon.tech)
   - Click "Sign Up" and create an account (free)
   - Verify your email

2. **Create a New Project**:
   - Click "Create Project"
   - Name: `roomieroster` (or your preference)
   - Region: Choose closest to your users
   - Click "Create Project"

3. **Get Your Connection String**:
   - After creation, you'll see a connection string like:
   ```
   postgresql://username:password@ep-xxx-pooler.us-east-2.aws.neon.tech/dbname?sslmode=require
   ```
   - **Copy this entire string** - you'll need it in the next step

### Step 2: Configure Environment Variables

1. **Edit your `.env` file**:
   ```bash
   cd /path/to/your/roomieroster/project
   nano .env  # or use any text editor
   ```

2. **Add/Update these lines**:
   ```bash
   # === DATABASE CONFIGURATION ===
   # Replace with your actual Neon connection string
   DATABASE_URL=postgresql://username:password@ep-xxx-pooler.us-east-2.aws.neon.tech/dbname?sslmode=require

   # === REQUIRED FOR PRODUCTION ===
   GOOGLE_CLIENT_ID=your_google_client_id_here
   GOOGLE_CLIENT_SECRET=your_google_client_secret_here
   FLASK_SECRET_KEY=your_32_character_hex_string_here
   ROOMIE_WHITELIST=your_email@example.com,roommate@example.com
   ```

3. **Generate a secure Flask secret key** (if you haven't already):
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Save the file** and verify no syntax errors

### Step 3: Migrate Your Existing Data

Your application already has a migration script that will safely transfer all your JSON data to PostgreSQL.

1. **Run the migration**:
   ```bash
   cd backend
   python3 migrate_data.py
   ```

2. **Expected output**:
   ```
   🔄 Starting data migration from JSON to PostgreSQL...
   ✅ Database tables created successfully
   📊 Migrating roommates... (4 records)
   📊 Migrating chores... (4 records)
   📊 Migrating assignments... (4 records)
   ✅ Migration completed successfully!

   📈 Migration Summary:
      Roommates: 4
      Chores: 4
      Assignments: 4
      Shopping Items: 0
      Requests: 0
      Laundry Slots: 0
   ```

3. **Verify migration success**:
   ```bash
   curl http://localhost:5001/api/health
   ```

   Should return:
   ```json
   {
     "status": "healthy",
     "database": "postgresql",
     "version": "1.0.0"
   }
   ```

### Step 4: Start the Application with PostgreSQL

1. **Launch the application**:
   ```bash
   python3 launch_app.py
   ```

2. **Look for these log messages**:
   ```
   ✅ Database connection successful
   ✅ Using PostgreSQL for data storage
   📊 Loaded: 4 chores, 4 roommates from database
   ```

3. **Verify in browser**: Open http://localhost:3000
   - All your existing data should be visible
   - Create a test chore to verify database writes work

---

## Part 2: Automated Backup System

Now that PostgreSQL is configured, let's set up automated backups to prevent any data loss.

### Backup Strategy

RoomieRoster will use a **dual-layer backup strategy**:

1. **Neon's Built-in Backups** (Automatic):
   - Point-in-time restore for 7 days (free tier) or 30 days (paid)
   - Instant recovery to any moment in time
   - No configuration needed - already active!

2. **External pg_dump Backups** (Your responsibility):
   - Daily backups stored in AWS S3 or local storage
   - Long-term retention (1+ years)
   - Compliance and disaster recovery
   - Full control over backup lifecycle

### Option A: Local Automated Backups (Simplest)

For development or small deployments, use local backups:

1. **Create the backup script** (already created for you in `/backend/scripts/backup_database.sh`)

2. **Test the backup manually**:
   ```bash
   cd backend/scripts
   chmod +x backup_database.sh
   ./backup_database.sh
   ```

3. **Set up daily automated backups** using cron:
   ```bash
   crontab -e
   ```

   Add this line (runs daily at 2 AM):
   ```
   0 2 * * * /path/to/backend/scripts/backup_database.sh >> /var/log/roomieroster_backup.log 2>&1
   ```

4. **Verify backups are created**:
   ```bash
   ls -lh backend/backups/
   ```

### Option B: Cloud Backups with AWS S3 (Production)

For production deployments, use AWS S3 for durable, off-site backups:

1. **Prerequisites**:
   - AWS account (free tier sufficient)
   - AWS CLI installed and configured

2. **Create S3 bucket**:
   ```bash
   aws s3 mb s3://roomieroster-backups-YOUR_UNIQUE_ID
   aws s3api put-bucket-versioning --bucket roomieroster-backups-YOUR_UNIQUE_ID --versioning-configuration Status=Enabled
   ```

3. **Configure backup with S3** (script already created for you in `/backend/scripts/backup_to_s3.sh`)

4. **Set up automated S3 backups**:
   ```bash
   crontab -e
   ```

   Add:
   ```
   0 2 * * * /path/to/backend/scripts/backup_to_s3.sh >> /var/log/roomieroster_backup_s3.log 2>&1
   ```

### Option C: GitHub Actions Automated Backups (Free for Public Repos)

For projects hosted on GitHub, use GitHub Actions for free automated backups:

1. **Create GitHub Secrets**:
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `DATABASE_URL`: Your Neon connection string
     - `AWS_ACCESS_KEY_ID`: Your AWS access key
     - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
     - `S3_BUCKET_NAME`: `roomieroster-backups-YOUR_ID`

2. **The workflow file is already created** at `.github/workflows/database-backup.yml`

3. **Workflow will run**:
   - Daily at 2 AM UTC
   - Can be triggered manually from Actions tab
   - Keeps 30 days of backups automatically

---

## Part 3: Data Recovery Procedures

### Scenario 1: Restore from Recent Time (Last 7 Days)

Using Neon's built-in point-in-time restore:

1. **Via Neon Dashboard**:
   - Log into [console.neon.tech](https://console.neon.tech)
   - Select your project
   - Go to "Branches" → "Restore"
   - Choose the date/time to restore to
   - Click "Create Branch"
   - Update your `DATABASE_URL` to point to the restored branch

2. **Via Neon CLI** (faster):
   ```bash
   # Install Neon CLI
   npm install -g neonctl

   # Restore to 2 days ago
   neonctl branch create --restore-to-parent='2 days ago'
   ```

### Scenario 2: Restore from pg_dump Backup

If you need to restore from your external backups:

1. **List available backups**:
   ```bash
   ls -lh backend/backups/
   # or for S3
   aws s3 ls s3://roomieroster-backups-YOUR_ID/
   ```

2. **Download backup** (if using S3):
   ```bash
   aws s3 cp s3://roomieroster-backups-YOUR_ID/backup_2025-10-12.sql.gz ./
   ```

3. **Restore the backup**:
   ```bash
   # Decompress
   gunzip backup_2025-10-12.sql.gz

   # Restore to database
   psql $DATABASE_URL < backup_2025-10-12.sql
   ```

4. **Verify restoration**:
   ```bash
   python3 launch_app.py
   # Check that all data is present
   ```

### Scenario 3: Complete Database Reset (CAUTION!)

If you need to completely reset and recreate:

```bash
cd backend
python3 -c "
from utils.database_init import database_initializer
from flask import Flask
app = Flask(__name__)
database_initializer.reset_database(app)
"
```

Then restore from backup using Scenario 2.

---

## Part 4: Monitoring and Health Checks

### Built-in Health Check Endpoint

RoomieRoster includes a comprehensive health check:

```bash
curl http://localhost:5001/api/health
```

**Response when healthy**:
```json
{
  "status": "healthy",
  "database": "postgresql",
  "version": "1.0.0",
  "database_connected": true,
  "tables_exist": true,
  "data_integrity": "ok"
}
```

**Response when unhealthy**:
```json
{
  "status": "unhealthy",
  "database": "json_fallback",
  "error": "Database connection failed",
  "database_connected": false
}
```

### Set Up Monitoring (Optional but Recommended)

#### Option 1: Simple Uptime Monitoring

Use a free service like [UptimeRobot](https://uptimerobot.com):
1. Create an account
2. Add a monitor for `https://your-app.onrender.com/api/health`
3. Set check interval to 5 minutes
4. Add email/SMS alerts

#### Option 2: Advanced Monitoring with Sentry

1. **Install Sentry**:
   ```bash
   cd backend
   pip install sentry-sdk[flask]
   echo "sentry-sdk[flask]==1.40.0" >> requirements.txt
   ```

2. **Configure Sentry** (code already added to `backend/app.py`)

3. **Set environment variable**:
   ```bash
   echo "SENTRY_DSN=your_sentry_dsn_here" >> .env
   ```

---

## Part 5: Security Best Practices

### Database Connection Security

1. **Always use SSL connections** (Neon enforces this):
   ```
   DATABASE_URL=postgresql://...?sslmode=require
   ```

2. **Never commit `.env` file** to git:
   ```bash
   echo ".env" >> .gitignore
   ```

3. **Use read-only replicas** for reporting (Neon paid feature)

### Access Control

1. **Whitelist roommate emails**:
   ```bash
   ROOMIE_WHITELIST=person1@gmail.com,person2@gmail.com
   ```

2. **Rotate database password** every 90 days:
   - Generate new password in Neon dashboard
   - Update `DATABASE_URL` in `.env`
   - Restart application

3. **Monitor failed login attempts**:
   ```bash
   # Check application logs
   tail -f backend/logs/*.log | grep "authentication failed"
   ```

---

## Part 6: Performance Optimization

### Database Indexing

RoomieRoster automatically creates these indexes:
- `roommates.id` (primary key)
- `chores.id` (primary key)
- `assignments.roommate_id` (foreign key)
- `assignments.chore_id` (foreign key)
- `assignments.assigned_date` (for sorting)

### Connection Pooling

For production, use connection pooling:

1. **Neon pooler is already enabled** in your connection string (if it has `-pooler.` in the hostname)

2. **For high-traffic sites**, adjust pool size in `backend/utils/database_config.py`:
   ```python
   pool_size=20,  # Default is 5
   max_overflow=40  # Default is 10
   ```

### Query Optimization

Monitor slow queries:
```sql
-- Run in Neon SQL Editor
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Troubleshooting

### Issue: "Database connection failed"

**Solution**:
1. Verify `DATABASE_URL` is correct in `.env`
2. Check Neon dashboard - is the project active?
3. Verify SSL mode: `?sslmode=require` at end of URL
4. Test connection:
   ```bash
   psql $DATABASE_URL -c "SELECT version();"
   ```

### Issue: "Migration failed - tables already exist"

**Solution**:
```bash
cd backend
python3 -c "
from utils.database_init import database_initializer
from flask import Flask
app = Flask(__name__)
database_initializer.reset_database(app)
"
python3 migrate_data.py
```

### Issue: "Application still using JSON files"

**Solution**:
1. Verify `DATABASE_URL` is set in `.env`
2. Restart the application
3. Check logs for database initialization messages
4. Run: `curl http://localhost:5001/api/health` and verify `"database": "postgresql"`

### Issue: "Backup script fails"

**Solution**:
1. Verify `pg_dump` is installed: `pg_dump --version`
2. Install PostgreSQL client tools:
   ```bash
   # macOS
   brew install postgresql@15

   # Ubuntu/Debian
   sudo apt-get install postgresql-client
   ```
3. Verify `DATABASE_URL` is set: `echo $DATABASE_URL`

---

## Summary Checklist

Before going to production, verify:

- [ ] PostgreSQL configured with Neon
- [ ] `DATABASE_URL` set in `.env`
- [ ] Data migrated successfully
- [ ] Application connects to PostgreSQL (not JSON files)
- [ ] Automated backups configured (local or S3)
- [ ] Backup restoration tested at least once
- [ ] Health check endpoint returning `"database": "postgresql"`
- [ ] Monitoring set up (UptimeRobot or similar)
- [ ] All environment variables set on Render
- [ ] SSL enforced (`sslmode=require`)
- [ ] Roommate whitelist configured

---

## Next Steps

1. **Run the setup**: Follow Part 1 to migrate to PostgreSQL
2. **Set up backups**: Choose Option A, B, or C from Part 2
3. **Test recovery**: Practice restoring from a backup (Part 3)
4. **Monitor**: Set up health monitoring (Part 4)

**Need help?** Check the troubleshooting section or review the logs in `backend/logs/`.
