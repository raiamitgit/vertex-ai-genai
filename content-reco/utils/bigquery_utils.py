"""
Utility functions for interacting with Google BigQuery.
Includes authentication, dataset/table management, data loading, and fetching.
"""
from google.cloud import bigquery
import pandas as pd

def get_bigquery_client(project_id):
    """Authenticates and returns a BigQuery client."""
    try:
        client = bigquery.Client(project=project_id)
        print(f"Successfully authenticated to BigQuery project: {project_id}")
        return client
    except Exception as e:
        print(f"Error authenticating to BigQuery: {e}")
        return None

def check_dataset_exists(client, dataset_ref):
    """Checks if a BigQuery dataset exists."""
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset {dataset_ref} already exists.")
        return True
    except:
        print(f"Dataset {dataset_ref} does not exist.")
        return False

def create_dataset(client, dataset_ref):
    """Creates a BigQuery dataset if it doesn't exist."""
    if not check_dataset_exists(client, dataset_ref):
        try:
            dataset = bigquery.Dataset(dataset_ref)
            dataset = client.create_dataset(dataset)
            print(f"Dataset {dataset.dataset_id} created.")
            return dataset
        except Exception as e:
            print(f"Error creating dataset {dataset_ref}: {e}")
            return None
    return client.get_dataset(dataset_ref)

def check_table_exists(client, table_ref):
    """Checks if a BigQuery table exists."""
    try:
        client.get_table(table_ref)
        print(f"Table {table_ref} already exists.")
        return True
    except:
        print(f"Table {table_ref} does not exist.")
        return False

def create_table(client, table_ref, schema):
    """Creates a BigQuery table with the given schema if it doesn't exist."""
    if not check_table_exists(client, table_ref):
        try:
            table = bigquery.Table(table_ref, schema=schema)
            table = client.create_table(table)
            print(f"Table {table.table_id} created.")
            return table
        except Exception as e:
            print(f"Error creating table {table_ref}: {e}")
            return None
    return client.get_table(table_ref)

def write_to_bigquery(client, table_ref, data):
    """Writes a list of dictionaries to BigQuery."""
    if not data:
        print("No data to write.")
        return

    try:
        errors = client.insert_rows_json(table_ref, data)
        if errors == []:
            print(f"Successfully wrote {len(data)} rows to {table_ref}.")
        else:
            print(f"Errors occurred while inserting rows: {errors}")
    except Exception as e:
        print(f"An error occurred writing to BigQuery: {e}")

def fetch_data_from_bigquery(client, project_id, dataset_name, table_name, columns="*"):
    """Fetches data from a BigQuery table into a pandas DataFrame."""
    table_id = f"{project_id}.{dataset_name}.{table_name}"
    try:
        query = f"SELECT {columns} FROM `{table_id}`"
        df = client.query(query).to_dataframe()
        print(f"Successfully fetched {len(df)} rows from {table_id}.")
        return df
    except Exception as e:
        print(f"Error fetching data from {table_id}: {e}")
        return None

def prepare_user_text_for_embedding(user_row, config):
    """Creates a text description for a user for embedding generation."""
    data_gen_config = config['data_generation']
    preferred_assets_list = data_gen_config['preferred_assets_list']

    fav_instrument_1 = user_row.get('fav_instrument_1')
    fav_instrument_2 = user_row.get('fav_instrument_2')
    preferred_assets_str = user_row.get('preferred_assets', '')
    trading_goal_str = user_row.get('trading_goal', '')
    experience_level = user_row.get('experience_level', 'intermediate')
    trading_frequency = user_row.get('trading_frequency', 'medium')
    order_type = user_row.get('most_used_order_type', 'limit')
    trade_duration = user_row.get('avg_trade_duration_minutes', 120)

    description = (
        f"User {user_row['user_id']} is an {experience_level}-level trader. "
        f"Their goals include: {trading_goal_str}. "
        f"They prefer trading: {preferred_assets_str}. "
        f"Key instruments are {fav_instrument_1} and {fav_instrument_2}. "
        f"Trading frequency: {trading_frequency}. "
        f"Order type: {order_type}. "
        f"Average trade duration: {trade_duration} minutes."
    )
    return description

def prepare_media_text_for_embedding(media_row):
    """Creates a text description for media content for embedding generation."""
    if media_row['type'] == 'article':
        return f"Title: {media_row.get('title', '')}. Content: {media_row.get('content', '')}"
    elif media_row['type'] == 'video':
        return f"Title: {media_row.get('title', '')}. Transcript: {media_row.get('transcript', '')}"
    return ""

def delete_table(client, table_ref):
    """Deletes a BigQuery table if it exists."""
    if check_table_exists(client, table_ref):
        try:
            client.delete_table(table_ref)
            print(f"Table {table_ref} deleted.")
        except Exception as e:
            print(f"Error deleting table {table_ref}: {e}")