# Content Recommendation System for Trading Platform (Demo)

## Overview

This project demonstrates a content recommendation system designed for a hypothetical futures trading platform. It generates personalized learning material recommendations (articles and videos) for users based on their profile and simulated trading history. The system leverages Google Cloud services, specifically **BigQuery** for data storage and **Vertex AI** for generating text embeddings. A simple web interface is provided using **Flet** to retrieve recommendations for a specific user on-demand.

**Key Features:**

* **Synthetic Data Generation:** Creates realistic-looking user profiles, media content (articles/videos), and interaction data if none exists.
* **Embedding-Based Recommendations:** Uses Vertex AI's text embedding models to represent users and content in a vector space[cite: 1].
* **Batch Recommendation Pipeline:** Calculates and stores the top N recommendations for all users in BigQuery[cite: 1].
* **Online Recommendation Retrieval:** Fetches pre-calculated recommendations for a specific user via a simple UI.
* **Configurable:** Uses a `config.yaml` file to manage settings for data generation, BigQuery tables, embedding models, and recommendation parameters.

**Approach:** This system is designed for scenarios where explicit user interaction data (like clicks, ratings, views) is unavailable[cite: 1]. It relies on generating embeddings from user profile data (experience, goals, trading activity) and media content (titles, descriptions, transcripts) to find relevant matches based on semantic similarity.

**WARNING:** This is a demo application intended for educational and illustrative purposes only. It uses synthetic data and simplified logic[cite: 1]. **It is NOT designed for production use** and lacks critical features like robust error handling, security measures, performance optimizations, monitoring, and A/B testing. Do NOT deploy this code in a live environment without significant modification, thorough testing, and expert review[cite: 1].

## Project Structure

content-recommendation/
├── data_generation/
│   ├── generate_data.py        # Script to generate synthetic data
│   └── utils/
│       ├── synthetic_data.py   # Functions for creating synthetic user/media items
│       └── bigquery_utils.py   # Utilities for BigQuery interactions
├── recommendation_engine/
│   ├── create_recommendation.py # Batch pipeline: generates embeddings & recommendations
│   ├── embeddings.py           # Handles interaction with Vertex AI Embedding API
│   └── recommender.py          # Calculates similarity and finds top recommendations
├── recommendation_app.py       # Flet application for online recommendation retrieval
├── config.yaml                 # Configuration file for the project
├── requirements.txt            # Python dependencies
└── README.md                   # This file 

## Setup and Configuration

1.  **Google Cloud Project:**
    * Ensure you have an active Google Cloud Project.
    * Enable the **BigQuery API** and **Vertex AI API** in your project[cite: 1].

2.  **Authentication:**
    * **Service Account (Recommended):**
        * Create a service account in your GCP project.
        * Grant it the following IAM roles:
            * `BigQuery Data Editor` [cite: 1]
            * `BigQuery Job User` [cite: 1]
            * `Vertex AI User` [cite: 1]
        * Download the service account key JSON file[cite: 1].
    * **Application Default Credentials (ADC):** Alternatively, configure ADC locally (e.g., via `gcloud auth application-default login`).

3.  **Environment Variables:**
    * Create a `.env` file in the project's root directory (`content-recommendation/`).
    * Add the following, replacing placeholders with your values:
        ```env
        # If using a service account key:
        GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service_account_key.json

        # Your GCP Project ID and Location:
        PROJECT_ID=your-gcp-project-id
        LOCATION=us-central1 # Or your preferred GCP region
        ```
    * The scripts rely on these variables for authentication and connecting to GCP services[cite: 1].

4.  **Configuration File (`config.yaml`):**
    * Review and adjust parameters in `config.yaml`:
        * `data_generation`: Control the amount of synthetic data (users, articles, videos).
        * `bigquery`: Define the dataset and table names to be used/created.
        * `embedding_model`: Specify the Vertex AI embedding model (e.g., `text-embedding-004`) and API parameters.
        * `batch_recommendation`: Set the number of recommendations to *store* per user and the similarity metric (`cosine` or `euclidean`).
        * `online_recommendation`: Set the number of recommendations to *retrieve* in the Flet app.

## Installation

1.  **Clone the Repository** (if you haven't already).
2.  **Navigate to Project Directory:**
    ```bash
    cd content-recommendation
    ```
3.  **Install Dependencies:** Create a virtual environment (recommended) and install packages:
    ```bash
    pip install -r requirements.txt
    ```
    This installs libraries like `google-cloud-bigquery`, `google-cloud-aiplatform`, `scikit-learn`, `flet`, etc..

## Usage Workflow

### 1. Generate Synthetic Data (Optional)

If you don't have existing user and media data in the specified BigQuery tables, run the generation script. **Note:** This will *truncate* (delete all data from) the target tables before inserting new data.

```bash
python -m data_generation/generate_data.py
```

This script uses functions from utils/synthetic_data.py and utils/bigquery_utils.py to create and upload data.

2. Run Batch Recommendation Pipeline
This is the core process that generates embeddings and recommendations for all users.

```bash
python -m recommendation_engine/create_recommendation.py
```

Fetches user and media data from BigQuery.
Prepares text descriptions for users and media.
Calls the Vertex AI API via embeddings.py to get embeddings.
Calculates similarities using functions in recommender.py.
Deletes the old recommendations table and writes the top N new recommendations per user to the specified BigQuery table (user_recommendations by default).
This script should ideally be scheduled to run regularly (e.g., daily or weekly) using a tool like Google Cloud Scheduler or Cloud Composer.

3. Retrieve Recommendations On-Demand (Flet App)
Run the Flet application to look up recommendations for a specific user.

```bash
python recommendation_app.py
```

This starts a local web application.
Enter a user_id (e.g., user_001 if using generated data) into the input field.
Click "Get Recommendations".
The app queries the user_recommendations BigQuery table to fetch the top recommendations (with content snippets) stored during the batch process.

Customization
Embedding Model: Change `embedding_model.model_name` in `config.yaml` to use a different compatible Vertex AI model.
Similarity Metric: Modify `batch_recommendation.similarity_metric` in `config.yaml` (cosine or euclidean). The calculation logic is in `recommender.py`.
Recommendation Logic: For strategies beyond simple embedding similarity, modify `recommendation_engine/recommender.py` and potentially `create_recommendation.py`.
Text Preparation: Adjust the text formatting logic in `utils/bigquery_utils.py` (`prepare_user_text_for_embedding`, `prepare_media_text_for_embedding`) to better represent your specific user/content data for embedding. A better approach is to use LLMs, such as Gemini models, to generate the user profile by provide it much richer data. Improve the profile by indexing it more towards the latest data signals.
Data Source: Modify `data_generation/generate_data.py` and `recommendation_engine/create_recommendation.py` to read from your actual data sources instead of generating/using the synthetic ones.