import asyncio
import os
import sys
from pathlib import Path

# Add the project root to path so we can import agent_3
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
# Load environment variables from agent_3/.env
env_path = Path('agent_3').resolve() / '.env'
load_dotenv(dotenv_path=env_path)

# Override for local testing
os.environ["RUNNING_IN_CLOUD"] = "false"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

from agent_3.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.file_artifact_service import FileArtifactService
from google.genai import types

async def main():
    # Setup paths and services
    current_dir = Path('.').resolve()
    adk_dir = current_dir / "agent_3" / ".adk"
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
    
    # Simulate uploading a JSON file
    json_content = '{"name": "Alice", "age": 30, "city": "New York"}'
    part = types.Part(inline_data=types.Blob(
        mime_type="application/json",
        data=json_content.encode('utf-8')
    ))
    
    await artifact_service.save_artifact(
        app_name="test_app",
        user_id="test_user",
        session_id="test_session",
        filename="data.json",
        artifact=part
    )
    print("Saved test artifact data.json")
    
    # Test Case 1: Video Generation
    print("\n--- Test Case 1: Video Generation ---")
    try:
        async for event in runner.run_async(
            user_id="test_user", session_id="test_session",
            new_message=types.Content(role="user", parts=[
                types.Part.from_text(text="I uploaded data.json. Generate a video of a cat playing with a ball.")
            ]),
        ):
            if event.is_final_response():
                print("Agent Response:")
                if event.content and event.content.parts:
                    print(event.content.parts[0].text)
                else:
                    print("No text response")
    except Exception as e:
        print(f"Video test failed: {e}")

    # Test Case 2: Image Generation
    print("\n--- Test Case 2: Image Generation ---")
    try:
        async for event in runner.run_async(
            user_id="test_user", session_id="test_session",
            new_message=types.Content(role="user", parts=[
                types.Part.from_text(text="Generate an infographic showing the population growth of cities.")
            ]),
        ):
            if event.is_final_response():
                print("Agent Response:")
                if event.content and event.content.parts:
                    print(event.content.parts[0].text)
                else:
                    print("No text response")
    except Exception as e:
        print(f"Image test failed: {e}")

    # Test Case 3: Document Generation
    print("\n--- Test Case 3: Document Generation ---")
    try:
        async for event in runner.run_async(
            user_id="test_user", session_id="test_session",
            new_message=types.Content(role="user", parts=[
                types.Part.from_text(text="Summarize the data in data.json and put it in a report.")
            ]),
        ):
            if event.is_final_response():
                print("Agent Response:")
                if event.content and event.content.parts:
                    print(event.content.parts[0].text)
                else:
                    print("No text response")
    except Exception as e:
        print(f"Doc test failed: {e}")

if __name__ == '__main__':
    asyncio.run(main())
