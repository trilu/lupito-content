# AKC Scraper - Manual Deployment Instructions

## Prerequisites Required

1. **Google Cloud Account** with billing enabled
2. **Docker Desktop** (download from docker.com) OR use Google Cloud Shell
3. **gcloud CLI** authenticated

## Option 1: Deploy Using Google Cloud Shell (Easiest - No Local Setup)

1. **Open Google Cloud Shell:**
   ```
   https://console.cloud.google.com/cloudshell
   ```

2. **Clone your repository or upload files:**
   ```bash
   # In Cloud Shell, upload these files:
   # - Dockerfile.akc
   # - requirements.akc.txt  
   # - server.py
   # - jobs/akc_cloud_scraper.py
   ```

3. **Set environment variables:**
   ```bash
   export PROJECT_ID="breed-data"
   export SUPABASE_URL="your_supabase_url"
   export SUPABASE_SERVICE_KEY="your_supabase_service_key"
   ```

4. **Build and deploy:**
   ```bash
   # Build the container
   gcloud builds submit --tag gcr.io/${PROJECT_ID}/akc-scraper \
     --file Dockerfile.akc .
   
   # Deploy to Cloud Run
   gcloud run deploy akc-breed-scraper \
     --image gcr.io/${PROJECT_ID}/akc-scraper \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2 \
     --timeout 900 \
     --set-env-vars "SUPABASE_URL=${SUPABASE_URL},SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}"
   ```

## Option 2: Deploy Using Docker Hub

1. **Install Docker Desktop** (if not installed)

2. **Build locally:**
   ```bash
   docker build -f Dockerfile.akc -t lupitopetai/akc-breed-scraper .
   ```

3. **Push to Docker Hub:**
   ```bash
   docker login
   docker push lupitopetai/akc-breed-scraper
   ```

4. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy akc-breed-scraper \
     --image docker.io/lupitopetai/akc-breed-scraper \
     --platform managed \
     --region us-central1 \
     --project breed-data \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2 \
     --timeout 900 \
     --set-env-vars "SUPABASE_URL=xxx,SUPABASE_SERVICE_KEY=xxx"
   ```

## Option 3: Quick Local Test (No Cloud)

If you want to test locally first:

```bash
# Create test container
docker build -f Dockerfile.akc -t akc-test .

# Run locally
docker run -p 8080:8080 \
  -e SUPABASE_URL="your_url" \
  -e SUPABASE_SERVICE_KEY="your_key" \
  akc-test

# Test in another terminal
curl http://localhost:8080
curl -X POST http://localhost:8080/scrape -H 'Content-Type: application/json' -d '{"limit": 1}'
```

## After Deployment

Once deployed to Cloud Run, you'll get a URL like:
`https://akc-breed-scraper-xxxxx-uc.a.run.app`

### Test the service:
```bash
# Check if running
curl https://your-service-url

# Start scraping 10 breeds
curl -X POST https://your-service-url/scrape \
  -H 'Content-Type: application/json' \
  -d '{"limit": 10}'

# Check job status (use job_id from response)
curl https://your-service-url/status/job_id
```

### Monitor in Cloud Console:
1. Go to Cloud Run: https://console.cloud.google.com/run
2. Click on `akc-breed-scraper`
3. Check "Logs" tab for real-time logs

## Troubleshooting

### Authentication Issues:
```bash
gcloud auth login
gcloud config set project breed-data
```

### Enable APIs:
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Check Service Status:
```bash
gcloud run services describe akc-breed-scraper --region us-central1
```

### View Logs:
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit 20
```

## Expected Results

After successful deployment and scraping:
- Service will extract physical data (height, weight, lifespan)
- Data will be saved to `akc_breeds` table in Supabase
- Check results:
  ```sql
  SELECT breed_slug, height_cm_max, weight_kg_max, has_physical_data
  FROM akc_breeds
  WHERE has_physical_data = true;
  ```

## Cost Estimate

- Cloud Run: ~$0.10-$0.50 for full scrape
- Cloud Build: ~$0.003 per build minute
- Total: Less than $1 for complete deployment and scraping

---

**Next Steps:**
1. Choose deployment option above
2. Deploy the service
3. Run scraping for all 160 breeds
4. Verify data in database