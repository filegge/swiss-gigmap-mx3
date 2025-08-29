#!/bin/bash
# Deployment script for Google Cloud Run

set -e

# Configuration
PROJECT_ID="phils-data-appsd"
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

# Create secret for API credentials if it doesn't exist
echo "🔐 Setting up API credentials secret..."
if ! gcloud secrets describe mx3-api-credentials >/dev/null 2>&1; then
    echo "Creating secret for MX3 API credentials..."
    gcloud secrets create mx3-api-credentials --data-file=/dev/stdin <<EOF
{
    "consumer_key": "$(cat consumer_key.txt | tr -d '\n')",
    "consumer_secret": "$(cat consumer_secret.txt | tr -d '\n')"
}
EOF
fi

# Load credentials from .env file
source .env

# Build and deploy
echo "🏗️  Building container image with fresh data..."
gcloud builds submit \
    --tag gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --build-arg CONSUMER_KEY="$CONSUMER_KEY" \
    --build-arg CONSUMER_SECRET="$CONSUMER_SECRET" \
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