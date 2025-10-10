import os
import requests
import concurrent.futures
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from google.cloud import storage
from google.cloud import bigquery
from google.api_core.exceptions import NotFound

# Load environment variables
load_dotenv()

# ===========================
# --- Configuration & Env ---
# ===========================
PHYSNA_API_BASE_URL = "https://app-api.physna.com/v3"
PHYSNA_AUTH_URL = os.getenv("AUTH_URL")
PHYSNA_TENANT_ID = os.getenv("PHYSNA_TENANT_ID")
PHYSNA_CLIENT_ID = os.getenv("PHYSNA_CLIENT_ID")
PHYSNA_CLIENT_SECRET = os.getenv("PHYSNA_CLIENT_SECRET")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GCS_THUMBNAIL_FOLDER = os.getenv("GCS_THUMBNAIL_FOLDER", "physna_thumbnails/")

# BigQuery details
BQ_PROJECT_ID = os.getenv("BQ_PROJECT_ID")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID")
BQ_METADATA_TABLE = os.getenv("BQ_METADATA_TABLE")

# Flags & Limits
ENABLE_FETCH_ASSETS = True
ENABLE_PROCESS_THUMBNAILS = True
ENABLE_BQ_INIT_LOAD = True
ASSET_LIMIT = 0 # Set to 0 for all, or integer for limit

# Threading Config
MAX_WORKERS = 20 # Number of parallel threads for GCS upload

TARGET_FOLDERS = [
    "E1_tkv708_Chevy_Equinox_unique_parts",
    "E2_tkv250_Cadillac_Optiq_unique_parts",
    "E3_tkv601_Cadillac_Vistiq_unique_parts"
]

_access_token = None

# ===========================
# --- Helpers (API & BQ) ---
# ===========================
def _get_physna_token() -> str:
    """Retrieves or refreshes the Physna authentication token."""
    global _access_token
    if _access_token: return _access_token
    if not all([PHYSNA_AUTH_URL, PHYSNA_CLIENT_ID, PHYSNA_CLIENT_SECRET]):
        raise ValueError("Missing Physna credentials in .env")
    payload = {"grant_type": "client_credentials", 
               "client_id": PHYSNA_CLIENT_ID, 
               "client_secret": PHYSNA_CLIENT_SECRET}
    # Note: Token fetch is not thread-safe by default, but okay if called once before pool.
    resp = requests.post(PHYSNA_AUTH_URL, data=payload)
    resp.raise_for_status()
    _access_token = resp.json()["access_token"]
    return _access_token

def _get_headers() -> Dict[str, str]:
    """Constructs standard HTTP headers for Physna API requests."""
    token = _get_physna_token()
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

# --- BQ Schema Def & Patcher ---
def _get_full_descriptive_schema() -> List[bigquery.SchemaField]:
    """Defines the FINAL Supply Chain Demo Schema."""
    return [
        bigquery.SchemaField("part_id", "STRING", mode="REQUIRED", description="Primary Key. Physna Asset ID."),
        bigquery.SchemaField("part_name", "STRING", mode="NULLABLE", description="Engineering name from filename."),
        bigquery.SchemaField("physna_folder_name", "STRING", mode="NULLABLE", description="Physna folder (Vehicle Context)."),
        bigquery.SchemaField("physna_path", "STRING", mode="NULLABLE", description="Full Physna file path."),
        bigquery.SchemaField("gcs_image_path", "STRING", mode="NULLABLE", description="gs:// URI to 2D image."),
        # --- Enriched Data ---
        bigquery.SchemaField("detailed_part_description", "STRING", mode="NULLABLE", description="AI-generated description."),
        bigquery.SchemaField("material", "STRING", mode="NULLABLE", description="Primary material."),
        bigquery.SchemaField("finish", "STRING", mode="NULLABLE", description="Surface finish."),
        bigquery.SchemaField("weight_kg", "FLOAT64", mode="NULLABLE", description="Weight in kg."),
        bigquery.SchemaField("revision_number", "INT64", mode="NULLABLE", description="Design revision."),
        bigquery.SchemaField("engineering_notes", "STRING", mode="NULLABLE", description="Contextual notes."),
        bigquery.SchemaField("source_vehicle_platform", "STRING", mode="NULLABLE", description="Vehicle platform."),
        bigquery.SchemaField("annual_demand_units", "INT64", mode="NULLABLE", description="Forecasted units/year."),
        bigquery.SchemaField("primary_supplier_name", "STRING", mode="NULLABLE", description="Main vendor name."),
        bigquery.SchemaField("supplier_id", "STRING", mode="NULLABLE", description="Supplier ID."),
        bigquery.SchemaField("cost_per_unit_usd", "FLOAT64", mode="NULLABLE", description="Unit cost in USD."),
        bigquery.SchemaField("lead_time_weeks", "INT64", mode="NULLABLE", description="Lead time in weeks."),
        bigquery.SchemaField("country_of_origin", "STRING", mode="NULLABLE", description="Manufacturing country."),
        bigquery.SchemaField("supplier_risk_rating", "STRING", mode="NULLABLE", description="Risk rating (Low/Med/High)."),
        bigquery.SchemaField("current_inventory_on_hand", "INT64", mode="NULLABLE", description="Units in inventory."),
    ]

def _patch_table_schema_descriptions(bq_client: bigquery.Client, table_ref: bigquery.TableReference):
    """Force updates the table schema specifically to apply descriptions."""
    print("Patching table with schema descriptions...")
    try:
        table = bq_client.get_table(table_ref)
        table.schema = _get_full_descriptive_schema()
        bq_client.update_table(table, ["schema"])
        print("Schema descriptions applied successfully.")
    except Exception as e:
        print(f"Failed to patch schema descriptions: {e}")

# ===========================
# --- Core Functionality ---
# ===========================
def fetch_and_filter_assets(limit: int = ASSET_LIMIT) -> List[Dict[str, Any]]:
    """Fetches and filters assets from Physna API sequentially."""
    print(f"Starting asset fetch. Limit: {'All' if limit == 0 else limit}...")
    url = f"{PHYSNA_API_BASE_URL}/tenants/{PHYSNA_TENANT_ID}/assets"
    # Ensure token is fetched once before threading starts if needed later
    headers = _get_headers() 
    filtered_assets = []
    page = 1; per_page = 50 # Fetch in larger batches for efficiency
    
    while True:
        try:
            resp = requests.get(url, headers=headers, params={"page": page, "perPage": per_page})
            resp.raise_for_status()
            data = resp.json()
            assets = data.get("assets", [])
            if not assets: break 
            
            for asset in assets:
                asset_path = asset.get("path", "")
                if any(folder in asset_path for folder in TARGET_FOLDERS):
                    filtered_assets.append({
                        "part_id": asset.get("id"),
                        "part_name": os.path.basename(asset_path) if asset_path else "Unknown",
                        "physna_folder_name": os.path.dirname(asset_path),
                        "physna_path": asset_path,
                        "gcs_image_path": None # Will be filled by thread pool
                    })
                    if limit > 0 and len(filtered_assets) >= limit: 
                        print(f"Found {len(filtered_assets)} matching assets (Limit reached).")
                        return filtered_assets
            
            page_data = data.get("pageData", {})
            print(f"Fetched page {page}/{page_data.get('lastPage', '?')}. Found {len(filtered_assets)} matches so far.")
            if page >= page_data.get("lastPage", page): break
            page += 1
            
        except Exception as e:
            print(f"Error fetching assets on page {page}: {e}"); break
            
    print(f"Total found: {len(filtered_assets)} matching assets.")
    return filtered_assets

# --- Threaded Task ---
def _process_single_thumbnail(asset: Dict[str, Any], bucket: storage.Bucket, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Worker function to process one asset's thumbnail."""
    asset_id = asset["part_id"]
    thumb_url = f"{PHYSNA_API_BASE_URL}/tenants/{PHYSNA_TENANT_ID}/assets/{asset_id}/thumbnail.png"
    gcs_filename = f"{GCS_THUMBNAIL_FOLDER.strip('/')}/{asset_id}.png"
    
    try:
        # Create a new session per thread/request for best practice
        with requests.Session() as session:
            img_resp = session.get(thumb_url, headers=headers, stream=True, timeout=30)
            
            if img_resp.status_code == 200:
                # Upload to GCS (Storage client is thread-safe)
                blob = bucket.blob(gcs_filename)
                blob.upload_from_file(img_resp.raw, content_type="image/png")
                
                # Update asset and return it
                asset["gcs_image_path"] = f"gs://{bucket.name}/{gcs_filename}"
                print(f"  [OK] {asset['gcs_image_path']}")
                return asset
            else:
                print(f"  [SKIP] {asset_id} - No thumb (Status {img_resp.status_code})")
                return None
    except Exception as e:
        print(f"  [ERROR] {asset_id}: {e}")
        return None

def process_thumbnails_to_gcs_threaded(assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Orchestrates the parallel downloading and uploading of thumbnails.
    """
    if not GCS_BUCKET_NAME: raise ValueError("GCS_BUCKET_NAME missing")
    if not assets: return []

    print(f"Starting threaded thumbnail processing ({MAX_WORKERS} workers) for {len(assets)} assets...")
    
    # Initialize GCS client (thread-safe) and get headers once
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    headers = _get_headers() 
    
    processed_assets = []
    
    # Use ThreadPoolExecutor for I/O bound tasks
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_asset = {
            executor.submit(_process_single_thumbnail, asset, bucket, headers): asset 
            for asset in assets
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_asset):
            result_asset = future.result()
            if result_asset and result_asset.get("gcs_image_path"):
                processed_assets.append(result_asset)

    print(f"Finished. Successfully uploaded {len(processed_assets)}/{len(assets)} thumbnails.")
    # Update original list objects with the results (optional, but keeps state consistent)
    for p_asset in processed_assets:
        for o_asset in assets:
            if o_asset['part_id'] == p_asset['part_id']:
                o_asset['gcs_image_path'] = p_asset['gcs_image_path']
                
    return assets

def setup_bq_and_load_basic(assets: List[Dict[str, Any]]):
    """Loads foundation data into BigQuery and applies the descriptive schema."""
    if not all([BQ_PROJECT_ID, BQ_DATASET_ID, BQ_METADATA_TABLE]):
         print("Missing BQ details. Skipping.")
         return

    bq_client = bigquery.Client(project=BQ_PROJECT_ID)
    dataset_ref = bigquery.DatasetReference(BQ_PROJECT_ID, BQ_DATASET_ID)
    table_ref = dataset_ref.table(BQ_METADATA_TABLE)

    # Filter for assets that actually have images uploaded
    rows_to_insert = [
        {
            "part_id": a["part_id"],
            "part_name": a["part_name"],
            "physna_folder_name": a["physna_folder_name"],
            "physna_path": a["physna_path"],
            "gcs_image_path": a["gcs_image_path"]
        }
        for a in assets if a.get("gcs_image_path")
    ]
    
    if not rows_to_insert:
        print("No data with images to load into BigQuery.")
        return

    print(f"Loading {len(rows_to_insert)} rows (WRITE_TRUNCATE) into BigQuery...")
    
    # Minimal schema for load
    load_schema = [
        bigquery.SchemaField("part_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("part_name", "STRING"),
        bigquery.SchemaField("physna_folder_name", "STRING"),
        bigquery.SchemaField("physna_path", "STRING"),
        bigquery.SchemaField("gcs_image_path", "STRING"),
    ]

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=load_schema, 
        autodetect=False 
    )
    
    try:
        job = bq_client.load_table_from_json(rows_to_insert, table_ref, job_config=job_config)
        job.result()
        print("Data loaded successfully.")
        _patch_table_schema_descriptions(bq_client, table_ref)
        print("BigQuery Schema updated. Refresh UI.")
    except Exception as e:
        print(f"BigQuery Load/Patch failed: {e}")

# ===========================
# --- Main ---
# ===========================
def run_ingest_pipeline():
    """Orchestrates the Fetch -> Threaded GCS -> BigQuery Ingest pipeline."""
    print("=== Starting Ingest Pipeline ===")
    assets = []
    if ENABLE_FETCH_ASSETS: 
        assets = fetch_and_filter_assets(ASSET_LIMIT)
        
    if not assets:
        print("No assets to process.")
        return

    if ENABLE_PROCESS_THUMBNAILS: 
        # Use the new threaded function
        assets = process_thumbnails_to_gcs_threaded(assets)
        
    if ENABLE_BQ_INIT_LOAD: 
        setup_bq_and_load_basic(assets)
        
    print("=== Ingest Finished ===")

if __name__ == "__main__":
    run_ingest_pipeline()