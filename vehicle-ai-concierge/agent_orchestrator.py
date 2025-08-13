# Description: The central agent orchestrator using the Agent Development Kit (ADK).

import asyncio
import json
import os
import uuid
from typing import Dict, Any, AsyncGenerator
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.tools.agent_tool import AgentTool

# Load environment variables
load_dotenv()

# --- ADK Environment Configuration ---
os.environ["GOOGLE_CLOUD_PROJECT"] = os.getenv("VERTEX_AI_PROJECT_ID")
os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("VERTEX_AI_LOCATION")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")

# --- Tool Imports ---
from tools import (
    parts_search_tool,
    dealership_search_tool,
    image_editor_tool,
    lead_generation_tool,
    website_search_tool,
)

# --- 1. Define Specialist Agents (to be used as tools) ---
website_search_agent = Agent(
    name="WebsiteSearchAgent",
    model=MODEL_NAME,
    description="Use for general questions, vehicle info, support, or anything on the Buick website.",
    instruction="You are a helpful search assistant. Use the 'search' tool to find information for the user and return the complete, unmodified output from the tool.",
    tools=[website_search_tool.search],
)

parts_search_agent = Agent(
    name="PartsSearchAgent",
    model=MODEL_NAME,
    description="Use to search for vehicle parts and accessories.",
    instruction="""
        You are a data formatting agent. Your primary function is to process the output from the `search_parts` tool and format it into a specific JSON structure.
        If you lack the necessary details to run the `search_parts` tool (e.g., vehicle year or model), your response must be a simple, direct question to the user asking for the missing information.
        If the tool runs successfully, you MUST format your final response as a single, valid JSON string with 'text' and 'rich_content' keys.
        - 'text': A one to two sentence summary that highlights the top result.
        - 'rich_content': The original, unmodified list of part dictionaries.
    """,
    tools=[parts_search_tool.search_parts],
)

dealership_search_agent = Agent(
    name="DealershipSearchAgent",
    model=MODEL_NAME,
    description="Use to find nearby Buick dealerships by zip code.",
    instruction="You are a dealership locator. Format the 'find_dealerships' tool output as a single JSON string with 'text' (a friendly summary) and 'rich_content' (the raw tool data) keys.",
    tools=[dealership_search_tool.find_dealerships],
)

image_editor_agent = Agent(
    name="ImageEditorAgent",
    model=MODEL_NAME,
    description="Use to edit vehicle images, such as changing the color.",
    instruction="You are a vehicle personalization assistant. Use the edit_image tool and return its direct, unmodified output.",
    tools=[image_editor_tool.edit_image],
)

lead_generation_agent = Agent(
    name="LeadGenerationAgent",
    model=MODEL_NAME,
    description="Use to collect user info for a price quote.",
    instruction="You are a lead generation specialist. Use your tools to collect user contact information to create a quote request.",
    tools=[
        lead_generation_tool.check_and_request_info,
        lead_generation_tool.extract_and_confirm_lead,
    ],
)

# --- 2. Define the Root Agent (The Orchestrator) ---
root_agent = Agent(
    name="BuickConciergeOrchestrator",
    model=MODEL_NAME,
    description="The main conversational agent for Buick.",
    instruction="""
        You are the Buick AI Concierge, a warm and friendly assistant.
        1. On the user's first message, your response MUST start with a warm greeting.
        2. If the query starts with "Edit this image:", call the `ImageEditorAgent`.
        3. For all other queries, use your specialist agent tools.
        4. Pass specialist agent responses directly to the user without modification.
        5. If the query is unrelated to Buick, respond with: "I'm sorry, but my expertise is focused on Buick vehicles. How can I help with that?"
    """,
    tools=[
        AgentTool(agent=website_search_agent),
        AgentTool(agent=parts_search_agent),
        AgentTool(agent=dealership_search_agent),
        AgentTool(agent=image_editor_agent),
        AgentTool(agent=lead_generation_agent),
    ],
)

# --- 3. ADK Runner and Invocation Logic ---
session_service = InMemorySessionService()
app_name = "buick_ai_concierge"

runner = Runner(
    agent=root_agent,
    app_name=app_name,
    session_service=session_service,
)

async def get_or_create_session(user_id: str) -> str:
    """Gets a session ID for a user, creating one if it doesn't exist."""
    session_id = f"session_for_{user_id}"
    existing_session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if not existing_session:
        print(f"Creating new session {session_id} for user {user_id}")
        await session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
    return session_id


async def invoke_agent(user_id: str, message: str) -> Dict[str, Any]:
    """
    Asynchronously invokes the agent for a given user, handling session management.
    """
    session_id = await get_or_create_session(user_id)
    user_content = types.Content(role="user", parts=[types.Part(text=message)])

    final_response = {"text": "Sorry, I encountered an issue.", "rich_content": []}
    rich_content_processed = False

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=user_content
    ):
        if not rich_content_processed and event.is_final_response() and event.content and event.content.parts:
            final_response["text"] = event.content.parts[0].text

        function_responses = event.get_function_responses()
        if function_responses:
            for resp in function_responses:
                tool_result = resp.response.get("result", {})
                data = None

                # Step 1: Check if the result is already a dictionary (ideal case)
                if isinstance(tool_result, dict):
                    data = tool_result
                # Step 2: If it's a string, try to parse it as JSON
                elif isinstance(tool_result, str):
                    try:
                        # Clean up potential markdown code blocks
                        if "```json" in tool_result:
                            tool_result = tool_result.split("```json")[1].split("```")[0]
                        data = json.loads(tool_result)
                    except (json.JSONDecodeError, AttributeError):
                        # If parsing fails, treat it as a plain text response
                        final_response["text"] = tool_result
                        rich_content_processed = True
                        continue

                # Step 3: If we have a valid dictionary, process it
                if data:
                    if 'summary' in data:  # From WebsiteSearchAgent
                        final_response["text"] = data.get("summary", "Here's what I found.")
                        final_response["rich_content"] = data.get("results", [])
                    elif 'image_url' in data: # From ImageEditorAgent
                        final_response["text"] = "Here is the edited image you requested."
                        final_response["rich_content"] = [data]
                    else:  # From Parts, Dealership, or Lead Gen Agent
                        final_response["text"] = data.get("text", final_response["text"])
                        final_response["rich_content"] = data.get("rich_content", [])
                    
                    rich_content_processed = True
                else:
                    # Fallback for unexpected data types
                     final_response["text"] = str(tool_result)
                     rich_content_processed = True


    return final_response


# --- 4. Main function for standalone testing ---
async def main():
    print("--- Testing Agent Orchestrator ---")
    test_user_id = "test_user_001"
    test_queries = [ "show me some suvs", "find a dealership in 02090" ]

    for query in test_queries:
        print("\n" + "="*50)
        print(f"USER QUERY: {query} (User: {test_user_id})")
        print("="*50)
        
        response = await invoke_agent(test_user_id, query)

        print("\n--- AGENT RESPONSE ---")
        print(f"Text: {response.get('text')}")
        if response.get("rich_content"):
            print("Rich Content:")
            print(json.dumps(response.get("rich_content"), indent=2))
        print("----------------------")

if __name__ == "__main__":
    asyncio.run(main())



