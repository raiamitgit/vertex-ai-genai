import os
from dotenv import load_dotenv
from google.cloud import bigquery

# Load environment variables
load_dotenv()

# ===========================
# --- Configuration ---
# ===========================
def get_config() -> dict:
    """
    Retrieves, validates, and constructs configuration from environment variables.

    Returns:
        dict: A dictionary containing all necessary project, BQ, GCS, and Model IDs.
    
    Raises:
        ValueError: If critical environment variables are missing.
    """
    config = {
        "PROJECT_ID": os.getenv("BQ_PROJECT_ID"),
        "DATASET_ID": os.getenv("BQ_DATASET_ID"),
        "METADATA_TABLE": os.getenv("BQ_METADATA_TABLE"),
        "STAGING_TABLE": f"{os.getenv('BQ_METADATA_TABLE')}_staging_raw",
        "BQ_REGION": os.getenv("BQ_REGION"),
        "CONNECTION_ID": os.getenv("BQ_CONNECTION_ID"), 
        "MODEL_NAME": os.getenv("BQ_MODEL_NAME"),
        "BQ_GEMINI_MODEL": os.getenv("BQ_GEMINI_MODEL"),
        "OBJECT_TABLE_NAME": os.getenv("BQ_OBJECT_TABLE", "physna_images_obj"),
        "GCS_BUCKET": os.getenv("GCS_BUCKET_NAME"),
        "GCS_URI_PATTERN": f"gs://{os.getenv('GCS_BUCKET_NAME')}/{os.getenv('GCS_THUMBNAIL_FOLDER', '').strip('/')}/*",
    }
    if not all([config['PROJECT_ID'], config['DATASET_ID'], config['METADATA_TABLE']]):
         raise ValueError("Missing critical BQ environment variables.")

    config["FULL_MODEL_ID"] = f"{config['PROJECT_ID']}.{config['DATASET_ID']}.{config['MODEL_NAME']}"
    config["FULL_OBJ_TABLE_ID"] = f"{config['PROJECT_ID']}.{config['DATASET_ID']}.{config['OBJECT_TABLE_NAME']}"
    config["FULL_META_TABLE_ID"] = f"{config['PROJECT_ID']}.{config['DATASET_ID']}.{config['METADATA_TABLE']}"
    config["FULL_STAGING_TABLE_ID"] = f"{config['PROJECT_ID']}.{config['DATASET_ID']}.{config['STAGING_TABLE']}"
    config["FULL_CONNECTION_ID"] = f"{config['PROJECT_ID']}.{config['BQ_REGION']}.{config['CONNECTION_ID']}"
    return config

# ===========================
# --- Prompt Definition ---
# ===========================
GEMINI_PROMPT_TEMPLATE = """
Role: Automotive Supply Chain & Engineering Analyst.
Task: Analyze the image of this steering assembly part and generate specific, realistic metadata for a supply chain demo.

Context:
- Part Name: '{{part_name}}'
- Physna Folder: '{{folder_context}}'

Instructions & Logic:
1.  **Identify Vehicle:** Extract the vehicle platform (Equinox EV, Optiq, or Vistiq) directly from the provided 'Physna Folder' context.
2.  **Analyze Part:** Determine its material, finish, and function from the image.
3.  **Apply Demo Logic:**
    *   If the vehicle is **Vistiq**, the `finish` MUST be "Zinc-Plated" and `engineering_notes` MUST mention "Zinc-plating required for corrosion resistance on Vistiq platform due to specific underbody exposure."
    *   For other vehicles, generate a plausible finish (e.g., "None", "E-Coat") and appropriate notes.
4.  **Suppliers & Risk:** Select a realistic supplier from the list below. Assign `supplier_risk_rating` and `country_of_origin` to create a varied risk profile.
    -  **Apex Forge & Casting** (Good for heavy metal parts like knuckles or shafts)
    -  **Global Motion Systems** (Good for a Tier 1 integrator of complete assemblies)
    -  **Velos Precision Components** (Good for machined parts like tie rods)
    -  **OmniSteer Solutions** (Specialized steering supplier)
    -  **Titan Metalworks Intl.** (Raw materials or heavy stampings)
    -  **AccuForm Technologies** (Precision formed parts/brackets)
    -  **ElectraDrive Controls** (For electronic steering modules/sensors)
    -  **Sterling Manufacturing Group** (A legacy, generalist supplier)
    -  **InnovaTech Automotive** (Modern, perhaps higher-cost components)
    -  **United Industrial Supply** (Good for commodities like fasteners/bolts)
5.  **Economics:** Generate realistic `cost_per_unit_usd`, `annual_demand_units`, etc.

Output Requirement: Return ONLY a single valid JSON object.

Required JSON Structure:
{
    "detailed_part_description": "String. Start with deduced function, then visual characteristics.",
    "material": "String (e.g., Grade 5 Steel, 6061 Aluminum, ABS Plastic)",
    "finish": "String (Apply Vistiq logic above. e.g., Zinc-Plated, None, Powder Coated)",
    "weight_kg": Float (Realistic estimate),
    "revision_number": Integer (e.g., 1, 2, 3),
    "engineering_notes": "String (Context/Root cause. Apply Vistiq logic above.)",
    "source_vehicle_platform": "String (based on the `Physna Folder` name above - Chevy Equinox or Buick Optiq or Cadillac Vistiq)",
    "annual_demand_units": Integer (Realistic volume, e.g. 50,000 - 300,000)",
    "primary_supplier_name": "String (From Approved List)",
    "supplier_id": "String (Generate realistic ID like SUP-XXXX)",
    "cost_per_unit_usd": Float (Realistic, e.g., 0.50 to 25.00),
    "lead_time_weeks": Integer (e.g., 4 to 16),
    "country_of_origin": "String (e.g., USA, Mexico, China, Germany)",
    "supplier_risk_rating": "String (Low, Medium, High)",
    "current_inventory_on_hand": Integer (Realistic snapshot)
}
"""

# ===========================
# --- BQ Operations ---
# ===========================
def setup_bqml_resources(client: bigquery.Client, cfg: dict):
    """
    Configures the BigQuery ML Model (Gemini) and Object Table (GCS link).

    Args:
        client (bigquery.Client): BQ client.
        cfg (dict): Configuration dictionary.
    """
    print("--- Setup: Creating/Updating BQML Model and Object Table ---")
    setup_sql = f"""
    BEGIN
        CREATE OR REPLACE MODEL `{cfg['FULL_MODEL_ID']}`
        REMOTE WITH CONNECTION `{cfg['FULL_CONNECTION_ID']}`
        OPTIONS(endpoint = '{cfg['BQ_GEMINI_MODEL']}');

        CREATE OR REPLACE EXTERNAL TABLE `{cfg['FULL_OBJ_TABLE_ID']}`
        WITH CONNECTION `{cfg['FULL_CONNECTION_ID']}`
        OPTIONS (
            object_metadata = 'SIMPLE',
            uris = ['{cfg['GCS_URI_PATTERN']}']
        );
    END;
    """
    try:
        client.query(setup_sql).result()
        print(f"Resources configured. Object Table points to: {cfg['GCS_URI_PATTERN']}")
    except Exception as e:
        print(f"ERROR: Failed to setup BQML resources. Details: {e}")
        raise

# --- STEP 1: Generate & Stage ---
def generate_and_stage_data(client: bigquery.Client, cfg: dict) -> int:
    """
    Step 1: Runs Gemini on all parts, cleans output, and saves to a staging table.

    Generates a prompt per row using foundation data context. Extracts, cleans,
    and parses the Gemini JSON output. Filters out failures.

    Returns:
        int: Number of successfully generated and staged records.
    """
    print(f"\n--- Step 1: Generating Gemini Results & Staging Clean JSON ---")
    print(f"Target Staging Table: {cfg['FULL_STAGING_TABLE_ID']}")

    raw_prompt = GEMINI_PROMPT_TEMPLATE.strip()
    json_text_path = '$.candidates[0].content.parts[0].text'

    staging_sql = f"""
    CREATE OR REPLACE TABLE `{cfg['FULL_STAGING_TABLE_ID']}` AS
    SELECT
        raw.part_id,
        raw.gemini_complex_result, -- Keep for debugging
        SAFE.PARSE_JSON(
            REGEXP_REPLACE(
                TRIM(JSON_VALUE(raw.gemini_complex_result, '{json_text_path}')),
                r'^```(?:json)?\s*|\s*```$', 
                ''
            )
        ) AS cleaned_json_payload
    FROM (
        SELECT
            base.part_id,
            ml.ml_generate_text_result as gemini_complex_result
        FROM `{cfg['FULL_META_TABLE_ID']}` base
        JOIN `{cfg['FULL_OBJ_TABLE_ID']}` imgs
          ON base.gcs_image_path = imgs.uri
        LEFT JOIN ML.GENERATE_TEXT(
            MODEL `{cfg['FULL_MODEL_ID']}`,
            (
                SELECT 
                    uri, 
                    REPLACE(
                        REPLACE(
                            r'''{raw_prompt}''', 
                            '{{{{part_name}}}}', COALESCE(base.part_name, 'Unknown')
                        ),
                        '{{{{folder_context}}}}', COALESCE(base.physna_folder_name, 'Unknown')
                    ) AS prompt 
                FROM `{cfg['FULL_META_TABLE_ID']}` base
                JOIN `{cfg['FULL_OBJ_TABLE_ID']}` imgs ON base.gcs_image_path = imgs.uri
            ),
            STRUCT(0.1 AS temperature, 64000 AS max_output_tokens)
        ) ml ON imgs.uri = ml.uri
        WHERE ml.ml_generate_text_result IS NOT NULL
    ) raw
    WHERE 
      JSON_VALUE(raw.gemini_complex_result, '{json_text_path}') IS NOT NULL 
      AND
      SAFE.PARSE_JSON(
        REGEXP_REPLACE(TRIM(JSON_VALUE(raw.gemini_complex_result, '{json_text_path}')), r'^```(?:json)?\s*|\s*```$', '')
      ) IS NOT NULL
    """

    print("Executing Gemini generation and staging...")
    job = client.query(staging_sql)
    job.result()

    table = client.get_table(cfg['FULL_STAGING_TABLE_ID'])
    row_count = table.num_rows
    print(f"Step 1 Complete. Staged {row_count} records with successfully parsed JSON.")
    return row_count

# --- STEP 2: Merge Staging to Main ---
def merge_staging_to_main(client: bigquery.Client, cfg: dict):
    """
    Step 2: Merges clean data from staging into the main metadata table.

    Uses JSON_VALUE to extract fields from the staged JSON payload and updates
    matching part_id rows in the main table.
    """
    print(f"\n--- Step 2: Merging Clean Data from Staging to Main ---")

    merge_sql = f"""
    MERGE `{cfg['FULL_META_TABLE_ID']}` T
    USING `{cfg['FULL_STAGING_TABLE_ID']}` S
    ON T.part_id = S.part_id
    WHEN MATCHED THEN
        UPDATE SET
            detailed_part_description = JSON_VALUE(S.cleaned_json_payload, '$.detailed_part_description'),
            material = JSON_VALUE(S.cleaned_json_payload, '$.material'),
            finish = JSON_VALUE(S.cleaned_json_payload, '$.finish'),
            weight_kg = CAST(JSON_VALUE(S.cleaned_json_payload, '$.weight_kg') AS FLOAT64),
            revision_number = CAST(JSON_VALUE(S.cleaned_json_payload, '$.revision_number') AS INT64),
            engineering_notes = JSON_VALUE(S.cleaned_json_payload, '$.engineering_notes'),
            source_vehicle_platform = JSON_VALUE(S.cleaned_json_payload, '$.source_vehicle_platform'),
            annual_demand_units = CAST(JSON_VALUE(S.cleaned_json_payload, '$.annual_demand_units') AS INT64),
            primary_supplier_name = JSON_VALUE(S.cleaned_json_payload, '$.primary_supplier_name'),
            supplier_id = JSON_VALUE(S.cleaned_json_payload, '$.supplier_id'),
            cost_per_unit_usd = CAST(JSON_VALUE(S.cleaned_json_payload, '$.cost_per_unit_usd') AS FLOAT64),
            lead_time_weeks = CAST(JSON_VALUE(S.cleaned_json_payload, '$.lead_time_weeks') AS INT64),
            country_of_origin = JSON_VALUE(S.cleaned_json_payload, '$.country_of_origin'),
            supplier_risk_rating = JSON_VALUE(S.cleaned_json_payload, '$.supplier_risk_rating'),
            current_inventory_on_hand = CAST(JSON_VALUE(S.cleaned_json_payload, '$.current_inventory_on_hand') AS INT64)
    """

    print("Executing MERGE query...")
    job = client.query(merge_sql)
    job.result()
    print(f"Step 2 Complete. Successfully updated {job.num_dml_affected_rows} records in main table.")

# ===========================
# --- Main Execution ---
# ===========================
def main():
    """Orchestrates the Gemini Enrichment pipeline (Setup -> Generate/Stage -> Merge)."""
    print("=== Starting Multi-Step BigQuery/Gemini Enrichment ===")
    try:
        config = get_config()
        bq_client = bigquery.Client(project=config["PROJECT_ID"])
        setup_bqml_resources(bq_client, config)
        
        staged_count = generate_and_stage_data(bq_client, config)
        
        if staged_count > 0:
            merge_staging_to_main(bq_client, config)
        else:
            print("\n[STOP] No valid results generated in Step 1.")

    except Exception as e:
        print(f"\n🛑 GCP/BigQuery Error: {e}")
    except Exception as e:
        print(f"\n🛑 Program Error: {e}")
    print("=== Finished ===")

if __name__ == "__main__":
    main()