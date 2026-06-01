"""Triggers search interactions with Workflow agents.

Workflow agents configured with structured triggers (e.g., schedules) require
an executing session to satisfy routing preconditions. This script creates a
session with the required agent, trigger-type, and revision labels, and then
invokes the streamAssist endpoint using that session. Without these labels
attached to the session, the API returns a FAILED_PRECONDITION error because the
routing engine cannot validate the starting node constraints.
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
AGENT_ID = os.environ.get("AGENT_ID")
TRIGGER_TYPE = os.environ.get("TRIGGER_TYPE", "schedule")
REVISION_ID = os.environ.get("REVISION_ID")

def get_access_token():
    """Retrieves Google Cloud Access Token using Application Default Credentials.

    Returns:
        str: The access token.
    """
    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)
    return credentials.token

def create_workflow_session(token):
    """Creates a Session in Discovery Engine with routing labels.

    The routing engine uses these session labels to match the incoming request
    with the target workflow agent, its starting trigger type, and the active
    revision.

    Args:
        token (str): The access token.

    Returns:
        str: The resource name of the created session.
    """
    url = (
        f"https://discoveryengine.googleapis.com/v1alpha/"
        f"projects/{PROJECT_ID}/locations/global/collections/default_collection/"
        f"engines/{ENGINE_ID}/sessions"
    )
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": PROJECT_ID
    }
    
    payload = {
        "userPseudoId": "api_workflow_trigger",
        "labels": [
            "agent",
            "agent:workflow-agent",
            f"agent:workflow-agent:{AGENT_ID}",
            f"agent:workflow-agent:trigger-type:{TRIGGER_TYPE}",
            f"revision:{REVISION_ID}"
        ]
    }
    
    print(f"Creating session with workflow labels for agent {AGENT_ID}...")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        raise RuntimeError(f"Failed to create session: {response.status_code}\n{response.text}")
        
    session_data = response.json()
    session_name = session_data.get("name")
    print(f"Successfully created session: {session_name}")
    return session_name

def trigger_workflow():
    """Triggers the Workflow agent via streamAssist.

    Retrieves access token, creates session, constructs streamAssist payload,
    and streams response.
    """

    token = get_access_token()
    
    # 1. Creates session
    session_name = create_workflow_session(token)
    
    # 2. Prepares request
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
    
    payload = {
        "query": {
            "text": "Prepare sales prep for Example Corporation"
        },
        "session": session_name,  # Passes session
        "agentsSpec": {
            "agentSpecs": [
                {
                    "agentId": AGENT_ID
                }
            ]
        },
        "assistSkippingMode": "REQUEST_ASSIST"  # Bypasses routing
    }
    
    print(f"\nSending streamAssist trigger payload for agent {AGENT_ID}...")
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
    trigger_workflow()
