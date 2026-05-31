#!/bin/bash
# Script to deploy the profile_agent to Cloud Run.

# Load environment variables from parent .env file if it exists
if [ -f ../.env ]; then
  export $(grep -v '^#' ../.env | xargs)
elif [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

PROJECT="${GOOGLE_CLOUD_PROJECT:-data-n-models}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="profile-a2ui-agent"

echo "===================================================="
echo "Deploying profile-a2ui-agent to Google Cloud Run..."
echo "Project: $PROJECT"
echo "Region:  $REGION"
echo "===================================================="

# Run gcloud run deploy using source build
gcloud run deploy "$SERVICE_NAME" \
  --source=. \
  --project="$PROJECT" \
  --region="$REGION" \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=True,GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=$REGION,RUN_MODE=solved"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo ""
  echo "===================================================="
  echo "Service deployed successfully!"
  AGENT_URL=$(gcloud run services describe "$SERVICE_NAME" --project="$PROJECT" --region="$REGION" --format="value(status.url)")
  echo "Service URL: $AGENT_URL"
  echo "===================================================="
else
  echo ""
  echo "Deployment failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
