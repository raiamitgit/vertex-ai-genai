# Description: Main Flask web application to serve the AI Concierge.

import asyncio
import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

# Import the agent orchestrator
import agent_orchestrator

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Set a secret key for session management. In a production app, use a secure, randomly generated key.
app.secret_key = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development")

@app.route("/")
def index():
    """Renders the main chat page."""
    # Ensure a user_id is set in the session when the page is first loaded.
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """Handles chat messages from the user."""
    message = request.json.get("message")
    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    # Ensure user_id exists, creating one if it doesn't.
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    
    user_id = session["user_id"]
    print(f"Received message from user_id: {user_id}")

    try:
        # CORRECTED: Use asyncio.run() to properly execute the async function
        # from a synchronous context and wait for its result.
        response_data = asyncio.run(agent_orchestrator.invoke_agent(user_id, message))
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error invoking agent: {e}")
        return jsonify({"error": "Sorry, an internal error occurred."}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8000)

