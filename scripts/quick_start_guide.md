# Quick Start Guide - Multi-Orchestrator Scaling

## 🚀 Launch Scaled Scraping (20 Concurrent Scrapers)

### Quick Launch
```bash
# Start all 4 orchestrator instances (20 scrapers total)
./scripts/start_multi_orchestrators.sh

# Monitor progress 
python scripts/multi_orchestrator_dashboard.py

# Continuous monitoring (updates every 30s)
python scripts/multi_orchestrator_dashboard.py --continuous
```

### Manual Launch (Individual Instances)
```bash
# Terminal 1 - Instance 1 (US, GB, DE, CA, FR)
source venv/bin/activate
python scripts/scraper_orchestrator.py --instance 1 --offset-start 0

# Terminal 2 - Instance 2 (IT, ES, NL, AU, NO)  
source venv/bin/activate
python scripts/scraper_orchestrator.py --instance 2 --offset-start 300

# Terminal 3 - Instance 3 (US, GB, DE, CA, FR)
source venv/bin/activate  
python scripts/scraper_orchestrator.py --instance 3 --offset-start 600

# Terminal 4 - Instance 4 (IT, ES, NL, AU, NO)
source venv/bin/activate
python scripts/scraper_orchestrator.py --instance 4 --offset-start 900
```

## 📊 Monitoring Commands

### Dashboard Options
```bash
# Single snapshot
python scripts/multi_orchestrator_dashboard.py

# Continuous updates (Ctrl+C to stop)
python scripts/multi_orchestrator_dashboard.py --continuous

# Enhanced quick status
./scripts/quick_status.sh

# Watch process status
watch -n 10 "ps aux | grep -E '(orchestrator|scraper)'"
```

### Log Files
```bash
# View orchestrator logs
tail -f logs/orchestrators/instance_1.log
tail -f logs/orchestrators/instance_2.log
tail -f logs/orchestrators/instance_3.log
tail -f logs/orchestrators/instance_4.log

# All logs at once
tail -f logs/orchestrators/*.log
```

## 🎯 Expected Performance

| Metric | Before | After (4x) | Improvement |
|--------|---------|------------|-------------|
| **Scrapers** | 5 | 20 | 4x |
| **Countries** | 5 | 10 | 2x diversity |
| **Rate** | 150/hr | 300-500/hr | 3-4x |
| **Time to 6K** | 40 hours | 12-20 hours | 2-3x faster |

## 🛑 Stop All Instances

```bash
# Graceful shutdown of all orchestrators and scrapers
./scripts/stop_all_orchestrators.sh

# Emergency force kill
pkill -9 -f orchestrator
pkill -9 -f scraper
```

## 🔧 Architecture Overview

**Instance Distribution:**
- **Instance 1**: Offset 0-299, Countries: US🇺🇸, GB🇬🇧, DE🇩🇪, CA🇨🇦, FR🇫🇷
- **Instance 2**: Offset 300-599, Countries: IT🇮🇹, ES🇪🇸, NL🇳🇱, AU🇦🇺, NO🇳🇴
- **Instance 3**: Offset 600-899, Countries: US🇺🇸, GB🇬🇧, DE🇩🇪, CA🇨🇦, FR🇫🇷  
- **Instance 4**: Offset 900-1199, Countries: IT🇮🇹, ES🇪🇸, NL🇳🇱, AU🇦🇺, NO🇳🇴

**Optimizations Applied:**
- ⚡ Reduced delays: 12-31 seconds (was 15-40)
- 🌍 10 country codes (was 5) for better distribution
- 🔄 Non-overlapping offsets prevent duplication
- 📊 Enhanced monitoring for 4 instances

## ✅ Quick Health Check

```bash
# Check all is running correctly
ps aux | grep -E "(orchestrator|scraper)" | grep -v grep | wc -l
# Should show 24 processes (4 orchestrators + 20 scrapers)

# Quick status with file counts
./scripts/quick_status.sh

# Check GCS activity
gsutil ls gs://lupito-content-raw-eu/scraped/zooplus/$(date +%Y%m%d)* | wc -l
```

The system is designed to run autonomously. Monitor with the dashboard and let it work toward the 95% coverage goal!