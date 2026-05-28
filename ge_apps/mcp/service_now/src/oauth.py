"""Mock OAuth 2.0 Provider for Gemini Enterprise.

This module implements an OAuth 2.0 authorization code flow provider using FastAPI. It is designed to satisfy Gemini Enterprise's OAuth configuration during registration.

It provides:
1. GET /oauth/authorize: A mock consent page that redirects back to Gemini.
2. POST /oauth/token: A mock token exchange endpoint returning a dummy access token.
"""

import logging
from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger("oauth_provider")

router = APIRouter(prefix="/oauth")

class TokenResponse(BaseModel):
    """OAuth 2.0 standard token response schema."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: str = "mock-refresh-token"
    scope: str = "read write"


@router.get("/authorize", response_class=HTMLResponse)
async def oauth_authorize(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(...),
    state: str = Query(None),
    scope: str = Query(None)
):
    """Serves a mock user consent screen for OAuth 2.0 authorization.

    When Gemini Enterprise initiates the OAuth flow, it redirects the user's browser
    to this endpoint. This endpoint renders a simple HTML page explaining that
    Gemini is requesting access to ServiceNow tools. When the user clicks "Authorize",
    it redirects back to Gemini's redirect_uri with a mock authorization code.

    Args:
        request: The incoming FastAPI Request.
        client_id: The client identifier (mocked).
        redirect_uri: The URI to redirect back to after authorization.
        response_type: Expected to be 'code'.
        state: An opaque state value passed by Gemini to prevent CSRF (must be returned).
        scope: Optional list of requested scopes.
    """
    logger.info(f"Received Authorization request from client_id: {client_id}, redirecting to: {redirect_uri}")

    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only 'code' response_type is supported in this mock flow.")

    # Build the redirect URL that redirects back to Gemini's oauth-redirect endpoint
    # with a mock code and the exact state passed in the request.
    mock_code = "mock-auth-code-12345"
    redirect_url = f"{redirect_uri}?code={mock_code}"
    if state:
        redirect_url += f"&state={state}"

    # HTML response for the consent screen.
    # Includes a clean UI and an "Authorize" button that triggers the redirect.
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ServiceNow MCP Authorization</title>
        <style>
            body {{ font-family: 'Google Sans', Arial, sans-serif; background-color: #f5f5f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .card {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }}
            h2 {{ color: #1a73e8; margin-top: 0; }}
            p {{ color: #5f6368; line-height: 1.5; }}
            .btn {{ background-color: #1a73e8; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 20px; }}
            .btn:hover {{ background-color: #1557b0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Authorize ServiceNow Integration</h2>
            <p><strong>Gemini Enterprise</strong> is requesting permission to access your ServiceNow instance to query and manage support cases on your behalf.</p>
            <p>This is a secure simulation environment.</p>
            <a href="{redirect_url}" class="btn">Authorize & Consent</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/token", response_model=TokenResponse)
async def oauth_token(
    grant_type: str = Form(...),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    client_id: str = Form(None),
    client_secret: str = Form(None),
    refresh_token: str = Form(None)
):
    """Exchanges an authorization code or refresh token for a mock access token.

    This endpoint is called server-to-server by Gemini's backend using standard
    x-www-form-urlencoded POST. It validates the grant type and returns a static,
    dummy access token.

    Args:
        grant_type: Expected to be 'authorization_code' or 'refresh_token'.
        code: The authorization code received in /authorize.
        redirect_uri: The redirect URI used in the authorization request.
        client_id: Client identifier.
        client_secret: Client secret key.
        refresh_token: The refresh token if grant_type is 'refresh_token'.

    Returns:
        A JSON response containing the standard OAuth2 Token structure.
    """
    logger.info(f"Received token exchange request. Grant Type: {grant_type}")

    if grant_type == "authorization_code":
        if not code:
            raise HTTPException(status_code=400, detail="Code parameter is required for authorization_code grant.")
        logger.info(f"Validating code: {code}. Issuing mock access token.")
        return TokenResponse(
            access_token="mock-access-token-xyz987654321",
            expires_in=3600
        )
    
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token is required for refresh_token grant.")
        logger.info("Refreshing token. Issuing new mock access token.")
        return TokenResponse(
            access_token="mock-access-token-refreshed-99999",
            expires_in=3600
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type '{grant_type}'. Only 'authorization_code' and 'refresh_token' are supported.")
