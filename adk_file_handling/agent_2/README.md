# Agent 2: ZIP File Interception

## Key Goal
The key goal of this agent is to showcase how to process arbitrary or unsupported file types (specifically ZIP files) by intercepting them before they reach the model.

## Features
- **ZIP File Interception**: Uses `before_model_callback` to intercept ZIP file uploads that Gemini cannot process natively.
- **In-Memory Extraction**: Extracts the contents of the ZIP file in memory without saving to disk, ensuring efficiency and security.
- **Inline Injection**: Injects the extracted file contents directly into the prompt as text (for CSV/JSON) or bytes (for other supported types), allowing the model to answer questions about them.
- **Arbitrary File Processing**: Proves that ADK can be adapted to handle any custom file format by preprocessing it before it reaches the model.
- **Thinking Traces Enabled**: Configured to include thinking traces (`include_thoughts=True`) to show the model's reasoning process.

## How to Run
Run the `agent.py` file using the ADK runner. Ensure you have configured local file artifact storage or GCS if running in the cloud.
