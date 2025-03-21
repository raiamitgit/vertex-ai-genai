import os, yaml, json
import mimetypes
import streamlit as st
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.cloud import storage
from google.cloud import aiplatform

# Load environment variables at the beginning
load_dotenv()

# Load config from YAML
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

class ScamAnalyzer:
    def __init__(self):
        """
        Initializes the ScamAnalyzer with project details.
        """
        # Get variables directly from os.environ, with defaults from config.yaml
        self.project_id = os.environ.get("PROJECT_ID")
        self.location = os.environ.get("LOCATION")
        self.bucket_name = os.environ.get("BUCKET_NAME")
        self.folder = os.environ.get("FOLDER_PATH")
        self.primary_prompt = config["PRIMARY_PROMPT"]
        self.model_name = config["MODEL_NAME"]

        # Instantiate vertex_ai client
        self.ai_client = genai.Client(
            vertexai=True,
            project=self.project_id,
            location=self.location,
        )
        self.storage_client = storage.Client()

    def predict_gemini(self, text_input, 
                       image_uri: Optional[str] = None,
                       video_uri: Optional[str] = None) -> Optional[str]:
        """
        Sends a prompt to the Gemini model for prediction.
        """
        system_instruction = config["SYSTEM_INSTRUCTION"]
        print(system_instruction)
        system_instruction=types.Part.from_text(text=system_instruction)

        text_prompt = config[self.primary_prompt].replace("__text_input__", text_input)
        print(text_prompt)
        prompt = types.Part.from_text(text=text_prompt)
        
        parts = [prompt]
        if image_uri:
            image_part = types.Part.from_uri(
                file_uri=image_uri,
                mime_type="image/jpeg"
                )
            parts.append(image_part)
        # if video_uri:
        #     video_part = types.Part.from_uri(
        #         file_uri=video_uri,
        #         mime_type="video/webm",
        #     )
        #     parts.append(video_part)

        contents = [
            types.Content(
            role="user",
            parts=parts
            )
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature = 1,
            top_p = 0.95,
            max_output_tokens = 8192,
            response_modalities = ["TEXT"],
            # response_mime_type = "application/json",
            # response_schema = {"type":"OBJECT","properties":{"response":{"type":"STRING"}}},
            system_instruction=[system_instruction]
        )
        
        try:
            response = ""
            for chunk in self.ai_client.models.generate_content_stream(
                model = self.model_name,
                contents = contents,
                config = generate_content_config,
                ):
                response += chunk.text

            return response

        except Exception as e:
            print(f"Error during Gemini prediction: {e}")
            st.error(f"Error during Gemini prediction: {e}")
            return None


    def upload_to_gcs(self, file, destination_blob_name):
        """
        Uploads a file to Google Cloud Storage.
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_file(file)
            gcs_uri = f"gs://{self.bucket_name}/{destination_blob_name}"
            print(f"File uploaded to {gcs_uri}")
            return gcs_uri
        except Exception as e:
            print(f"Error uploading to GCS: {e}")
            st.error(f"Error uploading to GCS: {e}")
            return None
