#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Automation script to deploy the profile_agent to Cloud Run in SOLVED mode.

PROJECT="data-n-models"
REGION="us-central1"
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
  echo "✅ Service deployed successfully!"
  AGENT_URL=$(gcloud run services describe "$SERVICE_NAME" --project="$PROJECT" --region="$REGION" --format="value(status.url)")
  echo "Service URL: $AGENT_URL"
  echo "===================================================="
else
  echo ""
  echo "❌ Deployment failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
