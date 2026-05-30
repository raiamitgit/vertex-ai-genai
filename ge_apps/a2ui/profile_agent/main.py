# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Production A2A FastAPI server with strictly-compliant userAction postbacks."""

import json
import os
import logging
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import our unified agent and the solved executor
from agent import root_agent
from agent_executor import SolvedAgentExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_server")

app = FastAPI()

# Read the RUN_MODE from environment
RUN_MODE = os.environ.get("RUN_MODE", "solved").lower()
logger.info(f"Starting A2A server in RUN_MODE: {RUN_MODE}")

# Instantiate the session service globally
session_service = InMemorySessionService()

# 1. Initialize the Repro Runner
repro_runner = Runner(
    agent=root_agent,
    app_name="profile_agent_repro",
    session_service=session_service
)

# 2. Initialize the Solved Runner
solved_runner = Runner(
    agent=root_agent,
    app_name="profile_agent_solved",
    session_service=session_service
)

# 3. Initialize the Solved Executor
solved_executor = SolvedAgentExecutor(solved_runner)

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
    """Main A2A Endpoint. Handles SendMessage requests with strictly-compliant userAction postbacks."""
    body = await request.json()
    
    # Log the incoming request
    logger.info(f"--- INCOMING A2A REQUEST ---")
    logger.info(json.dumps(body))
    logger.info(f"-----------------------------")
    
    # Validate JSON-RPC 2.0 basic structure
    if body.get("jsonrpc") != "2.0":
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": body.get("id")}
        )
        
    method = body.get("method")
    request_id = body.get("id")
    
    # Align method check to 'message/send'
    if method != "message/send":
        logger.warning(f"Received unsupported method: {method}")
        return JSONResponse(
            status_code=404,
            content={"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method '{method}' not supported"}, "id": request_id}
        )
        
    # Parse the incoming user message & check for A2UI userAction notification events
    is_user_action = False
    user_query = ""
    
    try:
        params = body.get("params", {})
        message = params.get("message", {})
        parts = message.get("parts", [])
        
        # Scan all incoming parts for A2UI click notification event
        for part in parts:
            if part.get("kind") == "data" and "userAction" in part.get("data", {}):
                is_user_action = True
                break
                
        if parts and "text" in parts[0]:
            user_query = parts[0].get("text").lstrip("> ").strip()
            logger.info(f"Parsed User Prompt: '{user_query}'")
            
    except Exception as e:
         logger.error(f"Failed to parse parameters: {e}")
         return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32602, "message": f"Invalid params: {e}"}, "id": request_id}
        )

    # FIX: Handle 'userAction' postbacks gracefully using strictly-compliant flat A2A Task objects
    if is_user_action:
        logger.info("Detected userAction notification event (Button click). Acknowledging compliantly...")
        u_task_id = f"task-{uuid.uuid4()}"
        u_context_id = f"context-{uuid.uuid4()}"
        
        # Construct strictly valid flat Task payload matching a2a.compat.v0_3.types
        task_obj = {
            "id": u_task_id,
            "context_id": u_context_id,
            "contextId": u_context_id,
            "status": {
                "state": "completed"
            }
        }
        
        # Return flat Task object directly inside result
        a2a_response = {
            "jsonrpc": "2.0",
            "result": task_obj,
            "id": request_id
        }
        return a2a_response

    # Validate prompt existence for non-postback requests
    if not user_query:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32602, "message": "Prompt is required."}, "id": request_id}
        )

    # ==========================================================================
    # PATH A: SOLVED MODE (Delimiter-Splitting -> Flat Message Response)
    # ==========================================================================
    if RUN_MODE == "solved":
        try:
            logger.info("Executing Solved Path (Splitting Delimiter)...")
            a2a_parts = await solved_executor.execute(user_query)
            
            u_message_id = f"msg-{uuid.uuid4()}"
            u_context_id = f"context-{uuid.uuid4()}"
            
            # Construct flat Message response
            flat_message = {
                "kind": "message",
                "message_id": u_message_id,
                "messageId": u_message_id,
                "context_id": u_context_id,
                "contextId": u_context_id,
                "role": "agent",
                "parts": a2a_parts
            }
            
            a2a_response = {
                "jsonrpc": "2.0",
                "result": flat_message,
                "id": request_id
            }
            return a2a_response
            
        except Exception as e:
            logger.error(f"Error in solved path execution: {e}")
            return JSONResponse(
                status_code=500,
                content={"jsonrpc": "2.0", "error": {"code": -32000, "message": f"Solved execution failed: {e}"}, "id": request_id}
            )

    # ==========================================================================
    # PATH B: REPRO MODE (Naive Delimiter -> Flat Message Repro)
    # ==========================================================================
    else:
        logger.info("Executing Repro Path (Naive Delimiter)...")
        session_id = "repro-session-123"
        user_id = "repro-user"
        
        try:
            await session_service.create_session(
                app_name="profile_agent_repro",
                user_id=user_id,
                session_id=session_id
            )
        except Exception:
            pass
        
        agent_raw_response = ""
        new_message = types.Content(role='user', parts=[types.Part(text=user_query)])
        
        try:
            async for event in repro_runner.run_async(user_id=user_id, session_id=session_id, new_message=new_message):
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            agent_raw_response = part.text
                            break
        except Exception as e:
            logger.error(f"Error in repro path execution: {e}")
            return JSONResponse(
                status_code=500,
                content={"jsonrpc": "2.0", "error": {"code": -32000, "message": f"Repro execution failed: {e}"}, "id": request_id}
            )

        u_message_id = f"msg-{uuid.uuid4()}"
        u_context_id = f"context-{uuid.uuid4()}"
        
        flat_message = {
            "kind": "message",
            "message_id": u_message_id,
            "messageId": u_message_id,
            "context_id": u_context_id,
            "contextId": u_context_id,
            "role": "agent",
            "parts": [
                {
                    "text": agent_raw_response
                }
            ]
        }

        a2a_response = {
            "jsonrpc": "2.0",
            "result": flat_message,
            "id": request_id
        }
        return a2a_response
