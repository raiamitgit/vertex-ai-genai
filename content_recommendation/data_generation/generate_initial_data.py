"""
Generates initial synthetic user and media metadata, loads it into BigQuery,
and optionally triggers AI content generation.

Steps:
1. Generate basic user and media metadata in memory.
2. Write metadata to temporary local NDJSON files.
3. Ensure the target BigQuery dataset exists.
4. Load NDJSON files into BigQuery tables (WRITE_TRUNCATE, auto-schema).
5. Clean up temporary files.
6. If --generate-ai-content flag is set, call the AI content generation script.
"""
import os
import sys
import yaml
import json
import tempfile
import argparse
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import bigquery
from typing import List, Dict, Any

# --- Import project modules ---
from data_generation.synthetic_data_generators import (
    generate_user_basic,
    generate_article_metadata,
    generate_video_metadata
)
from data_generation.populate_generated_content import run_ai_content_generation
from utils.bigquery_utils import (
    get_bigquery_client,
    create_dataset,
    load_ndjson_from_file,
)

# --- Setup Project Root Path ---
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
except NameError:
    PROJECT_ROOT = os.getcwd()
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)

# --- Argument Parsing ---
parser = argparse.ArgumentParser(
    description="Generate initial synthetic data, load to BigQuery, "
                "and optionally generate AI content."
)
parser.add_argument(
    "--generate-ai-content",
    action="store_true",
    help="If set, run BQML queries to generate AI content after loading initial data."
)
args = parser.parse_args()

# --- Config and Env Loading ---
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
config_path = os.path.join(PROJECT_ROOT, 'config.yaml')

load_dotenv(dotenv_path=dotenv_path)
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

if not PROJECT_ID:
    print("FATAL ERROR: GCP PROJECT_ID environment variable is not set.")
    sys.exit(1)

try:
    print(f"Loading configuration from: {config_path}")
    with open(config_path, "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)
except Exception as e:
    print(f"FATAL ERROR loading config.yaml: {e}")
    sys.exit(1)

# --- Validate and Extract Config ---
try:
    BQ_CONFIG = config['bigquery']
    DATA_GEN_CONFIG = config['data_generation']
    DATASET_NAME = BQ_CONFIG['dataset_name']
    USERS_TABLE_NAME = BQ_CONFIG['users_table_name']
    MEDIA_TABLE_NAME = BQ_CONFIG['media_table_name']
    NUM_USERS = int(DATA_GEN_CONFIG['num_users'])
    NUM_ARTICLES = int(DATA_GEN_CONFIG['num_articles'])
    NUM_VIDEOS = int(DATA_GEN_CONFIG['num_videos'])
except (KeyError, ValueError, TypeError) as e:
    print(f"FATAL ERROR: Missing/invalid required key in config.yaml: {e}")
    sys.exit(1)

# --- Constants ---
USERS_FILENAME = "users_metadata.ndjson"
MEDIA_FILENAME = "media_metadata.ndjson"

# --- Helper Function ---
def write_ndjson(data_list: List[Dict[str, Any]], file_path: str) -> bool:
    """Writes a list of dictionaries to a newline-delimited JSON file.

    Args:
        data_list (List[Dict[str, Any]]): The list of data records (dictionaries).
        file_path (str): The full path to the output NDJSON file.

    Returns:
        bool: True if writing was successful, False otherwise.
    """
    print(f"Writing {len(data_list)} records to {file_path}...")
    record_count = 0
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            for item in data_list:
                if isinstance(item, dict):
                    serializable_item = {}
                    for key, value in item.items():
                        if isinstance(value, datetime):
                            serializable_item[key] = value.isoformat() # Ensure ISO format
                        else:
                            serializable_item[key] = value
                    json.dump(serializable_item, f, ensure_ascii=False)
                    f.write('\n')
                    record_count += 1
                else:
                    print(f"WARN: Skipping non-dict item during NDJSON write: {type(item)}")
        print(f"Successfully wrote {record_count} records.")
        return True
    except IOError as e:
        print(f"ERROR: Failed to write NDJSON file {file_path}: {e}")
        return False
    except TypeError as e:
        print(f"ERROR: JSON serialization failed for {file_path}: {e}")
        return False

# --- Main Execution Function ---
def run_initial_metadata_load(generate_ai: bool):
    """
    Orchestrates metadata generation, NDJSON writing, and BigQuery loading.

    Args:
        generate_ai (bool): Flag indicating whether to trigger AI content
                            generation after loading initial data.
    """
    print("--- Starting Initial Metadata Generation and Loading ---")

    bq_client = get_bigquery_client(PROJECT_ID)
    if not bq_client:
        sys.exit(1)

    dataset_ref = bq_client.dataset(DATASET_NAME)
    users_table_ref = dataset_ref.table(USERS_TABLE_NAME)
    media_table_ref = dataset_ref.table(MEDIA_TABLE_NAME)

    print("\n--- Ensuring BigQuery Dataset Exists ---")
    if not create_dataset(bq_client, dataset_ref, LOCATION):
        print(f"ERROR: Failed to create/verify dataset {DATASET_NAME}. Exiting.")
        sys.exit(1)

    print(f"\n--- Generating {NUM_USERS} User Records (Metadata Only) ---")
    users_metadata = [generate_user_basic(i + 1, config) for i in range(NUM_USERS)]
    users_metadata = [u for u in users_metadata if u is not None]
    print(f"Generated {len(users_metadata)} valid user metadata records.")

    print(f"--- Generating {NUM_ARTICLES} Article + {NUM_VIDEOS} Video Records (Metadata Only) ---")
    articles_metadata = [generate_article_metadata(i + 1, config) for i in range(NUM_ARTICLES)]
    videos_metadata = [generate_video_metadata(i + 1, config) for i in range(NUM_VIDEOS)]
    all_media_metadata = [m for m in articles_metadata + videos_metadata if m is not None]
    print(f"Generated {len(all_media_metadata)} valid media metadata records.")

    if not users_metadata or not all_media_metadata:
        print("ERROR: Failed to generate sufficient user or media metadata. Exiting.")
        sys.exit(1)

    initial_load_successful = False
    with tempfile.TemporaryDirectory(prefix="synth_data_") as temp_dir:
        users_file_path = os.path.join(temp_dir, USERS_FILENAME)
        media_file_path = os.path.join(temp_dir, MEDIA_FILENAME)
        print(f"\n--- Writing Data to Temporary Files in: {temp_dir} ---")

        if not write_ndjson(users_metadata, users_file_path):
            print("ERROR writing user NDJSON file. Exiting.")
            sys.exit(1)

        if not write_ndjson(all_media_metadata, media_file_path):
            print("ERROR writing media NDJSON file. Exiting.")
            sys.exit(1)

        print("\n--- Loading Data from NDJSON Files into BigQuery ---")

        print(f"Loading users into {users_table_ref.path}...")
        load_success_users = load_ndjson_from_file(
            client=bq_client,
            local_file_path=users_file_path,
            table_ref=users_table_ref,
        )

        print(f"Loading media into {media_table_ref.path}...")
        load_success_media = load_ndjson_from_file(
            client=bq_client,
            local_file_path=media_file_path,
            table_ref=media_table_ref,
        )

        if not load_success_users or not load_success_media:
            print("ERROR: Data loading failed for one or more tables.")
        else:
             initial_load_successful = True

    # Temp directory cleaned up here

    if initial_load_successful:
        print("\n--- Initial Metadata Loading Complete ---")
        print(f"User data loaded into: {PROJECT_ID}.{DATASET_NAME}.{USERS_TABLE_NAME}")
        print(f"Media data loaded into: {PROJECT_ID}.{DATASET_NAME}.{MEDIA_TABLE_NAME}")

        if generate_ai:
            print("\n--- Triggering AI Content Generation (--generate-ai-content set) ---")
            run_ai_content_generation(bq_client, config)
        else:
            print("\n--- Skipping AI Content Generation (--generate-ai-content not set) ---")
            print("Next step: Run populate_generated_content.py separately or re-run with the flag.")
    else:
         print("\n--- Initial Metadata Loading FAILED ---")
         print("Skipping AI content generation due to loading errors.")


# --- Script Entry Point ---
if __name__ == "__main__":
    run_initial_metadata_load(generate_ai=args.generate_ai_content)
