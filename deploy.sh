#!/bin/bash
# Deployment script for Google Cloud Run

set -e

# Configuration
PROJECT_ID="phils-data-apps"
SERVICE_NAME="swiss-bandmap"
REGION="europe-west1"

echo "🚀 Deploying Swiss Bandmap to Google Cloud Run..."

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Load credentials from .env file
source .env

# Build and deploy
echo "🏗️  Building container image with fresh data..."
gcloud builds submit \
    --config cloudbuild.yaml \
    --substitutions _CONSUMER_KEY="$CONSUMER_KEY",_CONSUMER_SECRET="$CONSUMER_SECRET",_SERVICE_NAME="$SERVICE_NAME" \
    .

echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars CONSUMER_KEY="$CONSUMER_KEY" \
    --set-env-vars CONSUMER_SECRET="$CONSUMER_SECRET" \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10

echo "✅ Deployment completed!"
echo "🌐 Your app should be available at:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)"