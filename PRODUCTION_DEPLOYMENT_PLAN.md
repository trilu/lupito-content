# Production Deployment Plan - AKC Breed Scraper

## Current Status ✅

### What Works (KEEP)
- **Local scraper**: `jobs/akc_breed_scraper.py` - 100% success rate on 160 breeds
- **Flask API server**: `server.py` - Job management, file serving, monitoring endpoints
- **Monitoring**: `monitor_job_detailed.sh` - Real-time progress tracking
- **QA reporting**: Generates validation reports with extraction success metrics

### What Failed (ARCHIVED)
- **Selenium + Chrome in Cloud Run**: DevToolsActivePort errors, sandboxing conflicts
- **Multiple deployment attempts**: v1-v6 all failed due to Chrome compatibility issues

## Recommended Production Architecture

### Option 1: Hybrid Approach (RECOMMENDED)
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cloud Run     │    │   Local Runner   │    │   Supabase DB   │
│   (Flask API)   │◄──►│   (Scraper)      │◄──►│   (Storage)     │
│                 │    │                  │    │                 │
│ • Job triggers  │    │ • Actual scraping│    │ • Breed data    │
│ • Status checks │    │ • BeautifulSoup  │    │ • Images        │
│ • File serving  │    │ • Local execution│    │ • Metadata      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Benefits:**
- ✅ Reliable scraping (proven to work)
- ✅ Scalable API endpoints
- ✅ Cost-effective (no browser resources in cloud)
- ✅ Easy monitoring and management

### Option 2: Managed Service
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cloud Run     │    │  ScrapingBee     │    │   Supabase DB   │
│   (Flask API)   │◄──►│  (Browser API)   │    │   (Storage)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Benefits:**
- ✅ Fully cloud-based
- ✅ Managed browser infrastructure
- ❌ Additional cost (~$50-100/month)
- ❌ External dependency

### Option 3: VM Deployment
```
┌─────────────────────────────────────┐    ┌─────────────────┐
│         Google Compute Engine       │    │   Supabase DB   │
│  ┌─────────────┐ ┌─────────────────┐ │    │   (Storage)     │
│  │ Flask API   │ │ Local Scraper   │ │◄──►│                 │
│  └─────────────┘ └─────────────────┘ │    │                 │
└─────────────────────────────────────┘    └─────────────────┘
```

**Benefits:**
- ✅ Full control over environment
- ✅ Can run browser if needed
- ❌ Higher cost and maintenance
- ❌ More complex deployment

## Implementation Roadmap

### Phase 1: Immediate (1-2 days)
1. ✅ **Archive failed attempts** - COMPLETED
2. ✅ **Document lessons learned** - COMPLETED
3. **Deploy working Flask API to Cloud Run**
   - Remove Chrome/Selenium dependencies
   - Keep job management endpoints
   - Deploy as lightweight service

### Phase 2: Data Integration (3-5 days)
1. **Create Supabase import script**
   ```python
   # Import extracted breed data to Supabase
   # Handle deduplication and updates
   # Generate success/failure reports
   ```

2. **Test data pipeline**
   - Run local scraper
   - Import to Supabase
   - Validate results

### Phase 3: Production Setup (1 week)
1. **Set up automated scheduling**
   - Cron job for periodic updates
   - Error notifications
   - Data freshness monitoring

2. **Create monitoring dashboard**
   - Breed count tracking
   - Data completeness metrics
   - Error reporting

## Deployment Commands

### Deploy Flask API (No Browser)
```bash
# Create lightweight Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY server.py .
COPY monitor_job.sh .
EXPOSE 8080
ENV PORT=8080
CMD ["python3", "server.py"]
EOF

# Build and deploy
gcloud builds submit --tag us-central1-docker.pkg.dev/breed-data/docker-repo/akc-api:production
gcloud run deploy akc-api \
  --image us-central1-docker.pkg.dev/breed-data/docker-repo/akc-api:production \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1
```

### Local Scraper Setup
```bash
# Install dependencies locally
pip install requests beautifulsoup4 python-dotenv supabase

# Run scraper
python3 jobs/akc_breed_scraper.py --urls-file akc_breed_urls.txt

# Import to Supabase (to be created)
python3 import_to_supabase.py --file latest_breed_data.json
```

## Cost Analysis

### Current (Failed) Approach
- **Cloud Run**: $20-50/month (high memory, CPU for Chrome)
- **Build minutes**: $10-20/month (multiple failed deployments)
- **Total**: $30-70/month + time cost

### Recommended Approach
- **Cloud Run API**: $5-15/month (lightweight service)
- **Local execution**: $0 (use existing hardware)
- **Total**: $5-15/month

## Risk Mitigation

### Data Loss Prevention
- ✅ **QA reports generated** - Track what was extracted
- ✅ **JSON file outputs** - Backup before database import
- ✅ **Git versioning** - Code and results tracked

### Monitoring
- ✅ **Real-time progress tracking** - Working monitoring scripts
- ✅ **Error detection** - Comprehensive logging
- ✅ **Success metrics** - 100% extraction rate achieved

### Scalability
- **Horizontal**: Run multiple local scrapers in parallel
- **Vertical**: Upgrade to managed services if volume increases
- **Geographic**: Deploy in multiple regions if needed

## Next Actions

1. **Immediate**: Deploy lightweight Flask API to Cloud Run
2. **Short-term**: Create Supabase import pipeline
3. **Medium-term**: Set up automated scheduling
4. **Long-term**: Consider migration to managed services if scale requires

## Files Structure (Clean)

```
lupito-content/
├── jobs/
│   ├── akc_breed_scraper.py          # ✅ WORKING LOCAL SCRAPER
│   └── import_to_supabase.py         # 🔲 TO CREATE
├── server.py                         # ✅ Flask API (reusable)
├── monitor_job_detailed.sh           # ✅ Monitoring script
├── akc_breed_urls.txt                # ✅ Input URLs
├── akc_breed_qa_report_*.csv         # ✅ QA reports
├── AKC_SCRAPER_DOCUMENTATION.md      # ✅ Updated docs
├── PRODUCTION_DEPLOYMENT_PLAN.md     # ✅ This file
└── archive/failed_attempts/          # 🗂️ Selenium/Chrome archive
    ├── README.md
    ├── Dockerfile.akc
    ├── akc_selenium_scraper.py
    └── requirements.akc.optimized.txt
```

**Decision**: Proceed with **Option 1 (Hybrid Approach)** - proven, cost-effective, reliable.