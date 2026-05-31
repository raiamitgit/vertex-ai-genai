"""A2UI agent for profile demo."""

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
You are a user profile assistant. Your goal is to help users see their profile information cleanly.

To achieve this, you MUST follow these steps:
1. Call the `get_user_profile` tool to retrieve the user's name, imageUrl, and LinkedIn profile URL.
2. Output a friendly conversational greeting.
3. Output the opening tag `<a2ui-json>`.
4. Generate the strictly-formatted A2UI JSON card for the image and name ONLY. Do not add any iframe or link inside A2UI.
5. Output the closing tag `</a2ui-json>`.
6. Output a line with a direct Markdown hyperlink to their LinkedIn profile. You MUST NOT include an exclamation mark ('!') before the link. The format must be exactly:
   "[LinkedIn Profile](LINKEDIN_URL)"
"""

A2UI_FEW_SHOT_TEMPLATE = """
You MUST strictly generate the A2UI JSON by copying this exact schema layout.

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
                  "profileName"
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
    description="An agent that returns the current user profile card and an external text link to LinkedIn.",
    tools=[get_user_profile]
)
