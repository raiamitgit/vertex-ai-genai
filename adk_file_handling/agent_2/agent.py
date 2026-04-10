"""
ADK Agent: ZIP File Interception and Processing

Shows how to build an ADK agent that intercepts ZIP file uploads, extracts content in memory, and injects it into the conversation.

Key concepts:
1.  **ZIP Interception**: Use `before_model_callback` to inspect messages for ZIP files.
2.  **In-Memory Extraction**: Extract files from the ZIP and handle based on file type.
3.  **Inline Injection**: Inject text content for JSON/CSV or bytes for other files into the prompt.
"""
import io
import logging
import mimetypes
import os
from pathlib import Path
import zipfile

from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.artifacts import FileArtifactService, GcsArtifactService
from google.adk.models.llm_request import LlmRequest
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

Use the `load_artifacts_tool` to read the content of files.

### Supported File Types:
1. **PDF Documents**: When a user references a PDF, use the `load_artifacts_tool` to read the text.
2. **CSV Data Files**: When a user references a CSV, use the `load_artifacts_tool` to read the data.
3. **Images (PNG, JPG, JPEG)**: You can process image files natively.
4. **ZIP Files**: If you upload a ZIP file, the system extracts its content. You will see a message listing the files. Use the `load_artifacts_tool` if you need to read them again.
5. **JSON Files**: You can process JSON files. The system extracts the content and provides it to you.
6. **Other Files**: If the user uploads any other file type, tell them that you cannot process it.

### Guardrails:
* **File-Centric Focus**: Answer questions based on the data in the uploaded files.
* **Enforce File Uploads**: If the user asks a question but has not uploaded any file, tell them to upload one first.
* **No General Knowledge Queries**: Refuse to answer general questions unrelated to an uploaded file.
* **Always Use Tools**: Do not assume you know the content of a file without reading it.

Keep interactions helpful within these boundaries.
"""

async def intercept_zip_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
    """Callback executed before the model runs to intercept and extract ZIP files.
    
    RATIONALE:
    Gemini API will not support ZIP files natively. Handled by intercepting
    in this callback, extracting files in memory, and injecting content directly
    into message parts as text or bytes.
    """
    logger.debug("Entering before_model_callback")
    if llm_request.contents:
        for i, content in enumerate(llm_request.contents):
            if content.role == "user":
                new_parts = []
                content_modified = False
                for part in content.parts:
                    # Extract file_data and inline_data, handling both objects and dictionaries (UI may send dicts)
                    file_data = getattr(part, 'file_data', None)
                    inline_data = getattr(part, 'inline_data', None)
                        
                    is_zip = False
                    zip_bytes = None
                    mime_type = None
                    
                    if file_data:
                        mime_type = getattr(file_data, 'mime_type', None)
                        if not mime_type and isinstance(file_data, dict):
                            mime_type = file_data.get('mime_type')
                    elif inline_data:
                        mime_type = getattr(inline_data, 'mime_type', None)
                        if not mime_type and isinstance(inline_data, dict):
                            mime_type = inline_data.get('mime_type')
                            
                    # Case 1: Intercept ZIP files
                    if mime_type == "application/zip":
                        logger.info("Found ZIP file in request! Intercepting.")
                        is_zip = True
                        if file_data:
                            filename = getattr(file_data, 'display_name', None) or os.path.basename(getattr(file_data, 'file_uri', ''))
                            if not filename and isinstance(file_data, dict):
                                filename = file_data.get('display_name') or os.path.basename(file_data.get('file_uri', ''))
                            logger.info(f"Attempting to load artifact: {filename}")
                            artifact_part = await callback_context.load_artifact(filename)
                            zip_bytes = artifact_part.inline_data.data
                        else:
                            zip_bytes = getattr(inline_data, 'data', None)
                            if not zip_bytes and isinstance(inline_data, dict):
                                zip_bytes = inline_data.get('data')
                                
                    # Case 2: Intercept JSON files and inject content as text
                    elif mime_type == "application/json":
                        logger.info("Found JSON file in request! Intercepting.")
                        content_modified = True
                        if file_data:
                            filename = getattr(file_data, 'display_name', None) or os.path.basename(getattr(file_data, 'file_uri', ''))
                            if not filename and isinstance(file_data, dict):
                                filename = file_data.get('display_name') or os.path.basename(file_data.get('file_uri', ''))
                            logger.info(f"Attempting to load artifact: {filename}")
                            artifact_part = await callback_context.load_artifact(filename)
                            json_bytes = artifact_part.inline_data.data
                            new_parts.append(types.Part.from_text(text=f"[System: Content of {filename}:]\n{json_bytes.decode('utf-8')}"))
                        else:
                            json_bytes = getattr(inline_data, 'data', None)
                            if not json_bytes and isinstance(inline_data, dict):
                                json_bytes = inline_data.get('data')
                            new_parts.append(types.Part.from_text(text=f"[System: Content of JSON file:]\n{json_bytes.decode('utf-8')}"))
                        continue
                        
                    # Process the intercepted ZIP file
                    if is_zip:
                        content_modified = True
                        callback_context.state["zip_intercepted"] = True
                        
                        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                            file_names = z.namelist()
                            for file_name in file_names:
                                # Skip directories
                                if file_name.endswith('/'):
                                    continue
                                    
                                # Skip macOS metadata files
                                if os.path.basename(file_name).startswith('._') or '__MACOSX' in file_name:
                                    logger.info(f"Skipping macOS metadata file: {file_name}")
                                    continue
                                    
                                logger.info(f"Extracting {file_name} from ZIP.")
                                with z.open(file_name) as f:
                                    file_content = f.read()
                                    
                                # Guess mime type
                                mime_type, _ = mimetypes.guess_type(file_name)
                                if not mime_type:
                                    mime_type = "application/octet-stream"
                                    
                                logger.info(f"Extracted {file_name}, size: {len(file_content)} bytes, mime_type: {mime_type}")
                                    
                                # If JSON or CSV, return as text
                                if mime_type in ["application/json", "text/csv"]:
                                    try:
                                        text_content = file_content.decode('utf-8')
                                        new_parts.append(types.Part.from_text(text=f"[System: Content of {file_name} (extracted):]\n{text_content}"))
                                    except UnicodeDecodeError:
                                        logger.warning(f"Failed to decode {file_name} as utf-8. Sending as bytes.")
                                        new_parts.append(types.Part.from_bytes(data=file_content, mime_type=mime_type))
                                else:
                                    # Send as bytes (inline_data)
                                    new_parts.append(types.Part.from_bytes(data=file_content, mime_type=mime_type))
                                    
                        new_parts.append(types.Part.from_text(text=f"[System: ZIP file extracted. Content of the files has been injected below. You do not need to call load_artifacts for these files: {', '.join(file_names)}]"))
                    else:
                        new_parts.append(part)
                
                if content_modified:
                    llm_request.contents[i] = types.Content(role="user", parts=new_parts)
                    logger.info("Handled special files in request.")
    return None

# Agent definition using callback to handle unsupported (ZIP and JSON) files.
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
    before_model_callback=intercept_zip_callback,
)

# Environment Setup
running_in_cloud = os.getenv("RUNNING_IN_CLOUD", "false").lower() == "true"
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
bucket_name = os.getenv("GCS_ARTIFACT_BUCKET")

if running_in_cloud:
    # In the cloud, use Vertex AI for sessions and GCS for artifacts.
    print(f"Using VertexAiSessionService (Project: {project_id})")
    session_service = VertexAiSessionService(project=project_id, location=location)
    artifact_service = GcsArtifactService(bucket_name=bucket_name)
else:
    # Locally, use in-memory sessions and local file storage for artifacts.
    print("Using FileArtifactService (Local)")
    session_service = InMemorySessionService()
    adk_dir = Path('.').resolve() / ".adk"
    artifacts_dir = adk_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_service = FileArtifactService(root_dir=artifacts_dir)

# Runner ties everything together.
runner = Runner(
    app_name="minimal_summarizer_agent",
    agent=orchestrator,
    session_service=session_service,
    artifact_service=artifact_service,
)

root_agent = runner.agent
