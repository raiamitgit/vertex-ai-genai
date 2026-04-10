import asyncio
import os
import sys
from pathlib import Path

# Add the project root to path so we can import agent_4
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set environment variables for Vertex AI and ADC
os.environ["RUNNING_IN_CLOUD"] = "false"
os.environ["GCS_ARTIFACT_BUCKET"] = "dummy-bucket"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = "data-n-models"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

from agent_4.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.file_artifact_service import FileArtifactService
from google.genai import types

async def main():
    # Setup paths and services
    current_dir = Path('.').resolve()
    adk_dir = current_dir / "agent_4" / ".adk"
    artifacts_dir = adk_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    session_service = InMemorySessionService()
    await session_service.create_session(app_name="test_app", user_id="test_user", session_id="test_session")
    
    artifact_service = FileArtifactService(root_dir=artifacts_dir)
    
    runner = Runner(
        agent=root_agent, 
        app_name="test_app", 
        session_service=session_service,
        artifact_service=artifact_service
    )
    
    # Simulate uploading a CSV file
    csv_content = "name,age\nAlice,30\nBob,25"
    part = types.Part(inline_data=types.Blob(
        mime_type="text/csv",
        data=csv_content.encode('utf-8')
    ))
    
    await artifact_service.save_artifact(
        app_name="test_app",
        user_id="test_user",
        session_id="test_session",
        filename="data.csv",
        artifact=part
    )
    print("Saved test artifact data.csv")
    
    print("Running agent with CSV file using Gemini 3...")
    try:
        async for event in runner.run_async(
            user_id="test_user", session_id="test_session",
            new_message=types.Content(role="user", parts=[
                types.Part.from_text(text="I uploaded data.csv. What is the average age?")
            ]),
        ):
            if event.is_final_response():
                print("Agent Response:")
                if event.content and event.content.parts:
                    print(event.content.parts[0].text)
                else:
                    print("No text response")
    except Exception as e:
        print(f"Error running agent: {e}")

if __name__ == '__main__':
    asyncio.run(main())
