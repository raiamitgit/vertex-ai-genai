"""
Generates AI content (user summaries, article text, video transcripts)
using BigQuery ML ML.GENERATE_TEXT function and updates BigQuery tables.

Uses nested SQL REPLACE functions within BQML calls to populate prompts
dynamically from table data at runtime. Extracts generated text using
JSON_EXTRACT_SCALAR.
"""
import os
import sys
import yaml
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
from utils.bigquery_utils import get_bigquery_client, execute_bq_query

# --- Module-level variables (populated by run_ai_content_generation) ---
PROJECT_ID: Optional[str] = None
DATASET_NAME: Optional[str] = None
USERS_TABLE_NAME: Optional[str] = None
MEDIA_TABLE_NAME: Optional[str] = None
TEXT_GENERATOR_MODEL_NAME: Optional[str] = None
ARTICLE_PROMPT_TEMPLATE: Optional[str] = None
TRANSCRIPT_PROMPT_TEMPLATE: Optional[str] = None
USER_SUMMARY_PROMPT_TEMPLATE: Optional[str] = None
GEN_PARAMS: Dict[str, Any] = {}
DATASET_ID: Optional[str] = None
USERS_TABLE_ID: Optional[str] = None
MEDIA_TABLE_ID: Optional[str] = None
MODEL_ID: Optional[str] = None
GEN_PARAMS_SQL: str = "NULL"


# --- Helper ---
def format_gen_params_for_sql(params: Dict[str, Any]) -> str:
    """Formats generation parameters into a SQL STRUCT string for BQML.

    Args:
        params (Dict[str, Any]): Dictionary of generation parameters.

    Returns:
        str: A SQL string representing the STRUCT, or an empty string if no
             valid parameters are provided.
    """
    items = []
    if params:
        if 'temperature' in params: items.append(f"{params['temperature']} AS temperature")
        if 'top_p' in params: items.append(f"{params['top_p']} AS top_p")
        if 'top_k' in params: items.append(f"{params['top_k']} AS top_k")
        if 'max_output_tokens' in params: items.append(f"{params['max_output_tokens']} AS max_output_tokens")
    return f"{', '.join(items)}" if items else ""

# --- BQML Generation Functions ---
def generate_media_content(client: bigquery.Client) -> bool:
    """Generates article text/video transcripts using BQML and merges into media table.

    Uses module-level config variables (MEDIA_TABLE_ID, MODEL_ID, etc.).

    Args:
        client (bigquery.Client): Authenticated BigQuery client.

    Returns:
        bool: True if the BQML job completes successfully, False otherwise.
    """
    print(f"\n--- Starting Media Content Generation (Articles & Transcripts) ---")
    print(f"Target Table: {MEDIA_TABLE_ID}")
    print(f"Using Model: {MODEL_ID}")

    if not all([MEDIA_TABLE_ID, MODEL_ID, ARTICLE_PROMPT_TEMPLATE, TRANSCRIPT_PROMPT_TEMPLATE, GEN_PARAMS_SQL]):
         print("ERROR: Configuration variables not properly set for generate_media_content.")
         return False

    # MERGE statement using nested SQL REPLACE for runtime prompt population
    merge_sql = f"""
    MERGE `{MEDIA_TABLE_ID}` AS target
    USING (
      SELECT
        media_id,
        JSON_EXTRACT_SCALAR(ml_generate_text_result, '$.candidates[0].content.parts[0].text') AS generated_main_text
      FROM
        ML.GENERATE_TEXT(
          MODEL {MODEL_ID},
          (
            SELECT
              media_id, title, author_creator, tags, content_length, type,
              CASE type
                WHEN 'article' THEN
                  REPLACE(REPLACE(REPLACE(REPLACE(
                    '''{ARTICLE_PROMPT_TEMPLATE}''',
                    '{{title}}', IFNULL(title, '')),
                    '{{author_creator}}', IFNULL(author_creator, '')),
                    '{{tags}}', IFNULL(tags, '')),
                    '{{content_length}}', CAST(IFNULL(content_length, 500) AS STRING))
                WHEN 'video' THEN
                  REPLACE(REPLACE(REPLACE(REPLACE(
                    '''{TRANSCRIPT_PROMPT_TEMPLATE}''',
                    '{{title}}', IFNULL(title, '')),
                    '{{author_creator}}', IFNULL(author_creator, '')),
                    '{{tags}}', IFNULL(tags, '')),
                    '{{content_length}}', CAST(IFNULL(content_length, 300) AS STRING))
                ELSE 'Invalid media type specified.'
              END AS prompt
            FROM `{MEDIA_TABLE_ID}`
            WHERE main_text IS NULL OR LENGTH(main_text) = 0 -- Regenerate if empty
          ),
          {GEN_PARAMS_SQL}
       )
    ) AS source
    ON target.media_id = source.media_id
    WHEN MATCHED THEN
      UPDATE SET target.main_text = source.generated_main_text;
    """

    job_result = execute_bq_query(
        client,
        merge_sql,
        description=f"Generating and merging media content into {MEDIA_TABLE_NAME}"
    )

    if job_result is not None:
        print(f"Media content generation job completed successfully.")
        return True
    else:
        print(f"ERROR: Media content generation job failed.")
        return False


def generate_user_summaries(client: bigquery.Client) -> bool:
    """Generates user profile summaries using BQML and merges into users table.

    Uses module-level config variables (USERS_TABLE_ID, MODEL_ID, etc.).

    Args:
        client (bigquery.Client): Authenticated BigQuery client.

    Returns:
        bool: True if the BQML job completes successfully, False otherwise.
    """
    print(f"\n--- Starting User Profile Summary Generation ---")
    print(f"Target Table: {USERS_TABLE_ID}")
    print(f"Using Model: {MODEL_ID}")

    if not all([USERS_TABLE_ID, MODEL_ID, USER_SUMMARY_PROMPT_TEMPLATE, GEN_PARAMS_SQL]):
         print("ERROR: Configuration variables not properly set for generate_user_summaries.")
         return False

    # MERGE statement using nested SQL REPLACE for runtime prompt population
    merge_sql = f"""
    MERGE `{USERS_TABLE_ID}` AS target
    USING (
      SELECT
        user_id,
        JSON_EXTRACT_SCALAR(ml_generate_text_result, '$.candidates[0].content.parts[0].text') AS generated_summary_text
      FROM
        ML.GENERATE_TEXT(
          MODEL {MODEL_ID},
          (
            SELECT
              user_id, experience_level, trading_goal, preferred_assets, account_age_months,
              fav_instrument_1, fav_instrument_1_volume_perc, fav_instrument_2,
              fav_instrument_2_volume_perc, avg_trade_duration_minutes,
              most_used_order_type, win_rate_perc, average_leverage_multiple,
              trading_frequency,
              -- Dynamically construct prompt using SQL REPLACE
              REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                '''{USER_SUMMARY_PROMPT_TEMPLATE}''',
                '{{experience_level}}', IFNULL(experience_level, 'N/A')),
                '{{trading_goal}}', IFNULL(trading_goal, 'N/A')),
                '{{preferred_assets}}', IFNULL(preferred_assets, 'N/A')),
                '{{account_age_months}}', CAST(IFNULL(account_age_months, 0) AS STRING)),
                '{{fav_instrument_1}}', IFNULL(fav_instrument_1, 'N/A')),
                '{{fav_instrument_1_volume_perc}}', CAST(IFNULL(fav_instrument_1_volume_perc, 0) AS STRING)),
                '{{fav_instrument_2}}', IFNULL(fav_instrument_2, 'N/A')),
                '{{fav_instrument_2_volume_perc}}', CAST(IFNULL(fav_instrument_2_volume_perc, 0) AS STRING)),
                '{{avg_trade_duration_minutes}}', CAST(IFNULL(avg_trade_duration_minutes, 0) AS STRING)),
                '{{most_used_order_type}}', IFNULL(most_used_order_type, 'N/A')),
                '{{win_rate_perc}}', CAST(IFNULL(win_rate_perc, 0.0) AS STRING)),
                '{{average_leverage_multiple}}', CAST(IFNULL(average_leverage_multiple, 1.0) AS STRING)),
                '{{trading_frequency}}', IFNULL(trading_frequency, 'N/A'))
              AS prompt
            FROM `{USERS_TABLE_ID}`
            WHERE profile_summary IS NULL OR LENGTH(profile_summary) = 0 -- Regenerate if empty
          ),
          {GEN_PARAMS_SQL}
        )
    ) AS source
    ON target.user_id = source.user_id
    WHEN MATCHED THEN
      UPDATE SET target.profile_summary = source.generated_summary_text;
    """

    job_result = execute_bq_query(
        client,
        merge_sql,
        description=f"Generating and merging user summaries into {USERS_TABLE_NAME}"
    )

    if job_result is not None:
        print(f"User summary generation job completed successfully.")
        return True
    else:
        print(f"ERROR: User summary generation job failed.")
        return False


# --- Main Orchestration Function ---
def run_ai_content_generation(client: bigquery.Client, config: Dict[str, Any]):
    """Orchestrates the generation of AI content (media and user summaries).

    Sets module-level variables needed by the generation functions.

    Args:
        client (bigquery.Client): Authenticated BigQuery client instance.
        config (Dict[str, Any]): Dictionary loaded from config.yaml.
    """
    global PROJECT_ID, DATASET_NAME, USERS_TABLE_NAME, MEDIA_TABLE_NAME, \
           TEXT_GENERATOR_MODEL_NAME, ARTICLE_PROMPT_TEMPLATE, \
           TRANSCRIPT_PROMPT_TEMPLATE, USER_SUMMARY_PROMPT_TEMPLATE, \
           GEN_PARAMS, DATASET_ID, USERS_TABLE_ID, MEDIA_TABLE_ID, \
           MODEL_ID, GEN_PARAMS_SQL

    print("\n--- Running AI Content Generation ---")

    # --- Extract Config and Set Globals ---
    try:
        PROJECT_ID = os.getenv("PROJECT_ID")
        if not PROJECT_ID:
             print("ERROR: PROJECT_ID not found in environment for AI generation.")
             return

        BQ_CONFIG = config['bigquery']
        BQML_CONFIG = config['bqml_models']
        PROMPT_CONFIG = config['bqml_prompts']
        GEN_PARAMS = config.get('bqml_generation_params', {})

        DATASET_NAME = BQ_CONFIG['dataset_name']
        USERS_TABLE_NAME = BQ_CONFIG['users_table_name']
        MEDIA_TABLE_NAME = BQ_CONFIG['media_table_name']
        TEXT_GENERATOR_MODEL_NAME = BQML_CONFIG['text_generator']

        ARTICLE_PROMPT_TEMPLATE = PROMPT_CONFIG['generate_article']
        TRANSCRIPT_PROMPT_TEMPLATE = PROMPT_CONFIG['generate_video_transcript']
        USER_SUMMARY_PROMPT_TEMPLATE = PROMPT_CONFIG['generate_user_summary']

        DATASET_ID = f"{PROJECT_ID}.{DATASET_NAME}"
        USERS_TABLE_ID = f"{DATASET_ID}.{USERS_TABLE_NAME}"
        MEDIA_TABLE_ID = f"{DATASET_ID}.{MEDIA_TABLE_NAME}"
        MODEL_ID = f"`{PROJECT_ID}.{TEXT_GENERATOR_MODEL_NAME}`" # Assumes model is in same project

        GEN_PARAMS_SQL_INNER = format_gen_params_for_sql(GEN_PARAMS)
        GEN_PARAMS_SQL = f"STRUCT({GEN_PARAMS_SQL_INNER})" if GEN_PARAMS_SQL_INNER else "NULL"

    except KeyError as e:
        print(f"ERROR: Missing required key in config.yaml for AI generation: {e}")
        return

    # --- Execute Generation Steps ---
    media_success = generate_media_content(client)
    if media_success:
        user_success = generate_user_summaries(client)
        if not user_success:
             print("WARNING: User summary generation failed after media generation succeeded.")
    else:
        print("ERROR: Halting AI generation as media content step failed.")


# --- Main Execution (for direct script running) ---
if __name__ == "__main__":
    print("--- Starting AI Content Generation Script (Direct Execution) ---")

    dotenv_path_main = os.path.join(os.path.dirname(SCRIPT_DIR), '.env')
    config_path_main = os.path.join(os.path.dirname(SCRIPT_DIR), 'config.yaml')

    print(f"Loading .env from: {dotenv_path_main}")
    load_dotenv(dotenv_path=dotenv_path_main)
    PROJECT_ID_MAIN = os.getenv("PROJECT_ID")

    if not PROJECT_ID_MAIN:
        print("FATAL ERROR: GCP PROJECT_ID environment variable is not set in .env file.")
        sys.exit(1)

    try:
        print(f"Loading configuration from: {config_path_main}")
        with open(config_path_main, "r", encoding='utf-8') as f:
            config_main = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"FATAL ERROR: config.yaml not found at {config_path_main}")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL ERROR loading config.yaml: {e}")
        sys.exit(1)

    bq_client_main = get_bigquery_client(PROJECT_ID_MAIN)
    if not bq_client_main:
        print("Exiting script due to BigQuery client initialization failure.")
        sys.exit(1)

    run_ai_content_generation(bq_client_main, config_main)

    print("\n--- AI Content Generation Script (Direct Execution) Finished ---")