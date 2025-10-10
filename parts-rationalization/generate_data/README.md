# Physna to BigQuery: Supply Chain Metadata Enrichment Pipeline
This folder contains a two-part data pipeline designed to ingest asset thumbnails from Physna, store representative images in Google Cloud Storage (GCS), and utilize BigQuery ML (Gemini) to generate synthetic, context-aware supply chain and engineering metadata.

## Overview

The pipeline transforms raw 3thumbnail asset data into a unified, enriched BigQuery data warehouse table ready for analysis or dashboarding.

It consists of two Python scripts intended to be run sequentially:

1.  **`physna_assets.py` (Ingest):** Fetches asset metadata from Physna, downloads 2D thumbnails in parallel, uploads them to GCS, and initializes the BigQuery table with "foundation" data.
2.  **`product_metadata.py` (Enrich):** Uses the foundation data and GCS images to prompt Gemini (via BigQuery ML). It generates synthetic business and engineering details (e.g., suppliers, costs, materials, risks) based on specific vehicle platform logic and merges this data back into the main table.

---

## Prerequisites

Before running these scripts, ensure you have the following:

### 1. System & Python
*   Python 3.9+
*   Required Python packages installed:
    ```bash
    pip install requests python-dotenv google-cloud-storage google-cloud-bigquery
    ```

### 2. Physna Access
*   Tenant ID, Client ID, and Client Secret for API access.
*   Access to the target vehicle folders defined in the scripts.

### 3. Google Cloud Platform (GCP)
*   Active GCP Project with billing enabled.
*   **APIs Enabled:** BigQuery API, Cloud Storage API, Vertex AI API.
*   **GCS Bucket:** A bucket created to store the thumbnails.
*   **BigQuery Dataset:** A dataset created to host the metadata tables.
*   **BigQuery Cloud Resource Connection:** A connection (e.g., type Vertex AI) created in BigQuery.
    *   *Crucial:* The Service Account associated with this connection must have `Vertex AI User` and `Storage Object Viewer` (for the GCS bucket) IAM roles.

---

## Configuration (.env)

Create a `.env` file in the same folder as the scripts. Populate it with the following variables:

```ini
# =========================
# PHYSNA Configuration
# =========================
AUTH_URL=https://your-physna-auth-url/oauth/token
PHYSNA_TENANT_ID=your-tenant-uuid
PHYSNA_CLIENT_ID=your-client-id
PHYSNA_CLIENT_SECRET=your-client-secret

# =========================
# Google Cloud Storage (GCS)
# =========================
# The bucket where images will be stored
GCS_BUCKET_NAME=your-gcp-bucket-name
# The subfolder within the bucket (optional, defaults to physna_thumbnails/)
GCS_THUMBNAIL_FOLDER=physna_thumbnails/

# =========================
# BigQuery Configuration
# =========================
BQ_PROJECT_ID=your-gcp-project-id
BQ_DATASET_ID=your_bq_dataset_name
# The name of the main output table
BQ_METADATA_TABLE=master_part_list_enriched

# Region must match your Dataset and Connection
BQ_REGION=us-central1

# The ID of the Cloud Resource Connection (just the ID, e.g., "vertex-conn")
BQ_CONNECTION_ID=your-bq-connection-id

# =========================
# Gemini Model Config
# =========================
# Name for the Model Reference created inside BigQuery
BQ_MODEL_NAME=physna_gemini_ref
# The actual Vertex AI endpoint to use (must be vision capable)
BQ_GEMINI_MODEL=gemini-1.5-flash
# Name for the Object Table created inside BigQuery
BQ_OBJECT_TABLE=physna_images_obj
```

---

## Usage Instructions

Run the scripts in the following order. Ensure your local environment is authenticated with GCP (e.g., via `gcloud auth application-default login`).

### Step 1: Run Ingestion
This script fetches assets, performs multithreaded image uploads to GCS, and creates/resets the BigQuery table with foundation data.

```bash
python physna_assets.py
```
*Configuration Flags in script:* You can adjust `ASSET_LIMIT` (set to 0 for all) or `MAX_WORKERS` (threading) directly in the `physna_assets.py` file.

### Step 2: Run Enrichment
Once Step 1 is complete and images are in GCS/data is in BQ, run the enrichment script. This sets up BQML resources, runs Gemini on the images, stages the results, and merges them into the main table.

```bash
python product_metadata.py
```
*Note:* This step can take time depending on the number of assets, as it calls the Gemini API for every part image.

---

## Data Output & Logic

The final BigQuery table (`BQ_METADATA_TABLE`) will contain the following schema.

### Demo Logic Applied
The `product_metadata.py` script applies specific logic based on the source Physna folder:
*   **Vehicle Identification:** Extracts `Equinox EV`, `Optiq`, or `Vistiq` from the folder name.
*   **Vistiq Rule:** If the vehicle is "Vistiq", Gemini is instructed to set the `finish` to "Zinc-Plated" and add a specific corrosion-related engineering note.

### Schema

| Category | Column Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **Foundation** | `part_id` | STRING | Primary Key. Unique GM part number (Physna Asset ID). |
| (From Physna) | `part_name` | STRING | Common engineering name derived from filename. |
| | `physna_folder_name` | STRING | The folder in Physna (provides vehicle context). |
| | `physna_path` | STRING | Specific file path in Physna. |
| | `gcs_image_path` | STRING | gs:// URI to the stored 2D image. |
| **Enriched** | `detailed_part_description`| STRING | AI-generated description of function/visuals. |
| (From Gemini) | `source_vehicle_platform` | STRING | Extracted vehicle (Equinox EV, Optiq, Vistiq). |
| | `material` | STRING | AI-deduced material (e.g., Steel, Aluminum). |
| | `finish` | STRING | Surface finish (applies Vistiq Zinc rule). |
| | `engineering_notes` | STRING | Contextual notes/root cause info. |
| | `primary_supplier_name` | STRING | Selected from approved supplier list. |
| | `supplier_risk_rating` | STRING | Synthetic risk (Low, Medium, High). |
| | `cost_per_unit_usd` | FLOAT64 | Synthetic realistic cost. |
| | `[...others]` | ... | (weight, revision, demand, inventory, etc.) |

---

## Troubleshooting

*   **GCP Permissions Errors in Step 2:** Ensure the BigQuery Connection ID service account has `Storage Object Viewer` on the GCS bucket and `Vertex AI User` roles.
*   **0 Rows Enriched in Step 2:** Check the console output. If Gemini blocked images due to safety filters, or if the returned JSON structure didn't match the extraction path, rows might not be merged. Review the staging table (`[BQ_METADATA_TABLE]_staging_raw`) in BigQuery to inspect raw Gemini outputs.
*   **Physna Auth Errors:** Verify credentials and `AUTH_URL` in `.env`. Ensure the client has access to the requested tenant.