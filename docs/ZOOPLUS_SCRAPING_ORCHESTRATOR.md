# Zooplus Scraping Orchestrator Documentation

## Overview

The Zooplus Scraping Orchestrator is a sophisticated system designed to efficiently scrape product ingredients and nutrition data from Zooplus to achieve 95% database coverage. It manages multiple concurrent scrapers with automatic restart, rate limiting protection, and real-time monitoring.

## 🎯 Objective

**Primary Goal**: Increase ingredients coverage from 23.8% (1,946 products) to 95% (7,780 products) by scraping 5,834 additional products from Zooplus.

**Secondary Goal**: Extract complete nutrition data (protein, fat, fiber, ash, moisture) alongside ingredients for comprehensive product analysis.

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                 Zooplus Scraping Orchestrator              │
├─────────────────────────────────────────────────────────────┤
│  Main Controller (scraper_orchestrator.py)                 │
│  ├── Session Manager                                       │
│  ├── Coverage Monitor                                      │
│  ├── Auto-restart Logic                                    │
│  └── Error Handling                                        │
├─────────────────────────────────────────────────────────────┤
│  5 Concurrent Scraper Sessions                             │
│  ├── US Session  (orchestrated_scraper.py us)             │
│  ├── UK Session  (orchestrated_scraper.py gb)             │
│  ├── DE Session  (orchestrated_scraper.py de)             │
│  ├── CA Session  (orchestrated_scraper.py ca)             │
│  └── FR Session  (orchestrated_scraper.py fr)             │
├─────────────────────────────────────────────────────────────┤
│  Data Flow                                                  │
│  Zooplus → ScrapingBee → GCS Storage → Supabase Database  │
├─────────────────────────────────────────────────────────────┤
│  Monitoring & Analytics                                     │
│  ├── Real-time Dashboard (orchestrator_dashboard.py)       │
│  ├── Coverage Tracking                                     │
│  ├── Performance Metrics                                   │
│  └── Progress Visualization                                │
└─────────────────────────────────────────────────────────────┘
```

### Technical Stack

- **Web Scraping**: ScrapingBee API with premium proxy protection
- **Storage**: Google Cloud Storage (GCS) for intermediate data
- **Database**: Supabase (PostgreSQL) for final storage
- **Monitoring**: Real-time dashboard with coverage tracking
- **Language**: Python 3.9+ with asyncio-style process management

## 🚀 Getting Started

### Prerequisites

```bash
# Required environment variables
export SCRAPING_BEE=your_scrapingbee_api_key
export SUPABASE_URL=your_supabase_url
export SUPABASE_SERVICE_KEY=your_supabase_service_key
export GCS_BUCKET=your_gcs_bucket_name

# Required Python packages
pip install requests beautifulsoup4 google-cloud-storage supabase python-dotenv
```

### Quick Start

```bash
# 1. Start the orchestrator
source venv/bin/activate
python scripts/scraper_orchestrator.py

# 2. Monitor progress (in another terminal)
python scripts/orchestrator_dashboard.py

# 3. Continuous monitoring
watch -n 30 "python scripts/orchestrator_dashboard.py"
```

## 📋 Configuration

### Session Configuration

The orchestrator manages 5 concurrent sessions with different configurations to avoid rate limiting:

```python
session_configs = [
    {
        "name": "us1", 
        "country_code": "us", 
        "min_delay": 15, 
        "max_delay": 25, 
        "batch_size": 12
    },
    {
        "name": "gb1", 
        "country_code": "gb", 
        "min_delay": 20, 
        "max_delay": 30, 
        "batch_size": 12
    },
    {
        "name": "de1", 
        "country_code": "de", 
        "min_delay": 25, 
        "max_delay": 35, 
        "batch_size": 12
    },
    {
        "name": "ca1", 
        "country_code": "ca", 
        "min_delay": 30, 
        "max_delay": 40, 
        "batch_size": 12
    },
    {
        "name": "fr1", 
        "country_code": "fr", 
        "min_delay": 18, 
        "max_delay": 28, 
        "batch_size": 12
    }
]
```

### ScrapingBee Parameters

Each session uses proven parameters that successfully bypass Zooplus anti-bot measures:

```python
scraping_params = {
    'api_key': SCRAPINGBEE_API_KEY,
    'url': target_url,
    'render_js': 'true',              # Execute JavaScript
    'premium_proxy': 'true',          # Use premium proxy network
    'stealth_proxy': 'true',          # Anti-detection features
    'country_code': session_country,   # Rotate by country
    'wait': '3000',                   # Wait for page load
    'return_page_source': 'true'      # Return full HTML
}
```

## 🎛️ Core Components

### 1. Scraper Orchestrator (`scraper_orchestrator.py`)

**Purpose**: Main controller that manages all scraping sessions

**Key Features**:
- Manages up to 5 concurrent scraper sessions
- Auto-restart completed sessions with new batches
- Real-time coverage monitoring toward 95% goal
- Non-overlapping product offsets (prevents duplication)
- Error handling and retry logic
- Process lifecycle management

**Core Methods**:
```python
class ScraperOrchestrator:
    def get_current_coverage() -> Dict
    def create_scraper_session(config, offset) -> ScraperSession
    def start_scraper_session(session, offset) -> bool
    def check_session_status(session) -> bool
    def restart_session(session, offset) -> bool
    def monitor_and_manage_sessions()
```

### 2. Orchestrated Scraper (`orchestrated_scraper.py`)

**Purpose**: Individual scraper managed by orchestrator

**Key Features**:
- Accepts configuration via command line arguments
- Uses proven ScrapingBee parameters for success
- Extracts ingredients and nutrition data
- Saves results to GCS with session metadata
- Detailed logging with session identifier

**Data Extraction**:
```python
# Ingredients extraction patterns
ingredients_patterns = [
    r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives|Nutritional)|$)',
    r'(?:Composition|Ingredients)[:\s]*([A-Za-z][^.]{30,}(?:\.[^.]{20,})*?)(?:Analytical|$)'
]

# Nutrition extraction patterns
nutrition_patterns = [
    (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein_percent'),
    (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat_percent'),
    (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fiber_percent'),
    (r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', 'ash_percent'),
    (r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', 'moisture_percent')
]
```

### 3. Real-time Dashboard (`orchestrator_dashboard.py`)

**Purpose**: Live monitoring of scraping progress and system status

**Dashboard Features**:
- Current database coverage statistics
- Progress bar toward 95% goal
- Active session monitoring with country flags
- GCS file count tracking
- Performance metrics and time estimates
- Process status monitoring

**Key Metrics Displayed**:
```
📊 DATABASE COVERAGE PROGRESS
   Current: 1,946 products (23.8%)
   Target:  7,780 products (95.0%)
   Gap:     5,834 products needed
   Available: 2,614 Zooplus products

   Progress: [██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 23.8%

🚀 ACTIVE PROCESSES
   Orchestrators: 1
   Scrapers: 5

☁️  ACTIVE GCS SESSIONS
   🇺🇸 US: 3 sessions, 24 files
   🇬🇧 GB: 3 sessions, 18 files
   🇩🇪 DE: 3 sessions, 21 files
   📄 Total files scraped today: 63
```

## 📊 Performance & Monitoring

### Expected Performance

**Conservative Estimates**:
- **Rate**: 100-200 products/hour (all 5 sessions combined)
- **Time to 95%**: 30-60 hours of continuous operation
- **Success Rate**: 70-80% ingredients extraction
- **Uptime**: 90%+ with auto-restart

**Optimistic Estimates**:
- **Rate**: 300-400 products/hour  
- **Time to 95%**: 15-20 hours
- **Success Rate**: 80-90% ingredients extraction
- **Uptime**: 95%+ with robust error handling

### Monitoring Commands

```bash
# Real-time dashboard
python scripts/orchestrator_dashboard.py

# Continuous monitoring (updates every 30 seconds)
watch -n 30 "python scripts/orchestrator_dashboard.py"

# Check running processes
ps aux | grep orchestrator

# Count today's scraped files
gsutil ls gs://lupito-content-raw-eu/scraped/zooplus/$(date +%Y%m%d)*/*.json | wc -l

# Quick database status
./scripts/quick_status.sh
```

## 🛡️ Rate Limiting & Anti-Detection

### Multi-layered Protection

1. **ScrapingBee Proxy Protection**:
   - Premium proxy network
   - Stealth mode anti-detection
   - Residential IP rotation

2. **Geographic Distribution**:
   - 5 different country codes (US, UK, DE, CA, FR)
   - Separate rate limits per country
   - Distributed request patterns

3. **Timing Strategies**:
   - Variable delays: 15-40 seconds between requests
   - Randomized timing to appear human
   - Progressive backoff on errors

4. **Session Management**:
   - Non-overlapping product offsets
   - Separate GCS folders per session
   - Independent error tracking

### Historical Success Rate

Based on diagnostic testing and parallel session results:
- ✅ **Individual requests**: 100% success rate (HTTP 200)
- ✅ **Parallel sessions**: 6 files successfully scraped
- ✅ **Stealth mode**: Largest responses (1.1MB vs 720KB basic)
- ❌ **Single session batches**: HTTP 400 rate limiting

## 📁 File Structure

```
scripts/
├── scraper_orchestrator.py          # Main orchestrator controller
├── orchestrated_scraper.py          # Individual scraper implementation  
├── orchestrator_dashboard.py        # Real-time monitoring dashboard
├── parallel_scraper.py             # Manual parallel session runner
├── working_proxy_scraper.py         # Single session scraper (proven)
├── diagnose_blocking.py             # ScrapingBee diagnostic tool
├── monitor_parallel_sessions.py     # Basic session monitor
├── quick_status.sh                  # Quick database status check
└── ORCHESTRATOR_USAGE.md           # Quick usage guide

docs/
└── ZOOPLUS_SCRAPING_ORCHESTRATOR.md # This documentation
```

## 🗄️ Data Flow

### 1. Target Selection
```sql
-- Products missing ingredients from Zooplus
SELECT product_key, product_name, brand, product_url 
FROM foods_canonical 
WHERE product_url ILIKE '%zooplus%' 
AND ingredients_raw IS NULL
LIMIT batch_size OFFSET session_offset
```

### 2. Scraping Process
```
Zooplus Product URL → ScrapingBee API → HTML Response → BeautifulSoup Parser → Structured Data
```

### 3. Data Extraction
```python
extracted_data = {
    'url': original_url,
    'scraped_at': timestamp,
    'session_id': session_identifier,
    'country_code': scraper_country,
    'product_name': extracted_title,
    'ingredients_raw': extracted_ingredients,  # Main target
    'nutrition': {                            # Bonus data
        'protein_percent': float,
        'fat_percent': float,
        'fiber_percent': float,
        'ash_percent': float,
        'moisture_percent': float
    }
}
```

### 4. Storage Pipeline
```
Structured Data → JSON Format → GCS Bucket → Processing Script → Supabase Database
```

## 🚨 Error Handling

### Error Categories

1. **HTTP Errors**:
   - 400: Rate limiting (handled by country rotation + delays)
   - 422: Invalid parameters (prevented by proven config)
   - 429: API rate limit (handled by session distribution)
   - 500: Server errors (automatic retry)

2. **Parsing Errors**:
   - Empty responses (logged, continue)
   - Missing data (partial extraction)
   - Invalid HTML (skip product)

3. **Infrastructure Errors**:
   - GCS upload failures (retry with exponential backoff)
   - Database connection issues (queue for later processing)
   - Process crashes (automatic session restart)

### Recovery Strategies

```python
# Automatic session restart
if session.status == "failed" and session.restart_count < max_restarts:
    restart_session(session, new_offset)

# Error backoff
if consecutive_errors >= 3:
    delay = base_delay * (2 ** consecutive_errors)  # Exponential backoff
    
# Graceful degradation  
if extraction_fails:
    save_partial_data_with_error_flag()
```

## 📈 Success Metrics

### Coverage Milestones

- **Start**: 23.8% ingredients coverage (1,946 products)
- **Milestone 1**: 50% coverage (~2,000 more products)  
- **Milestone 2**: 75% coverage (~4,000 more products)
- **Goal**: 95% coverage (5,834 more products)

### Quality Metrics

- **Ingredients Extraction**: Target 70-80% success rate
- **Nutrition Extraction**: Target 60-70% success rate
- **Data Completeness**: Target 80%+ complete records
- **Error Rate**: Target <20% HTTP errors
- **Uptime**: Target 90%+ orchestrator availability

### Performance Tracking

```python
# Real-time metrics
session_stats = {
    'total_attempts': int,
    'successful_extractions': int, 
    'with_ingredients': int,
    'with_nutrition': int,
    'error_count': int,
    'success_rate': float,
    'products_per_hour': float
}

# Overall progress
orchestrator_stats = {
    'coverage_start': 23.8,
    'coverage_current': float,
    'coverage_target': 95.0,
    'products_scraped_total': int,
    'estimated_completion': datetime
}
```

## 🔧 Troubleshooting

### Common Issues

**1. Orchestrator Won't Start**
```bash
# Check for missing dependencies
pip install -r requirements.txt

# Verify environment variables
env | grep -E "(SCRAPING_BEE|SUPABASE|GCS)"

# Check file permissions
chmod +x scripts/scraper_orchestrator.py
```

**2. Sessions Failing**
```bash
# Check ScrapingBee API key
curl -X GET "https://app.scrapingbee.com/api/v1/?api_key=YOUR_KEY&url=https://httpbin.org/ip"

# Monitor session logs
python scripts/orchestrator_dashboard.py

# Check GCS permissions
gsutil ls gs://your-bucket-name/
```

**3. Low Success Rate**
- Sessions automatically restart on high error rates
- Check ScrapingBee credit balance
- Verify target URLs are still valid
- Monitor for Zooplus site changes

**4. Performance Issues**
```bash
# Check system resources
top -p $(pgrep -f orchestrator)

# Monitor network usage
netstat -i

# Check GCS upload speed
gsutil cp test_file gs://bucket/test/ -v
```

### Emergency Commands

```bash
# Stop all orchestrator processes
pkill -f orchestrator

# Stop all scraper sessions  
pkill -f orchestrated_scraper

# Emergency cleanup
ps aux | grep -E "(orchestrator|orchestrated_scraper)" | awk '{print $2}' | xargs kill -9

# Check for zombie processes
ps aux | grep -E "(orchestrator|orchestrated_scraper)" | grep -E "(Z|<defunct>)"
```

## 🔮 Future Enhancements

### Scalability Improvements

1. **Dynamic Session Management**:
   - Auto-scale sessions based on success rate
   - Intelligent country code rotation
   - Adaptive delay optimization

2. **Enhanced Monitoring**:
   - Web-based dashboard with charts
   - Slack/email notifications
   - Performance analytics and reporting

3. **Data Quality**:
   - Machine learning for extraction improvement
   - Automated data validation
   - Duplicate detection and merging

### Integration Possibilities

1. **Multi-source Scraping**:
   - Extend to other pet food retailers
   - Manufacturer website scraping
   - Price tracking integration

2. **Advanced Analytics**:
   - Ingredient trend analysis
   - Brand comparison tools
   - Nutritional adequacy scoring

## 📞 Support & Maintenance

### Monitoring Schedule

- **Hourly**: Check dashboard for progress
- **Daily**: Review error logs and success rates  
- **Weekly**: Analyze performance trends
- **Monthly**: Update configuration based on learnings

### Maintenance Tasks

1. **Regular**:
   - Monitor ScrapingBee credit usage
   - Clean up old GCS files
   - Update database coverage statistics

2. **Periodic**:
   - Review and update extraction patterns
   - Optimize session configurations
   - Update documentation

3. **Emergency**:
   - Restart failed orchestrator
   - Handle API changes
   - Scale resources if needed

---

## 📊 Current Status

**As of Last Update**:
- **Database Coverage**: 23.8% ingredients (1,946/8,190 products)
- **Target**: 95% coverage (7,780 products)  
- **Gap**: 5,834 products needed
- **Available**: 2,614 Zooplus products to scrape
- **Orchestrator Status**: ✅ Deployed and running
- **Expected Completion**: 15-60 hours depending on performance

**The orchestrator is designed for autonomous operation toward the 95% coverage goal. Monitor via dashboard and let it work continuously!**

---

*For questions or issues, check the troubleshooting section above or review the ORCHESTRATOR_USAGE.md quick guide.*