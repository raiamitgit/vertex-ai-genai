"""FastAPI server hosting the A2A User Profile Agent."""

import json
import os
import logging
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from google.adk import Runner
from google.adk.sessions import InMemorySessionService

# Import our unified agent and the executor
from agent import root_agent
from agent_executor import SolvedAgentExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_server")

app = FastAPI()

# Instantiate the session service globally
session_service = InMemorySessionService()

# Initialize the Runner and the Executor
runner = Runner(
    agent=root_agent,
    app_name="profile_agent",
    session_service=session_service
)
executor = SolvedAgentExecutor(runner)

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """A2A Discovery Endpoint. Exposes the Agent Card."""
    try:
        with open("agent_card.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent card not found.")

@app.post("/")
async def handle_a2a_request(request: Request):
    """Main A2A Endpoint. Handles SendMessage requests."""
    body = await request.json()

    # Log incoming A2A request for diagnostic monitoring
    logger.info("--- INCOMING A2A REQUEST ---")
    logger.info(json.dumps(body))
    logger.info("-----------------------------")

    # Validate JSON-RPC 2.0 structure
    if body.get("jsonrpc") != "2.0":
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": body.get("id")}
        )

    method = body.get("method")
    request_id = body.get("id")

    if method != "message/send":
        logger.warning(f"Received unsupported method: {method}")
        return JSONResponse(
            status_code=404,
            content={"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method '{method}' not supported"}, "id": request_id}
        )

    user_query = ""
    try:
        params = body.get("params", {})
        message = params.get("message", {})
        parts = message.get("parts", [])

        if parts and "text" in parts[0]:
            user_query = parts[0].get("text").lstrip("> ").strip()
            logger.info(f"Parsed User Prompt: '{user_query}'")

    except Exception as e:
         logger.error(f"Failed to parse parameters: {e}")
         return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32602, "message": f"Invalid params: {e}"}, "id": request_id}
        )

    if not user_query:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32602, "message": "Prompt is required."}, "id": request_id}
        )

    try:
        # Execute agent through parsing executor
        a2a_parts = await executor.execute(user_query)

        message_id = f"msg-{uuid.uuid4()}"
        context_id = f"context-{uuid.uuid4()}"

        # Package response into A2A compliant flat Message object
        flat_message = {
            "kind": "message",
            "message_id": message_id,
            "messageId": message_id,
            "context_id": context_id,
            "contextId": context_id,
            "role": "agent",
            "parts": a2a_parts
        }

        return {
            "jsonrpc": "2.0",
            "result": flat_message,
            "id": request_id
        }

    except Exception as e:
        logger.error(f"Error in execution path: {e}")
        return JSONResponse(
            status_code=500,
            content={"jsonrpc": "2.0", "error": {"code": -32000, "message": f"Execution failed: {e}"}, "id": request_id}
        )
