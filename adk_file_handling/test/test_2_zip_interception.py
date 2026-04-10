import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import importlib
import io
import zipfile

# Add parent directory to path to find google.adk
sys.path.insert(0, os.path.abspath('.'))

# Load environment variables from the folder's .env file
env_path = Path('agent_2').resolve() / '.env'
load_dotenv(dotenv_path=env_path)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

# Import module
import agent_2.agent as agent_module
orchestrator = agent_module.orchestrator

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.file_artifact_service import FileArtifactService
from google.adk.artifacts import GcsArtifactService
from google.genai import types

async def test_zip_file_data():
    print("Testing ZIP interception (file_data)...")
    
    # Setup paths and services
    current_dir = Path('.').resolve()
    adk_dir = current_dir / "agent_2" / ".adk"
    artifacts_dir = adk_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    session_service = InMemorySessionService()
    artifact_service = GcsArtifactService(bucket_name=os.getenv("GCS_ARTIFACT_BUCKET"))
    
    runner = Runner(
        app_name="minimal_summarizer_agent",
        agent=orchestrator,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    )
    
    user_id = "test_user"
    session_id = "test_session_zip_file_data"
    
    await session_service.create_session(app_name="minimal_summarizer_agent", user_id=user_id, session_id=session_id)
    
    # Create a ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as z:
        z.writestr("extracted_file_data.txt", "This content was extracted from file_data ZIP!")
    zip_bytes = zip_buffer.getvalue()
    
    # Save it as an artifact
    await artifact_service.save_artifact(
        app_name="minimal_summarizer_agent",
        user_id=user_id,
        session_id=session_id,
        filename="fake.zip",
        artifact=types.Part.from_bytes(data=zip_bytes, mime_type="application/zip")
    )
    print("Saved fake.zip as artifact.")

    # Simulate uploading a ZIP file as file_data (like the UI likely does)
    zip_part = types.Part(
        file_data=types.FileData(
            mime_type="application/zip",
            file_uri="https://example.com/fake.zip"
        )
    )
    
    text_part = types.Part.from_text(text="I uploaded a zip file. Can you process it?")
    
    message = types.Content(
        role="user",
        parts=[zip_part, text_part]
    )
    
    print("Sending query with ZIP file (file_data) to Orchestrator...")
    
    try:
        final_response = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
             content_str = event.content if hasattr(event, 'content') and event.content else ""
             print(f"Event from {event.author}: {content_str}")
             if event.author == "minimal_summarizer":
                 if isinstance(content_str, str):
                     final_response += content_str
                 elif hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                     for part in event.content.parts:
                         if hasattr(part, 'text') and part.text:
                             final_response += part.text
                 
        print(f"Final response: {final_response}")
        if "This content was extracted from file_data ZIP!" in final_response or "extracted_file_data.txt" in final_response:
            print("SUCCESS: Model processed the extracted content!")
        else:
            print("FAILURE: Model response does not indicate processing of extracted content.")
             
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    async def main():
        await test_zip_file_data()
        
    asyncio.run(main())
