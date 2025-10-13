# Monitoring Guide for RoomieRoster

**Purpose:** Complete guide for setting up and maintaining production monitoring and alerting.

**Last Updated:** 2025-10-13

---

## 📊 Monitoring Overview

RoomieRoster uses a multi-layer monitoring approach:
1. **Application Health Checks** - Built-in health endpoint
2. **External Uptime Monitoring** - UptimeRobot (recommended)
3. **Platform Monitoring** - Render built-in tools
4. **Database Monitoring** - Neon PostgreSQL metrics

---

## 🎯 What to Monitor

### Critical Metrics

| Metric | Target | Alert Threshold | Priority |
|--------|--------|-----------------|----------|
| Uptime | 99.9% | Down for 5+ min | Critical |
| Response Time | < 500ms | > 2s | High |
| Database Connection | Active | Disconnected | Critical |
| Auth Bypass Status | Disabled | Enabled in prod | Critical |
| Storage Type | PostgreSQL | JSON files | Critical |

### Secondary Metrics

| Metric | Target | Alert Threshold | Priority |
|--------|--------|-----------------|----------|
| Memory Usage | < 80% | > 90% | Medium |
| CPU Usage | < 70% | > 85% | Medium |
| Database Size | < 2.5GB | > 2.8GB (free tier) | Medium |
| Error Rate | < 1% | > 5% | High |

---

## 🔍 Health Check Endpoint

### Endpoint Details

**URL:** `/api/health`
**Method:** GET
**Response:** JSON

**Example Response:**
```json
{
  "status": "healthy",
  "database": "PostgreSQL",
  "database_connected": true,
  "auth_bypass": false,
  "version": "1.0.0",
  "timestamp": "2025-10-13T10:30:00Z"
}
```

### Response Fields

- `status`: "healthy" or "unhealthy"
- `database`: "PostgreSQL" or "JSON" (should always be PostgreSQL in production)
- `database_connected`: Boolean indicating active database connection
- `auth_bypass`: Boolean (should always be false in production)
- `version`: Application version
- `timestamp`: Current server time (ISO 8601)

### Using Health Check

**Manual Check:**
```bash
curl https://roomie-roster.onrender.com/api/health

# Pretty print
curl https://roomie-roster.onrender.com/api/health | python3 -m json.tool
```

**Automated Script:**
```bash
#!/bin/bash
# health-check.sh

HEALTH_URL="https://roomie-roster.onrender.com/api/health"

response=$(curl -s $HEALTH_URL)
status=$(echo $response | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")

if [ "$status" == "healthy" ]; then
    echo "✅ System healthy"
    exit 0
else
    echo "❌ System unhealthy: $response"
    exit 1
fi
```

---

## 🤖 UptimeRobot Setup (Recommended)

### Why UptimeRobot?

- **Free tier:** 50 monitors, 5-minute intervals
- **Multiple alert methods:** Email, SMS, Slack, webhook
- **Status pages:** Public status page for users
- **Reliability:** 99.99% uptime for monitoring service
- **Easy setup:** 5-minute configuration

### Step-by-Step Setup

#### 1. Create Account

1. Visit [uptimerobot.com](https://uptimerobot.com)
2. Click "Sign Up Free"
3. Enter email and create password
4. Verify email address
5. Log in to dashboard

#### 2. Add Primary Monitor

1. Click "Add New Monitor"
2. Configure:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** `RoomieRoster Health Check`
   - **URL:** `https://roomie-roster.onrender.com/api/health`
   - **Monitoring Interval:** 5 minutes
   - **Monitor Timeout:** 30 seconds
   - **HTTP Method:** GET
   - **HTTP Auth Type:** None

3. Click "Create Monitor"

#### 3. Add Alert Contacts

1. Go to "My Settings" → "Alert Contacts"
2. Click "Add Alert Contact"
3. Configure:
   - **Type:** Email
   - **Name:** Your name
   - **Value:** Your email
   - **Notifications:**
     - ✅ Up
     - ✅ Down
     - ✅ Still Down (reminder)

4. Save and verify email

#### 4. Configure Advanced Settings

1. Edit the health check monitor
2. Go to "Advanced" settings:
   - **Alert When:** Down for 2 consecutive checks (10 minutes)
   - **Alert Threshold:** 2 times
   - **Keyword:** "healthy" (check response contains this word)
   - **Keyword Type:** Exists

3. Save settings

#### 5. Add Secondary Monitors (Optional)

**Frontend Monitor:**
```
Monitor Type: HTTP(s)
Friendly Name: RoomieRoster Frontend
URL: https://roomie-roster.onrender.com/
Interval: 5 minutes
Keyword: "RoomieRoster" (check HTML contains app name)
```

**API Endpoint Monitor:**
```
Monitor Type: HTTP(s)
Friendly Name: RoomieRoster API
URL: https://roomie-roster.onrender.com/api/roommates
Interval: 10 minutes
Expected Status: 401 (requires authentication, proves API is responding)
```

**Database Check Monitor:**
```
Monitor Type: Keyword
Friendly Name: RoomieRoster Database Status
URL: https://roomie-roster.onrender.com/api/health
Interval: 5 minutes
Keyword: "PostgreSQL"
Keyword Type: Exists
```

### Alert Configuration Best Practices

**Alert Escalation:**
1. **First alert (down 10 min):** Email
2. **Second alert (down 30 min):** SMS + Email
3. **Third alert (down 1 hour):** Webhook to Slack + SMS + Email

**Alert Groups:**
- Create separate alert contacts for different team members
- Set up escalation: Developer → Team Lead → CTO
- Use "Still Down" reminders every 30 minutes

---

## 🚀 Render Built-in Monitoring

### Dashboard Access

1. Log into [dashboard.render.com](https://dashboard.render.com)
2. Select your RoomieRoster service
3. View tabs:
   - **Metrics:** CPU, Memory, Network
   - **Logs:** Real-time application logs
   - **Events:** Deployments, restarts, errors

### Key Render Metrics

**CPU Usage:**
- Normal: < 50%
- Warning: 50-80%
- Critical: > 80%

**Memory Usage:**
- Free tier: 512MB
- Normal: < 400MB
- Warning: 400-480MB
- Critical: > 480MB (may trigger restart)

**Response Time:**
- Normal: < 500ms
- Warning: 500ms-2s
- Critical: > 2s

### Render Health Check Setup

1. Go to service settings
2. Find "Health Check Path"
3. Set to: `/api/health`
4. Render will:
   - Check every 30 seconds
   - Restart service if unhealthy
   - Alert on repeated failures

### Log Monitoring

**Key Log Patterns to Watch:**

**Success Indicators:**
```
✅ Database connected: PostgreSQL
✅ Loaded environment variables
Starting gunicorn
Worker booted with pid: [number]
```

**Warning Signs:**
```
⚠️  DEVELOPMENT AUTH BYPASS IS ENABLED
⚠️  Generated temporary SECRET_KEY
⚠️  Using JSON file storage
Database connection slow
```

**Critical Errors:**
```
❌ Database connection failed
❌ AUTH BYPASS REJECTED
ERROR: [any error message]
CRITICAL: [any critical message]
```

---

## 💾 Neon Database Monitoring

### Neon Console Dashboard

1. Log into [console.neon.tech](https://console.neon.tech)
2. Select your project
3. View:
   - **Usage:** Storage, compute hours
   - **Queries:** Slow queries, most frequent
   - **Connections:** Active connections

### Key Neon Metrics

**Storage:**
- Free tier limit: 3GB
- Current: Check dashboard
- Alert at: 2.5GB (83%)
- Action at: 2.8GB (93%) - archive old data

**Compute Hours:**
- Free tier: 100 hours/month
- Current: Check dashboard
- Alert at: 80 hours/month

**Connection Count:**
- Free tier: 100 concurrent
- Normal: 5-10
- Warning: > 50
- Critical: > 80

### Slow Query Monitoring

Check for slow queries in Neon dashboard:
```sql
-- Queries taking > 1 second
-- Review and optimize if found
```

---

## 📈 Custom Monitoring Scripts

### Automated Health Check Script

Create `monitor.sh`:

```bash
#!/bin/bash
# Continuous health monitoring

HEALTH_URL="https://roomie-roster.onrender.com/api/health"
ALERT_EMAIL="admin@example.com"
CHECK_INTERVAL=300  # 5 minutes

while true; do
    echo "$(date): Checking health..."

    response=$(curl -s -w "%{http_code}" $HEALTH_URL)
    http_code="${response: -3}"
    body="${response:0:${#response}-3}"

    if [ "$http_code" != "200" ]; then
        echo "❌ ALERT: HTTP $http_code"
        echo "Subject: RoomieRoster Down" | mail -s "Alert" $ALERT_EMAIL
    else
        status=$(echo $body | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
        database=$(echo $body | python3 -c "import sys, json; print(json.load(sys.stdin).get('database', 'unknown'))")

        if [ "$status" != "healthy" ]; then
            echo "❌ ALERT: Status unhealthy"
            echo "Subject: RoomieRoster Unhealthy" | mail -s "Alert" $ALERT_EMAIL
        elif [ "$database" != "PostgreSQL" ]; then
            echo "❌ ALERT: Using $database instead of PostgreSQL"
            echo "Subject: RoomieRoster Database Issue" | mail -s "Alert" $ALERT_EMAIL
        else
            echo "✅ System healthy"
        fi
    fi

    sleep $CHECK_INTERVAL
done
```

Run as background service:
```bash
chmod +x monitor.sh
nohup ./monitor.sh > monitor.log 2>&1 &
```

### Database Connection Monitor

```python
#!/usr/bin/env python3
# database-monitor.py

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, 'backend')

from flask import Flask
from utils.database_init import database_initializer

def check_database():
    """Check database connection and report status."""
    app = Flask(__name__)

    with app.app_context():
        try:
            status = database_initializer.get_database_status()

            timestamp = datetime.now().isoformat()

            if status['connected'] and status['storage_type'] == 'PostgreSQL':
                print(f"{timestamp} ✅ Database healthy: PostgreSQL connected")
                return True
            else:
                print(f"{timestamp} ❌ Database issue: {status}")
                return False

        except Exception as e:
            print(f"{timestamp} ❌ Database check failed: {str(e)}")
            return False

if __name__ == "__main__":
    while True:
        check_database()
        time.sleep(300)  # Check every 5 minutes
```

---

## 📊 Monitoring Dashboard

### Recommended Tools

1. **UptimeRobot:** External uptime monitoring
2. **Render Dashboard:** Application metrics
3. **Neon Console:** Database metrics
4. **Custom Dashboard:** Combine all metrics

### Creating Custom Dashboard

Use tools like Grafana, Datadog, or simple HTML page:

```html
<!DOCTYPE html>
<html>
<head>
    <title>RoomieRoster Status</title>
    <meta http-equiv="refresh" content="60">
</head>
<body>
    <h1>RoomieRoster Status Dashboard</h1>

    <div id="status"></div>

    <script>
        fetch('https://roomie-roster.onrender.com/api/health')
            .then(r => r.json())
            .then(data => {
                const html = `
                    <h2>Status: ${data.status}</h2>
                    <p>Database: ${data.database}</p>
                    <p>Connected: ${data.database_connected}</p>
                    <p>Auth Bypass: ${data.auth_bypass}</p>
                    <p>Last Check: ${new Date().toLocaleString()}</p>
                `;
                document.getElementById('status').innerHTML = html;
            });
    </script>
</body>
</html>
```

---

## 🚨 Alert Response Procedures

### When You Receive an Alert

**1. Acknowledge Alert**
- Verify alert is real (not false positive)
- Check UptimeRobot dashboard
- Check Render dashboard

**2. Assess Severity**
- **P0 (Critical):** Service completely down
- **P1 (High):** Degraded performance
- **P2 (Medium):** Warning threshold reached
- **P3 (Low):** Informational

**3. Initial Response**

**For P0 (Service Down):**
```bash
# Check health endpoint
curl https://roomie-roster.onrender.com/api/health

# Check Render logs
# Go to Render dashboard → Logs

# Check database status
# Go to Neon console → Project status
```

**For P1 (Degraded):**
- Review Render metrics (CPU, Memory)
- Check for error spikes in logs
- Verify database connections

**4. Resolution**

**Service Down:**
1. Restart service in Render dashboard
2. Check logs for root cause
3. Verify health after restart
4. Monitor for stability

**Database Issues:**
1. Check Neon dashboard for outages
2. Verify DATABASE_URL is correct
3. Test connection manually
4. Consider failover to backup

**5. Post-Incident**
- Document what happened
- Update runbook if needed
- Review monitoring thresholds
- Implement prevention measures

---

## 📅 Routine Monitoring Tasks

### Daily
- [ ] Check UptimeRobot dashboard (quick glance)
- [ ] Review Render logs for errors
- [ ] Verify no user-reported issues

### Weekly
- [ ] Review response time trends
- [ ] Check database storage usage
- [ ] Review error patterns in logs
- [ ] Test health endpoint manually

### Monthly
- [ ] Review all monitoring metrics
- [ ] Update alert thresholds if needed
- [ ] Test alert escalation
- [ ] Perform monitoring drill
- [ ] Review and archive old logs

---

## 📞 Support and Escalation

### Contact Information

**Internal Team:**
- Developer: [email]
- DevOps: [email]
- On-Call: [phone]

**External Support:**
- Render: support@render.com
- Neon: support@neon.tech
- UptimeRobot: support@uptimerobot.com

### Escalation Matrix

| Issue | First Contact | Escalate After | Escalate To |
|-------|---------------|----------------|-------------|
| Service Down | Developer | 30 min | DevOps |
| Database Down | Developer | 15 min | DevOps + Neon |
| Security Alert | Security Team | Immediate | CTO |
| Performance | Developer | 2 hours | DevOps |

---

## ✅ Monitoring Health Checklist

Your monitoring is healthy when:

- [ ] UptimeRobot shows all monitors "Up"
- [ ] No critical alerts in last 24 hours
- [ ] Response times < 500ms average
- [ ] Database connected (PostgreSQL)
- [ ] Auth bypass disabled in production
- [ ] Error rate < 1%
- [ ] All team members receive alerts
- [ ] Alert escalation tested monthly
- [ ] Monitoring documentation up to date

**With proper monitoring, you'll know about issues before your users do!**
