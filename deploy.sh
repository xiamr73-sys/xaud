#!/bin/bash

# ==========================================
# BLDC AI Simulator - Cloud Run Deploy Script
# ==========================================

# ⚠️ IMPORTANT: Replace 'YOUR-PROJECT-ID' below with your actual Google Cloud Project ID
PROJECT_ID="YOUR-PROJECT-ID"
SERVICE_NAME="motor-sim"
REGION="us-central1"

echo "🚀 Starting Deployment for Project: $PROJECT_ID"

# 1. Build Container Image (Cloud Build)
echo "📦 Building Container Image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# 2. Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated

echo "✅ Deployment Complete! Check the URL above."
