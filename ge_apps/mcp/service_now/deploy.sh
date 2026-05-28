#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "=== Deploying Custom ServiceNow BYO-MCP Server ==="

# Ensure execution occurs in the correct directory
CDIR="$(dirname "$0")"
cd "$CDIR"

# 1. Check gcloud authentication
if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud CLI is not installed or not in PATH."
    exit 1
fi

# 2. Load ServiceNow credentials from local .env file
if [ -f ".env" ]; then
    echo "Loading environment variables from local .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo "ERROR: .env file not found in the directory."
    echo "Please copy .env.example to .env and populate with ServiceNow credentials."
    exit 1
fi

# Verify required variables
if [ -z "$SN_INSTANCE_URL" ] || [ -z "$SN_USERNAME" ] || [ -z "$SN_PASSWORD" ]; then
    echo "ERROR: Missing required credentials in .env file."
    exit 1
fi

# Extract active GCP project or use fallback
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT" ]; then
    PROJECT="data-n-models"
fi

REGION="us-central1"
SERVICE_NAME="service-now-byo-mcp"

echo "Project: $PROJECT"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME"

# 3. Deploy to Google Cloud Run (using source builds)
echo "Building and deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region="$REGION" \
    --project="$PROJECT" \
    --allow-unauthenticated \
    --set-env-vars SN_INSTANCE_URL="$SN_INSTANCE_URL",SN_USERNAME="$SN_USERNAME",SN_PASSWORD="$SN_PASSWORD"

# 4. Extract the Service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT" --format="value(status.url)")

echo ""
echo "=================================================="
echo "Deployment Successful!"
echo "=================================================="
echo "Service URL: $SERVICE_URL"
echo ""
echo "Copy these endpoints to configure the Custom MCP Data Store in Gemini Enterprise:"
echo ""
echo "1. MCP Server URL:"
echo "   $SERVICE_URL/mcp"
echo ""
echo "2. Authorization URL:"
echo "   $SERVICE_URL/oauth/authorize"
echo ""
echo "3. Token URL:"
echo "   $SERVICE_URL/oauth/token"
echo ""
echo "4. Client ID:"
echo "   mock-client-id"
echo ""
echo "5. Client Secret:"
echo "   mock-client-secret"
echo "=================================================="
