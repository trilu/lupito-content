# WEEKLY MAINTENANCE SETUP

## Cron Job Configuration

Add to crontab (`crontab -e`):

```bash
# Run weekly catalog maintenance every Sunday at 2 AM
0 2 * * 0 cd /Users/sergiubiris/Desktop/lupito-content && source venv/bin/activate && python3 weekly_catalog_maintenance.py >> logs/weekly_maintenance.log 2>&1
```

## Manual Run

To run maintenance manually:

```bash
cd /Users/sergiubiris/Desktop/lupito-content
source venv/bin/activate
python3 weekly_catalog_maintenance.py
```

## What It Does

1. **Enrichment Check**: Identifies products needing enrichment
2. **MV Refresh**: Attempts to refresh materialized views
3. **Brand Health**: Checks top brands for quality issues
4. **Production Health**: Verifies production isn't empty
5. **Gate Compliance**: Measures against quality gates
6. **Report Generation**: Creates health report in docs/

## Alert Conditions

The script will flag issues if:
- Production has < 50 SKUs
- Any brand has < 70% coverage
- Quality gates are not met
- Enrichment backlog is > 100 products

## Log Location

Logs are saved to: `logs/weekly_maintenance.log`
