# Scam Detection with Gemini
This application utilizes Google's Gemini model to analyze text, images, or videos to identify potential scams. It provides an assessment of whether the input is likely a scam, the potential type of scam, and the reasoning behind the assessment.

## Note
This code is provided for demonstration purposes only. It is intended to showcase the capabilities of the Gemini model for scam detection. It may not be suitable for production environments without further testing, refinement, and hardening. The analysis provided by the model is probabilistic and should not be considered definitive security advice. Always exercise caution and verify information independently.

## Features

* **Scam Analysis:** Analyzes input text, images, or videos to detect scam indicators.
* **Likelihood Score:** Assigns a propensity score (small, medium, high) indicating the likelihood of the input being a scam.
* **Scam Type Identification:** Attempts to categorize the scam type (e.g., phishing, tech support scam) or marks it as "unknown".
* **Reasoning:** Provides an explanation for the scam assessment.
* **Web Interface:** Uses Streamlit to provide a simple user interface for text input or file upload (images/video).
* **Cloud Integration:** Uploads media files to Google Cloud Storage for processing by the Gemini model.

## How it Works

1.  The user inputs text directly or uploads an image/video file through the Streamlit interface.
2.  If a file is uploaded, it is first transferred to a specified Google Cloud Storage bucket.
3.  The application sends the input text and/or the URI of the uploaded file to the Gemini model via the configured API.
4.  Specific prompts guide the Gemini model to look for common scam indicators and structure its response.
5.  The Gemini model analyzes the input and returns a JSON response containing the scam assessment (is\_scam, propensity, scam\_type, reasoning).
6.  The application displays the model's response to the user.

## Setup and Configuration

1.  **Environment Variables:** The application requires environment variables for `PROJECT_ID`, `LOCATION`, `BUCKET_NAME`, and potentially `FOLDER_PATH` for Google Cloud configuration. Ensure these are set (e.g., using a `.env` file).
2.  **Configuration File (`config.yaml`):** This file defines the Gemini model to use (`MODEL_NAME`), the system instructions, and various prompts (`PRIMARY_PROMPT`, `PROMPT_1`, `PROMPT_2`, etc.) used for interacting with the model.
3.  **Dependencies:** Install necessary Python libraries (Streamlit, google-cloud-aiplatform, google-cloud-storage, python-dotenv, PyYAML, google-generativeai).

## Running the Application

Execute the Streamlit application script:
```bash
streamlit run app.py