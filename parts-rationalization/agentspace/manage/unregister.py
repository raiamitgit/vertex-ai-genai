"""
Script to unregister the agent from Agentspace and delete the Agent Engine.

This script provides two main functionalities, which can be run separately or
together:
1.  --unregister: Finds the agent in Agentspace by its display name and removes
    its registration.
2.  --delete: Deletes the underlying Agent Engine deployment from Vertex AI.

Usage (from the parent `part_optimization` directory):
    # Unregister from Agentspace only
    python -m scripts.unregister --unregister

    # Delete the Agent Engine deployment only
    python -m scripts.unregister --delete

    # Do both
    python -m scripts.unregister --unregister --delete
"""

import argparse
import os
import sys

import google.auth
import google.auth.transport.requests
import requests
import vertexai
from dotenv import load_dotenv
from vertexai import agent_engines

# --- Core Logic Functions ---

def find_agentspace_agent_id(project_id, location, app_id, display_name, token):
    """Finds the agent ID in Agentspace by its display name."""
    print(f"\n--- Searching for agent '{display_name}' in Agentspace ---")
    region = location.split('-')[0]
    hostname = f"{region}-discoveryengine.googleapis.com" if region != "global" else "discoveryengine.googleapis.com"
    
    api_url = (
        f"https://{hostname}/v1alpha/projects/{project_id}/locations/{region}/"
        f"collections/default_collection/engines/{app_id}/assistants/default_assistant/agents"
    )
    headers = {"Authorization": f"Bearer {token}", "x-goog-user-project": project_id}
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        agents = response.json().get("agents", [])
        
        for agent in agents:
            if agent.get("displayName") == display_name:
                agent_id = agent.get("name").split('/')[-1]
                print(f"Found agent with ID: {agent_id}")
                return agent_id
        
        print(f"Agent with display name '{display_name}' not found.")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"Could not list agents. Status: {e.response.status_code}, Response: {e.response.text}")
        return None

def unregister_from_agentspace(project_id, location, app_id, agent_id, token):
    """Sends a DELETE request to unregister the agent from Agentspace."""
    print("\n--- Unregistering from Agentspace ---")
    region = location.split('-')[0]
    hostname = f"{region}-discoveryengine.googleapis.com" if region != "global" else "discoveryengine.googleapis.com"

    api_url = (
        f"https://{hostname}/v1alpha/projects/{project_id}/locations/{region}/"
        f"collections/default_collection/engines/{app_id}/assistants/default_assistant/agents/{agent_id}"
    )
    headers = {"Authorization": f"Bearer {token}", "x-goog-user-project": project_id}

    try:
        response = requests.delete(api_url, headers=headers)
        if response.status_code in [200, 204]:
            print(f"Agent '{agent_id}' successfully unregistered.")
        elif response.status_code == 404:
            print(f"Agent '{agent_id}' was already unregistered or not found.")
        else:
            response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Unregistration failed. Status: {e.response.status_code}, Response: {e.response.text}")

def delete_agent_engine(project_id, location, resource_name):
    """Deletes the Agent Engine service from Vertex AI."""
    print("\n--- Deleting Agent Engine from Vertex AI ---")
    if not resource_name:
        print("SKIPPING: AGENT_ENGINE_RESOURCE_NAME not set in .env file.")
        return

    try:
        vertexai.init(project=project_id, location=location)
        agent_engines.delete(resource_name)
        print(f"Agent Engine '{resource_name.split('/')[-1]}' successfully deleted.")
    except Exception as e:
        if "NotFound" in str(e):
            print("Agent Engine was already deleted or not found.")
        else:
            print(f"Deletion failed: {e}")

# --- Main Execution ---

def main():
    """Parses arguments and orchestrates the cleanup process."""
    parser = argparse.ArgumentParser(description="Undeploy and unregister the GM Part Optimization Agent.")
    parser.add_argument("--unregister", action="store_true", help="Unregister the agent from Agentspace.")
    parser.add_argument("--delete", action="store_true", help="Delete the Agent Engine from Vertex AI.")
    args = parser.parse_args()

    if not args.unregister and not args.delete:
        parser.print_help()
        sys.exit(0)

    load_dotenv()
    
    project_id = os.getenv("GCP_PROJECT_ID")
    location = os.getenv("AGENTSPACE_LOCATION")
    app_id = os.getenv("AGENTSPACE_APP_ID")
    resource_name = os.getenv("AGENT_ENGINE_RESOURCE_NAME")
    display_name = os.getenv("AGENT_DISPLAY_NAME")

    print("\nThis script will perform the following irreversible actions:")
    if args.unregister:
        print(f"  - Unregister agent named '{display_name}' from Agentspace App '{app_id}'.")
    if args.delete and resource_name:
        print(f"  - Delete Agent Engine '{resource_name.split('/')[-1]}' from Vertex AI.")
    
    try:
        if input("\nAre you sure you want to continue? (y/n): ").lower() != 'y':
            print("Cancelled.")
            sys.exit(0)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(0)

    # --- Execute Actions ---
    if args.unregister:
        try:
            creds, _ = google.auth.default()
            creds.refresh(google.auth.transport.requests.Request())
            token = creds.token
            agent_id = find_agentspace_agent_id(project_id, location, app_id, display_name, token)
            if agent_id:
                unregister_from_agentspace(project_id, location, app_id, agent_id, token)
        except Exception as e:
            print(f"A critical error occurred during unregistration: {e}")

    if args.delete:
        delete_agent_engine(project_id, location, resource_name)

    print("\n--- Script finished. ---")

if __name__ == "__main__":
    main()
