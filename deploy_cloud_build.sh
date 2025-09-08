#!/bin/bash

# Deploy AKC Scraper using Google Cloud Build (no local Docker required)

set -e

# Configuration
PROJECT_ID="breed-data"
SERVICE_NAME="akc-breed-scraper"
REGION="us-central1"

echo "🚀 AKC Breed Scraper - Cloud Build Deployment"
echo "============================================="
echo "Project: ${PROJECT_ID}"
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo ""

# Check prerequisites
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

# Load environment variables
source .env

# Check gcloud is configured
echo "📋 Checking Google Cloud configuration..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# Create a temporary file with environment variables for Cloud Run
echo "📝 Preparing environment variables..."
cat > .env.yaml << EOF
SUPABASE_URL: "${SUPABASE_URL}"
SUPABASE_SERVICE_KEY: "${SUPABASE_SERVICE_KEY}"
EOF

# Submit build to Cloud Build
echo "🏗️ Building container with Cloud Build..."
gcloud builds submit \
    --config cloudbuild.yaml \
    --substitutions=_SERVICE_NAME=${SERVICE_NAME} \
    --project ${PROJECT_ID}

# Update Cloud Run service with environment variables
echo "🔐 Setting environment variables..."
gcloud run services update ${SERVICE_NAME} \
    --set-env-vars "SUPABASE_URL=${SUPABASE_URL},SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}" \
    --region ${REGION} \
    --project ${PROJECT_ID}

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --format 'value(status.url)')

# Clean up temp file
rm -f .env.yaml

echo ""
echo "✅ Deployment complete!"
echo "================================"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "📝 Test the service:"
echo "  curl ${SERVICE_URL}"
echo ""
echo "🚀 Start scraping:"
echo "  # Scrape 10 breeds:"
echo "  curl -X POST ${SERVICE_URL}/scrape -H 'Content-Type: application/json' -d '{\"limit\": 10}'"
echo ""
echo "  # Scrape all breeds:"
echo "  curl -X POST ${SERVICE_URL}/scrape"
echo ""
echo "📊 Check status:"
echo "  curl ${SERVICE_URL}/status/<job_id>"
echo ""
echo "📋 View logs:"
echo "  gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --limit 50"