"""
Generates synthetic user and media data and loads it into BigQuery.
It ensures the target dataset and tables exist, truncates tables before loading.
"""
import os
import yaml
from dotenv import load_dotenv
from utils.synthetic_data import generate_user, generate_article, generate_video
from utils.bigquery_utils import get_bigquery_client, create_dataset, create_table, write_to_bigquery, check_table_exists
from google.cloud import bigquery

# Load environment variables
load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")

# Load configuration
with open("config.yaml", "r") as f:  # Path adjusted
    config = yaml.safe_load(f)

DATASET_NAME = config['bigquery']['dataset_name']
USERS_TABLE_NAME = config['bigquery']['users_table_name']
MEDIA_TABLE_NAME = config['bigquery']['media_table_name']
NUM_USERS = config['data_generation']['num_users']
NUM_ARTICLES = config['data_generation']['num_articles']
NUM_VIDEOS = config['data_generation']['num_videos']

# BigQuery Schema Definitions
users_schema = [
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("experience_level", "STRING"),
    bigquery.SchemaField("trading_goal", "STRING"),
    bigquery.SchemaField("preferred_assets", "STRING"),
    bigquery.SchemaField("account_age_months", "INTEGER"),
    bigquery.SchemaField("fav_instrument_1", "STRING"),
    bigquery.SchemaField("fav_instrument_1_volume_perc", "INTEGER"),
    bigquery.SchemaField("fav_instrument_2", "STRING"),
    bigquery.SchemaField("fav_instrument_2_volume_perc", "INTEGER"),
    bigquery.SchemaField("avg_trade_duration_minutes", "INTEGER"),
    bigquery.SchemaField("most_used_order_type", "STRING"),
    bigquery.SchemaField("win_rate_perc", "FLOAT"),
    bigquery.SchemaField("average_leverage_multiple", "FLOAT"),
    bigquery.SchemaField("trading_frequency", "STRING"),
]

media_schema = [
    bigquery.SchemaField("media_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("type", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("title", "STRING"),
    bigquery.SchemaField("author", "STRING"),
    bigquery.SchemaField("creator", "STRING"),
    bigquery.SchemaField("created_date", "TIMESTAMP"),
    bigquery.SchemaField("tags", "STRING", mode="REPEATED"),
    bigquery.SchemaField("content", "STRING"),
    bigquery.SchemaField("content_length_words", "INTEGER"),
    bigquery.SchemaField("transcript", "STRING"),
    bigquery.SchemaField("video_length_seconds", "INTEGER"),
    bigquery.SchemaField("transcript_length_words", "INTEGER"),
]

def truncate_table(client, table_ref):
    """Truncates a BigQuery table if it exists."""
    if check_table_exists(client, table_ref):
        try:
            query = f"TRUNCATE TABLE `{table_ref.project}.{table_ref.dataset_id}.{table_ref.table_id}`"
            query_job = client.query(query)
            query_job.result()  # Wait for the job to complete
            print(f"Table {table_ref} truncated.")
        except Exception as e:
            print(f"Error truncating table {table_ref}: {e}")

if __name__ == "__main__":
    if not PROJECT_ID:
        print("Please set the PROJECT_ID environment variable in .env file.")
        exit()

    bq_client = get_bigquery_client(PROJECT_ID)
    if not bq_client:
        exit()

    dataset_ref = bq_client.dataset(DATASET_NAME)
    create_dataset(bq_client, dataset_ref)

    users_table_ref = dataset_ref.table(USERS_TABLE_NAME)
    media_table_ref = dataset_ref.table(MEDIA_TABLE_NAME)

    # Create tables if they don't exist
    create_table(bq_client, users_table_ref, users_schema)
    create_table(bq_client, media_table_ref, media_schema)

    # Truncate tables
    truncate_table(bq_client, users_table_ref)
    truncate_table(bq_client, media_table_ref)

    print("Generating user data...")
    users_data_list = [generate_user(i + 1, config) for i in range(NUM_USERS)]
    print("Writing user data to BigQuery...")
    write_to_bigquery(bq_client, users_table_ref, users_data_list)

    print("Generating media data...")
    media_data_list = []
    for i in range(NUM_ARTICLES):
        media_data_list.append(generate_article(i + 1, config))
    for i in range(NUM_VIDEOS):
        media_data_list.append(generate_video(i + 1, config))
    print("Writing media data to BigQuery...")
    write_to_bigquery(bq_client, media_table_ref, media_data_list)

    print("Data generation and BigQuery upload complete.")