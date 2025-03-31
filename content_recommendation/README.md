# Trading Content Recommendation Demo

## Overview

This project demonstrates a content recommendation system built using Google Gemini, Google Cloud BigQuery and BigQuery ML (BQML). It simulates a platform providing educational trading content (articles, videos) and recommends relevant items to users based on their profiles and content similarity calculated using vector embeddings.

**Goal:** To showcase an end-to-end workflow involving synthetic data generation, AI-powered content/summary creation, embedding generation, vector search for similarity matching, and a simple user interface for displaying recommendations.

**Disclaimer:** This application is strictly a demonstration project. It uses synthetic data and simplified logic. **It is NOT intended for production use.**

## Key Features

* **Synthetic Data Generation:** Creates synthetic user profiles and media metadata using Gemini model.
    * `data_generation/synthetic_data_generators.py`
* **AI Content Generation (BQML):** Uses BigQuery ML `ML.GENERATE_TEXT` (with a configured Gemini model) to automatically generate user profile summaries and article/video transcript text based on metadata.
    * `data_generation/populate_generated_content.py`
* **Embedding Generation (BQML):** Uses BigQuery ML `ML.GENERATE_EMBEDDING` (with a configured text embedding model) to create vector representations of user summaries and media content.
    * `recommendation_engine/generate_embeddings.py`
* **Vector Search Recommendations (BQML):** Since this is lightweight application, it uses BigQuery's `VECTOR_SEARCH` function to find the most relevant media items for a given user based on embedding similarity (Cosine distance). This performs an on-demand search. For high volume use cases, use VECTOR INDEXES in BigQuery.
    * `recommendation_app.py`
* **Web User Interface (Flet):** A simple, interactive UI built with Flet that allows entering a user ID and viewing their profile details and top recommended content items. In this demo the application is served directly from BigQuery. However, for production and low latency use cases, the application should be served from either application databases or Vertex Feature Store.
    * `recommendation_app.py`

## Technology Stack

* **Language:** Python 3.x
* **UI Framework:** Flet
* **Cloud Platform:** Google Cloud Platform (GCP)
* **Data store & ML:** BigQuery, Gemini, Vertex AI

## Setup
1.  **Clone/Download:** Get the project files.
2.  **Environment Variables:** Create a `.env` file in the project root directory with your Google Cloud Project ID:
    ```plaintext
    PROJECT_ID=your-gcp-project-id
    # LOCATION=your-bq-location
    ```
3.  **Python Environment:** Create a virtual environment (recommended) and install dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```
4.  **BigQuery Setup:**
    * Ensure you have a Google Cloud project with the BigQuery API enabled.
    * Ensure your environment is authenticated (e.g., run `gcloud auth application-default login`).
    * The scripts will attempt to create the dataset specified in `config.yaml` (`bigquery.dataset_name`) if it doesn't exist.
    * **BQML Models:**
        * Make sure the BQML text generation model (`bqml_models.text_generator`) and embedding model (`bqml_models.text_embedder`) specified in `config.yaml` exist in your BigQuery dataset or are valid model references. You may need to create/deploy these separately.
        * Ensure the service account or user running the scripts has permissions to invoke these models.
    * **(Optional) Vector Index:** For larger datasets (>>5000 media items), create a vector index on the `media_embeddings` table for better `VECTOR_SEARCH` performance. Use the DDL command (see `vectors.vector_index.sql` artifact), adjusting parameters as needed. For the small dataset size in the default config, the index is not required, and `VECTOR_SEARCH` will use brute force.

## Running the Application

1.  **Generate Data & AI Content:**
    * Run the initial data generation script. The `--generate-ai-content` flag runs the BQML text generation step immediately after loading initial data.
    ```bash
    python data_generation/generate_initial_data.py --generate-ai-content
    ```
2.  **Generate Embeddings:**
    * Run the embedding generation script.
    ```bash
    python vectors/generate_embeddings.py --target all
    ```
3.  **Run the Flet UI:**
    * Start the recommendation application.
    ```bash
    python recommendation_app.py
    ```
    * Enter a valid User ID (e.g., `user_001`, `user_002` based on the default config) into the input field and click "Find Recommendations".

## Helpful Links

* **Google BigQuery:** [https://cloud.google.com/bigquery](https://cloud.google.com/bigquery)
* **BigQuery ML Overview:** [https://cloud.google.com/bigquery/docs/bqml-introduction](https://cloud.google.com/bigquery/docs/bqml-introduction)
* **BQML `ML.GENERATE_TEXT`:** [https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-text](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-text)
* **BQML `ML.GENERATE_EMBEDDING`:** [https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-embedding](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-embedding)
* **BQML `VECTOR_SEARCH` Function:** [https://cloud.google.com/bigquery/docs/vector-search](https://cloud.google.com/bigquery/docs/vector-search)
* **BQML `ML.DISTANCE` Function:** [https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-distance](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-distance)

