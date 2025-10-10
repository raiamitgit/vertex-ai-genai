import os
import mimetypes
import requests
import urllib.parse
import json
import base64
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from google.cloud import bigquery

import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel

load_dotenv()

# Configuration
API_BASE_URL = "https://app-api.physna.com/v3"
WEB_BASE_URL = "https://app.physna.com"

# Load critical config from env
AUTH_URL = os.getenv("AUTH_URL")
TENANT_ID = os.getenv("PHYSNA_TENANT_ID")
CLIENT_ID = os.getenv("PHYSNA_CLIENT_ID")
CLIENT_SECRET = os.getenv("PHYSNA_CLIENT_SECRET")

# BigQuery Config for Workaround
BQ_PROJECT_ID = os.getenv("BQ_PROJECT_ID")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID")
BQ_METADATA_TABLE = os.getenv("BQ_METADATA_TABLE")
BQ_EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "multimodalembedding@001") 
GCP_REGION = os.getenv("GCP_REGION", "us-central1") # Default if not set

# Flags
USE_BQ_VECTOR_SEARCH = True

# ===========================
# --- Internal Helpers ---
# ===========================

def _validate_config():
    """Checks for required environment variables."""
    if not all([AUTH_URL, TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        raise ValueError("Missing required PHYSNA_ env variables (TENANT_ID, CLIENT_ID, or CLIENT_SECRET).")

def _get_access_token() -> str:
    """Retrieves the Cognito access token."""
    _validate_config()
    
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    try:
        token_resp = requests.post(AUTH_URL, data=data)
        token_resp.raise_for_status()
        return token_resp.json()["access_token"]
    except Exception as e:
        raise ConnectionError(f"Physna Authentication failed: {e}")

def _get_headers() -> Dict[str, str]:
    """Gets auth token and returns standard headers."""
    token = _get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "accept": "application/json"
    }

def _generate_asset_web_url(asset_id: str) -> str:
    """Constructs the browser URL for a single asset."""
    return f"{WEB_BASE_URL}/tenants/{TENANT_ID}/asset/{asset_id}"

def _generate_compare_web_url(asset1_id: str, asset2_id: str) -> Optional[str]:
    """Constructs the browser URL to compare two assets."""
    if asset1_id == asset2_id:
        return None
        
    base_path = f"{WEB_BASE_URL}/tenants/{TENANT_ID}/compare"
    params = {
        "asset1Id": asset1_id,
        "asset2Id": asset2_id,
        "tenant1Id": TENANT_ID,
        "tenant2Id": TENANT_ID
    }
    query_string = urllib.parse.urlencode(params)
    return f"{base_path}?{query_string}"

def _get_vertex_embedding(local_image_path: str) -> List[float]:
    """
    Generates an image embedding using Vertex AI Generative AI SDK.
    Ref: https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-multimodal-embeddings#python_1
    """
    print(f"Generating embedding via Vertex AI GenAI SDK for: {local_image_path}", flush=True)
    
    if not all([BQ_PROJECT_ID, GCP_REGION, BQ_EMBEDDING_MODEL_NAME]):
         raise ValueError("Missing GCP config (Project, Region, or Model Name) for Vertex AI.")

    try:
        vertexai.init(project=BQ_PROJECT_ID, location=GCP_REGION)
    
        model_name = BQ_EMBEDDING_MODEL_NAME
        model = MultiModalEmbeddingModel.from_pretrained(model_name)
        source_image = Image.load_from_file(local_image_path)
        embeddings = model.get_embeddings(image=source_image)
        image_vector = embeddings.image_embedding
        
        # Log dimension to ensure it matches DB (usually 1408 for standard multimodal)
        print(f"Generated embedding vector with dimension: {len(image_vector)}", flush=True)
        return image_vector

    except Exception as e:
        print(f"Vertex AI SDK Error: {e}", flush=True)
        raise (f"Vertex AI Embedding generation failed: {e}")

def _bq_image_search(local_image_path: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Hybrid approach: Generate embedding in Python, search in BigQuery.
    """
    if not all([BQ_PROJECT_ID, BQ_DATASET_ID, BQ_METADATA_TABLE]):
        raise ValueError("BigQuery environment variables missing for vector search.")

    print(f"Starting BigQuery Vector Search for: {local_image_path}", flush=True)

    try:
        # This will now have the correct dimensions (e.g., 1408)
        query_vector = _get_vertex_embedding(local_image_path)
    except Exception as e:
        # Return error structure acceptable to agent
        print(f"Embedding generation failed. Aborting search.", flush=True)
        raise e

    client = bigquery.Client(project=BQ_PROJECT_ID)
    full_table_id = f"{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_METADATA_TABLE}"

    query = f"""
        SELECT
            base.part_id,
            base.part_name,
            base.physna_path,
            base.physna_folder_name,
            -- Calculate cosine similarity based on indexed vectors
            (1 - ML.DISTANCE(base.image_embedding, @query_vector, 'COSINE')) as similarity_score
        FROM `{full_table_id}` AS base
        WHERE base.image_embedding IS NOT NULL
        ORDER BY similarity_score DESC
        LIMIT @limit
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("query_vector", "FLOAT64", query_vector),
            bigquery.ScalarQueryParameter("limit", "INT64", max_results)
        ]
    )

    try:
        print("Executing BigQuery Vector Search query...", flush=True)
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        matches = []
        for row in results:
            # Filter noise
            if row.similarity_score < 0.60: continue

            matches.append({
                "asset": {
                    "id": row.part_id,
                    "name": row.part_name,
                    "path": row.physna_path,
                    "metadata": {"folder": row.physna_folder_name}
                },
                "matchPercentage": row.similarity_score * 100 
            })

        print(f"BQ Search completed. Found {len(matches)} matches > 60%.", flush=True)

        return {
            "matches": matches,
            "totalCandidates": len(results),
            "search_method": "vertex_sdk_bq_search"
        }

    except Exception as e:
        print(f"BigQuery Query Failed: {e}", flush=True)
        if "Array inputs are not equal in length" in str(e):
            raise ValueError(f"Dimension mismatch. DB vector len != Query vector len ({len(query_vector)}). Check model versions.")
        raise ConnectionError(f"BigQuery search failed: {e}")

def _physna_image_search(local_image_path: str, max_results: int = 1) -> Dict[str, Any]:
    """Internal helper to perform visual search (upload)."""
    if USE_BQ_VECTOR_SEARCH:
        return _bq_image_search(local_image_path, max_results)

    _validate_config()

    if not os.path.exists(local_image_path):
        raise FileNotFoundError(f"Image not found at: {local_image_path}")

    api_url = f"{API_BASE_URL}/tenants/{TENANT_ID}/assets/visual-search"
    headers = _get_headers()

    mime_type, _ = mimetypes.guess_type(local_image_path)
    if mime_type is None: mime_type = "application/octet-stream"
    filename = os.path.basename(local_image_path)

    payload = {"page": "1", "perPage": str(max_results)}

    print(f"Starting Visual Search for {filename}...")
    try:
        with open(local_image_path, "rb") as f:
            files = {"file": (filename, f, mime_type)}
            resp = requests.post(api_url, headers=headers, files=files, data=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise (f"Physna Visual Search failed: {e}")

def _physna_geometric_part_search(asset_id: str) -> Dict[str, Any]:
    """Internal helper to perform geometric search on an existing asset."""
    _validate_config()
    
    api_url = f"{API_BASE_URL}/tenants/{TENANT_ID}/assets/{asset_id}/geometric-search"
    headers = _get_headers()
    
    payload = {
        "page": 1,
        "perPage": 20,
        "searchQuery": "",
        "filters": {
            "folders": ["E1_tkv708_Chevy_Equinox_unique_parts/",
                        "E2_tkv250_Cadillac_Optiq_unique_parts/", 
                        "E3_tkv601_Cadillac_Vistiq_unique_parts/"],
            "metadata": {},
            "extensions": []
        },
        "minThreshold": 85
    }

    print(f"Starting Part Search for Asset ID: {asset_id}...")
    try:
        resp = requests.post(api_url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 404:
             raise ValueError(f"Physna Asset {asset_id} not found.")
        raise (f"Physna Part Search failed: {e}")

def _process_search_results(source_asset_id: str, raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes raw API results into JSON with URLs, metadata, and match percentage.
    Handles nested {'asset': {...}, 'matchPercentage': ...} structure.
    """
    matches_data = raw_results.get('matches', [])
    processed_matches = []

    for match_item in matches_data:
        # 1. Extract Asset Details (nested under 'asset')
        asset_details = match_item.get('asset', {})
        match_id = asset_details.get('id')
        
        if not match_id: continue

        # 2. Extract Metadata & Score (Ensuring matchPercentage is captured)
        match_percentage = match_item.get('matchPercentage') # Extracted from outer object
        metadata = asset_details.get('metadata', {})
        
        # Determine name from 'name' or 'path'
        name = asset_details.get('name')
        if not name:
            path = asset_details.get('path', '')
            name = os.path.basename(path) if path else 'Unknown Asset'

        # 3 & 4. Generate URLs
        asset_web_url = _generate_asset_web_url(match_id)
        compare_web_url = _generate_compare_web_url(source_asset_id, match_id)

        # 5. Format Result (Including match_percentage in output)
        processed_matches.append({
            "asset_id": match_id,
            "name": name,
            "match_percentage": match_percentage, # Included in final JSON
            "metadata": metadata,
            "urls": {
                "asset_details": asset_web_url,
                "comparison_vs_source": compare_web_url
            }
        })

    return {
        "source_asset_id": source_asset_id,
        "source_asset_url": _generate_asset_web_url(source_asset_id),
        "results_count": len(processed_matches),
        "results": processed_matches
    }

# ===========================
# --- Public Agent Tools ---
# ===========================

def search_parts_by_asset_id(asset_id: str) -> Dict[str, Any]:
    """
    Executes a geometric part search using an existing Physna Asset ID.

    Finds geometrically similar parts within configured folders, extracts metadata
    and match percentage, and generates direct web URLs for the found parts and
    comparison views against the source asset.

    Args:
        asset_id: The unique Physna identifier for the source asset already in the tenant.

    Returns:
        A dictionary containing the source asset details and a list of matched results.
        Each result includes the asset ID, name, match percentage, metadata,
        individual asset URL, and a comparison URL against the source.
    """
    # 1. Execute Search
    raw_results = _physna_geometric_part_search(asset_id)
    
    # 2-5. Extract data (including match %), Generate URLs, and Format Output
    formatted_results = _process_search_results(asset_id, raw_results)
    
    return formatted_results

def search_parts_by_image(local_image_path: str) -> Dict[str, Any]:
    """
    Executes a part search by first uploading a local 2D image (visual search).

    This tool first uploads the image to find the closest matching 3D model in the
    Physna tenant. It then uses that best-match 3D model as the source to perform
    a geometric part search to find similar parts.

    Args:
        local_image_path: The absolute or relative file path to the image (jpg, png) on the local machine.

    Returns:
        A dictionary containing the search results, including context about the
        intermediate asset that was identified from the image.
    """
    # 1. Execute image search (limit to 1 to get best match)
    print(f"Step 1: Finding 3D model from image: {local_image_path}")
    image_results = _physna_image_search(local_image_path, max_results=1)
    
    matches_data = image_results.get('matches', image_results.get('models', []))
    
    if not matches_data:
        return {
            "status": "error",
            "message": "No 3D models found matching the provided image. Cannot proceed with part search."
        }

    # Extract the 1st result as the new source.
    # Handles potential nested 'asset' structure in image search results too.
    first_match = matches_data[0]
    if 'asset' in first_match and isinstance(first_match['asset'], dict):
        source_details = first_match['asset']
    else:
        # Fallback if image search returns flat structure
        source_details = first_match

    source_asset_id = source_details.get('id')
    
    # Determine source name for context
    source_name = source_details.get('name')
    if not source_name:
        path = source_details.get('path', '')
        source_name = os.path.basename(path) if path else 'Unknown Asset'

    if not source_asset_id:
         return {"status": "error", "message": "Could not extract valid Asset ID from image match."}

    print(f"Found source asset from image: {source_name} ({source_asset_id})")

    # 2. Follow steps for asset search using the found ID
    raw_geometric_results = _physna_geometric_part_search(source_asset_id)
    
    # Process and format (includes match percentage extraction)
    formatted_results = _process_search_results(source_asset_id, raw_geometric_results)
    
    # Add context about the image origin
    formatted_results['search_origin'] = {
        "type": "image_upload",
        "input_image": os.path.basename(local_image_path),
        "identified_source_asset": source_name,
        "method": image_results.get('search_method', 'physna_api')
    }
    
    return formatted_results
