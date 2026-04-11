# Agent 4: Custom Code Execution for Structured Data

## Key Goal
The key goal of this agent is to showcase how to use Code Execution to process and analyze structured data files (such as CSV and JSON) effectively.

## Features
- **Structured Data Analysis**: Demonstrates how an agent can write and execute Python code to answer complex questions about data files, calculate metrics, and generate summaries.
- **Custom Code Execution**: Uses ADK's `UnsafeLocalCodeExecutor` to process files in an isolated local process. This approach bypasses issues where native Gemini code execution conflicts with other model tools.
- **Robust Self-Correction**: Demonstrated ability to rewrite generated Python code when dependencies (like `pandas`) are missing, falling back to built-in libraries like `csv` to ensure reliability.
- **Advanced Model Config**: Uses `gemini-3-flash-preview` with thinking traces enabled (`include_thoughts=True`) to provide transparency into the model's reasoning process before execution.
- **Preview Model Integration**: Showcases how to use Gemini preview models (which only support the `global` region) with ADK by using a custom wrapper to override the region.

## How to Run
Run the `agent.py` file using the ADK runner. Ensure the environment variables in the `.env` file (such as `GCS_ARTIFACT_BUCKET` and `AGENT_ENGINE_ID`) are properly configured.
