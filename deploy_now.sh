#!/bin/bash

# Quick deployment script after authentication
set -e

echo "🚀 AKC Scraper Cloud Deployment"
echo "================================"

# Configuration
PROJECT_ID="breed-data"
REGION="us-central1"
SERVICE_NAME="akc-breed-scraper"

# Load environment variables
if [ -f .env ]; then
    source .env
    echo "✅ Environment variables loaded from .env"
else
    echo "❌ .env file not found!"
    exit 1
fi

# Set project
echo "📋 Setting project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable cloudbuild.googleapis.com --quiet
gcloud services enable run.googleapis.com --quiet
gcloud services enable containerregistry.googleapis.com --quiet

# Build container using Cloud Build
echo "🏗️ Building container with Google Cloud Build..."
echo "This will build the Docker image in the cloud (no local Docker needed)"

# Submit build (specify Dockerfile directly)
cp Dockerfile.akc Dockerfile
gcloud builds submit \
    --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
    --timeout=20m

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 5 \
    --set-env-vars "SUPABASE_URL=${SUPABASE_URL},SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo ""
echo "✅ Deployment Complete!"
echo "======================="
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "📝 Test Commands:"
echo ""
echo "1. Check service status:"
echo "   curl ${SERVICE_URL}"
echo ""
echo "2. Start scraping 5 breeds (test):"
echo "   curl -X POST ${SERVICE_URL}/scrape -H 'Content-Type: application/json' -d '{\"limit\": 5}'"
echo ""
echo "3. Scrape all 160 breeds:"
echo "   curl -X POST ${SERVICE_URL}/scrape"
echo ""
echo "4. Check job status (replace JOB_ID):"
echo "   curl ${SERVICE_URL}/status/JOB_ID"
echo ""
echo "📊 View logs:"
echo "   gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --limit 20"