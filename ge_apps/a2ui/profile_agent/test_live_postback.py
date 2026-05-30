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

"""Rigorous live postback verification script."""

import json
import requests

CLOUD_RUN_URL = "https://profile-a2ui-agent-m4sz4fgk5a-uc.a.run.app"

def test_live_postback():
    print("====================================================")
    print(f"Querying Live Cloud Run Endpoint: {CLOUD_RUN_URL}")
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
    
    response = requests.post(
        CLOUD_RUN_URL,
        headers={"Content-Type": "application/json"},
        json=postback_request
    )
    
    print(f"HTTP Status: {response.status_code}")
    print("Raw Outgoing Response Payload from Server:")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_live_postback()
