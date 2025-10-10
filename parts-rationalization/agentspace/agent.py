import os
import logging
import tempfile
import uuid
import base64
from dotenv import load_dotenv

# Import ADK and Cloud Logging
import google.adk
from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
from google.cloud import logging as cloud_logging
import google.cloud.aiplatform

# Import the tools
from tools.physna_tool import search_parts_by_asset_id, search_parts_by_image
from tools.database_tool import fetch_details_from_database

# --- Logging Configuration ---
# Set to INFO for production
LOG_LEVEL = logging.INFO 

try:
    # Initialize Google Cloud Structured Logging
    client = cloud_logging.Client()
    client.setup_logging(log_level=LOG_LEVEL)
    logging.info("Google Cloud Structured Logging enabled.")
except Exception as e:
    # Basic logging for local testing
    logging.basicConfig(level=LOG_LEVEL,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.warning(f"Could not initialize Cloud Logging: {e}. Using standard output.")


# --- Environment Setup ---
load_dotenv()
os.environ["GOOGLE_CLOUD_PROJECT"] = os.getenv("GCP_PROJECT_ID")
os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GCP_LOCATION")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

async def search_parts_by_image_upload(tool_context: ToolContext):
    """
    This function finds parts which are similar to an image uploaded by the user.
    Handles an uploaded image from the chat, saves it temporarily, and triggers a part search.
    This tool is context-aware and uses the ToolContext to find the uploaded artifact.

    Returns:
        A dictionary containing the closet matching source asset (found via image search) and
        a list of geometrically matched parts. Includes match percentage, metadata,
        and comparison URLs.
    """
    logging.info("--- Starting search_parts_by_image_upload ---")
    image_data = None  # Holds raw bytes
    mime_type = None
    image_source = None

    # Check for inline image data
    for p in tool_context.user_content.parts:
        if p.inline_data and "image" in p.inline_data.mime_type:
            image_data = p.inline_data.data # Already bytes
            mime_type = p.inline_data.mime_type
            image_source = "inline_data"
            logging.info(f"Found inline image. Mime: {mime_type}")
            break

    # If no inline image, check for uploaded artifacts
    if not image_data:
        logging.info("Checking for artifacts...")
        try:
            artifacts = await tool_context.list_artifacts()
            
            if artifacts:
                logging.info("Found artifacts - {artifacts}")
                # Get the most recent one
                filename = artifacts[-1]
                logging.info(f"Loading artifact: '{filename}'")
                loaded_artifact = await tool_context.load_artifact(filename=filename)
                # Extract data from the known structure: {'inlineData': {'mimeType': '...', 'data': '...'}}
                inline_data_obj = loaded_artifact.get("inlineData")

                if inline_data_obj and isinstance(inline_data_obj, dict):
                    b64_data = inline_data_obj.get("data")
                    mime_type = inline_data_obj.get("mimeType")

                    if b64_data and mime_type and "image" in mime_type:
                        try:
                            image_data = base64.b64decode(b64_data)
                            image_source = f"artifact '{filename}'"
                            logging.info(f"Successfully loaded and decoded artifact. Mime: {mime_type}")
                        except Exception as b64_err:
                            logging.error(f"Failed to decode base64 data from '{filename}': {b64_err}")
                    else:
                        logging.error(f"Artifact '{filename}' is not a valid image or is missing data.")
                else:
                    logging.error(f"Artifact '{filename}' did not contain expected 'inlineData' structure.")
            else:
                logging.info("No artifacts found in context.")

        except Exception as e:
            logging.error(f"Error loading artifacts: {e}", exc_info=True)

    if not image_data:
        return {"status": "error", "message": "No valid image found. Please upload an image."}

    suffix = ".jpg" 
    if "png" in mime_type: suffix = ".png"
    elif "gif" in mime_type: suffix = ".gif"
    elif "jpeg" in mime_type: suffix = ".jpeg"
    temp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}{suffix}")
    try:
        logging.info(f"Saving image bytes to temporary file: {temp_path}")
        with open(temp_path, "wb") as f:
            f.write(image_data)
        
        logging.info("Executing image search tool...")
        result = search_parts_by_image(local_image_path=temp_path)
        return result

    except Exception as e:
        logging.error(f"Error during image processing/search: {e}", exc_info=True)
        return {"status": "error", "message": f"Error processing image: {str(e)}"}
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logging.debug(f"Deleted temp file: {temp_path}")
            except Exception:
                pass # Ignore cleanup errors

# --- Agent Instructions ---
agent_description = """You are the GM Part Search Assistant. Your purpose is to help engineers find information about existing parts, including geometric similarity searches and detailed supply chain and engineering data retrieval from a database."""

agent_instructions = """
You are a helpful assistant for General Motors Design engineers.
Your goal is to promote part reuse by providing easy access to geometric search and detailed part information.

You have access to the following tools:

1.  **`search_parts_by_asset_id`**:
    *   **When to use:** Use this when the user provides a specific, existing Physna Asset ID (typically a UUID string, e.g., "123e4567-e89b...") to find *geometrically similar* parts.
    *   **Action:** It performs a direct geometric search using that asset as the source.

2.  **`search_parts_by_image_upload`**:
    *   **When to use:** Use this when the user uploads an image file directly into the chat to find *geometrically similar* parts. **Do not pass any parameters to this tool.**
    *   **Action:** It automatically detects the uploaded image, finds a matching 3D model, and then uses that model to find geometrically similar parts.

3.  **`fetch_details_from_database`**:
    *   **When to use:** Use this when the user asks for specific details about a known part, such as its material, cost, inventory, supplier, engineering notes, or the vehicle it belongs to. This tool is for retrieving data, not for similarity searches.
    *   **Action:** It queries a database for detailed information using the part's `asset_id`.

**Operational Guidelines:**

1.  **Maintain Context:** Pay close attention to the conversational history. If the user asks a follow-up question that refers to items you just presented (e.g., "what's the difference between part 1 and 2"), do not ask for IDs you have already provided in the previous turn. Use the asset IDs from your own search results to answer the question.

2.  **Analyze the Request:**
    *   **For Similarity:** If the user wants to find *similar* parts, determine if they are providing an Asset ID or uploading an image.
    *   **For Details:** If the user asks a specific question about a part (e.g., "what is the cost of part X?", "compare part X and part Y", "how much inventory for part Z?"), you will need the `asset_id` of the part(s) in question. Before asking the user, check if you have already provided the asset ID in a previous turn.

3.  **Select the Tool:**
    *   For similarity searches, choose `search_parts_by_asset_id` or `search_parts_by_image_upload`.
    *   For detailed questions, use `fetch_details_from_database` with the appropriate `asset_id`.

4.  **Process and Present Results:**
    *   **Similarity Search Results:** Summarize the number of results and present the top matches clearly, including:
        - Part Name (add Part URL as a hyperlink)
        - Asset Id
        - Match Percentages (Rounded to two decimal places)
        - Comparison URLs (show as hyperlink).
    *   **Detailed Information Results:** When the `fetch_details_from_database` tool returns data, do not just show the raw JSON. Instead, use the information to answer the user's question directly, following the specific formatting guidelines below.

    *   **Output Formatting Guidelines:**
        *   **For a question about a single part:**
            1.  Provide a direct, plain English answer to the user's question.
            2.  Follow the answer with a bulleted list of the most relevant details that support your answer.
            *   *Example Query:* "What is the inventory of part X and why does it have zinc coating?"
            *   *Example Response:*
                "The current on-hand inventory for part X is 15,230 units. It has a Zinc-Plated finish for corrosion resistance.

                *   **Part Name:** E3_86331563_001_MODULE_ASM_DRVR_MONITORING_SYS_94937.glb
                *   **Inventory:** 15,230 units
                *   **Finish:** Zinc-Plated
                *   **Engineering Notes:** Zinc-plating required for corrosion resistance on Vistiq platform due to specific underbody exposure."

        *   **For a question comparing multiple parts:**
            1.  Start with a single summary sentence that highlights the 2-3 most important differences (e.g., cost, material, supplier).
            2.  Follow this summary with a clear, bulleted comparison of the parts, detailing their key attributes.
            *   *Example Query:* "Compare parts A, B, and C."
            *   *Example Response:*
                "The primary differences between these parts are their vehicle platform, material, and cost, with Part C being the most expensive.

                *   **Part 1 (Asset ID: ...)**
                    *   **Vehicle Platform:** Cadillac Vistiq
                    *   **Material:** High-Strength Steel, ABS Plastic
                    *   **Cost:** $62.50
                    *   **Supplier:** OmniSteer Solutions
                *   **Part 2 (Asset ID: ...)**
                    *   **Vehicle Platform:** Cadillac Optiq
                    *   **Material:** Reinforced ABS Polymer
                    *   **Cost:** $85.50
                    *   **Supplier:** ElectraDrive Controls
                *   **Part 3 (Asset ID: ...)**
                    *   **Vehicle Platform:** Cadillac Vistiq
                    *   **Material:** ABS Plastic
                    *   **Cost:** $125.50
                    *   **Supplier:** ElectraDrive Controls"

5.  **Handle Errors:** If a tool fails or returns no results, explain the issue clearly to the user and suggest next steps.
"""

# --- Agent Definition ---
root_agent = LlmAgent(
    name="gm_design_agent",
    model=os.getenv("ADK_AGENT_MODEL", "gemini-1.5-pro"), # Using a standard model name
    description=agent_description,
    instruction=agent_instructions,
    tools=[
        search_parts_by_asset_id,
        search_parts_by_image_upload,
        fetch_details_from_database,
    ],
)