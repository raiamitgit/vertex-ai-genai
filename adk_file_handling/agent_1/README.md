# Agent 1: Basic Document Processing

## Key Goal
The key goal of this agent is to demonstrate the most basic file processing pattern in ADK using built-in tools and strict guardrails to ensure accurate answers based on uploaded documents.

## Features
- **Built-in Tool Usage**: Leverages `load_artifacts_tool` to read the content of uploaded PDF and CSV files, showing the standard way to access user-provided files.
- **Strict Guardrails**: 
  - **File-Centric Focus**: Only answers questions based on uploaded files to prevent hallucination.
  - **Enforce Uploads**: Instructs users to upload a file if they ask a question without doing so.
  - **No General Knowledge**: Refuses to answer general questions unrelated to the uploaded files, keeping the agent focused on the provided data.
- **Thinking Traces Enabled**: Configured to include thinking traces (`include_thoughts=True`) to show the model's reasoning process before it provides an answer.

## How to Run
Run the `agent.py` file using the ADK runner. It will default to local in-memory sessions unless `RUNNING_IN_CLOUD=true` is set.
