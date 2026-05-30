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

"""A2UI agent for profile demo (Strict CSP compliant)."""

from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext
import json

# Shared Mock Data Tool
def get_user_profile(tool_context: ToolContext) -> str:
    """Call this tool to get the current user profile."""
    return json.dumps({
        "name": "Amit Rai",
        "imageUrl": "https://media.licdn.com/dms/image/v2/C4E03AQHKuOfawBQQpA/profile-displayphoto-shrink_800_800/profile-displayphoto-shrink_800_800/0/1551663790520?e=1781740800&v=beta&t=LRI509zzmXrwVOzvXl1KB9roVlRrw-GEPpAbv-pbCx0",
        "linkedin": "https://www.linkedin.com/in/aamitrai"
    })

AGENT_INSTRUCTION = """
You are a user profile assistant. Your goal is to help users get their profile information using a rich UI.

To achieve this, you MUST follow these steps:
1.  Call the `get_user_profile` tool to retrieve the name, imageUrl, and linkedin profile url.
2.  Output a friendly conversational greeting.
3.  Output the opening tag `<a2ui-json>`.
4.  Generate the strictly-formatted A2UI JSON card.
5.  Output the closing tag `</a2ui-json>`.
"""

A2UI_FEW_SHOT_TEMPLATE = """
You MUST strictly generate the A2UI JSON by copying this exact schema layout.
You MUST include the literal single-quoted 'none' inside Content-Security-Policy exactly as shown: `content="connect-src 'none';"`
Do not use double quotes or HTML entities for the keyword 'none'.

---BEGIN A2UI JSON TEMPLATE---
[
  {
    "beginRendering": {
      "surfaceId": "userProfileSurface",
      "root": "profileColumn"
    }
  },
  {
    "surfaceUpdate": {
      "surfaceId": "userProfileSurface",
      "components": [
        {
          "id": "profileColumn",
          "component": {
            "Column": {
              "children": {
                "explicitList": [
                  "profileImage",
                  "profileName",
                  "linkedinButtonFrame"
                ]
              },
              "alignment": "center"
            }
          }
        },
        {
          "id": "profileImage",
          "component": {
            "Image": {
              "url": {
                "literalString": "IMAGE_URL"
              },
              "usageHint": "avatar"
            }
          }
        },
        {
          "id": "profileName",
          "component": {
            "Text": {
              "text": {
                "literalString": "USER_NAME"
              },
              "usageHint": "h3"
            }
          }
        },
        {
          "id": "linkedinButtonFrame",
          "component": {
            "WebFrameSrcdoc": {
              "htmlContent": {
                "literalString": "<!DOCTYPE html><html><head><meta http-equiv=\\"Content-Security-Policy\\" content=\\"connect-src 'none';\\"></head><body style=\\"margin:0; padding:0;\\"><div style=\\"text-align:center; padding-top:4px;\\"><a href=\\"LINKEDIN_URL\\" target=\\"_blank\\" style=\\"display:inline-block; padding:10px 28px; background:#d2e3fc; color:#185abc; border-radius:100px; text-decoration:none; font-family:sans-serif; font-size:14px; font-weight:500;\\">LinkedIn Profile</a></div></body></html>"
              },
              "height": 52
            }
          }
        }
      ]
    }
  }
]
---END A2UI JSON TEMPLATE---
"""

root_agent = LlmAgent(
    name="user_profile",
    model="gemini-2.5-flash",
    instruction=AGENT_INSTRUCTION + A2UI_FEW_SHOT_TEMPLATE,
    description="An agent that returns the current user profile with strict CSP-compliant safe WebFrame redirect links.",
    tools=[get_user_profile]
)
