import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to find vertexai if needed
sys.path.insert(0, os.path.abspath('.'))

import vertexai
from google.genai import types as genai_types

# Load environment variables from agent_1/.env
env_path = Path('agent_1').resolve() / '.env'
load_dotenv(dotenv_path=env_path)

async def test_minimal():
    engine_id = "projects/455386119460/locations/us-central1/reasoningEngines/2790552264958279680"
    
    print(f"Testing minimal agent with ID: {engine_id}")
    
    client = vertexai.Client(location="us-central1")
    agent = client.agent_engines.get(name=engine_id)

    data_folder = os.getenv("DATA_FOLDER_PATH", "data")
    pdf_path = (Path(data_folder) / "market_conditions.pdf").resolve()
    print(f"Reading PDF from: {pdf_path}")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()



    try:
        # Attempt to send Content object with file parts
        content = genai_types.Content(
            role="user",
            parts=[
                genai_types.Part.from_text(text="Please summarize this document."),
                genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
            ]
        )
        
        print("Sending query with PDF...")
        async for event in agent.async_stream_query(message=content, user_id="test_user"):
            print(event)
            
    except Exception as e:
        print(f"Failed to query: {e}")

if __name__ == "__main__":
    asyncio.run(test_minimal())
