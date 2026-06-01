"""Triggers search interactions with No-Code agents.

Sends streamAssist requests to the Discovery Engine API using credentials
retrieved via Application Default Credentials.
"""

import os
import json
import requests
import google.auth
import google.auth.transport.requests
from dotenv import load_dotenv

# Loads configuration
load_dotenv()

PROJECT_ID = os.environ.get("GCP_PROJECT")
ENGINE_ID = os.environ.get("ENGINE_ID")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID", "default_assistant")
NOCODE_AGENT_ID = os.environ.get("NOCODE_AGENT_ID")

def get_access_token():
    """Retrieves Google Cloud Access Token using Application Default Credentials."""
    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)
    return credentials.token

def trigger_nocode():
    """Triggers the No-Code agent via streamAssist.

    Loads configuration, requests access token, constructs payload, and
    streams response.
    """
    token = get_access_token()
    
    # prepare streamAssist request
    url = (
        f"https://discoveryengine.googleapis.com/v1alpha/"
        f"projects/{PROJECT_ID}/locations/global/collections/default_collection/"
        f"engines/{ENGINE_ID}/assistants/{ASSISTANT_ID}:streamAssist"
    )
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": PROJECT_ID
    }
    
    # Standard conversational assist payload
    payload = {
        "query": {
            "text": "What ServiceNow incidents are assigned to user@example.com?"
        },
        "agentsSpec": {
            "agentSpecs": [
                {
                    "agentId": NOCODE_AGENT_ID
                }
            ]
        }
    }
    
    print(f"Sending streamAssist trigger payload for No-Code agent {NOCODE_AGENT_ID}...")
    response = requests.post(url, headers=headers, json=payload, stream=True)
    
    print(f"HTTP Response Status: {response.status_code}")
    if response.status_code != 200:
        print(response.text)
        return
        
    print("\n--- STREAM START ---")
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            print(decoded_line)
    print("--- STREAM END ---")

if __name__ == "__main__":
    trigger_nocode()
