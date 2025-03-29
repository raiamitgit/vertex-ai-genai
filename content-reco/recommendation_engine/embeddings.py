"""
Functions for generating text embeddings using the Google Cloud Vertex AI API.
Handles batching and exponential backoff for robustness.
"""
import os
import time
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

def generate_embeddings(publisher, model_name, max_retries, batch_size, texts):
    """Generates embeddings using Vertex AI API."""
    if not PROJECT_ID or not LOCATION:
        raise ValueError("PROJECT_ID and LOCATION must be set in the .env file.")

    client = aiplatform.gapic.PredictionServiceClient(
        client_options={"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
    )
    instances = []
    for text in texts:
        instance = json_format.ParseDict(
            {"content": text},
            Value(),
        )
        instances.append(instance)

    parameters_dict = {}
    parameters = json_format.ParseDict(parameters_dict, Value())
    endpoint = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/{publisher}/models/{model_name}"

    embeddings = []
    for i in range(0, len(instances), batch_size):
        batch = instances[i:i + batch_size]
        retries = 0
        success = False
        while not success and retries < max_retries:
            try:
                response = client.predict(
                    endpoint=endpoint,
                    instances=batch,
                    parameters=parameters,
                )
                for prediction_ in response.predictions:
                    embedding_value = prediction_.get("embeddings", {}).get("values")
                    if embedding_value:
                        embeddings.append(embedding_value)
                success = True
            except Exception as e:
                retries += 1
                print(f"Error generating embeddings (attempt {retries}/{max_retries}): {e}")
                time.sleep(2**retries) # Exponential backoff
        if not success:
            print(f"Failed to get embeddings for batch after {max_retries} retries.")

    return embeddings