# AKC Breed Scraper - Cloud Deployment Guide

## Overview

Cloud-ready AKC breed scraper that extracts physical characteristics and other data from akc.org using undetected-chromedriver to bypass bot detection.

## Current Status

- ✅ 160 breeds scraped with content
- ❌ Physical data (height, weight) not extracted due to JavaScript rendering
- ✅ Cloud-ready scraper created with undetected-chromedriver
- ✅ Docker container configured for Cloud Run
- 🔄 Ready for deployment

## Files Created

1. **`jobs/akc_cloud_scraper.py`** - Main cloud-ready scraper with bot bypass
2. **`Dockerfile.akc`** - Docker configuration with Chrome
3. **`requirements.akc.txt`** - Python dependencies
4. **`docker-compose.akc.yml`** - Local testing setup
5. **`deploy_docker_hub.sh`** - Deployment script
6. **`deploy_akc_scraper.sh`** - Google Cloud Run deployment

## Deployment Options

### Option 1: Google Cloud Run (Recommended)

**Advantages:**
- Serverless, pay-per-use
- Auto-scaling
- Managed infrastructure
- Built-in monitoring

**Steps:**

1. **Prepare environment:**
```bash
# Update deployment script with your details
nano deploy_docker_hub.sh
# Set DOCKER_USERNAME and GCP_PROJECT
```

2. **Build and deploy:**
```bash
chmod +x deploy_docker_hub.sh
./deploy_docker_hub.sh
```

3. **Trigger scraping:**
```bash
# Scrape 10 breeds
curl -X POST https://your-service-url/scrape \
  -H 'Content-Type: application/json' \
  -d '{"limit": 10}'

# Check status
curl https://your-service-url/status/<job_id>
```

### Option 2: Docker (Local or Cloud VM)

**Run with Docker Compose:**
```bash
# Start web server
docker-compose -f docker-compose.akc.yml up

# Or run as one-time job
docker-compose -f docker-compose.akc.yml --profile job up akc-scraper-job
```

**Run directly with Docker:**
```bash
# Build image
docker build -f Dockerfile.akc -t akc-scraper .

# Run web server
docker run -p 8080:8080 --env-file .env akc-scraper

# Run scraper directly
docker run --env-file .env akc-scraper \
  python3 jobs/akc_cloud_scraper.py --cloud --limit 10
```

### Option 3: AWS Lambda/ECS

**AWS Lambda (with container):**
- Max 15 minutes timeout
- Good for small batches

**AWS ECS/Fargate:**
- Better for long-running tasks
- Similar to Cloud Run

### Option 4: Local Development

```bash
# Install dependencies
pip3 install -r requirements.akc.txt

# Run scraper
python3 jobs/akc_cloud_scraper.py --test
```

## API Endpoints (Web Server Mode)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/scrape` | POST | Start scraping job |
| `/status/<job_id>` | GET | Check job status |

### Request Examples

**Start scraping all breeds:**
```json
POST /scrape
{}
```

**Scrape specific number:**
```json
POST /scrape
{
  "limit": 20
}
```

**Scrape specific breeds:**
```json
POST /scrape
{
  "breeds": ["german-shepherd-dog", "golden-retriever"]
}
```

## Environment Variables

Create `.env` file:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
```

## Monitoring & Debugging

### Check logs in Cloud Run:
```bash
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=akc-breed-scraper" \
  --limit 50
```

### Check Docker logs:
```bash
docker logs <container_id>
```

### Database Verification:
```sql
-- Check breeds with physical data
SELECT breed_slug, display_name, 
       height_cm_max, weight_kg_max, lifespan_years_max,
       has_physical_data
FROM akc_breeds
WHERE has_physical_data = true;

-- Count coverage
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN has_physical_data THEN 1 ELSE 0 END) as with_physical
FROM akc_breeds;
```

## Troubleshooting

### Chrome/ChromeDriver Issues
- Docker container includes matching Chrome/ChromeDriver versions
- Uses undetected-chromedriver to bypass detection

### Memory Issues
- Cloud Run configured with 2GB RAM
- Adjust in deployment script if needed

### Timeout Issues
- Cloud Run timeout set to 15 minutes
- For larger batches, use batch processing

### Bot Detection
- Scraper uses stealth techniques
- 3-second delay between requests
- Random user agents

## Next Steps

1. **Deploy to Cloud Run:**
   - Update Docker Hub username in script
   - Run deployment script
   - Test with small batch

2. **Run full update:**
   - Trigger scraping for all 160 breeds
   - Monitor progress via API

3. **Verify data:**
   - Check database for physical data
   - Generate coverage report

4. **Merge tables:**
   - After validation, merge akc_breeds into breeds_details

## Expected Results

After successful scraping:
- Height, weight, lifespan data for most breeds
- Energy levels, shedding, trainability ratings
- Comprehensive content sections
- ~60% total breed coverage (up from 35%)

## Cost Estimates

**Google Cloud Run:**
- ~$0.10 per 1000 requests
- ~$0.08 per GB-hour memory
- Estimated: <$5 for full scrape

**Docker Hub:**
- Free for public repositories
- $5/month for private repos

---

*Ready for deployment - just update credentials and run deployment script!*