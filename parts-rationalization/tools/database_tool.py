import os
from dotenv import load_dotenv
from google.cloud import bigquery

# Load environment variables
load_dotenv()

def fetch_details_from_database(asset_id: str) -> dict:
    """
    Retrieves detailed information for a specific part from the BigQuery master table.

    Args:
        asset_id: The unique identifier for the part (e.g., a Physna Asset ID).

    Returns:
        A dictionary containing the part's details if found, otherwise an error message.
    """
    project_id = os.getenv("BQ_PROJECT_ID")
    dataset_id = os.getenv("BQ_DATASET_ID")
    table_id = os.getenv("BQ_METADATA_TABLE")

    if not all([project_id, dataset_id, table_id]):
        return {"status": "error", "message": "BigQuery configuration is missing in environment variables."}

    full_table_id = f"{project_id}.{dataset_id}.{table_id}"
    client = bigquery.Client(project=project_id)

    query = f"""
        SELECT *
        FROM `{full_table_id}`
        WHERE part_id = @asset_id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("asset_id", "STRING", asset_id),
        ]
    )

    try:
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        if results.total_rows == 0:
            return {"status": "not_found", "message": f"No details found for part with asset_id: {asset_id}"}

        # Convert the first row to a dictionary
        part_details = dict(list(results)[0].items())
        return {"status": "success", "data": part_details}

    except Exception as e:
        return {"status": "error", "message": f"An error occurred while querying BigQuery: {str(e)}"}
