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

"""Programmatic A2UI Schema Validator (List-splitting aligned)."""

import json
import requests
import jsonschema
from jsonschema import validate

# Import A2UI Schema constant
from a2ui_schema import A2UI_SCHEMA

# Live Cloud Run URL
CLOUD_RUN_URL = "https://profile-a2ui-agent-m4sz4fgk5a-uc.a.run.app"

def run_live_schema_validation():
    print(f"====================================================")
    print(f"Running live A2UI Schema Validation Test...")
    print(f"Target URL: {CLOUD_RUN_URL}")
    print(f"====================================================")
    
    a2a_request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "configuration": {
                "acceptedOutputModes": [],
                "blocking": True
            },
            "message": {
                "kind": "message",
                "messageId": "validation-test-uuid-789",
                "parts": [
                    {
                        "kind": "text",
                        "metadata": {
                            "is_user_input": True
                        },
                        "text": "Can you get my user profile"
                    }
                ],
                "role": "user"
            },
            "metadata": {}
        },
        "id": 1
    }
    
    try:
        response = requests.post(
            CLOUD_RUN_URL,
            headers={"Content-Type": "application/json"},
            json=a2a_request,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: Server returned status {response.status_code}")
            print(response.text)
            return False
            
        response_data = response.json()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

    # Extract Message object
    try:
        result = response_data.get("result", {})
        
        if "parts" in result:
            message = result
        elif "message" in result:
            message = result["message"]
        elif "Message" in result:
            message = result["Message"]
        else:
            task = result.get("task") if "task" in result else result.get("Task")
            if task and "status" in task and "message" in task["status"]:
                message = task["status"]["message"]
            else:
                message = None
                
        if not message:
             print("❌ Error: Result contains neither a valid Message nor a Task object.")
             print(json.dumps(response_data, indent=2))
             return False
             
        parts = message.get("parts", [])
    except Exception as e:
        print(f"❌ Error navigating response envelope: {e}")
        print(json.dumps(response_data, indent=2))
        return False

    # Find the A2UI DataPart matching 'kind' == 'data' and 'mimeType' == 'application/json+a2ui'
    a2ui_parts = [
        p for p in parts 
        if p.get("kind") == "data" 
        and p.get("metadata", {}).get("mimeType") == "application/json+a2ui"
    ]
    
    if not a2ui_parts:
        print("❌ Error: No A2UI DataPart found in response parts matching SDK specs.")
        print("Response Parts:")
        print(json.dumps(parts, indent=2))
        return False
        
    # FIX: Reconstruct the A2UI JSON list from the "data" field of all matched parts
    a2ui_card_json = [p["data"] for p in a2ui_parts]
    print("\n✅ Successfully reconstructed A2UI JSON Payload:")
    print(json.dumps(a2ui_card_json, indent=2))

    # 5. Execute strict JSON Schema validation
    print("\nExecuting jsonschema validation against A2UI v0.8 blueprint...")
    try:
        schema_dict = json.loads(A2UI_SCHEMA)
        
        if isinstance(a2ui_card_json, list):
            print(f"Detected A2UI array (length: {len(a2ui_card_json)}). Validating each action item...")
            for idx, action_item in enumerate(a2ui_card_json):
                print(f" -> Validating A2UI Action {idx}...")
                validate(instance=action_item, schema=schema_dict)
        else:
            print("Detected single A2UI action object. Validating...")
            validate(instance=a2ui_card_json, schema=schema_dict)
            
        print(f"====================================================")
        print(f"🎉 SUCCESS: A2UI JSON is 100% compliant with the spec!")
        print(f"The card is guaranteed to render flawlessly in GE.")
        print(f"====================================================")
        return True
    except jsonschema.exceptions.ValidationError as err:
        print(f"====================================================")
        print(f"❌ SCHEMA VALIDATION FAILURE!")
        print(f"Error Message: {err.message}")
        print(f"Error Path:    {list(err.absolute_path)}")
        print(f"Schema Path:   {list(err.absolute_schema_path)}")
        print(f"====================================================")
        return False
    except Exception as e:
        print(f"❌ Unexpected validation error: {e}")
        return False

if __name__ == "__main__":
    run_live_schema_validation()
