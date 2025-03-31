"""
BigQuery interaction utilities.

Provides helper functions for connecting to BigQuery, managing datasets and tables,
executing queries, fetching results, and loading data from NDJSON files.
"""
import os
from typing import List, Dict, Any, Optional, Iterator
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.api_core.exceptions import GoogleAPICallError, Forbidden

# ==============================================================================
# Client and Query Execution Helpers
# ==============================================================================

def get_bigquery_client(project_id: str) -> Optional[bigquery.Client]:
    """Authenticates and returns a BigQuery client instance.

    Performs a simple test query to verify connection and permissions.

    Args:
        project_id (str): The Google Cloud Project ID.

    Returns:
        Optional[bigquery.Client]: A bigquery.Client object if authentication
                                   is successful, otherwise None.
    """
    if not project_id:
        print("ERROR: GCP Project ID is required to initialize BigQuery client.")
        return None
    try:
        client = bigquery.Client(project=project_id)
        print("Testing BigQuery connection...")
        client.query("SELECT 1").result() # Test query
        print(f"BigQuery client authenticated successfully for project: {project_id}")
        return client
    except Forbidden as e:
         print(f"ERROR: BigQuery client authentication failed (Forbidden): {e}. "
               "Check permissions (e.g., BigQuery User/JobUser roles).")
         return None
    except Exception as e: # Catch other potential exceptions
        print(f"ERROR: BigQuery client authentication/connection failed: {e}")
        return None


def execute_bq_query(
    client: bigquery.Client,
    query: str,
    job_config: Optional[bigquery.QueryJobConfig] = None,
    description: str = "Executing BigQuery query"
) -> Optional[Iterator[bigquery.table.Row]]:
    """Executes a BigQuery SQL query, waits for completion, and checks for errors.

    Suitable for DDL/DML or queries where row results are not the primary output,
    but job success/failure needs checking.

    Args:
        client (bigquery.Client): Authenticated BigQuery client.
        query (str): The SQL query string to execute.
        job_config (Optional[bigquery.QueryJobConfig], optional): Query job configuration.
                                                                  Defaults to None.
        description (str, optional): A description logged before executing the query.
                                     Defaults to "Executing BigQuery query".

    Returns:
        Optional[Iterator[bigquery.table.Row]]: The results iterator if the job
                                                succeeded (may be empty), or None
                                                if the client is invalid or the
                                                job failed.
    """
    if not client:
        print("ERROR: execute_bq_query called with an invalid BigQuery client.")
        return None

    print(f"{description}...")
    job = None
    try:
        query_job = client.query(query, job_config=job_config)
        job = query_job
        print(f"  Job ID: {query_job.job_id}")
        results_iterator = query_job.result() # Waits for completion

        if query_job.errors:
            print(f"ERROR: BigQuery job {query_job.job_id} failed:")
            for error in query_job.errors:
                print(f"  Reason: {error.get('reason', 'N/A')}, "
                      f"Message: {error.get('message', 'N/A')}")
            # print(f"Failed Query:\n---\n{query}\n---") # Uncomment for debugging
            return None

        print(f"  Job {query_job.job_id} completed successfully.")
        return results_iterator

    except GoogleAPICallError as e:
        job_id_str = f"Job ID: {job.job_id}" if job else "Job ID: N/A"
        print(f"ERROR: API call error during BigQuery query execution ({job_id_str}): {e}")
        # print(f"Failed Query:\n---\n{query}\n---") # Uncomment for debugging
        return None
    except Exception as e:
        job_id_str = f"Job ID: {job.job_id}" if job else "Job ID: N/A"
        print(f"ERROR: Unexpected exception during BigQuery query execution ({job_id_str}): {e}")
        # print(f"Failed Query:\n---\n{query}\n---") # Uncomment for debugging
        return None


def fetch_bq_results(
    client: bigquery.Client,
    query: str,
    job_config: Optional[bigquery.QueryJobConfig] = None
) -> Optional[List[Dict[str, Any]]]:
    """Executes a BigQuery SQL query and returns results as a list of dictionaries.

    Args:
        client (bigquery.Client): Authenticated BigQuery client.
        query (str): The SQL query string to execute.
        job_config (Optional[bigquery.QueryJobConfig], optional): Query job configuration.
                                                                  Defaults to None.

    Returns:
        Optional[List[Dict[str, Any]]]: A list of dictionaries representing the rows,
                                        or None if an error occurs or the client is invalid.
    """
    if not client:
        print("ERROR: fetch_bq_results called with an invalid BigQuery client.")
        return None

    print(f"Executing BQ query to fetch results...")
    job = None
    try:
        query_job = client.query(query, job_config=job_config)
        job = query_job
        print(f"  Job ID: {query_job.job_id}")
        results_iterator = query_job.result() # Waits for completion

        if query_job.errors:
            print(f"ERROR: BigQuery job {query_job.job_id} failed:")
            for error in query_job.errors:
                print(f"  Reason: {error.get('reason', 'N/A')}, "
                      f"Message: {error.get('message', 'N/A')}")
            # print(f"Failed Query:\n---\n{query}\n---") # Uncomment for debugging
            return None

        records = [dict(row.items()) for row in results_iterator]
        print(f"  Fetched {len(records)} records.")
        return records

    except NotFound as e:
         print(f"ERROR: Query execution failed - Resource not found: {e}")
         # print(f"Failed Query:\n---\n{query}\n---") # Uncomment for debugging
         return None
    except GoogleAPICallError as e:
        job_id_str = f"Job ID: {job.job_id}" if job else "Job ID: N/A"
        print(f"ERROR: API call error during BigQuery query execution ({job_id_str}): {e}")
        # print(f"Failed Query:\n---\n{query}\n---") # Uncomment for debugging
        return None
    except Exception as e:
        job_id_str = f"Job ID: {job.job_id}" if job else "Job ID: N/A"
        print(f"ERROR: Unexpected exception during BigQuery query execution ({job_id_str}): {e}")
        # print(f"Failed Query:\n---\n{query}\n---") # Uncomment for debugging
        return None

# ==============================================================================
# Dataset and Table Management
# ==============================================================================

def create_dataset(
    client: bigquery.Client,
    dataset_ref: bigquery.DatasetReference,
    location: Optional[str] = None
) -> bool:
    """Ensures a BigQuery dataset exists, creating it if necessary.

    Args:
        client (bigquery.Client): Authenticated BigQuery client.
        dataset_ref (bigquery.DatasetReference): Reference to the dataset.
        location (Optional[str], optional): Location for dataset creation.
                                            Defaults to None (uses client default).

    Returns:
        bool: True if the dataset exists or is created successfully, False otherwise.
    """
    if not client:
        print("ERROR: create_dataset called with invalid BigQuery client.")
        return False
    try:
        print(f"Ensuring dataset {dataset_ref} exists...")
        dataset_obj = bigquery.Dataset(dataset_ref)
        if location:
            dataset_obj.location = location
        # exists_ok=True makes this call idempotent
        created_dataset = client.create_dataset(dataset_obj, exists_ok=True, timeout=30)
        print(f"Dataset {created_dataset.dataset_id} exists/created in {created_dataset.location}.")
        return True
    except GoogleAPICallError as e:
        print(f"ERROR: API call error ensuring dataset {dataset_ref} exists: {e}")
        return False
    except Exception as e: # Catch other potential issues
        print(f"ERROR: Failed to ensure dataset {dataset_ref} exists: {e}")
        return False

def check_table_exists(
    client: bigquery.Client, table_ref: bigquery.TableReference
) -> bool:
    """Checks if a BigQuery table exists.

    Args:
        client (bigquery.Client): Authenticated BigQuery client.
        table_ref (bigquery.TableReference): Reference to the table.

    Returns:
        bool: True if the table exists, False otherwise.
    """
    if not client: return False
    try:
        client.get_table(table_ref)
        return True
    except NotFound:
        return False
    except Exception as e:
        print(f"WARN: Error checking if table {table_ref} exists: {e}")
        return False # Treat other errors as table not accessible/existing

def delete_table(client: bigquery.Client, table_ref: bigquery.TableReference) -> bool:
    """Deletes a BigQuery table if it exists.

    Args:
        client (bigquery.Client): Authenticated BigQuery client.
        table_ref (bigquery.TableReference): Reference to the table to delete.

    Returns:
        bool: True if the table doesn't exist or is deleted successfully, False otherwise.
    """
    if not client: return False
    print(f"Attempting to delete table {table_ref} if it exists...")
    try:
        # not_found_ok=True makes this idempotent if table is already gone
        client.delete_table(table_ref, not_found_ok=True)
        print(f"Table {table_ref} deleted (or did not exist).")
        return True
    except GoogleAPICallError as e:
        print(f"ERROR: API call error deleting table {table_ref}: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to delete table {table_ref}: {e}")
        return False

def truncate_table(
    client: bigquery.Client, project_id: str, dataset_id: str, table_id: str
) -> bool:
    """Truncates a BigQuery table using SQL TRUNCATE TABLE if it exists.

    Args:
        client (bigquery.Client): Authenticated BigQuery client.
        project_id (str): GCP project ID.
        dataset_id (str): BigQuery dataset ID.
        table_id (str): BigQuery table ID.

    Returns:
        bool: True if the table was truncated successfully or did not exist,
              False if an error occurred during truncation.
    """
    if not client: return False
    table_ref_obj = client.dataset(dataset_id).table(table_id)
    if check_table_exists(client, table_ref_obj):
        table_ref_str = f"`{project_id}`.`{dataset_id}`.`{table_id}`"
        query = f"TRUNCATE TABLE {table_ref_str}"
        results_iterator = execute_bq_query(
            client, query,
            description=f"Truncating table {table_id}"
        )
        if results_iterator is not None:
            print(f"Table {table_ref_str} truncated.")
            return True
        else:
            print(f"ERROR: Failed to truncate table {table_ref_str}.")
            return False
    else:
        print(f"INFO: Table {table_id} does not exist, skipping truncation.")
        return True # Considered success as the table is effectively empty

# ==============================================================================
# Data Loading
# ==============================================================================

def load_ndjson_from_file(
    client: bigquery.Client,
    local_file_path: str,
    table_ref: bigquery.TableReference,
) -> bool:
    """Loads data from a local NDJSON file into a BigQuery table.

    Uses BigQuery's schema autodetection and creates the table if it doesn't exist.
    Truncates the table before loading (WRITE_TRUNCATE).

    Args:
        client (bigquery.Client): Authenticated BigQuery client.
        local_file_path (str): Path to the local NDJSON file.
        table_ref (bigquery.TableReference): Reference to the destination BigQuery table.

    Returns:
        bool: True if the load job completes successfully, False otherwise.
    """
    if not client:
        print("ERROR: load_ndjson_from_file requires a valid BigQuery client.")
        return False
    if not os.path.exists(local_file_path):
        print(f"ERROR: Local NDJSON file not found: {local_file_path}")
        return False

    job_config = bigquery.LoadJobConfig(
        autodetect=True, # Automatically infer schema
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE, # Overwrite existing table
    )

    table_name_str = f"{table_ref.dataset_id}.{table_ref.table_id}"
    print(f"Loading data from '{os.path.basename(local_file_path)}' into {table_name_str} "
          f"(auto-schema, create/truncate)...")
    load_job = None
    try:
        with open(local_file_path, "rb") as source_file:
            load_job = client.load_table_from_file(
                file_obj=source_file,
                destination=table_ref,
                job_config=job_config,
                job_id_prefix=f"load_auto_{table_ref.table_id}_" # Custom prefix for job ID
            )
        print(f"  Load job started: {load_job.job_id}")
        load_job.result(timeout=300) # Wait up to 5 minutes for completion

        if load_job.errors:
            print(f"ERROR: Load job {load_job.job_id} for {table_name_str} failed:")
            for error in load_job.errors:
                 print(f"  Reason: {error.get('reason')}, Message: {error.get('message')}")
            if any("schema" in str(e).lower() for e in load_job.errors):
                print("  HINT: Schema auto-detection might have failed. "
                      "Ensure NDJSON is well-formed and fields are consistent.")
            return False
        elif load_job.state == 'DONE':
            # Check output rows even on success
            rows_loaded = load_job.output_rows if load_job.output_rows is not None else 0
            print(f"  Load job completed successfully. Loaded {rows_loaded} rows.")
            return True
        else:
            print(f"WARN: Load job {load_job.job_id} finished with unexpected state: {load_job.state}")
            return False

    except TimeoutError:
        job_id_str = f"Job ID: {load_job.job_id}" if load_job else "Job ID: N/A"
        print(f"ERROR: Load job {job_id_str} for {table_name_str} timed out.")
        return False
    except GoogleAPICallError as e:
        job_id_str = f"Job ID: {load_job.job_id}" if load_job else "Job ID: N/A"
        print(f"ERROR: API call error during file load for {table_name_str} ({job_id_str}): {e}")
        return False
    except Exception as e:
        job_id_str = f"Job ID: {load_job.job_id}" if load_job else "Job ID: N/A"
        print(f"ERROR: Unexpected exception during file load for {table_name_str} ({job_id_str}): {e}")
        return False