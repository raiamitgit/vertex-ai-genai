# Agent 3: Artifact & Image Generation for Gemini Enterprise

## Key Goal
The key goal of this agent is to demonstrate how to process input data and return enriched documents to Gemini Enterprise. It also showcases how to render images and infographics directly within the Gemini Enterprise UI, leveraging the GCS Artifact Service for seamless integration.

## Features
- **Document Generation**: Uses a custom tool to generate polished Word documents (`.docx`) containing reports, summaries, or structured answers.
- **Image Rendering in Gemini Enterprise**: Uses `gemini-3.1-flash-image-preview` to generate visual content like charts or infographics based on text descriptions, demonstrating multimodal output capabilities.
- **GCS Artifact Service Integration**: Connects the generated outputs to Gemini Enterprise by saving them as artifacts in Google Cloud Storage, ensuring they are accessible and rendered correctly in the UI.
- **Response Enforcement**: Strict system instructions force the agent to answer *only* by creating a document or generating an image, rather than returning raw chat text, making it ideal for report generation workflows.

## How to Run
Run the `agent.py` file. Note that image generation requires specific model access and region settings (typically `global`). Ensure that the environment variables for GCS are properly configured.
