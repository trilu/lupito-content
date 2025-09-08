#!/bin/bash

# Deploy AKC Scraper using Docker Hub
# This script builds and pushes to Docker Hub, then deploys to Cloud Run

set -e

# Configuration - UPDATE THESE
DOCKER_USERNAME="lupitopetai"  # Replace with your Docker Hub username
SERVICE_NAME="akc-breed-scraper"
IMAGE_NAME="${DOCKER_USERNAME}/${SERVICE_NAME}"
IMAGE_TAG="latest"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

# Google Cloud Configuration
GCP_PROJECT="breed-data"  # Replace with your GCP project ID
REGION="us-central1"

echo "🚀 AKC Breed Scraper Docker Deployment"
echo "======================================"
echo "Docker Image: ${FULL_IMAGE}"
echo ""

# Check prerequisites
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env with:"
    echo "  SUPABASE_URL=your_supabase_url"
    echo "  SUPABASE_SERVICE_KEY=your_supabase_key"
    exit 1
fi

# Step 1: Build Docker image
echo "📦 Building Docker image..."
docker build -f Dockerfile.akc -t ${FULL_IMAGE} .

# Step 2: Push to Docker Hub
echo "⬆️ Pushing to Docker Hub..."
echo "Please login to Docker Hub if prompted:"
docker login
docker push ${FULL_IMAGE}

echo "✅ Docker image pushed successfully!"
echo ""

# Step 3: Deploy to Google Cloud Run (optional)
read -p "Deploy to Google Cloud Run? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Deploying to Cloud Run..."
    
    # Read env vars
    source .env
    
    gcloud run deploy ${SERVICE_NAME} \
        --image docker.io/${FULL_IMAGE} \
        --platform managed \
        --region ${REGION} \
        --project ${GCP_PROJECT} \
        --memory 2Gi \
        --cpu 2 \
        --timeout 900 \
        --max-instances 5 \
        --allow-unauthenticated \
        --set-env-vars "SUPABASE_URL=${SUPABASE_URL},SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
        --platform managed \
        --region ${REGION} \
        --project ${GCP_PROJECT} \
        --format 'value(status.url)')
    
    echo "✅ Cloud Run deployment complete!"
    echo "Service URL: ${SERVICE_URL}"
fi

echo ""
echo "📝 Alternative Deployment Options:"
echo ""
echo "1. Run locally with Docker:"
echo "   docker run -p 8080:8080 --env-file .env ${FULL_IMAGE}"
echo ""
echo "2. Deploy to other cloud providers:"
echo "   - AWS ECS/Fargate"
echo "   - Azure Container Instances"
echo "   - Digital Ocean App Platform"
echo ""
echo "3. Run the scraper directly (without web server):"
echo "   docker run --env-file .env ${FULL_IMAGE} python3 jobs/akc_cloud_scraper.py --limit 10"