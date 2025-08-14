import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

# Import agent prompts and all tools
from . import prompts
from tools import (
    website_search_tool,
    dealership_search_tool,
    parts_search_tool,
    lead_generation_tool,
)

# --- ADK Environment Configuration ---
load_dotenv()
os.environ["GOOGLE_CLOUD_PROJECT"] = os.getenv("VERTEX_AI_PROJECT_ID")
os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("VERTEX_AI_LOCATION")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")


# --- 1. Define Specialist Agents ---

website_search_agent = Agent(
    name="WebsiteSearchAgent",
    model=MODEL_NAME,
    description="Use for general questions, vehicle information, support issues, or anything that might be on the Buick website.",
    instruction=prompts.get_website_search_instructions(),
    tools=[website_search_tool.search],
)

dealership_search_agent = Agent(
    name="DealershipSearchAgent",
    model=MODEL_NAME,
    description="Use this tool to find nearby Buick dealerships by zip code.",
    instruction=prompts.get_dealership_search_instructions(),
    tools=[dealership_search_tool.find_dealerships],
)

parts_search_agent = Agent(
    name="PartsSearchAgent",
    model=MODEL_NAME,
    description="Use to search for vehicle parts and accessories for a specific model and year.",
    instruction=prompts.get_parts_search_instructions(),
    tools=[parts_search_tool.search_parts],
)

lead_generation_agent = Agent(
    name="LeadGenerationAgent",
    model=MODEL_NAME,
    description="Use when the user wants a price quote, to schedule a test drive, or provides contact info.",
    instruction=prompts.get_lead_generation_instructions(),
    tools=[lead_generation_tool.format_lead_for_confirmation],
)


# --- 2. Define the Root Agent (The Orchestrator) ---

root_agent = Agent(
    name="BuickConciergeOrchestrator",
    model=MODEL_NAME,
    description="The main conversational agent for all Buick customer needs.",
    instruction=prompts.get_orchestrator_instructions(),
    tools=[
        AgentTool(agent=website_search_agent),
        AgentTool(agent=dealership_search_agent),
        AgentTool(agent=parts_search_agent),
        AgentTool(agent=lead_generation_agent),
    ],
)
