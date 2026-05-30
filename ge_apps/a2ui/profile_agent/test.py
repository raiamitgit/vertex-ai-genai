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

"""Production-aligned A2A Client Simulator for Testing."""

import json
import requests

# A2A Server URL
SERVER_URL = "http://localhost:8000"

def test_send_message():
    """Simulates Gemini Enterprise sending a message/send request to our agent."""
    print(f"Connecting to A2A Server at: {SERVER_URL}...")
    
    # 1. Fetch the Agent Card (A2A Discovery)
    try:
        card_response = requests.get(f"{SERVER_URL}/.well-known/agent.json")
        if card_response.status_code == 200:
            print("\n[SUCCESS] Fetched Agent Card:")
            print(json.dumps(card_response.json(), indent=2))
        else:
            print(f"\n[ERROR] Failed to fetch Agent Card. Status: {card_response.status_code}")
            return
    except Exception as e:
        print(f"\n[ERROR] Connection failed during discovery: {e}")
        return

    # 2. Send the user prompt using the ACTUAL Gemini Enterprise 'message/send' payload structure
    a2a_request = {
        "jsonrpc": "2.0",
        "method": "message/send",  # <--- Aligned to production
        "params": {
            "configuration": {
                "acceptedOutputModes": [],
                "blocking": true
            },
            "message": {
                "kind": "message",
                "messageId": "test-message-uuid-456",
                "parts": [
                    {
                        "kind": "text",
                        "metadata": {
                            "is_user_input": true
                        },
                        "text": "> Show my profile"  # <--- Aligned to production format
                    }
                ],
                "role": "user"
            },
            "metadata": {}
        },
        "id": 1
    }
    
    print("\n[A2A Request] Sending message/send payload:")
    print(json.dumps(a2a_request, indent=2))
    
    try:
        response = requests.post(
            SERVER_URL,
            headers={"Content-Type": "application/json"},
            json=a2a_request,
            timeout=30
        )
        
        if response.status_code == 200:
            print("\n[A2A Response] Received JSON-RPC response from server:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"\n[ERROR] A2A Request failed. Status: {response.status_code}, Response: {response.text}")
            
    except Exception as e:
        print(f"\n[ERROR] Connection failed during execution: {e}")

if __name__ == "__main__":
    test_send_message()
