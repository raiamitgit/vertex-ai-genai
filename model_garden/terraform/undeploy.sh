#!/usr/bin/env bash
set -eo pipefail

PROJECT_ID="${PROJECT_ID:-YOUR_PROJECT_ID}"

echo "Initiating Terraform destroy to undeploy model and delete dedicated endpoint for project ${PROJECT_ID}..."
terraform destroy -auto-approve -var="project_id=${PROJECT_ID}"

echo "Undeployment and endpoint teardown complete."
