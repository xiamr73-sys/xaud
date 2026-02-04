#!/bin/bash

# GCP Deployment Script
# Usage: ./deploy_gcp.sh [PROJECT_ID] [APP_NAME]

PROJECT_ID=$1
APP_NAME=${2:-quant-monitor}
REGION="us-central1"

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: ./deploy_gcp.sh [PROJECT_ID] [APP_NAME]"
    echo "Please provide your Google Cloud Project ID."
    exit 1
fi

echo "🚀 Starting Deployment to Google Cloud..."
echo "Project: $PROJECT_ID"
echo "App Name: $APP_NAME"

# 1. Enable Services
echo "1️⃣  Enabling required GCP services..."
gcloud services enable appengine.googleapis.com cloudbuild.googleapis.com run.googleapis.com --project $PROJECT_ID

# 2. Build & Deploy to App Engine (Easiest for Streamlit)
#    Alternatively, we could build a Docker image and deploy to Cloud Run.
#    Here we use App Engine Flexible or Standard. Standard is cheaper but has timeouts for websockets.
#    Streamlit uses websockets, so App Engine Flex or Cloud Run is better.
#    Let's use Cloud Run for better cost/performance for Streamlit.

echo "2️⃣  Building and Deploying to Cloud Run (Recommended for Streamlit)..."

gcloud builds submit --tag gcr.io/$PROJECT_ID/$APP_NAME --project $PROJECT_ID

gcloud run deploy $APP_NAME \
  --image gcr.io/$PROJECT_ID/$APP_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8501 \
  --project $PROJECT_ID

echo "✅ Deployment Complete!"
echo "Your app should be available at the URL above."
