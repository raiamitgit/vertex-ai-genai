import os
import json
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account

load_dotenv()

def get_config() -> dict:
    """
    Retrieves and constructs configuration from environment variables.
    """
    config = {
        "PROJECT_ID": os.getenv("BQ_PROJECT_ID"),
        "DATASET_ID": os.getenv("BQ_DATASET_ID"),
        "METADATA_TABLE": os.getenv("BQ_METADATA_TABLE"),
        "OBJECT_TABLE_NAME": os.getenv("BQ_OBJECT_TABLE"),
        "BQ_REGION": os.getenv("BQ_REGION"),
        "CONNECTION_ID": os.getenv("BQ_CONNECTION_ID"),
        "MODEL_NAME": os.getenv("EMBEDDING_MODEL"),
    }
    config["FULL_META_TABLE_ID"] = f"{config['PROJECT_ID']}.{config['DATASET_ID']}.{config['METADATA_TABLE']}"
    config["FULL_OBJECT_TABLE_ID"] = f"{config['PROJECT_ID']}.{config['DATASET_ID']}.{config['OBJECT_TABLE_NAME']}"
    config["FULL_MODEL_ID"] = f"{config['PROJECT_ID']}.{config['DATASET_ID']}.{config['MODEL_NAME'].replace('@', '_').replace('-', '_')}"
    config["FULL_CONNECTION_ID"] = f"{config['PROJECT_ID']}.{config['BQ_REGION']}.{config['CONNECTION_ID']}"
    return config

def setup_embedding_model(client: bigquery.Client, cfg: dict):
    """
    Creates the BigQuery ML embedding model if it doesn't exist.
    """
    print("--- Setup: Creating/Verifying BQML Embedding Model ---")
    model_sql = f"""
    CREATE OR REPLACE MODEL `{cfg['FULL_MODEL_ID']}`
    REMOTE WITH CONNECTION `{cfg['FULL_CONNECTION_ID']}`
    OPTIONS(endpoint = '{cfg['MODEL_NAME']}');
    """
    try:
        client.query(model_sql).result()
        print(f"Model '{cfg['FULL_MODEL_ID']}' created or already exists.")
    except Exception as e:
        print(f"ERROR: Failed to create BQML model. Details: {e}")
        raise

def add_embedding_column(client: bigquery.Client, cfg: dict):
    """
    Adds the 'image_embedding' column to the metadata table if it doesn't exist.
    """
    print("--- Step 1: Altering table to add embedding column ---")
    try:
        alter_table_sql = f"""
        ALTER TABLE `{cfg['FULL_META_TABLE_ID']}`
        ADD COLUMN IF NOT EXISTS image_embedding ARRAY<FLOAT64>;
        """
        client.query(alter_table_sql).result()
        print("Successfully added or verified 'image_embedding' column.")
    except Exception as e:
        print(f"ERROR: Failed to add embedding column. Details: {e}")
        raise

def generate_embeddings(client: bigquery.Client, cfg: dict):
    """
    Generates and saves image embeddings into the metadata table.
    """
    print("\n--- Step 2: Generating and populating image embeddings ---")
    try:
        generate_embeddings_sql = f"""
        MERGE `{cfg['FULL_META_TABLE_ID']}` T
        USING (
            SELECT
                uri,
                ml_generate_embedding_result AS embedding
            FROM
                ML.GENERATE_EMBEDDING(
                    MODEL `{cfg['FULL_MODEL_ID']}`,
                    TABLE `{cfg['FULL_OBJECT_TABLE_ID']}`
                )
        ) S
        ON T.gcs_image_path = S.uri
        WHEN MATCHED THEN
            UPDATE SET T.image_embedding = S.embedding;
        """
        job = client.query(generate_embeddings_sql)
        job.result()
        print(f"Embedding generation complete. Updated {job.num_dml_affected_rows} rows.")
    except Exception as e:
        print(f"ERROR: Failed to generate embeddings. Details: {e}")
        raise

def create_vector_index(client: bigquery.Client, cfg: dict):
    """
     Create vector indexs in BigQuery. Skipped for tables with less than 5K rows.
    """
    print("\n--- Step 3: Vector Index Creation ---")
    
    table = client.get_table(cfg['FULL_META_TABLE_ID'])
    if table.num_rows < 5000:
        print("Skipping vector index creation due to table size constraints (< 5000 rows).")
        print("Vector search will be performed directly on the table.")
        return
    else:
        print("Attempting to create vector index")
        index_name = f"{cfg['METADATA_TABLE']}_embedding_idx"
        create_index_sql = f"""
        CREATE OR REPLACE VECTOR INDEX `{index_name}`
        ON `{cfg['FULL_META_TABLE_ID']}`(image_embedding)
        OPTIONS(index_type = 'TREE_AH', distance_type = 'COSINE', 
                tree_ah_options = '{{"leaf_node_embedding_count": 1000}}');
        """
        try:
            client.query(create_index_sql).result()
            print(f"Successfully created vector index '{index_name}'.")
        except Exception as e:
            print(f"ERROR: Failed to create vector index. Details: {e}")
            raise

def main():
    """Orchestrates the embedding generation and indexing pipeline."""
    print("=== Starting Image Embedding and Indexing Pipeline ===")
    try:
        config = get_config()
        bq_client = bigquery.Client(project=config["PROJECT_ID"])
        
        setup_embedding_model(bq_client, config)
        add_embedding_column(bq_client, config)
        generate_embeddings(bq_client, config)
        create_vector_index(bq_client, config)

    except Exception as e:
        print(f"\n Program Error: {e}")
    print("=== Finished ===")

if __name__ == "__main__":
    main()
