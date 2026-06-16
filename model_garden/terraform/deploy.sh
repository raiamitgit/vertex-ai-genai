#!/usr/bin/env bash
set -eo pipefail

PROJECT_ID="${PROJECT_ID:-YOUR_PROJECT_ID}"

echo "Ensuring Vertex AI Service Agent (P4SA) exists for project ${PROJECT_ID}..."
gcloud beta services identity create --service=aiplatform.googleapis.com --project="${PROJECT_ID}"

echo "Initializing Terraform..."
terraform init

echo "Deploying dedicated endpoint and model..."
terraform apply -auto-approve -var="project_id=${PROJECT_ID}"

echo "Deployment complete."
