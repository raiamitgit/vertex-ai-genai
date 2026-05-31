"""Verify A2A server responses against Pydantic schemas (WebFrame integrated)."""

import json
from fastapi.testclient import TestClient
from a2a.compat.v0_3.types import SendMessageResponse

# Import our app from main.py
from main import app

client = TestClient(app)

def test_user_action_postback_validation():
    print("\n====================================================")
    print("TEST 1: Verifying 'userAction' postback payload...")
    print("====================================================")
    
    postback_request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "configuration": {
                "acceptedOutputModes": [],
                "blocking": True
            },
            "message": {
                "contextId": "context-6b317997-20e2-48b3-b7bc-fef1f70c87cb",
                "kind": "message",
                "messageId": "984988a4-702a-4c34-9f37-77739f3ce3af",
                "parts": [
                    {
                        "kind": "text",
                        "metadata": {"is_user_input": True},
                        "text": "User action triggered."
                    },
                    {
                        "data": {
                            "userAction": {
                                "context": {"url": "https://www.linkedin.com/in/aamitrai"},
                                "name": "openUrl",
                                "sourceComponentId": "linkedinButton",
                                "surfaceId": "userProfileSurface",
                                "timestamp": "2026-05-29T11:35:53.538Z"
                            }
                        },
                        "kind": "data",
                        "metadata": {
                            "mimeType": "application/json+a2ui",
                            "is_user_input": True
                        }
                    }
                ],
                "role": "user"
            },
            "metadata": {}
        },
        "id": 1
    }
    
    response = client.post("/", json=postback_request)
    
    assert response.status_code == 200, f"[ERROR] Local server failed with status: {response.status_code}"
    response_json = response.json()
    print("Received local postback response:")
    print(json.dumps(response_json, indent=2))
    
    try:
        SendMessageResponse.model_validate(response_json)
        print("[SUCCESS] 'userAction' postback response is Pydantic-compliant!")
    except Exception as err:
        print(f"[ERROR] Pydantic validation failed for postback: {err}")
        raise err

def test_standard_query_validation():
    print("\n====================================================")
    print("TEST 2: Verifying standard query prompt payload...")
    print("====================================================")
    
    query_request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "configuration": {"acceptedOutputModes": [], "blocking": True},
            "message": {
                "kind": "message",
                "messageId": "test-query-id-123",
                "parts": [
                    {
                        "kind": "text",
                        "metadata": {"is_user_input": True},
                        "text": "Can you show me the profile"
                    }
                ],
                "role": "user"
            },
            "metadata": {}
        },
        "id": 2
    }
    
    response = client.post("/", json=query_request)
    
    assert response.status_code == 200, f"[ERROR] Local server failed with status: {response.status_code}"
    response_json = response.json()
    print("Received local query response:")
    print(json.dumps(response_json, indent=2))
    
    try:
        SendMessageResponse.model_validate(response_json)
        print("[SUCCESS] Standard query response is Pydantic-compliant!")
    except Exception as err:
        print(f"[ERROR] Pydantic validation failed for query: {err}")
        raise err

if __name__ == "__main__":
    test_user_action_postback_validation()
    test_standard_query_validation()
