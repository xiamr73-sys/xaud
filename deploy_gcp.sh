#!/bin/bash

# Configuration
APP_NAME="crypto-monitor"
REGION="us-central1"

# Force set Project ID to 'nextual' as requested to avoid detection errors
PROJECT_ID="project-2d8472bc-a374-4f55-beb"
gcloud config set project $PROJECT_ID

echo "🚀 Starting deployment to Google Cloud Run..."
echo "Project ID: $PROJECT_ID"
echo "App Name: $APP_NAME"
echo "Region: $REGION"

# 1. Enable necessary services
echo "🔌 Enabling Cloud Build and Cloud Run services..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com

# 2. Build Docker image using Cloud Build (Server-side build)
echo "🔨 Submitting build to Google Cloud Build..."
# Ensure no double slashes in tag
IMAGE_TAG="gcr.io/${PROJECT_ID}/${APP_NAME}"
echo "Target Image: $IMAGE_TAG"

# Adding --timeout to ensure it doesn't time out, and capturing output to check for success
gcloud builds submit --tag "$IMAGE_TAG" .

# Check if build succeeded
if [ $? -ne 0 ]; then
    echo "❌ Cloud Build failed! Please check the logs above."
    exit 1
fi

# 3. Deploy to Cloud Run
# Note: --no-cpu-throttling is important for the background thread to keep running
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $APP_NAME \
  --image "$IMAGE_TAG" \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --no-cpu-throttling \
  --min-instances 1 \
  --port 5001

echo "✅ Deployment complete!"
echo "📊 Service Status:"
gcloud run services describe $APP_NAME --platform managed --region $REGION
