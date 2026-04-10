"""
ADK Agent: Document Processing with Custom Code Execution Tool

Shows how to build an ADK agent that handles document workflows, file processing via a custom
code execution function tool, and image generation.

Key Functionalities:
1.  **Custom Code Execution Tool**: Uses `UnsafeLocalCodeExecutor` inside a function tool to process CSV and JSON files.
2.  **Image Generation**: Uses `gemini-3.1-flash-image-preview` with `response_modalities=["IMAGE"]` to generate visuals.
3.  **Text Response**: Responds in text by default.
4.  **Guardrails**: Enforce a file-centric focus where the agent refuses to answer questions unless a file is provided.
5.  **GCS Artifact Management**: Use Google Cloud Storage for artifacts to work with the Enterprise UI.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.artifacts import FileArtifactService, GcsArtifactService
from google.adk.code_executors.code_execution_utils import CodeExecutionInput
from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, VertexAiSessionService
from google.adk.tools import FunctionTool, ToolContext
from google.adk.tools.load_artifacts_tool import load_artifacts_tool
from google.genai import types

# Load environment variables from .env file in the same directory
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Custom class to force global location for Gemini 3 models
class GlobalGemini(Gemini):
    def __init__(self, model: str):
        # Set the environment variable to force the ADK SDK to use the global location for the client.
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        super().__init__(model=model)

# --- Single Agent for Document Processing ---
SYSTEM_INSTRUCTION = """You are a Document Assistant. Your job is to assist users by answering questions derived from the files they upload.

### Response Format:
1. **Chat**: By default, answer the user's questions in the chat text.
2. **Infographics**: If the user asks to generate an image, chart, or infographic to explain something:
    - Generate a prompt describing the visual you want.
    - Invoke the `generate_infographic` tool with the prompt and a filename (e.g., 'chart.png').
    - Your final text response to the user must only be a confirmation message like: "I have generated the visuals for you."

### Processing Files:
1. **CSV and JSON Files**: You MUST use the `execute_python_code` tool to read and process these files. Write Python code to read the file, analyze the data, and print the result. You must specify the file names you need to read in the `files_to_load` argument so the system can make them available on disk for your script.
2. **Other Files (PDF, Images)**: Use Gemini's native capabilities to process them.
3. **Unsupported Files**: If the user uploads a file type that is not supported by Gemini and is not CSV/JSON, decline to process it.

### Guardrails:
* **File-Centric Focus**: Answer questions based on the data provided in the uploaded files.
* **Enforce File Uploads**: If the user asks a question but has not uploaded any file, instruct them to upload one first.
* **No General Knowledge Queries**: Refuse to answer general questions unrelated to an uploaded file.
* **Always Use Tools**: Do not assume you know the content of a file without reading it.

Keep interactions helpful within these boundaries.
"""

async def execute_python_code(code: str, files_to_load: list[str] = None, tool_context: ToolContext = None) -> dict:
    """Executes Python code locally. Use this to process CSV or JSON files.
    
    Args:
        code: The Python code to execute.
        files_to_load: Optional list of file names (artifacts) to make available on disk for the script.
        tool_context: ADK ToolContext provided automatically.
    """
    logger.info(f"Executing custom code execution tool. Files to load: {files_to_load}")
    
    # Load requested files from artifact store and write to disk
    if files_to_load and tool_context:
        for filename in files_to_load:
            try:
                logger.info(f"Loading artifact {filename} for code execution")
                part = await tool_context.load_artifact(filename)
                if part.inline_data and part.inline_data.data:
                    with open(filename, "wb") as f:
                        f.write(part.inline_data.data)
                    logger.info(f"Dumped artifact {filename} to disk.")
            except Exception as e:
                logger.error(f"Failed to load artifact {filename}: {e}")
                
    executor = UnsafeLocalCodeExecutor()
    input_data = CodeExecutionInput(code=code)
    
    try:
        result = executor.execute_code(None, input_data)
        
        # Clean up temp files
        if files_to_load:
            for filename in files_to_load:
                try:
                    if os.path.exists(filename):
                        os.remove(filename)
                        logger.info(f"Cleaned up temp file {filename}")
                except Exception as e:
                    logger.error(f"Failed to remove temp file {filename}: {e}")
                    
        return {
            "status": "success" if not result.stderr else "error",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        logger.error(f"Error in execute_python_code: {e}")
        return {"status": "error", "message": str(e)}

async def generate_infographic(prompt: str, filename: str, tool_context: ToolContext) -> dict:
    """Generates an image or infographic based on the prompt using Gemini 3.1 Flash Image Preview model.
    
    RATIONALE:
    Shows how to do text-to-image generation in an agent.
    Uses `gemini-3.1-flash-image-preview` by requesting the "IMAGE" response modality.
    
    Args:
        prompt: Description of the image to generate.
        filename: Desired filename for the saved image (e.g., 'infographic.png').
        tool_context: ADK ToolContext provided automatically.
    """
    from google.genai import Client
    from google.genai import types
    
    model_name = "gemini-3.1-flash-image-preview" 
    # Project is automatically picked up from GOOGLE_CLOUD_PROJECT environment variable
    client = Client(vertexai=True, location="global")
    
    try:
        logger.info(f"Attempting to generate image with model {model_name} and prompt: {prompt}")
        
        # To generate images with this preview model, we set response_modalities to ["IMAGE"]
        generate_content_config = types.GenerateContentConfig(
            response_modalities = ["IMAGE"],
        )
        
        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)]
                )
            ],
            config=generate_content_config,
        )
        
        part = response.candidates[0].content.parts[0]
        
        if part.inline_data:
            image_bytes = part.inline_data.data
        else:
            raise ValueError("No inline data found in the response part.")
            
        save_part = types.Part(inline_data=types.Blob(
            mime_type="image/png",
            data=image_bytes
        ))
        
        version = await tool_context.save_artifact(filename, save_part)
        
        return {
            "status": "success",
            "message": f"Image saved as artifact: {filename}",
            "version": version
        }
    except Exception as e:
        logger.error(f"Failed to generate image: {e}")
        return {"status": "error", "message": str(e)}

# Agent definition handling conversation and tools.
orchestrator = Agent(
    name="minimal_summarizer",
    description="Processes documents and data files using custom code execution.",
    model=GlobalGemini("gemini-3-flash-preview"),
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True
        )
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[load_artifacts_tool, execute_python_code, generate_infographic],
)

# Environment & Infrastructure Setup
running_in_cloud = os.getenv("RUNNING_IN_CLOUD", "false").lower() == "true"
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
bucket_name = os.getenv("GCS_ARTIFACT_BUCKET")

if running_in_cloud:
    # In the cloud, use Vertex AI for sessions.
    print(f"Using VertexAiSessionService (Project: {project_id})")
    session_service = VertexAiSessionService(project=project_id, location=location)
else:
    # Locally, use in-memory sessions.
    print("Using InMemorySessionService (Local)")
    session_service = InMemorySessionService()

# Always use GCS for artifacts to ensure files are accessible in UI.
print(f"Using GcsArtifactService with bucket: {bucket_name}")
artifact_service = GcsArtifactService(bucket_name=bucket_name)

# Runner ties everything together.
runner = Runner(
    app_name="minimal_summarizer_agent",
    agent=orchestrator,
    session_service=session_service,
    artifact_service=artifact_service,
)

root_agent = runner.agent
