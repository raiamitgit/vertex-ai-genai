import asyncio
import json
import os
from dotenv import load_dotenv

# ADK Imports
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types

# Import target agent
from agentspace.agent import root_agent

# Load env for Physna credentials
# Explicitly load the .env file from the repository root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Test Configuration ---
APP_NAME = "part_info_search"
USER_ID = "test_engineer"
KNOWN_VALID_ASSET_ID = os.getenv("EXAMPLE_BRACKET_ID")
# Correctly resolve the path to the image relative to this test file's location
base_dir = os.path.dirname(os.path.abspath(__file__))
SAMPLE_IMAGE_PATH = os.path.join(base_dir, '..', 'agentspace', 'sample_bracket.jpg')

from typing import List
from typing import Optional

async def run_test_scenario(
    session_id: str,
    parts: List[types.Part],
    description: str,
    artifact_to_save: Optional[types.Part] = None,
):
    """
    Helper to run a single test scenario using the ADK Runner.
    """
    print(f"\n{'='*60}\nSCENARIO: {description}\n{'='*60}")

    # 1. Setup services and runner
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        artifact_service=artifact_service,
        app_name=APP_NAME,
    )

    # 2. Create session
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )

    # 3. Manually save a pre-test artifact if provided
    if artifact_to_save:
        filename = os.path.basename(SAMPLE_IMAGE_PATH) # Use a consistent name
        await artifact_service.save_artifact(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
            filename=filename,
            artifact=artifact_to_save,
        )
        print(f"Pre-saved artifact '{filename}' for test setup.")

    # 4. Create the user's message content, which may or may not contain an image
    user_content = types.Content(role="user", parts=parts)
    final_response_text = "<No response generated>"

    print("...Running Agent...")
    
    # 3. Run Async Loop and Process Events
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=user_content
    ):
        # A. Capture Final text
        if event.is_final_response() and event.content:
            final_response_text = event.content.parts[0].text

        # B. Capture and print Tool executions (Crucial for testing physna_tool.py)
        function_responses = event.get_function_responses()
        if function_responses:
            for resp in function_responses:
                print(f"\n>>> TOOL CALLED: {resp.name}")
                
                # Pretty print the JSON response (truncating if very long)
                try:
                    resp_str = json.dumps(resp.response, indent=2)
                    if len(resp_str) > 1000:
                        print(f">>> TOOL OUTPUT (Truncated): \n{resp_str[:1000]}\n...[more data]...")
                    else:
                        print(f">>> TOOL OUTPUT: \n{resp_str}")
                except:
                    print(f">>> TOOL OUTPUT (Raw): {resp.response}")
                print("-" * 20)

    # 4. Print Final Agent Synthesis
    print(f"\nFINAL AGENT RESPONSE:\n{final_response_text}")
    print("="*60 + "\n")


async def main():
    print("--- Starting Physna Agent Integration Tests ---")

    # --- Test 1: Search by Asset ID ---
    if KNOWN_VALID_ASSET_ID:
        await run_test_scenario(
            session_id="sess_id_001",
            parts=[types.Part(text=f"Find parts that are geometrically similar to asset ID {KNOWN_VALID_ASSET_ID}.")],
            description="Valid Asset ID Search",
        )
    else:
        print("⚠️ Skipping ID Test: 'EXAMPLE_BRACKET_ID' not set in .env")

    # --- Test 2: Search by Image Upload (from Artifact) ---
    if os.path.exists(SAMPLE_IMAGE_PATH):
        with open(SAMPLE_IMAGE_PATH, "rb") as f:
            image_data = f.read()
        image_part = types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=image_data))
        
        await run_test_scenario(
            session_id="sess_artifact_upload_001",
            parts=[types.Part(text="Can you find parts that look like the uploaded image?")],
            description="Image Upload Search (from Artifact)",
            artifact_to_save=image_part, # Pre-save the artifact
        )
    else:
        print(f"⚠️ Skipping Image Upload (Artifact) Test: File '{SAMPLE_IMAGE_PATH}' not found.")

    # --- Test 3: Search by Image Upload (from Inline Blob) ---
    if os.path.exists(SAMPLE_IMAGE_PATH):
        with open(SAMPLE_IMAGE_PATH, "rb") as f:
            image_data = f.read()
        image_part = types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=image_data))

        await run_test_scenario(
            session_id="sess_inline_upload_001",
            parts=[
                types.Part(text="Analyze this image provided directly in the message."),
                image_part
            ],
            description="Image Upload Search (from Inline Blob)",
            # No artifact_to_save, image is passed directly in parts
        )
    else:
        print(f"⚠️ Skipping Image Upload (Inline Blob) Test: File '{SAMPLE_IMAGE_PATH}' not found.")

    # --- Test 4: Search by Image Path (should fail gracefully) ---
    if os.path.exists(SAMPLE_IMAGE_PATH):
        await run_test_scenario(
            session_id="sess_img_001",
            parts=[types.Part(text=f"I have a photo of a part at '{SAMPLE_IMAGE_PATH}'. Can you find similar designs in our database?")],
            description="Valid Image Path Search (should fail)",
        )
    else:
        print(f"⚠️ Skipping Image Path Test: File '{SAMPLE_IMAGE_PATH}' not found.")

    print("--- Tests Complete ---")

if __name__ == "__main__":
    asyncio.run(main())