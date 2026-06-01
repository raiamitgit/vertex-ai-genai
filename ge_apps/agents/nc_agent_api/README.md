# Gemini Enterprise API Triggers

A lightweight collection of standalone Python scripts designed to programmatically trigger and stream interactions with Vertex AI Search / Gemini Enterprise **Workflow Agents** (visual DAGs) and **No-Code Agents** (conversational search assistants) via direct REST API calls.

> [!WARNING]
> **OFFICIAL SUPPORT DISCLAIMER**: This repository contains experimental code patterns leveraging **v1alpha** features of Discovery Engine APIs. 
> 
> These features are **NOT officially supported by Google Cloud** and do not carry standard production SLAs or support guarantees. Use of these APIs is subject to change or deprecation without notice. They are intended solely for prototyping and experimentation.

---

## Key Capabilities & File Structure

*   **`trigger_workflow.py`**: 
    *   **Visual DAG Execution**: Automates the execution of Workflow Agents that utilize structured trigger types (e.g., schedules, events).
    *   **Pre-validation Session Engine**: Automatically pre-creates and registers a valid, pre-labeled Discovery Engine `Session` with the necessary routing metadata (`agent`, `agent:workflow-agent:<id>`, `agent:workflow-agent:trigger-type:<type>`, and `revision:<id>`) to bypass visual agent execution preconditions.
    *   **Chunked Streaming**: Streams the step-by-step planner execution steps and agent status from the `:streamAssist` endpoint.
*   **`trigger_nocode.py`**:
    *   **Direct Conversational Trigger**: Triggers No-Code Agents directly in a single, stateless stream request.
    *   **No Session Overhead**: Bypasses the session pre-creation requirement, executing a standard stream query directly using the agent's configuration.
*   **`test_triggers.py`**:
    *   **Integration Test Runner**: Executes both trigger scripts sequentially to verify their execution.
*   **`requirements.txt`**:
    *   Minimal, lightweight dependency definitions (`python-dotenv`, `requests`, `google-auth`) required to run the triggers.
*   **`.env.example`**:
    *   A template file showing all the configuration environment variables required to run the triggers (Project ID, Engine ID, Agent IDs, Revision IDs, etc.).

---

## Why is Session Pre-Creation Required for Workflow Agents?

Unlike standard No-Code Agents that execute in a stateless, conversational manner, **Workflow Agents** (configured via visual DAGs) have strict entry requirements (e.g., starting at a Schedule or Event trigger node). 

To run successfully, the Discovery Engine routing engine must validate that the incoming request is allowed to trigger the workflow. This validation is enforced at the **Session boundary**:

1.  **Pre-created Session**: You must first create a `Session` resource in the Discovery Engine API.
2.  **Routing Labels**: The created Session must contain specific, structured `labels` that serve as routing metadata:
    *   `agent`: Identifies it as an agent session.
    *   `agent:workflow-agent`: Identifies it as a workflow agent session.
    *   `agent:workflow-agent:<AGENT_ID>`: Specifies the target agent.
    *   `agent:workflow-agent:trigger-type:<TRIGGER_TYPE>`: Matches the workflow's entry node configuration (e.g., `schedule`).
    *   `revision:<REVISION_ID>`: Specifies the active revision of the workflow DAG to execute.
3.  **Constraint Enforcement**: If you invoke the `streamAssist` API with a workflow agent ID but *without* passing a pre-created, labeled Session, the API will reject the request with a `FAILED_PRECONDITION` error.


---

## Streaming Behavior & Task Tracking

### Does the script wait for the agent to finish?
**Yes.** Both trigger scripts block and wait for the agent to complete execution. 

Because the scripts invoke the `streamAssist` API with `stream=True` and iterate over the response line-by-line (`response.iter_lines()`), the Python process holds the connection open. The script will only proceed once the agent completes all processing steps and the Google Cloud server closes the HTTP connection.

### How do you track task completion and success?
The stream returns a series of JSON objects. You can programmatically parse these chunks to track the state of the execution:

1.  **Track State**: Inspect the `state` field inside the `answer` object of the streamed JSON chunks.
2.  **Success**: A chunk containing `"state": "SUCCEEDED"` indicates the Workflow Agent completed all steps in its DAG successfully.
3.  **Failure**: A chunk containing `"state": "FAILED"` indicates a node execution failure or timeout occurred.

---

## Quick Start

1.  **Setup Environment**:
    ```bash
    virtualenv .venv
    source .venv/bin/activate
    pip install -r requirements.txt -i https://pypi.org/simple
    ```
2.  **Configure**:
    Copy `.env.example` to `.env` and fill in your actual GCP and agent details:
    ```bash
    cp .env.example .env
    # edit .env with your configurations
    ```
3.  **Verify & Run**:
    ```bash
    # Run both integration triggers sequentially
    python3 test_triggers.py

    # Or execute trigger scripts individually
    python3 trigger_workflow.py
    python3 trigger_nocode.py
    ```
