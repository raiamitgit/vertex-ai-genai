"""
ADK Agent: Basic Document Processing

This script shows how to build a basic ADK agent that processes uploaded files (PDFs and CSVs) using the built-in `load_artifacts_tool`.

Key concepts:
1.  **Basic Agent Setup**: Defining a simple agent with instructions and tools.
2.  **Built-in Tool Usage**: Using `load_artifacts_tool` to read file content.
3.  **Session Service Selection**: Switching between in-memory and Vertex AI session services based on the environment.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, VertexAiSessionService
from google.adk.tools import ToolContext
from google.adk.tools.load_artifacts_tool import load_artifacts_tool
from google.genai import types

# Load environment variables from .env file in the same directory
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Single Agent for Document Processing ---
SYSTEM_INSTRUCTION = """You are a Document Assistant. Your job is to help users by answering questions about the files they upload.

Use the `load_artifacts_tool` to read the content of these files.

### Supported File Types:
1. **PDF Documents**: When a user references a PDF, use the `load_artifacts_tool` to read the text.
2. **CSV Data Files**: When a user references a CSV, use the `load_artifacts_tool` to read the data.
3. **Images (PNG, JPG, JPEG)**: You can process image files natively.
4. **Other Files**: If the user uploads any other file type, tell them that you cannot process it.

### Guardrails:
* **File-Centric Focus**: Answer questions based on the data in the uploaded files. Do not guess beyond the content.
* **Enforce File Uploads**: If the user asks a question but has not uploaded any file, tell them to upload one first.
* **No General Knowledge Queries**: Refuse to answer general questions unrelated to an uploaded file.
* **Always Use Tools**: Do not assume you know the content of a file without reading it.

Keep interactions helpful within these boundaries.
"""

# --- Agent Definition ---
# The main agent that handles that uses the load_artifacts_tool to process files.
orchestrator = Agent(
    name="minimal_summarizer",
    description="Processes documents including PDFs and CSVs.",
    model="gemini-2.5-flash",
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True
        )
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[load_artifacts_tool],
)

# --- Environment Setup ---
# Check if running in the cloud or locally to decide which session service to use.
running_in_cloud = os.getenv("RUNNING_IN_CLOUD", "false").lower() == "true"
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if running_in_cloud:
    # In the cloud, use VertexAiSessionService to persist chat history in Vertex AI.
    print(f"Using VertexAiSessionService (Project: {project_id})")
    session_service = VertexAiSessionService(project=project_id, location=location)
else:
    # Locally, use InMemorySessionService which clears history when the process restarts.
    print("Using InMemorySessionService")
    session_service = InMemorySessionService()

# Runner ties the agent and session service together.
runner = Runner(
    app_name="minimal_summarizer_agent",
    agent=orchestrator,
    session_service=session_service,
)

root_agent = runner.agent
