#!/bin/bash
# Weekly maintenance script for breeds database
# Schedule: Every Sunday at 2:00 AM UTC

# Set working directory
cd /Users/sergiubiris/Desktop/lupito-content

# Activate virtual environment
source venv/bin/activate

# Run maintenance job
python3 breeds_weekly_maintenance.py >> logs/breeds_maintenance.log 2>&1

# Check if successful
if [ $? -eq 0 ]; then
    echo "[$(date)] Weekly maintenance completed successfully" >> logs/breeds_maintenance.log
else
    echo "[$(date)] Weekly maintenance failed with error code $?" >> logs/breeds_maintenance.log
fi

# Deactivate virtual environment
deactivate

# Optional: Send notification (uncomment and configure as needed)
# mail -s "Breeds Weekly Maintenance Report" admin@example.com < reports/BREEDS_SPOTCHECK.md