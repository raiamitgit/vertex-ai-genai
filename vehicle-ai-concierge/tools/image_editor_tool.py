import requests
import uuid
import datetime
import os
from dotenv import load_dotenv
from helpers import gemini_helper
from google.cloud import storage
from typing import Dict

# Load environment variables
load_dotenv()

# --- GCS Configuration ---
# Read configuration from environment variables
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
DESTINATION_FOLDER = os.getenv("GCS_DESTINATION_FOLDER")
storage_client = storage.Client()

def edit_image(image_url: str, edit_instruction: str) -> Dict[str, str]:
    """
    Downloads an image, edits it using Gemini, uploads it to GCS,
    and returns the public URL.

    Args:
        image_url: The public URL of the image to edit.
        edit_instruction: The text prompt describing the desired edit.

    Returns:
        A dictionary containing the status and either the public GCS URL
        of the edited image or an error message.
    """
    if not BUCKET_NAME or not DESTINATION_FOLDER:
        return {"status": "error", "message": "GCS bucket name or folder is not configured in the environment."}

    print(f"Attempting to download image from: {image_url}")
    try:
        # Download the image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        image_bytes = response.content
        mime_type = response.headers.get('Content-Type')

        if not mime_type or not mime_type.startswith('image/'):
            return {"status": "error", "message": f"Invalid content type '{mime_type}'."}

        print("Image downloaded. Sending to Gemini for editing...")
        # Call the helper to perform the edit
        edited_image_bytes = gemini_helper.edit_image_from_bytes(
            image_bytes=image_bytes, mime_type=mime_type, prompt=edit_instruction
        )

        if edited_image_bytes:
            print("Image edited. Uploading to GCS...")
            
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
            
            # REMOVED: blob.make_public() - This line caused the error with
            # uniform bucket-level access and is not needed for authenticated local testing.
            
            print(f"Upload successful. Public URL: {blob.public_url}")
            return {
                "status": "success",
                "image_url": blob.public_url,
                "message": "Image successfully edited and uploaded."
            }
        else:
            return {"status": "error", "message": "Failed to edit image; model did not return data."}

    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to download image: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}

if __name__ == '__main__':
    print("--- Testing Image Editor Tool with GCS Upload ---")
    test_url = "https://images.pexels.com/photos/112460/pexels-photo-112460.jpeg"
    test_prompt = "Change the car's color to a metallic, deep blue."

    print(f"\nTesting with URL: {test_url}")
    print(f"Prompt: '{test_prompt}'")

    result = edit_image(test_url, test_prompt)

    if result["status"] == "success":
        print(f"\nSuccess: {result['message']}")
        print(f"Returned URL: {result['image_url']}")
    else:
        print(f"\nError: {result['message']}")

