# AKC Breed Scraper Documentation

## Project Overview
Extract comprehensive breed data from AKC.org for 160 dog breeds to fill missing information in the Supabase database.

## Problem Statement
- **Initial Issue**: 160 breeds already scraped but missing physical characteristics (height, weight, lifespan)
- **Root Cause**: JavaScript-rendered content on AKC.org wasn't captured by initial scraper
- **Solution**: Browser automation to execute JavaScript and extract complete breed profiles

## Data to Extract

### Physical Characteristics
- **Height**: Min/max in cm (converted from inches)
- **Weight**: Min/max in kg (converted from pounds)  
- **Life Span**: Min/max years
- **Coat Type**: Short, long, wiry, etc.
- **Colors**: Available color variations

### Breed Profile
- **Description**: Overview and breed summary
- **History**: Origin and breed development
- **Personality/Temperament**: Character traits
- **Care Requirements**: Grooming and maintenance needs
- **Health Information**: Common health issues and concerns
- **Training Info**: Trainability and training tips
- **Exercise Needs**: Activity level and exercise requirements
- **Nutrition**: Feeding guidelines
- **Breed Group**: AKC classification (Sporting, Working, etc.)

## Technical Architecture

### Components
1. **Scraper** (`jobs/akc_selenium_scraper.py`)
   - Selenium WebDriver with Chrome
   - Comprehensive data extraction
   - JSON file output

2. **Web Server** (`server.py`)
   - Flask API for triggering jobs
   - Background job processing
   - File download endpoints

3. **Docker Container** (`Dockerfile.akc`)
   - Python 3.9 base image
   - Google Chrome installation
   - Cloud Run optimized

4. **Monitoring** (`monitor_job.sh`)
   - Real-time job status tracking
   - Result retrieval

## Deployment Configuration

### Google Cloud Setup
```bash
# Project: breed-data (ID: 385123033381)
# Region: us-central1
# Service: akc-breed-scraper
# Image Registry: us-central1-docker.pkg.dev/breed-data/docker-repo/

# Resources
Memory: 2Gi
CPU: 2
Timeout: 900s
Max Instances: 5
```

### Build & Deploy Commands
```bash
# Build Docker image
cp Dockerfile.akc Dockerfile
gcloud builds submit --tag us-central1-docker.pkg.dev/breed-data/docker-repo/akc-breed-scraper:v3
rm Dockerfile

# Deploy to Cloud Run
gcloud run deploy akc-breed-scraper \
  --image us-central1-docker.pkg.dev/breed-data/docker-repo/akc-breed-scraper:v3 \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900 \
  --max-instances 5
```

## API Endpoints

### Start Scraping Job
```bash
curl -X POST https://akc-breed-scraper-385123033381.us-central1.run.app/scrape \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'  # Test with 5 breeds
```

### Check Job Status
```bash
curl https://akc-breed-scraper-385123033381.us-central1.run.app/status/{job_id}
```

### Download Results
```bash
curl -O https://akc-breed-scraper-385123033381.us-central1.run.app/download/{job_id}
```

### List All Jobs
```bash
curl https://akc-breed-scraper-385123033381.us-central1.run.app/jobs
```

## Chrome Driver Configuration

### Cloud Run Optimized Settings
```python
# Essential for Cloud Run
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--headless=new')

# Memory optimization
options.add_argument('--memory-pressure-off')
options.add_argument('--max_old_space_size=4096')

# Stealth settings
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
```

## Data Output Format

### JSON Structure
```json
{
  "breed_slug": "golden-retriever",
  "display_name": "Golden Retriever",
  "akc_url": "https://www.akc.org/dog-breeds/golden-retriever/",
  "extraction_status": "success",
  "extraction_timestamp": "2025-09-07T14:30:00",
  "has_physical_data": true,
  "has_profile_data": true,
  
  // Physical traits
  "height_cm_min": 54.6,
  "height_cm_max": 61.0,
  "weight_kg_min": 25.0,
  "weight_kg_max": 34.0,
  "life_span_years_min": 10,
  "life_span_years_max": 12,
  
  // Profile data
  "breed_group": "Sporting",
  "temperament": "Friendly, Intelligent, Devoted",
  "description": "The Golden Retriever is a sturdy, muscular dog...",
  "history": "The Golden Retriever was originally bred in Scotland...",
  "care_requirements": "Regular brushing is required...",
  "health_info": "Generally healthy breed but prone to...",
  "training_info": "Highly trainable and eager to please...",
  "exercise_needs": "Requires daily exercise and mental stimulation...",
  "coat_type": "Dense, water-repellent double coat",
  "colors": "Light golden to dark golden"
}
```

## Supabase Import Process

### 1. Download Results
```bash
curl -O https://akc-breed-scraper-385123033381.us-central1.run.app/download/{job_id}
```

### 2. Import Script (to be created)
```python
# Read JSON file
# Connect to Supabase
# Update breeds table with extracted data
# Log success/failures
```

## Troubleshooting

### Common Issues & Solutions

1. **Chrome Connection Error**
   - Issue: `cannot connect to chrome at 127.0.0.1:xxxxx`
   - Solution: Use regular Selenium instead of undetected-chromedriver

2. **Memory Issues**
   - Issue: Container runs out of memory
   - Solution: Increase Cloud Run memory to 4Gi

3. **Timeout Issues**
   - Issue: Scraping takes longer than timeout
   - Solution: Process in smaller batches (20-30 breeds at a time)

4. **Rate Limiting**
   - Issue: AKC blocks requests
   - Solution: Add 3-5 second delays between requests

## Results & Lessons Learned

### ✅ SUCCESS: Local Scraper
- **Status**: ✅ COMPLETED - 100% success rate
- **Breeds processed**: 160/160 (100%)
- **New breeds added**: 155
- **Breeds updated**: 5
- **Execution time**: ~15 minutes locally
- **Command**: `python3 jobs/akc_breed_scraper.py --urls-file akc_breed_urls.txt`

### ❌ FAILED: Selenium/Chrome in Cloud Run
- **Attempts**: v1-v6 all failed
- **Issue**: DevToolsActivePort file doesn't exist
- **Root cause**: Chrome browser conflicts with Cloud Run's sandboxed environment
- **Conclusion**: Selenium + Chrome is not viable for Cloud Run

### 🔧 What Works
1. **Local execution** with `requests` + `BeautifulSoup`
2. **Flask API server** for job management 
3. **Monitoring scripts** for progress tracking
4. **QA reporting** for data validation

### 🗑️ What to Abandon
1. **Selenium WebDriver** - unreliable in containerized environments
2. **Chrome browser** - resource intensive, permission issues
3. **Cloud Run scraping** - better suited for API services, not browser automation

### 📋 Recommendations
1. **Keep local scraper** - it works perfectly
2. **Use Flask API** for other scrapers that need HTTP endpoints
3. **Consider cloud functions** for lightweight scraping tasks
4. **Use managed services** (ScrapingBee, Browserless) for browser automation

## Monitoring Commands

```bash
# Watch job progress
./monitor_job.sh {job_id}

# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=akc-breed-scraper" --limit=50

# Check build status
gcloud builds list --limit=5

# Service health
curl https://akc-breed-scraper-385123033381.us-central1.run.app/health
```

## Performance Metrics

- **Processing Time**: ~30-60 seconds per breed
- **Success Rate Target**: >95%
- **Data Completeness**: Physical traits + full profile
- **Batch Size**: 20-30 breeds optimal
- **Total Time**: 2-3 hours for 160 breeds

## Files Reference

- `jobs/akc_selenium_scraper.py` - Main scraper with Selenium
- `jobs/akc_file_scraper.py` - Previous version with undetected-chromedriver
- `server.py` - Flask API server
- `Dockerfile.akc` - Docker configuration
- `requirements.akc.optimized.txt` - Python dependencies
- `monitor_job.sh` - Job monitoring script

## Contact & Support

- Service URL: https://akc-breed-scraper-385123033381.us-central1.run.app
- Project: breed-data
- Region: us-central1