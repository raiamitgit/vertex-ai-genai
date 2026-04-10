#!/bin/bash

# Deployment script for Minimal Summarizer Agent
# Creates a NEW instance in Agent Engine

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV_FILE="$SCRIPT_DIR/.env"

# Load environment variables from .env file if it exists
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

PROJECT="${GOOGLE_CLOUD_PROJECT:-data-n-models}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
DISPLAY_NAME="minimal_summarizer_agent"
ADK_BIN="${ADK_BIN:-$SCRIPT_DIR/../.venv/bin/adk}"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

echo "Deploying Minimal Summarizer to Agent Engine..."
echo "Project: $PROJECT"
echo "Region: $REGION"

# Run deployment command targeting summarizer_agent folder
$ADK_BIN deploy agent_engine \
  --project="$PROJECT" \
  --region="$REGION" \
  --display_name="$DISPLAY_NAME" \
  --requirements_file="$REQUIREMENTS_FILE" \
  --env_file "$ENV_FILE" \
  --trace_to_cloud \
  --otel_to_cloud \
  --validate-agent-import \
  "$SCRIPT_DIR"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "Deployment initiated successfully!"
else
  echo "Deployment failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
