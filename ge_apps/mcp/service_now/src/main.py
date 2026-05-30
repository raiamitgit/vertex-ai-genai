"""ServiceNow MCP Web Server Entrypoint.

This module acts as the host process for the ServiceNow BYO-MCP server.
It initializes a FastAPI web application, includes the Mock OAuth router,
and exposes the JSON-RPC 2.0 endpoint under `/mcp` and mock OAuth flow.

This host allows running both the tools and the auth handshake on a single port in Google Cloud Run.
"""

import os
import logging
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

# Ensure src is in path for nested imports during server startup
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from oauth import router as oauth_router
from mcp_server import mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main_entrypoint")

# 1. Initialize the FastAPI Web Application
app = FastAPI(
    title="ServiceNow BYO-MCP Integration Server",
    description="Unified web host for ServiceNow MCP tools and Mock OAuth endpoints.",
    version="1.0.0"
)

# 2. Register the Mock OAuth 2.0 Provider Router
# This registers the GET /oauth/authorize and POST /oauth/token routes
app.include_router(oauth_router)


@app.get("/", response_class=HTMLResponse)
async def root_index(request: Request):
    """Serves a landing page / health check endpoint.

    Helps administrators verify that the Cloud Run service is active and
    provides references for the connection parameters.
    """
    base_url = str(request.base_url).rstrip("/")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ServiceNow BYO-MCP Server</title>
        <style>
            body {{ font-family: 'Google Sans', Arial, sans-serif; color: #3c4043; background-color: #f8f9fa; padding: 40px; line-height: 1.6; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
            h1 {{ color: #1a73e8; border-bottom: 1px solid #dadce0; padding-bottom: 10px; }}
            h2 {{ color: #1e8e3e; margin-top: 30px; }}
            .status {{ display: inline-block; background-color: #e6f4ea; color: #137333; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 14px; margin-bottom: 20px; }}
            code {{ background-color: #f1f3f4; padding: 3px 6px; border-radius: 4px; font-family: monospace; font-size: 15px; word-break: break-all; }}
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ServiceNow BYO-MCP Server</h1>
            <div class="status">Active & Running</div>
            <p>This server is active and ready to connect to Gemini Enterprise. Use the following connection endpoints to register this custom data store:</p>
            
            <h2>Registration Endpoints</h2>
            <ul>
                <li><strong>MCP Server URL</strong>: <code>{base_url}/mcp</code></li>
                <li><strong>Authorization URL</strong>: <code>{base_url}/oauth/authorize</code></li>
                <li><strong>Token URL</strong>: <code>{base_url}/oauth/token</code></li>
                <li><strong>Client ID</strong>: <code>mock-client-id</code></li>
                <li><strong>Client Secret</strong>: <code>mock-client-secret</code></li>
            </ul>
            
            <h2>ServiceNow Target Instance</h2>
            <p>Connecting to: <code>{os.environ.get("SN_INSTANCE_URL", "Not Configured")}</code></p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# 3. Manual JSON-RPC 2.0 Router for Custom MCP (/mcp)
# The MCP StreamableHTTP protocol is implemented manually to bypass AnyIO
# task group initialization errors that occur when mounting FastMCP.streamable_http_app
# inside an independent FastAPI process.

@app.get("/mcp")
async def mcp_get_status():
    """Simple health check for the MCP endpoint."""
    return JSONResponse(content={"status": "active", "transport": "StreamableHTTP"})

@app.post("/mcp")
async def mcp_post_endpoint(request: Request):
    """Manual JSON-RPC 2.0 endpoint for Model Context Protocol handshakes and tool calls."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON-RPC payload")

    method = body.get("method")
    request_id = body.get("id", 1)

    logger.info(f"[MCP HANDLER] Received JSON-RPC request: method={method}, id={request_id}")

    # A. Protocol Handshake (Initialize)
    if method == "initialize":
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-11-25",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "service-now-byo-mcp",
                    "version": "1.0.0"
                }
            }
        })

    # B. Initialized Notification
    elif method == "notifications/initialized":
        return JSONResponse(content={})

    # C. Tool Discovery (tools/list)
    elif method == "tools/list":
        try:
            tools = []
            # Dynamically list tools registered on the FastMCP server instance
            discovered_tools = await mcp.list_tools()
            for tool in discovered_tools:
                # Annotate tools to control user consent prompts in Gemini Enterprise.
                # Read-only tools are marked with readOnlyHint=True to enable implicit execution.
                # Write and delete tools are marked with destructiveHint=True to enforce explicit user approval.
                if tool.name in ["list_incidents", "query_incident", "get_ticket_comments", "search_knowledge_base", "get_knowledge_article"]:
                    annotations = {
                        "readOnlyHint": True,
                        "idempotentHint": True,
                        "destructiveHint": False
                    }
                else:
                    annotations = {
                        "readOnlyHint": False,
                        "idempotentHint": False,
                        "destructiveHint": True
                    }
                
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                    "annotations": annotations
                })

            
            logger.info(f"[MCP HANDLER] Successfully discovered {len(tools)} tools")
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": tools
                }
            })
        except Exception as e:
            logger.error(f"[MCP HANDLER] Failed during tool discovery: {e}")
            return JSONResponse(status_code=500, content={
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Tool discovery failure: {str(e)}"
                }
            })

    # D. Tool Execution (tools/call)
    elif method == "tools/call":
        params = body.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"[MCP HANDLER] Attempting execution of tool: {name} with args: {arguments}")

        try:
            # Execute the tool using the FastMCP server directly in-process
            result = await mcp.call_tool(name, arguments)

            # Serialize the FastMCP return objects to standard JSON-RPC content blocks
            content = []
            if isinstance(result, list):
                for block in result:
                    if hasattr(block, "text"):
                        content.append({"type": "text", "text": block.text})
                    elif isinstance(block, dict):
                        content.append(block)
                    else:
                        content.append({"type": "text", "text": str(block)})
            else:
                content.append({"type": "text", "text": str(result)})

            logger.info(f"[MCP HANDLER] Successfully executed tool {name}")
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": content
                }
            })
        except Exception as e:
            logger.error(f"[MCP HANDLER] Error executing tool {name}: {e}")
            return JSONResponse(status_code=500, content={
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Tool execution error: {str(e)}"
                }
            })

    # E. Unsupported Methods
    else:
        logger.warning(f"[MCP HANDLER] Unsupported method called: {method}")
        return JSONResponse(status_code=404, content={
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        })
