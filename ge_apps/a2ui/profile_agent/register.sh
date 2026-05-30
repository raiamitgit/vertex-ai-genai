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

# Automation script to register the deployed Cloud Run agent with Gemini Enterprise.

# 1. Load active credentials from shared .env file in the parent folder
if [ -f "../.env" ]; then
  export $(grep -v '^#' ../.env | xargs)
else
  echo "❌ Error: Shared .env file not found in parent directory."
  exit 1
fi

SERVICE_NAME="profile-a2ui-agent"
REGION="us-central1"

echo "===================================================="
echo "Registering Agent with Gemini Enterprise..."
echo "Project ID:     $GOOGLE_CLOUD_PROJECT"
echo "Project Number: $GOOGLE_CLOUD_PROJECT_NUMBER"
echo "Engine ID:      $GEMINI_ENTERPRISE_APP_ID"
echo "===================================================="

# 2. Retrieve the live Cloud Run Service URL
echo "Fetching Cloud Run URL for service '$SERVICE_NAME'..."
AGENT_URL=$(gcloud run services describe "$SERVICE_NAME" --project="$GOOGLE_CLOUD_PROJECT" --region="$REGION" --format="value(status.url)")

if [ -z "$AGENT_URL" ]; then
  echo "❌ Error: Could not retrieve URL for Cloud Run service '$SERVICE_NAME'."
  exit 1
fi

echo "Live Agent URL: $AGENT_URL"

# 3. Programmatically generate the production agent card in a temp file
echo "Generating production Agent Card with dynamic URL..."
python3 -c "
import json
try:
    with open('agent_card.json', 'r') as f:
        card = json.load(f)
    card['url'] = '$AGENT_URL'
    with open('agent_card_prod.json', 'w') as f:
        json.dump(card, f, indent=2)
    print('✅ Production Agent Card generated (agent_card_prod.json).')
except Exception as e:
    print(f'❌ Failed to generate card: {e}')
    exit(1)
"
if [ $? -ne 0 ]; then
  exit 1
fi

# 4. Read and escape the production agent card JSON so it fits cleanly inside a stringified field
escaped_agent_card=$(python3 -c "
import json
with open('agent_card_prod.json', 'r') as f:
    data = json.load(f)
print(json.dumps(json.dumps(data))) # Double dumps stringifies and escapes the JSON
")

# 5. Trigger the Discovery Engine REST registration call using curl
echo "Sending registration call to Gemini Enterprise Discovery Engine..."
response=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "X-Goog-User-Project: $GOOGLE_CLOUD_PROJECT" \
  -H "Content-Type: application/json" \
  "https://global-discoveryengine.googleapis.com/v1alpha/projects/${GOOGLE_CLOUD_PROJECT_NUMBER}/locations/global/collections/default_collection/engines/${GEMINI_ENTERPRISE_APP_ID}/assistants/default_assistant/agents" \
  -d "{
    \"name\": \"profile-agent\",
    \"displayName\": \"Profile Agent\",
    \"description\": \"An agent that displays user profiles using A2UI v0.8 cards.\",
    \"a2aAgentDefinition\": {
      \"jsonAgentCard\": $escaped_agent_card
    }
  }")

# Clean up temp file
rm -f agent_card_prod.json

# Extract body and HTTP status code
http_status=$(echo "$response" | tail -n1)
response_body=$(echo "$response" | sed '$d')

if [ "$http_status" -eq 200 ] || [ "$http_status" -eq 201 ]; then
  echo ""
  echo "===================================================="
  echo "✅ Agent successfully registered with Gemini Enterprise!"
  echo "===================================================="
  echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
else
  echo ""
  echo "❌ Registration failed (HTTP Status: $http_status)"
  echo "Error Response:"
  echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
  exit 1
fi
