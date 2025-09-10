# Breeds Database Maintenance Setup Guide

## Overview

This guide covers the setup and configuration of the automated maintenance system for the breeds database, which has achieved Grade A+ quality (98.2% operational coverage).

---

## Current Status

- **Database Quality:** Grade A+ (98.2% operational coverage)
- **Total Breeds:** 583
- **Coverage Metrics:**
  - Size Category: 100%
  - Growth/Senior Months: 100%
  - Weight Data: 92.8%
  - Height Data: 88.7%

---

## Maintenance System Components

### 1. Weekly Spot-Check Script
**File:** `breeds_weekly_maintenance.py`

This script performs weekly health checks on the database:
- Randomly selects 5 breeds
- Checks for stale data (>180 days old)
- Identifies conflicts and missing data
- Attempts to re-scrape when needed
- Logs results to `reports/BREEDS_SPOTCHECK.md`

### 2. Cron Job Wrapper
**File:** `breeds_maintenance_cron.sh`

Shell script that:
- Activates the Python virtual environment
- Runs the maintenance script
- Logs output to `logs/breeds_maintenance.log`
- Handles errors gracefully

### 3. Cron Configuration
**File:** `crontab_example.txt`

Contains example cron schedules for automation.

---

## Setup Instructions

### Prerequisites

1. **Python Environment**
   ```bash
   # Ensure virtual environment exists
   cd /Users/sergiubiris/Desktop/lupito-content
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   ```bash
   # Ensure .env file contains:
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_KEY=your_service_key
   ```

3. **Create Logs Directory**
   ```bash
   mkdir -p logs
   mkdir -p reports
   ```

### Setting Up the Cron Job

#### Step 1: Make Scripts Executable
```bash
chmod +x breeds_maintenance_cron.sh
chmod +x breeds_weekly_maintenance.py
```

#### Step 2: Test the Script Manually
```bash
# Test the Python script directly
source venv/bin/activate
python3 breeds_weekly_maintenance.py

# Test the cron wrapper
./breeds_maintenance_cron.sh
```

#### Step 3: Configure Crontab

1. **Open crontab editor:**
   ```bash
   crontab -e
   ```

2. **Add the maintenance job:**
   ```bash
   # Weekly breeds maintenance - Every Sunday at 2:00 AM
   0 2 * * 0 /Users/sergiubiris/Desktop/lupito-content/breeds_maintenance_cron.sh
   ```

   **Alternative schedules:**
   ```bash
   # Every Monday at 3:00 AM
   0 3 * * 1 /Users/sergiubiris/Desktop/lupito-content/breeds_maintenance_cron.sh
   
   # Every 7 days at midnight
   0 0 */7 * * /Users/sergiubiris/Desktop/lupito-content/breeds_maintenance_cron.sh
   
   # For testing: Every hour
   0 * * * * /Users/sergiubiris/Desktop/lupito-content/breeds_maintenance_cron.sh
   ```

3. **Save and exit** (in vim: `:wq`)

#### Step 4: Verify Cron Job

1. **List active cron jobs:**
   ```bash
   crontab -l
   ```

2. **Check cron service status:**
   ```bash
   # On macOS
   sudo launchctl list | grep cron
   
   # On Linux
   systemctl status cron
   ```

3. **Monitor logs:**
   ```bash
   # Watch maintenance log
   tail -f logs/breeds_maintenance.log
   
   # Check spot-check reports
   tail -f reports/BREEDS_SPOTCHECK.md
   ```

---

## Production Deployment on Server

### For Linux/Ubuntu Server

1. **Install dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install python3-venv python3-pip
   ```

2. **Clone repository:**
   ```bash
   git clone https://github.com/trilu/lupito-content.git
   cd lupito-content
   ```

3. **Setup environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   nano .env
   ```

5. **Update paths in cron script:**
   ```bash
   # Edit breeds_maintenance_cron.sh
   nano breeds_maintenance_cron.sh
   # Update the cd path to your installation directory
   ```

6. **Setup cron job:**
   ```bash
   crontab -e
   # Add the weekly job with correct path
   0 2 * * 0 /path/to/lupito-content/breeds_maintenance_cron.sh
   ```

### For Docker Deployment

Create a `docker-compose.yml`:
```yaml
version: '3.8'
services:
  breeds-maintenance:
    build: .
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
    volumes:
      - ./logs:/app/logs
      - ./reports:/app/reports
    command: crond -f -l 2
```

Add to Dockerfile:
```dockerfile
# Install cron
RUN apt-get update && apt-get install -y cron

# Add crontab
COPY crontab /etc/cron.d/breeds-maintenance
RUN chmod 0644 /etc/cron.d/breeds-maintenance
RUN crontab /etc/cron.d/breeds-maintenance
```

---

## Monitoring and Alerts

### Log Monitoring

1. **Check recent runs:**
   ```bash
   grep "$(date +%Y-%m-%d)" logs/breeds_maintenance.log
   ```

2. **Check for errors:**
   ```bash
   grep "ERROR\|FAILED" logs/breeds_maintenance.log
   ```

3. **View spot-check history:**
   ```bash
   cat reports/BREEDS_SPOTCHECK.md
   ```

### Setting Up Email Alerts (Optional)

1. **Install mail utilities:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install mailutils
   
   # macOS
   brew install mailutils
   ```

2. **Update cron script to send alerts:**
   ```bash
   # Add to breeds_maintenance_cron.sh
   if [ $? -ne 0 ]; then
       echo "Breeds maintenance failed" | mail -s "Alert: Breeds Maintenance Failed" admin@example.com
   fi
   ```

### Slack/Discord Notifications (Optional)

Add webhook notifications to `breeds_weekly_maintenance.py`:
```python
import requests

def send_slack_notification(message):
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if webhook_url:
        requests.post(webhook_url, json={'text': message})

# In main():
if failed_updates > 0:
    send_slack_notification(f"Breeds maintenance: {failed_updates} breeds failed to update")
```

---

## Maintenance Operations

### Manual Overrides

When urgent corrections are needed:

```sql
-- Add override in Supabase SQL Editor
INSERT INTO breeds_overrides (
    breed_slug, 
    size_category, 
    adult_weight_avg_kg, 
    override_reason
) VALUES (
    'breed-slug-here',
    'l',
    35.0,
    'Correcting weight based on AKC standard'
);
```

### Force Re-scrape Specific Breed

```python
# Run manually
source venv/bin/activate
python3 -c "
from breeds_weekly_maintenance import rescrape_breed
success, message = rescrape_breed('labrador-retriever', 'Labrador Retriever')
print(f'Result: {message}')
"
```

### View Current Quality Metrics

```sql
-- Run in Supabase SQL Editor
SELECT * FROM breeds_quality_metrics;
```

---

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Fix script permissions
   chmod +x breeds_maintenance_cron.sh
   ```

2. **Virtual Environment Not Found**
   ```bash
   # Recreate venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Cron Job Not Running**
   ```bash
   # Check cron service
   service cron status
   
   # Restart if needed
   sudo service cron restart
   ```

4. **Database Connection Issues**
   ```bash
   # Verify .env file
   cat .env | grep SUPABASE
   
   # Test connection
   python3 -c "from supabase import create_client; print('Connected')"
   ```

### Logs Location

- **Maintenance logs:** `logs/breeds_maintenance.log`
- **Spot-check reports:** `reports/BREEDS_SPOTCHECK.md`
- **Cron logs:** `/var/log/cron` (Linux) or `/var/log/system.log` (macOS)

---

## Best Practices

1. **Regular Monitoring**
   - Check logs weekly after maintenance runs
   - Review spot-check reports for patterns
   - Monitor quality metrics monthly

2. **Backup Before Major Changes**
   ```sql
   -- Create backup table
   CREATE TABLE breeds_details_backup AS SELECT * FROM breeds_details;
   ```

3. **Test Changes First**
   - Run maintenance script manually before scheduling
   - Test on a subset of breeds first
   - Verify results in spot-check report

4. **Keep Dependencies Updated**
   ```bash
   source venv/bin/activate
   pip install --upgrade -r requirements.txt
   ```

---

## Support and Resources

- **Repository:** https://github.com/trilu/lupito-content
- **Quality Report:** `reports/BREEDS_QUALITY_FINAL.md`
- **Database Schema:** `grade_a_schema.sql`
- **Production View:** `publish_breeds_view.sql`

---

## Maintenance Schedule

| Task | Frequency | Automated | Output |
|------|-----------|-----------|---------|
| Spot-check 5 breeds | Weekly | Yes | BREEDS_SPOTCHECK.md |
| Re-scrape stale data | Weekly | Yes | breeds_maintenance.log |
| Quality metrics review | Monthly | No | Manual check |
| Full database audit | Quarterly | No | Manual report |

---

*Last Updated: 2025-09-10*  
*Database Quality: Grade A+ (98.2%)*