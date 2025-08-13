# File: helpers/gemini_helper.py
# Description: A reusable helper module for interacting with the Gemini API.

import os
import uuid
import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.cloud import storage # Import the GCS client
import base64
import requests

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
PROJECT_ID = os.getenv("VERTEX_AI_PROJECT_ID")
LOCATION = os.getenv("VERTEX_AI_LOCATION")
TEXT_MODEL_NAME = os.getenv("GEMINI_MODEL")
IMAGE_MODEL_NAME = "gemini-2.0-flash-preview-image-generation"

# --- Initialize Clients ---
genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
storage_client = storage.Client(project=PROJECT_ID)

def generate_text(prompt: str, google_search=False) -> str:
    """
    Generates text using the configured Gemini text model.
    """
    try:
        part = types.Part.from_text(text=prompt)
        contents = [types.Content(role="user", parts=[part])]
        tools = [types.Tool(google_search=types.GoogleSearch())] if google_search else []
        config = types.GenerateContentConfig(temperature=1, top_p=0.95, max_output_tokens=8192, tools=tools)
        response = genai_client.models.generate_content(model=f"{TEXT_MODEL_NAME}", contents=contents, config=config)
        return response.text.strip()
    except Exception as e:
        print(f"An error occurred during Gemini text generation: {e}")
        return ""

def edit_image_from_bytes(image_bytes: bytes, mime_type: str, prompt: str) -> bytes:
    """
    Edits an image using the Gemini image model.
    """
    try:
        image_part = types.Part(inline_data=types.Blob(mime_type=mime_type, data=image_bytes))
        text_part = types.Part.from_text(text=prompt)
        contents = [types.Content(role="user", parts=[image_part, text_part])]
        config = types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])
        response = genai_client.models.generate_content(model=f"{IMAGE_MODEL_NAME}", contents=contents, config=config)
        
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
        
        print("No image content found in the response.")
        return None
    except Exception as e:
        print(f"An error occurred during Gemini image editing: {e}")
        return None

if __name__ == '__main__':
    print("--- Testing gemini_helper.py ---")
    
    # --- Testing Image Editing with GCS Upload ---
    print("\n--- Testing Image Editing ---")
    test_image_url = "https://images.pexels.com/photos/112460/pexels-photo-112460.jpeg"
    test_edit_prompt = "Change the color of the car to a vibrant, glossy red."
    
    # GCS Configuration from environment
    BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
    DESTINATION_FOLDER = os.getenv("GCS_DESTINATION_FOLDER")

    if not BUCKET_NAME or not DESTINATION_FOLDER:
        print("GCS_BUCKET_NAME and GCS_DESTINATION_FOLDER must be set in .env file for this test.")
    else:
        print(f"Downloading image from: {test_image_url}")
        print(f"Edit instruction: '{test_edit_prompt}'")
        
        try:
            response = requests.get(test_image_url)
            response.raise_for_status()
            
            image_bytes = response.content
            mime_type = response.headers.get('Content-Type', 'image/jpeg')
            
            edited_image_bytes = edit_image_from_bytes(image_bytes, mime_type, test_edit_prompt)
            
            if edited_image_bytes:
                print("\nImage edited successfully. Uploading to GCS...")
                
                # Generate a unique filename
                timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                unique_id = uuid.uuid4().hex[:6]
                file_extension = mime_type.split('/')[-1]
                unique_filename = f"edited_image_{timestamp}_{unique_id}.{file_extension}"
                destination_blob_name = f"{DESTINATION_FOLDER}{unique_filename}"
                
                # Get the bucket and upload the file
                bucket = storage_client.bucket(BUCKET_NAME)
                blob = bucket.blob(destination_blob_name)
                blob.upload_from_string(edited_image_bytes, content_type=mime_type)
                blob.make_public()
                
                print(f"Successfully uploaded image to GCS.")
                print(f"Public URL: {blob.public_url}")
            else:
                print("\nImage editing failed.")
                
        except Exception as e:
            print(f"An error occurred during the test: {e}")
