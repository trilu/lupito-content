#!/bin/bash

# Deploy AKC Scraper to Google Cloud Run
# Prerequisites: 
# - gcloud CLI installed and configured
# - Docker installed
# - Supabase credentials in .env file

set -e

# Configuration
PROJECT_ID="your-gcp-project-id"
REGION="us-central1"
SERVICE_NAME="akc-breed-scraper"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying AKC Breed Scraper to Google Cloud Run"
echo "================================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env with SUPABASE_URL and SUPABASE_SERVICE_KEY"
    exit 1
fi

# Build Docker image
echo "📦 Building Docker image..."
docker build -f Dockerfile.akc -t ${IMAGE_NAME} .

# Push to Google Container Registry
echo "⬆️ Pushing image to GCR..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 5 \
    --allow-unauthenticated \
    --set-env-vars "$(cat .env | grep -v '^#' | xargs | tr ' ' ',')"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo "✅ Deployment complete!"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "📝 Usage:"
echo "  Test: curl ${SERVICE_URL}"
echo "  Scrape all: curl -X POST ${SERVICE_URL}/scrape"
echo "  Scrape 10: curl -X POST ${SERVICE_URL}/scrape -H 'Content-Type: application/json' -d '{\"limit\": 10}'"
echo "  Check status: curl ${SERVICE_URL}/status/<job_id>"