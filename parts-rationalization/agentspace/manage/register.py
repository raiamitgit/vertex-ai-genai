"""
Script to register a deployed Agent Engine with Google Cloud Agentspace.

This script makes the deployed agent discoverable and usable within an
Agentspace-enabled application (like a search or conversational AI app).

Usage (from the parent `part_optimization` directory):
    python -m scripts.register
"""

import json
import os
import sys

import google.auth
import google.auth.transport.requests
import requests
from dotenv import load_dotenv

def get_access_token() -> str:
    """
    Authenticates with Google Cloud and retrieves an OAuth2 access token.

    Returns:
        The access token string.

    Raises:
        RuntimeError: If authentication fails.
    """
    try:
        credentials, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return credentials.token
    except Exception as e:
        raise RuntimeError(f"Failed to get Google Cloud access token: {e}")

def main():
    """Orchestrates the agent registration process."""
    print("--- Starting Agentspace Registration ---")
    
    load_dotenv()
    print("Loaded configuration from .env file.")

    try:
        access_token = get_access_token()
    except RuntimeError as e:
        print(f"Authentication Error: {e}")
        sys.exit(1)

    # --- Construct API Request ---
    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    gcp_location = os.getenv("AGENTSPACE_LOCATION")
    agentspace_app_id = os.getenv("AGENTSPACE_APP_ID")
    agent_engine_resource_name = os.getenv("AGENT_ENGINE_RESOURCE_NAME")
    agent_display_name = os.getenv("AGENT_DISPLAY_NAME")
    agent_icon_uri = os.getenv("AGENT_ICON_URI")

    location = gcp_location.split('-')[0]
    hostname = f"{location}-discoveryengine.googleapis.com" if location != "global" else "discoveryengine.googleapis.com"
    api_url = (
        f"https://{hostname}/v1alpha/projects/{gcp_project_id}/locations/{location}/"
        f"collections/default_collection/engines/{agentspace_app_id}/assistants/default_assistant/agents"
    )

    payload = {
        "displayName": agent_display_name,
        "description": "Helps engineers find similar parts and get detailed supply chain data.",
        "icon": {"uri": agent_icon_uri},
        "adk_agent_definition": {
            "tool_settings": {
                "tool_description": (
                    "Use this agent to find similar parts or get specific details about a known part. "
                    "You can provide an asset id or image to find similar items, or ask for details like cost, material, or inventory "
                    "if you have a part's asset ID."
                )
            },
            "provisioned_reasoning_engine": {
                "reasoning_engine": agent_engine_resource_name
            },
        }
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-goog-user-project": gcp_project_id,
    }

    # --- Send Request and Handle Response ---
    print(f"Registering Agent in region '{location}' to App ID '{agentspace_app_id}'...")
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        print("\nAgentspace registration successful!")
        print(f"   Agent Name: {response.json().get('name')}")
    except requests.exceptions.HTTPError as e:
        print("\nAgentspace registration failed.")
        print(f"   Status Code: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)

    print("\n--- Script Finished ---")

if __name__ == "__main__":
    main()
