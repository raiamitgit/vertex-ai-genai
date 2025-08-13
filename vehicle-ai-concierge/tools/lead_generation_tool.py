# File: tools/lead_generation_tool.py
# Description: A conversational tool to generate a lead for a vehicle quote.

import json
from typing import List, Dict, Any
from helpers import gemini_helper
from google.adk.tools import ToolContext # Import ToolContext

# Define the structure of the lead information we need to collect
LEAD_SCHEMA = {
    "type": "object",
    "properties": {
        "first_name": {"type": "string", "description": "The user's first name."},
        "last_name": {"type": "string", "description": "The user's last name."},
        "zip_code": {"type": "string", "description": "The user's 5-digit zip code for locating nearby dealers and offers."},
        "phone_number": {"type": "string", "description": "The user's phone number."},
        "email": {"type": "string", "description": "The user's email address."},
        "contact_preference": {"type": "string", "enum": ["Email", "Telephone"], "description": "How the user prefers to be contacted."},
        "vehicle_model": {"type": "string", "description": "The model of the vehicle the user is interested in (e.g., 'Enclave', 'Envision')."},
        "vehicle_year": {"type": "integer", "description": "The model year of the vehicle."},
        "notes": {"type": "string", "description": "A summary of the user's specific interests, questions, or requested features (e.g., color, trim, specific questions about warranty or features)."}
    },
    "required": ["first_name", "last_name", "zip_code", "email", "contact_preference", "vehicle_model"]
}

def check_and_request_info(tool_context: ToolContext) -> str:
    """
    Analyzes chat history to find missing lead information and asks the user for it in a formatted way.
    """
    raw_events = tool_context._invocation_context.session.events
    chat_history = []
    for event in raw_events:
        if event.author and event.content and event.content.parts and event.content.parts[0].text:
            role = "user" if event.author == "user" else "assistant"
            chat_history.append({"role": role, "content": event.content.parts[0].text})
            
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    
    prompt = f"""
    You are an AI assistant helping a user get a price quote for a Buick vehicle.
    Your task is to determine what information is still needed from the user.
    1.  **Required Information for a Quote:**
        - First Name
        - Last Name
        - Zip Code
        - Email Address
        - Preferred method of contact (Email or Telephone)
    2.  **Analyze the Conversation History below:** Read through the chat history to see which of the required pieces of information the user has already provided.
    3.  **Ask for What's Missing:** Generate a friendly, natural-language question that asks the user ONLY for the information they have not yet provided. Format the list of missing items with each item on a new line and enclosed in bold markdown.
    Conversation History:
    ---
    {history_text}
    ---
    Generate the question for the missing information now.
    """
    return gemini_helper.generate_text(prompt)

def extract_and_confirm_lead(tool_context: ToolContext) -> str:
    """
    Extracts lead information from a conversation and generates a confirmation message.
    """
    raw_events = tool_context._invocation_context.session.events
    chat_history = []
    for event in raw_events:
        if event.author and event.content and event.content.parts and event.content.parts[0].text:
            role = "user" if event.author == "user" else "assistant"
            chat_history.append({"role": role, "content": event.content.parts[0].text})

    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    
    extraction_prompt = f"""
    You are an expert entity extraction AI. Analyze the entire conversation and extract the user's information into a JSON object based on this schema: {json.dumps(LEAD_SCHEMA, indent=2)}
    Conversation History:
    ---
    {history_text}
    ---
    Return ONLY the final JSON object.
    """
    extracted_json_str = gemini_helper.generate_text(extraction_prompt)
    
    try:
        if extracted_json_str.strip().startswith("```json"):
            extracted_json_str = extracted_json_str.strip()[7:-4]
        lead_data = json.loads(extracted_json_str)
        
        # Reverted to generating a simple, formatted string for confirmation.
        confirmation_message = "Great, thank you! Please take a moment to review the information below. If everything is correct, I can forward this to a dealership to get you a precise quote.\n\n"
        confirmation_message += f"**First Name:** {lead_data.get('first_name', 'N/A')}\n"
        confirmation_message += f"**Last Name:** {lead_data.get('last_name', 'N/A')}\n"
        confirmation_message += f"**Vehicle:** {lead_data.get('vehicle_year', '')} {lead_data.get('vehicle_model', 'N/A')}\n"
        confirmation_message += f"**Email:** {lead_data.get('email', 'N/A')}\n"
        if lead_data.get('phone_number'):
            confirmation_message += f"**Phone:** {lead_data.get('phone_number')}\n"
        confirmation_message += f"**Contact Preference:** {lead_data.get('contact_preference', 'N/A')}\n"
        confirmation_message += f"**Zip Code:** {lead_data.get('zip_code', 'N/A')}\n"
        if lead_data.get('notes'):
            confirmation_message += f"**Notes:** {lead_data.get('notes', '')}\n"
            
        return confirmation_message

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error processing LLM response: {e}")
        return "I seem to have had a little trouble gathering all of that. Could you please provide the information again?"
