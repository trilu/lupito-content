# Scraper Orchestrator Usage Guide

## 🎯 Goal
Reach 95% ingredients coverage (currently 23.8%) by managing 5 concurrent scrapers with automatic restart and monitoring.

## 📊 Current Status
- **Current**: 1,946 products (23.8%)
- **Target**: 7,780 products (95.0%)  
- **Gap**: 5,834 products needed
- **Available**: 2,614 Zooplus products

## 🚀 Quick Start

### 1. Start the Orchestrator
```bash
# Start the main orchestrator (manages 5 concurrent scrapers)
source venv/bin/activate && python scripts/scraper_orchestrator.py
```

### 2. Monitor Progress
```bash
# Real-time dashboard
source venv/bin/activate && python scripts/orchestrator_dashboard.py

# Continuous monitoring (updates every 30 seconds)
watch -n 30 "source venv/bin/activate && python scripts/orchestrator_dashboard.py"
```

### 3. Check Status
```bash
# Quick status
./scripts/quick_status.sh

# Check running processes
ps aux | grep orchestrator
```

## 🎛️ How the Orchestrator Works

### Architecture
```
Orchestrator (Main Controller)
├── Session 1: US (country_code=us, 15-25s delays)
├── Session 2: UK (country_code=gb, 20-30s delays)  
├── Session 3: DE (country_code=de, 25-35s delays)
├── Session 4: CA (country_code=ca, 30-40s delays)
└── Session 5: FR (country_code=fr, 18-28s delays)
```

### Features
- **Auto-restart**: When a session completes, automatically starts a new batch
- **Non-overlapping offsets**: Each session scrapes different products
- **Rate limiting protection**: Different country codes + delays prevent blocking
- **Real-time monitoring**: Track progress toward 95% goal
- **Error handling**: Automatic retry on failures
- **GCS storage**: All data saved to cloud storage first

### Session Configuration
```python
sessions = [
    {"name": "us1", "country_code": "us", "delays": "15-25s", "batch_size": 12},
    {"name": "gb1", "country_code": "gb", "delays": "20-30s", "batch_size": 12},
    {"name": "de1", "country_code": "de", "delays": "25-35s", "batch_size": 12},
    {"name": "ca1", "country_code": "ca", "delays": "30-40s", "batch_size": 12},
    {"name": "fr1", "country_code": "fr", "delays": "18-28s", "batch_size": 12},
]
```

## 📈 Expected Performance

### Conservative Estimates
- **Rate**: ~100-200 products/hour (all 5 sessions combined)
- **Time to 95%**: ~30-60 hours of continuous operation
- **Success rate**: 70-90% based on parallel test results

### Optimistic Estimates  
- **Rate**: ~300-400 products/hour
- **Time to 95%**: ~15-20 hours

## 🎯 Commands Reference

### Start/Stop
```bash
# Start orchestrator
python scripts/scraper_orchestrator.py

# Stop all orchestrator processes  
pkill -f orchestrator

# Stop all scraper processes
pkill -f orchestrated_scraper
```

### Monitoring
```bash
# Dashboard (one-time)
python scripts/orchestrator_dashboard.py

# Continuous dashboard
watch -n 30 python scripts/orchestrator_dashboard.py

# Check GCS activity
gsutil ls gs://lupito-content-raw-eu/scraped/zooplus/$(date +%Y%m%d)*/

# Count today's scraped files
gsutil ls gs://lupito-content-raw-eu/scraped/zooplus/$(date +%Y%m%d)*/*.json | wc -l
```

### Process Data
```bash
# After scraping sessions complete, process GCS files to update database
python scripts/process_gcs_scraped_data.py <gcs_folder_path>

# Example:
python scripts/process_gcs_scraped_data.py scraped/zooplus/20250912_211545_us1
```

## 🛟 Troubleshooting

### If Orchestrator Stops
```bash
# Check for errors
ps aux | grep orchestrator

# Restart
python scripts/scraper_orchestrator.py
```

### If Sessions Fail
- Sessions auto-restart up to 10 times
- Check dashboard for error patterns
- Individual sessions use proven ScrapingBee parameters

### If Rate Limited
- Each session uses different country codes
- Built-in delays: 15-40 seconds between requests
- ScrapingBee premium + stealth proxy protection

## 📊 Success Metrics

### Coverage Progress
- **Start**: 23.8% ingredients coverage
- **Milestone 1**: 50% coverage (~2,000 more products)
- **Milestone 2**: 75% coverage (~4,000 more products)  
- **Goal**: 95% coverage (5,834 more products)

### Quality Metrics
- **Ingredients extraction**: Target 70-80% success rate
- **Nutrition extraction**: Target 60-70% success rate  
- **Error rate**: Target <20% HTTP errors

## 🎉 Next Steps

1. **Monitor orchestrator** - Let it run continuously
2. **Check dashboard regularly** - Track progress toward 95%
3. **Process GCS files** - Run processing script after batches complete
4. **Scale up if needed** - Can increase to 8-10 concurrent sessions if performing well
5. **Celebrate 95%** - Database will be comprehensive for analysis!

---

*The orchestrator is designed to run autonomously toward the 95% coverage goal. Monitor via dashboard and let it work!*