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

"""A2A Executor with balanced bracket XML parsing and flat list-to-parts mapping."""

import json
import re
import logging
from google.adk import Runner
from google.genai import types

logger = logging.getLogger("agent_executor")

# Standard A2UI XML-style tags used by the official SDK
A2UI_OPEN_TAG = "<a2ui-json>"
A2UI_CLOSE_TAG = "</a2ui-json>"
A2UI_MIME_TYPE = "application/json+a2ui"

_A2UI_BLOCK_RE = re.compile(
    f"{re.escape(A2UI_OPEN_TAG)}(.*?){re.escape(A2UI_CLOSE_TAG)}", re.DOTALL
)

def _sanitize_json(raw: str) -> str:
    """Strip optional markdown code fences that the LLM may add."""
    s = raw.strip()
    if s.startswith("```json"):
        s = s[len("```json"):]
    elif s.startswith("```"):
        s = s[len("```"):]
    if s.endswith("```"):
        s = s[:-len("```")]
    return s.strip()

def extract_first_json_array(s: str) -> str:
    """Surgically extracts the first balanced JSON array [...] from a string."""
    bracket_count = 0
    start_idx = -1
    for i, char in enumerate(s):
        if char == '[':
            if bracket_count == 0:
                start_idx = i
            bracket_count += 1
        elif char == ']':
            bracket_count -= 1
            if bracket_count == 0 and start_idx != -1:
                return s[start_idx:i+1]
    return ""

def enforce_csp_tag(html_str: str) -> str:
    """Surgically normalizes or injects the exact Content-Security-Policy meta tag needed by older A2UI renderers."""
    compliant_tag = '<meta http-equiv="Content-Security-Policy" content="connect-src \'none\';">'
    
    # Match any existing CSP meta tag case-insensitively
    pattern = re.compile(r'<meta\s+[^>]*Content-Security-Policy[^>]*>', re.IGNORECASE)
    if pattern.search(html_str):
        return pattern.sub(compliant_tag, html_str)
        
    # Inject after <head> if it exists
    head_pattern = re.compile(r'(<head[^>]*>)', re.IGNORECASE)
    if head_pattern.search(html_str):
        return head_pattern.sub(rf'\1{compliant_tag}', html_str)
        
    # Inject after <html> if it exists
    html_pattern = re.compile(r'(<html[^>]*>)', re.IGNORECASE)
    if html_pattern.search(html_str):
        return html_pattern.sub(rf'\1<head>{compliant_tag}</head>', html_str)
        
    # Wrap if completely missing
    return f"<html><head>{compliant_tag}</head><body>{html_str}</body></html>"

def sanitize_ui_item(item: dict) -> dict:
    """Walks the component dictionary tree and normalizes WebFrameSrcdoc HTML Content-Security-Policy."""
    if not isinstance(item, dict):
        return item
        
    if "surfaceUpdate" in item:
        surface_update = item["surfaceUpdate"]
        if isinstance(surface_update, dict) and "components" in surface_update:
            components = surface_update["components"]
            if isinstance(components, list):
                for comp in components:
                    if isinstance(comp, dict) and "component" in comp:
                        comp_def = comp["component"]
                        if isinstance(comp_def, dict) and "WebFrameSrcdoc" in comp_def:
                            srcdoc_def = comp_def["WebFrameSrcdoc"]
                            if isinstance(srcdoc_def, dict) and "htmlContent" in srcdoc_def:
                                html_content = srcdoc_def["htmlContent"]
                                if isinstance(html_content, dict) and "literalString" in html_content:
                                    raw_html = html_content["literalString"]
                                    if isinstance(raw_html, str):
                                        sanitized_html = enforce_csp_tag(raw_html)
                                        html_content["literalString"] = sanitized_html
                                        logger.info("Surgically sanitized and validated WebFrameSrcdoc CSP meta tag!")
    return item

class SolvedAgentExecutor:
    """Bridges the delimiter-based ADK agent output with the A2A Protocol response format."""
    
    def __init__(self, runner: Runner):
        self.runner = runner

    async def execute(self, user_query: str) -> list:
        """Runs the agent, parses standard XML tags, and outputs strictly-compliant flat A2A Parts.

        Args:
            user_query: The user's text prompt.

        Returns:
            A list of strictly-compliant flat A2A Part dictionaries.
        """
        session_id = "solved-session-123"
        user_id = "solved-user"
        
        try:
            await self.runner.session_service.create_session(
                app_name="profile_agent_solved",
                user_id=user_id,
                session_id=session_id
            )
        except Exception:
            pass
            
        new_message = types.Content(role='user', parts=[types.Part(text=user_query)])
        agent_raw_response = ""
        
        # 1. Execute the ADK runner
        async for event in self.runner.run_async(user_id=user_id, session_id=session_id, new_message=new_message):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        agent_raw_response = part.text
                        break
                        
        if not agent_raw_response:
            raise ValueError("Agent returned empty response.")
            
        # 2. Parse using standard XML tags
        matches = list(_A2UI_BLOCK_RE.finditer(agent_raw_response))
        
        if not matches:
            logger.info("No XML A2UI tags found, returning raw response as TextPart.")
            return [{
                "kind": "text",
                "text": agent_raw_response.strip()
            }]
            
        a2a_parts = []
        last_end = 0
        
        for match in matches:
            start, end = match.span()
            
            # Extract conversational text preceding this block
            text_before = agent_raw_response[last_end:start].strip()
            if text_before:
                a2a_parts.append({
                    "kind": "text",
                    "text": text_before
                })
                
            # Extract and sanitize the raw JSON payload between tags
            raw_json_block = match.group(1).strip()
            json_payload_str = extract_first_json_array(_sanitize_json(raw_json_block))
            
            if not json_payload_str:
                logger.error(f"No balanced JSON array found in block: {raw_json_block}")
                continue
                
            # Parse the A2UI JSON list
            try:
                ui_definition = json.loads(json_payload_str)
                
                # FIX: Walk the list and append a SEPARATE, flat DataPart for each action item
                # This satisfies the A2A Pydantic schema which strictly expects a dictionary in 'data'
                if isinstance(ui_definition, list):
                    for item in ui_definition:
                        sanitized_item = sanitize_ui_item(item)
                        a2a_parts.append({
                            "kind": "data",
                            "data": sanitized_item,  # Flat dictionary item
                            "metadata": {
                                "mimeType": A2UI_MIME_TYPE
                            }
                        })
                else:
                    sanitized_item = sanitize_ui_item(ui_definition)
                    a2a_parts.append({
                        "kind": "data",
                        "data": sanitized_item,
                        "metadata": {
                            "mimeType": A2UI_MIME_TYPE
                        }
                    })
            except Exception as e:
                logger.error(f"Failed to parse isolated A2UI JSON: {e}. Block: {json_payload_str}")
                
            last_end = end
            
        # Extract trailing conversational text after the last block
        trailing_text = agent_raw_response[last_end:].strip()
        if trailing_text:
            a2a_parts.append({
                "kind": "text",
                "text": trailing_text
            })
            
        return a2a_parts
