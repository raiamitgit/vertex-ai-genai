# A2UI Profile Agent Demo (Reproduction & Solution)

This workspace demonstrates both the **reproduction** of a common Gemini Enterprise A2UI rendering bug and its **natural solution** using an A2A string-splitting executor (the same pattern used by the Google Chat Apps Script bridge).

Both modes are served from the same codebase and can be toggled instantly using an environment variable.

---

## Architecture Overview

AI agents excel at generating conversational responses alongside structured visual UI definitions (A2UI JSON). Since LLMs produce a single stream of characters, the quickstart tutorial uses a **Delimiter Pattern** where the model outputs the conversational text and A2UI JSON separated by a unique delimiter (`---a2ui_JSON---`).

*   **Repro Mode (`RUN_MODE=repro`)**:
    Mimics a naive Cloud Run deployment where the server does no output processing. The server wraps the entire raw agent output (including the delimiter and raw JSON) into a single A2A `TextPart`. 
    *   *Gemini Enterprise Behavior*: Renders the raw JSON as ugly plain text in the chat bubble.
*   **Solved Mode (`RUN_MODE=solved`)**:
    Implements the natural "A2A Bridge" pattern. The server intercepts the output, splits it at `---a2ui_JSON---`, parses the JSON, and maps them into clean A2A parts: a `TextPart` for the chat bubble and a `DataPart` (MIME `application/json`) for the native A2UI rendering engine.
    *   *Gemini Enterprise Behavior*: Displays the conversational text and renders a beautiful native visual card (avatar image, title, and LinkedIn button).

---

## Directory Contents

*   `a2ui_schema.py`: Defines the A2UI v0.8 JSON Schema constant, which is injected into the agent's system instructions.
*   `agent.py`: Defines the ADK `LlmAgent` (running `gemini-2.5-flash`) that fetches the profile data and composes the layout.
*   `agent_executor.py`: Implements the solved string-splitting parsing logic.
*   `main.py`: FastAPI web server exposing `POST /` for A2A JSON-RPC calls and `GET /.well-known/agent.json` for A2A discovery.
*   `agent_card.json`: The agent card metadata declaring A2UI v0.8 capability.
*   `test.py`: The local A2A client simulator used to query the server and inspect the network response envelopes.

---

## Setup Instructions

### 1. Prepare the Environment
Ensure your shared `.env` file in the parent `a2ui/` directory is configured with your GCP Project ID:
```bash
# file: a2ui/.env
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=YOUR_GCP_PROJECT_ID
GOOGLE_CLOUD_LOCATION=us-central1
```

Authenticate Google Cloud Application Default Credentials (ADC) on your terminal:
```bash
gcloud auth application-default login
```

### 2. Initialize the Virtual Environment
Create and activate an isolated virtual environment inside this directory, and install the specific ADK packages:
```bash
# Navigate to this folder
cd profile_agent

# Create venv using virtualenv (bypassing debian constraints)
virtualenv .venv
source .venv/bin/activate

# Install requirements from public PyPI
pip install -r requirements.txt --index-url https://pypi.org/simple/
```

---

## How to Test the Reproduction (The Bug)

1.  **Start the Server in Repro Mode**:
    ```bash
    # Load shared env and start uvicorn in repro mode (default)
    export $(grep -v '^#' ../.env | xargs)
    export RUN_MODE=repro
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```
2.  **Run the Test Client (In a separate terminal)**:
    ```bash
    source .venv/bin/activate
    python test.py
    ```
3.  **Observe the Bug**:
    In the output, note that the entire text response and the JSON structure are lumped together inside a single A2A `TextPart` under `text`:
    ```json
    "content": {
      "text": "Here is your profile information:\n---a2ui_JSON---\n[\n  {\n \"surfaceId\": ... [Raw JSON follows]"
    }
    ```

---

## How to Test the Resolution (The Fix)

1.  **Start the Server in Solved Mode**:
    ```bash
    # Load shared env and start uvicorn with RUN_MODE set to solved
    export $(grep -v '^#' ../.env | xargs)
    export RUN_MODE=solved
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```
2.  **Run the Test Client (In a separate terminal)**:
    ```bash
    source .venv/bin/activate
    python test.py
    ```
3.  **Observe the Solution**:
    In the output, note that the server has successfully split the payload into two clean parts:
    ```json
    "parts": [
      {
        "text": "Here is your profile information:"
      },
      {
        "data": {
          "value": [ ... A2UI JSON components ... ],
          "mimeType": "application/json"
        }
      }
    ]
    ```
    Gemini Enterprise can now render the UI natively.
