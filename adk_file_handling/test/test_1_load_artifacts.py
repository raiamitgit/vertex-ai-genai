import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import importlib

# Add parent directory to path to find google.adk
sys.path.insert(0, os.path.abspath('.'))

# Load environment variables from the folder's .env file
env_path = Path('agent_1').resolve() / '.env'
print(f"Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path)

# Ensure we use Vertex AI in the ADK models
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

# Import module
import agent_1.agent as agent_module
orchestrator = agent_module.orchestrator

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.file_artifact_service import FileArtifactService
from google.genai import types

async def test_programmatic():
    print("Testing agent programmatically...")
    
    # 1. Setup paths and services
    current_dir = Path('.').resolve()
    adk_dir = current_dir / "agent_1" / ".adk"
    artifacts_dir = adk_dir / "artifacts"
    
    # Clean up previous artifacts to ensure fresh start
    import shutil
    if adk_dir.exists():
        shutil.rmtree(adk_dir)
        
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize services
    session_service = InMemorySessionService()
    artifact_service = FileArtifactService(root_dir=artifacts_dir)
    
    runner = Runner(
        app_name="minimal_summarizer_agent",
        agent=orchestrator,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    )
    
    user_id = "test_user"
    session_id = "test_session_1"
    
    # Create session first
    await session_service.create_session(app_name="minimal_summarizer_agent", user_id=user_id, session_id=session_id)
    
    # Mock upload of sales_data.csv
    print("\n--- Mocking CSV Upload ---")
    csv_content = "Region,Sales\nNorth,100\nSouth,200\nWest,150\nEast,300"
    
    await artifact_service.save_artifact(
        app_name="minimal_summarizer_agent",
        user_id=user_id,
        filename="sales_data.csv",
        artifact=types.Part.from_text(text=csv_content),
        session_id=session_id
    )
    print(f"Saved sales_data.csv to artifact service.")
    
    # 2. Test CSV Flow
    print("\n--- Testing CSV Flow ---")
    try:
        prompt = (
            "I have uploaded 'sales_data.csv'. Here is the content:\n"
            f"{csv_content}\n"
            "Can you calculate the total revenue by region?"
        )
        
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
        
        print("Sending query to Orchestrator...")
        
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
             content_str = event.content if hasattr(event, 'content') and event.content else ""
             actions_str = event.actions if hasattr(event, 'actions') and event.actions else ""
             print(f"Event from {event.author}: {content_str} {actions_str}")
             
    except Exception as e:
        print(f"CSV test failed: {e}")
        import traceback
        traceback.print_exc()

    # 3. Test PDF Flow
    print("\n--- Testing PDF Flow ---")
    try:
        session_id = "test_session_3"
        await session_service.create_session(app_name="minimal_summarizer_agent", user_id=user_id, session_id=session_id)
        
        # Read real PDF file
        pdf_path = Path('data/vertex search.pdf').resolve()
        print(f"Reading PDF from: {pdf_path}")
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()
            
        await artifact_service.save_artifact(
            app_name="minimal_summarizer_agent",
            user_id=user_id,
            filename="test_doc.pdf",
            artifact=types.Part.from_bytes(data=pdf_content, mime_type="application/pdf"),
            session_id=session_id
        )
        print(f"Saved test_doc.pdf to artifact service.")
        
        prompt = "I have uploaded 'test_doc.pdf'. Can you summarize it?"
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
        
        print("Sending query to Orchestrator...")
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
             content_str = event.content if hasattr(event, 'content') and event.content else ""
             actions_str = event.actions if hasattr(event, 'actions') and event.actions else ""
             print(f"Event from {event.author}: {content_str} {actions_str}")
             
    except Exception as e:
        print(f"PDF test failed: {e}")
        import traceback
        traceback.print_exc()

    # 4. Test Guardrails (Negative Cases)
    print("\n--- Testing Guardrail: No File Uploaded ---")
    try:
        session_id = "test_session_guardrail_1"
        await session_service.create_session(app_name="minimal_summarizer_agent", user_id=user_id, session_id=session_id)
        
        prompt = "Can you help me summarize my document?"
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
        
        print("Sending query without file...")
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
             content_str = event.content if hasattr(event, 'content') and event.content else ""
             print(f"Event from {event.author}: {content_str}")
             
    except Exception as e:
        print(f"Guardrail 1 test failed: {e}")

    print("\n--- Testing Guardrail: General Question ---")
    try:
        session_id = "test_session_guardrail_2"
        await session_service.create_session(app_name="minimal_summarizer_agent", user_id=user_id, session_id=session_id)
        
        prompt = "Who was the first president of the United States?"
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
        
        print("Sending general question...")
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
             content_str = event.content if hasattr(event, 'content') and event.content else ""
             print(f"Event from {event.author}: {content_str}")
             
    except Exception as e:
        print(f"Guardrail 2 test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_programmatic())

