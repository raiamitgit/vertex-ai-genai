# ADK & Gemini Enterprise File Integration Patterns

This project demonstrates various patterns for integrating files with Google Cloud ADK (Agent Development Kit) and Gemini Enterprise. It showcases how to handle different file types and extend agent capabilities with custom tools.

## Key Goal
The primary goal of this project is to showcase different file integration patterns with ADK and Gemini Enterprise, proving that ADK can be adapted to process almost any file type through callbacks, tools, and custom execution environments.

## Agent Breakdown

### Agent 1: Basic Document Processing
- **Key Goal**: Demonstrate basic file processing patterns and strict guardrails.
- **Pattern**: Uses the built-in `load_artifacts_tool` to read PDF and CSV files.
- **Highlights**: Enforces a file-centric focus where the agent refuses to answer questions unless a file is provided.

### Agent 2: ZIP File Interception
- **Key Goal**: Showcase how to process arbitrary or unsupported file types.
- **Pattern**: Uses a `before_model_callback` to intercept files, extract contents from zip files in memory, and inject them directly into the conversation prompt.
- **Highlights**: This pattern demonstrates that ADK can handle any arbitrary file format by preprocessing it before it reaches the model. ZIP file handling is one implementation pattern for this agent.

### Agent 3: Artifact & Image Generation
- **Key Goal**: Demonstrate response patterns that generate new files as artifacts.
- **Pattern**: Uses custom tools to generate Word documents (`.docx`) for text responses and rendering images from descriptions. 
- **Highlights**: It uses GCSArtifactService for connecting the generated output to Gemini Enterprise.

### Agent 4: Custom Code Execution
- **Key Goal**: Use Code Execution for processing structured data
- **Pattern**: Uses a custom `execute_python_code` tool leveraging ADK's `UnsafeLocalCodeExecutor`.
- **Highlights**: Bypasses conflicts caused by native Gemini code execution tools by handling execution in an isolated local process, specifically tailored for CSV and JSON data analysis.

## Running the Agents
Each agent folder contains its own `agent.py` and can be run locally using the ADK runner or deployed to the cloud using standard deployment scripts.
