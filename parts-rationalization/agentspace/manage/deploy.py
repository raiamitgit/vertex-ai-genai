"""
Script to deploy the Part Optimization Agent to Google Cloud Agent Engine.

This script packages the ADK agent, its dependencies, and necessary tools,
and deploys it as a Reasoning Engine on Vertex AI.

Usage (from the parent `part_optimization` directory):
    python -m scripts.deploy
"""

import os
import sys

import vertexai
from dotenv import load_dotenv
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

from agentspace.agent import root_agent

load_dotenv()

def main():
    """Orchestrates the agent deployment process."""
    print("Loaded configuration from .env file.")

    # --- Initialize Vertex AI SDK ---
    print("\n--- Initializing Vertex AI SDK ---")
    vertexai.init(
        project=os.getenv("GCP_PROJECT_ID"),
        location=os.getenv("GCP_LOCATION"),
        staging_bucket=os.getenv("AGENT_STAGING_BUCKET")
    )
    print("SDK Initialized successfully.")

    # --- Create Deployable ADK App ---
    print("\n--- Creating Deployable ADK App ---")
    app = AdkApp(agent=root_agent, enable_tracing=True)
    print(f"ADK App created for agent: '{root_agent.name}'")

    # --- Deploy to Agent Engine ---
    print("\n--- Starting Deployment to Agent Engine (This may take several minutes) ---")
    try:
        # Define the full list of environment variables the agent needs in the cloud.
        cloud_env_vars_list = [
            "GCP_PROJECT_ID", "GCP_LOCATION", "GCS_BUCKET_NAME", "GCS_THUMBNAIL_FOLDER",
            "ADK_AGENT_MODEL", "BQ_PROJECT_ID", "BQ_REGION", "BQ_DATASET_ID",
            "BQ_METADATA_TABLE", "BQ_OBJECT_TABLE", "BQ_MODEL_NAME", "BQ_CONNECTION_ID",
            "BQ_GEMINI_MODEL", "PHYSNA_TENANT_ID", "PHYSNA_CLIENT_ID",
            "PHYSNA_CLIENT_SECRET", "AUTH_URL",
        ]
        cloud_env_vars = {var: os.getenv(var) for var in cloud_env_vars_list}

        agent_display_name = os.getenv("AGENT_DISPLAY_NAME")
        agent_description = "An agent that helps engineers find existing parts and retrieve detailed supply chain information."

        remote_app = agent_engines.create(
            agent_engine=app,
            requirements="./requirements.txt",
            extra_packages=["./agentspace", "./tools"],
            env_vars=cloud_env_vars,
            gcs_dir_name="part-search-agent-staging",
            display_name=agent_display_name,
            description=agent_description,
        )
        print("\nDeployment Successful!")
        print("Your agent is now running on Agent Engine.")
        print(f"   Resource Name: {remote_app.resource_name}")
        print("\nYou can now register this agent with Agentspace using its resource name.")
        print("   To do so, add the full resource name to your .env file as AGENT_ENGINE_RESOURCE_NAME and run the registration script.")

    except Exception as e:
        print(f"\nDeployment Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
