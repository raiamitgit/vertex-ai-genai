# Part Rationalization and Search Agent

This project provides a comprehensive solution for rationalizing engineering parts by leveraging geometric search, multimodal AI, and a robust data pipeline. It features an AI agent built with the Agent Development Kit (ADK) that allows engineers to find similar parts using either an existing part ID or an image, and to retrieve detailed supply chain and engineering metadata from a BigQuery database.

-----

## 🏛️ System Architecture

The system is composed of two main components: a **Data Pipeline** for enriching part data and an **AI Agent** for user interaction and search.

1.  **Data Pipeline**:

      * **Ingestion**: Asset metadata and 2D thumbnails are fetched from the **Physna** API.
      * **Storage**: Thumbnails are stored in **Google Cloud Storage (GCS)**.
      * **Enrichment**: A BigQuery ML model using **Gemini** generates synthetic supply chain and engineering data based on the part images and metadata.
      * **Embedding**: A multimodal embedding model generates vector embeddings for each part image to enable visual search.
      * **Data Warehouse**: All data is stored and managed in **BigQuery**.

2.  **AI Agent**:

      * **Framework**: Built using the **Google ADK**.
      * **Tools**: The agent is equipped with tools to:
          * `search_parts_by_asset_id`: Perform geometric similarity search via the Physna API.
          * `search_parts_by_image_upload`: Use BigQuery vector search to find visually similar parts from an uploaded image.
          * `fetch_details_from_database`: Retrieve detailed part attributes from the master BigQuery table.
      * **Deployment**: The agent is deployed as a **Agent Engine** on Vertex AI and registered with **Agentspace** for discoverability.

-----

## ✨ Features

  * **Geometric Part Search**: Find similar parts based on an existing Physna Asset ID.
  * **Visual Search**: Find similar parts by uploading a 2D image (e.g., a photo of a part).
  * **Detailed Data Retrieval**: Access rich, AI-generated metadata, including material, cost, supplier information, inventory levels, and engineering notes.
  * **Automated Data Enrichment**: A robust pipeline that automatically generates context-aware metadata for new parts.
  * **Scalable Architecture**: Built on serverless Google Cloud services like BigQuery, GCS, and Vertex AI.

-----

## 🚀 Getting Started

### 1\. Prerequisites

  * **Python 3.9+**
  * **Google Cloud Platform (GCP) Project**:
      * APIs Enabled: BigQuery, Cloud Storage, Vertex AI.
      * A GCS Bucket.
      * A BigQuery Dataset.
      * A BigQuery Cloud Resource Connection with appropriate IAM roles (`Vertex AI User`, `Storage Object Viewer`).
  * **Physna API Access**:
      * Tenant ID, Client ID, and Client Secret.

### 2\. Configuration

1.  Clone the repository.
2.  Create a `.env` file by copying the `.env.example` file.
3.  Populate the `.env` file with your specific GCP and Physna credentials and resource names.

### 3\. Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

-----

## ⚙️ Usage

The project is divided into two main workflows: running the data pipeline to populate your database and deploying the agent to interact with that data.

### Data Pipeline

The data pipeline populates and enriches the BigQuery database. Run the scripts in the `generate_data/` folder in the following order.

1.  **Ingest Assets from Physna (`physna_assets.py`)**:
    This script fetches asset metadata from Physna, uploads their thumbnails to GCS, and creates the initial "foundation" table in BigQuery.

    ```bash
    python generate_data/physna_assets.py
    ```

2.  **Generate Synthetic Metadata (`product_metadata.py`)**:
    This script uses a Gemini model via BigQuery ML to generate detailed, synthetic supply chain and engineering data for each part based on its image and name. The results are then merged into the main table.

    ```bash
    python generate_data/product_metadata.py
    ```

3.  **Generate Image Embeddings (`image_embedding.py`)**
    This script creates vector embeddings from the part images and stores them in BigQuery. This enables the visual search capability. It also creates a vector index for efficient searching on large datasets.

    ```bash
    python generate_data/image_embedding.py
    ```

### Agent Deployment & Management

The scripts to deploy and manage the agent are in the `agentspace/manage/` folder.

1.  **Deploy the Agent Engine (`deploy.py`)**:
    This script packages the ADK agent, its tools, and dependencies, and deploys it to Vertex AI as a Reasoning Engine.

    ```bash
    python agentspace/manage/deploy.py
    ```

    After deployment, copy the output **Resource Name** into your `.env` file as `AGENT_ENGINE_RESOURCE_NAME`.

2.  **Register with Agentspace (`register.py`)**:
    This script makes the deployed agent discoverable within an Agentspace-enabled application.

    ```bash
    python agentspace/manage/register.py
    ```

3.  **Unregister and Delete (`unregister.py`)**:
    This script can be used to remove the agent from Agentspace and delete the Agent Engine deployment from Vertex AI.

    ```bash
    # Unregister from Agentspace only
    python agentspace/manage/unregister.py --unregister

    # Delete the Agent Engine deployment only
    python agentspace/manage/unregister.py --delete
    ```

-----

## 🧪 Testing

The project includes tests to validate the functionality of the agent and its tools. The tests are located in the `tests/` directory.

  * `test_physna_tools.py`: Directly tests the functions in `physna_tool.py` for both asset ID and image-based search workflows.
  * `test_agent.py`: Runs integration test scenarios against the ADK agent, simulating user interactions for different search types.

To run the tests, ensure your `.env` file is correctly configured and execute the scripts:

```bash
python tests/test_physna_tools.py
python tests/test_agent.py
```