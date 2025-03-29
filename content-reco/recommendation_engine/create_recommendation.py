"""
This pipeline performs the batch processing for the recommendation system.
It fetches user and media data, generates embeddings, calculates similarities,
and stores the top N recommendations for each user in a BigQuery table.
"""
import os
import yaml
from dotenv import load_dotenv
from utils.bigquery_utils import (get_bigquery_client, fetch_data_from_bigquery,
                                  prepare_user_text_for_embedding, prepare_media_text_for_embedding,
                                  create_dataset, create_table, write_to_bigquery, delete_table)
from recommendation_engine.embeddings import generate_embeddings
from recommendation_engine.recommender import calculate_similarity
from google.cloud import bigquery
import numpy as np

# Load environment variables
load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

# Load configuration
with open("config.yaml", "r") as f: # Adjusted path
    config = yaml.safe_load(f)

BQ_DATASET = config['bigquery']['dataset_name']
BQ_USERS_TABLE = config['bigquery']['users_table_name']
BQ_MEDIA_TABLE = config['bigquery']['media_table_name']
BQ_RECOMMENDATIONS_TABLE = config['bigquery']['recommendations_table_name']
EMBEDDING_CONFIG = config['embedding_model']
BATCH_RECOMMENDATION_CONFIG = config['batch_recommendation']

# BigQuery Schema for Recommendations
recommendations_schema = [
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("recommended_media_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("rank", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("similarity_score", "FLOAT"),
    bigquery.SchemaField("processing_timestamp", "TIMESTAMP", mode="REQUIRED"),
]

if __name__ == "__main__":
    if not PROJECT_ID or not LOCATION:
        print("Please set the PROJECT_ID and LOCATION environment variables in .env file.")
        exit()

    bq_client = get_bigquery_client(PROJECT_ID)
    if not bq_client:
        exit()

    dataset_ref = bq_client.dataset(BQ_DATASET)
    create_dataset(bq_client, dataset_ref)
    recommendations_table_ref = dataset_ref.table(BQ_RECOMMENDATIONS_TABLE)

    # Delete and Recreate recommendations table to ensure clean data for each batch run
    delete_table(bq_client, recommendations_table_ref)
    create_table(bq_client, recommendations_table_ref, recommendations_schema)

    print("Fetching users data from BigQuery...")
    users_df = fetch_data_from_bigquery(bq_client, PROJECT_ID, BQ_DATASET, BQ_USERS_TABLE)
    print("Fetching media data from BigQuery...")
    media_df = fetch_data_from_bigquery(bq_client, PROJECT_ID, BQ_DATASET, BQ_MEDIA_TABLE,
                                       columns="media_id, type, title, content, transcript")

    if users_df is None or media_df is None:
        exit()

    print("Generating user embeddings...")
    user_texts = [prepare_user_text_for_embedding(user_row, config) for _, user_row in users_df.iterrows()]
    user_embeddings = generate_embeddings(
        EMBEDDING_CONFIG['publisher'],
        EMBEDDING_CONFIG['model_name'],
        EMBEDDING_CONFIG['max_retries'],
        EMBEDDING_CONFIG['batch_size'],
        user_texts
    )
    user_embeddings_map = dict(zip(users_df['user_id'], user_embeddings))
    print(f"Generated {len(user_embeddings_map)} user embeddings.")

    print("Generating media embeddings...")
    media_texts = [prepare_media_text_for_embedding(media_row) for _, media_row in media_df.iterrows()]
    media_embeddings = generate_embeddings(
        EMBEDDING_CONFIG['publisher'],
        EMBEDDING_CONFIG['model_name'],
        EMBEDDING_CONFIG['max_retries'],
        EMBEDDING_CONFIG['batch_size'],
        media_texts
    )
    media_embeddings_map = dict(zip(media_df['media_id'], media_embeddings))
    print(f"Generated {len(media_embeddings_map)} media embeddings.")

    all_recommendations_to_store = []
    # Use BQ SQL to get the current timestamp to ensure consistency
    current_timestamp = next(bq_client.query("SELECT CURRENT_TIMESTAMP()").result())[0]

    for user_id, user_embedding in user_embeddings_map.items():
        if user_embedding:
            # Filter out media without embeddings
            valid_media_ids = [media_id for media_id, emb in media_embeddings_map.items() if emb]
            valid_media_embeddings = [media_embeddings_map[mid] for mid in valid_media_ids]

            if not valid_media_embeddings:
                continue

            similarities = calculate_similarity(user_embedding, valid_media_embeddings, metric=BATCH_RECOMMENDATION_CONFIG['similarity_metric'])
            media_with_similarity = list(zip(valid_media_ids, similarities))
            sorted_media = sorted(media_with_similarity, key=lambda x: x[1], reverse=True)
            top_n = sorted_media[:BATCH_RECOMMENDATION_CONFIG['top_n_to_store']]

            for rank, (media_id, score) in enumerate(top_n):
                all_recommendations_to_store.append({
                    "user_id": user_id,
                    "recommended_media_id": media_id,
                    "rank": rank + 1,
                    "similarity_score": float(score),
                    "processing_timestamp": current_timestamp.isoformat() # Convert to ISO string
                })

    print(f"Writing {len(all_recommendations_to_store)} recommendations to BigQuery...")
    write_to_bigquery(bq_client, recommendations_table_ref, all_recommendations_to_store)

    print("Batch recommendation pipeline completed.")
