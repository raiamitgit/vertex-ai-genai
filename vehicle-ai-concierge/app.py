import asyncio
import os
import uuid
import json
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import logging # Import the logging module

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import the main agent from our agent package
from agent.agent import root_agent

# --- Basic Configuration for Logging ---
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development")

# --- ADK Runner and Session Management ---
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="buick_ai_concierge",
    session_service=session_service,
)

_created_sessions = set()

async def get_or_create_session(user_id: str) -> str:
    """Gets or creates a session for a given user."""
    session_id = f"session_for_{user_id}"
    if session_id not in _created_sessions:
        logging.info(f"Creating new session {session_id} for user {user_id}")
        await session_service.create_session(
            app_name="buick_ai_concierge", user_id=user_id, session_id=session_id
        )
        _created_sessions.add(session_id)
    return session_id

async def invoke_agent_and_process_response(user_id: str, message: str) -> dict:
    """
    Invokes the agent and processes the final response for the frontend.
    """
    session_id = await get_or_create_session(user_id)
    user_content = types.Content(role="user", parts=[types.Part(text=message)])

    final_agent_output = ""
    # Stream events from the agent to get the final raw output
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=user_content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_agent_output = event.content.parts[0].text

    # --- DEBUGGING: Log the raw output ---
    logging.info("--- Raw Agent Output ---")
    logging.info(final_agent_output)
    logging.info("------------------------")
    
    # Attempt to parse the raw output into the expected JSON format
    try:
        # Clean up potential markdown formatting from the LLM
        if "```json" in final_agent_output:
            json_str = final_agent_output.split("```json")[1].split("```")[0]
        else:
            json_str = final_agent_output

        # The model sometimes returns an incomplete JSON string; this finds the last valid bracket
        last_bracket_index = json_str.rfind('}')
        if last_bracket_index != -1:
            clean_json_str = json_str[:last_bracket_index + 1]
            response_data = json.loads(clean_json_str)
            
            # Ensure the response has the keys the frontend expects, even if empty
            if 'text' not in response_data:
                response_data['text'] = "Here is the information I found."
            if 'rich_content' not in response_data:
                response_data['rich_content'] = []

            return response_data
        else:
            # If no JSON is found, return the text directly
            return {"text": final_agent_output, "rich_content": []}

    except (json.JSONDecodeError, IndexError) as e:
        logging.error(f"Failed to parse agent's JSON response: {e}")
        # If parsing fails, return the raw text to avoid crashing the UI
        return {"text": final_agent_output, "rich_content": []}


@app.route("/")
def index():
    """Renders the main chat page."""
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """Handles chat messages from the user."""
    message = request.json.get("message")
    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    
    user_id = session["user_id"]

    try:
        response_data = asyncio.run(invoke_agent_and_process_response(user_id, message))
        return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Error in /chat endpoint: {e}")
        return jsonify({"error": "Sorry, an internal error occurred."}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8080)
