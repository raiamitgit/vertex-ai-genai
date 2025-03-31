"""
Generates vector embeddings for user summaries and media content using
BigQuery ML ML.GENERATE_EMBEDDING and saves them to new BigQuery tables.

Assumes AI-generated content (profile_summary, main_text) exists in source tables.
Uses CREATE OR REPLACE TABLE to store embedding results.
"""
import os
import sys
import yaml
import argparse
from dotenv import load_dotenv
from google.cloud import bigquery
from typing import Dict, Any, Optional

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

# --- Import project modules ---
from utils.bigquery_utils import get_bigquery_client, execute_bq_query, create_dataset

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="Generate embeddings for users and media content.")
parser.add_argument(
    "--target",
    choices=['users', 'media', 'all'],
    default='all',
    help="Specify whether to generate embeddings for 'users', 'media', or 'all'."
)
args = parser.parse_args()

# --- Config and Env Loading ---
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
config_path = os.path.join(PROJECT_ROOT, 'config.yaml')

load_dotenv(dotenv_path=dotenv_path)
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION") # Needed for dataset check

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
    BQML_CONFIG = config['bqml_models']

    DATASET_NAME = BQ_CONFIG['dataset_name']
    USERS_TABLE_NAME = BQ_CONFIG['users_table_name']
    MEDIA_TABLE_NAME = BQ_CONFIG['media_table_name']
    USER_EMBEDDINGS_TABLE_NAME = BQ_CONFIG['user_embeddings_table_name']
    MEDIA_EMBEDDINGS_TABLE_NAME = BQ_CONFIG['media_embeddings_table_name']
    EMBEDDING_MODEL_NAME = BQML_CONFIG['text_embedder']

except KeyError as e:
    print(f"FATAL ERROR: Missing required key in config.yaml: {e}")
    sys.exit(1)

# Construct full table/model IDs
DATASET_ID = f"{PROJECT_ID}.{DATASET_NAME}"
USERS_TABLE_ID = f"{DATASET_ID}.{USERS_TABLE_NAME}"
MEDIA_TABLE_ID = f"{DATASET_ID}.{MEDIA_TABLE_NAME}"
USER_EMBEDDINGS_TABLE_ID = f"{DATASET_ID}.{USER_EMBEDDINGS_TABLE_NAME}"
MEDIA_EMBEDDINGS_TABLE_ID = f"{DATASET_ID}.{MEDIA_EMBEDDINGS_TABLE_NAME}"
EMBEDDING_MODEL_ID = f"`{PROJECT_ID}.{EMBEDDING_MODEL_NAME}`" # Assumes model in same project


# --- Embedding Generation Functions ---

def generate_user_embeddings(client: bigquery.Client) -> bool:
    """Generates user profile embeddings using BQML and saves to user_embeddings table.

    Args:
        client (bigquery.Client): Authenticated BigQuery client.

    Returns:
        bool: True if the BQML job completes successfully, False otherwise.
    """
    print(f"\n--- Starting User Embedding Generation ---")
    print(f"Source Table: {USERS_TABLE_ID} (Column: profile_summary)")
    print(f"Target Table: {USER_EMBEDDINGS_TABLE_ID}")
    print(f"Using Model: {EMBEDDING_MODEL_ID}")

    # CREATE OR REPLACE TABLE using ML.GENERATE_EMBEDDING
    # Assumes the BQML function output column is named 'ml_generate_embedding_result'
    # and contains the embedding vector directly. Adjust if schema differs.
    sql = f"""
    CREATE OR REPLACE TABLE `{USER_EMBEDDINGS_TABLE_ID}`
    OPTIONS(description="Embeddings generated from user profile summaries")
    AS
    SELECT
        user_id,
        content, -- The input text
        ml_generate_embedding_result AS embedding, -- The output vector
        CURRENT_TIMESTAMP() as processing_timestamp
    FROM
        ML.GENERATE_EMBEDDING(
            MODEL {EMBEDDING_MODEL_ID},
            (
                SELECT
                    user_id,
                    profile_summary AS content -- Input column aliased as 'content'
                FROM `{USERS_TABLE_ID}`
                WHERE profile_summary IS NOT NULL AND LENGTH(profile_summary) > 0
            ),
            STRUCT('SEMANTIC_SIMILARITY' as task_type) -- Specify task type if needed by model
            -- Add output_dimensionality if required/supported: , 256 AS output_dimensionality
        );
    """

    job_result = execute_bq_query(
        client,
        sql,
        description=f"Generating user embeddings into {USER_EMBEDDINGS_TABLE_NAME}"
    )

    if job_result is not None:
        print(f"User embedding generation job completed successfully.")
        return True
    else:
        print(f"ERROR: User embedding generation job failed.")
        return False


def generate_media_embeddings(client: bigquery.Client) -> bool:
    """Generates media content embeddings using BQML and saves to media_embeddings table.

    Args:
        client (bigquery.Client): Authenticated BigQuery client.

    Returns:
        bool: True if the BQML job completes successfully, False otherwise.
    """
    print(f"\n--- Starting Media Embedding Generation ---")
    print(f"Source Table: {MEDIA_TABLE_ID} (Column: main_text)")
    print(f"Target Table: {MEDIA_EMBEDDINGS_TABLE_ID}")
    print(f"Using Model: {EMBEDDING_MODEL_ID}")

    # CREATE OR REPLACE TABLE using ML.GENERATE_EMBEDDING
    # Assumes the BQML function output column is named 'ml_generate_embedding_result'
    sql = f"""
    CREATE OR REPLACE TABLE `{MEDIA_EMBEDDINGS_TABLE_ID}`
    OPTIONS(description="Embeddings generated from media main text (articles/transcripts)")
    AS
    SELECT
        media_id,
        content, -- The input text
        ml_generate_embedding_result AS embedding, -- The output vector
        CURRENT_TIMESTAMP() as processing_timestamp
    FROM
        ML.GENERATE_EMBEDDING(
            MODEL {EMBEDDING_MODEL_ID},
            (
                SELECT
                    media_id,
                    main_text AS content -- Input column aliased as 'content'
                FROM `{MEDIA_TABLE_ID}`
                WHERE main_text IS NOT NULL AND LENGTH(main_text) > 0
            ),
            STRUCT('SEMANTIC_SIMILARITY' as task_type) -- Specify task type
            -- Add output_dimensionality if required/supported: , 256 AS output_dimensionality
        );
    """

    job_result = execute_bq_query(
        client,
        sql,
        description=f"Generating media embeddings into {MEDIA_EMBEDDINGS_TABLE_NAME}"
    )

    if job_result is not None:
        print(f"Media embedding generation job completed successfully.")
        return True
    else:
        print(f"ERROR: Media embedding generation job failed.")
        return False


# --- Main Execution ---
if __name__ == "__main__":
    print("--- Starting Embedding Generation Script ---")

    bq_client = get_bigquery_client(PROJECT_ID)
    if not bq_client:
        print("Exiting script due to BigQuery client initialization failure.")
        sys.exit(1)

    print(f"Ensuring dataset {DATASET_NAME} exists...")
    dataset_ref = bq_client.dataset(DATASET_NAME)
    if not create_dataset(bq_client, dataset_ref, LOCATION):
        print(f"ERROR: Failed to create/verify dataset {DATASET_NAME}. Exiting.")
        sys.exit(1)

    # --- Execute Generation Steps based on --target flag ---
    success = True
    if args.target in ['users', 'all']:
        if not generate_user_embeddings(bq_client):
            success = False

    if args.target in ['media', 'all']:
        if not generate_media_embeddings(bq_client):
            success = False

    if success:
        print("\n--- Embedding Generation Script Finished Successfully ---")
    else:
        print("\n--- Embedding Generation Script Finished with ERRORS ---")
        sys.exit(1)