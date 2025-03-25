import flet as ft
import os
import yaml
from dotenv import load_dotenv
from google.cloud import bigquery

# Load environment variables
load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

# Load configuration
try:
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    BQ_DATASET = config['bigquery']['dataset_name']
    BQ_RECOMMENDATIONS_TABLE = config['bigquery']['recommendations_table_name']
    BQ_MEDIA_TABLE = config['bigquery']['media_table_name']
    ONLINE_RECOMMENDATION_CONFIG = config['online_recommendation']
    TOP_N_RETRIEVE = ONLINE_RECOMMENDATION_CONFIG.get('top_n_to_retrieve', 5)
except FileNotFoundError:
    print("Error: config.yaml not found. Please create it.")
    exit()
except KeyError as e:
    print(f"Error: Missing configuration key in config.yaml: {e}")
    exit()

def get_bigquery_client(project_id):
    """Authenticates and returns a BigQuery client."""
    try:
        client = bigquery.Client(project=project_id)
        print(f"Successfully authenticated to BigQuery project: {project_id}")
        return client
    except Exception as e:
        print(f"Error authenticating to BigQuery: {e}")
        return None

def get_recommendations_with_snippets(user_id, top_n, bq_client, project_id, dataset_name, recommendations_table, media_table):
    """Retrieves top N recommendations for a given user with content snippets."""
    query = f"""
    SELECT
        r.recommended_media_id,
        m.title,
        m.type,
        m.content,
        m.transcript
    FROM
        `{project_id}.{dataset_name}.{recommendations_table}` r
    JOIN
        `{project_id}.{dataset_name}.{media_table}` m ON r.recommended_media_id = m.media_id
    WHERE
        r.user_id = @user_id
    ORDER BY
        r.rank
    LIMIT @top_n
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
            bigquery.ScalarQueryParameter("top_n", "INTEGER", top_n),
        ]
    )
    try:
        query_job = bq_client.query(query, job_config=job_config)
        results = query_job.result()
        recommendations = []
        for row in results:
            recommendations.append({
                "media_id": row.recommended_media_id,
                "title": row.title,
                "type": row.type,
                "content": row.content,
                "transcript": row.transcript
            })
        return recommendations
    except Exception as e:
        print(f"Error retrieving recommendations: {e}")
        return []

def main(page: ft.Page):
    page.title = "Trading Content Recommendations"
    page.padding = 50
    page.theme_mode = ft.ThemeMode.LIGHT

    user_id_input = ft.TextField(label="Enter User ID", width=300)
    results_column = ft.Column(spacing=20)
    error_text = ft.Text("", color=ft.colors.RED)

    def fetch_recommendations(e):
        results_column.controls.clear()
        error_text.value = ""
        user_id = user_id_input.value.strip()
        if not user_id:
            error_text.value = "Please enter a User ID."
            page.update()
            return

        if not PROJECT_ID or not LOCATION:
            error_text.value = "Error: PROJECT_ID and LOCATION environment variables not set."
            page.update()
            return

        bq_client = get_bigquery_client(PROJECT_ID)
        if not bq_client:
            error_text.value = "Error: Could not connect to BigQuery."
            page.update()
            return

        recommendations = get_recommendations_with_snippets(
            user_id,
            TOP_N_RETRIEVE,
            bq_client,
            PROJECT_ID,
            BQ_DATASET,
            BQ_RECOMMENDATIONS_TABLE,
            BQ_MEDIA_TABLE
        )

        if recommendations:
            for rec in recommendations:
                snippet = ""
                if rec['type'] == 'article' and rec['content']:
                    snippet = rec['content'][:200] + "..."
                elif rec['type'] == 'video' and rec['transcript']:
                    snippet = rec['transcript'][:200] + "..."

                results_column.controls.append(
                    ft.Card(
                        elevation=2,
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text(f"{rec['title']} ({rec['type']})", weight=ft.FontWeight.BOLD),
                                ft.Text(f"ID: {rec['media_id']}", size=10),
                                ft.Text(snippet, selectable=True),
                            ]),
                            width=600,
                            padding=10,
                        )
                    )
                )
        else:
            results_column.controls.append(ft.Text(f"No recommendations found for user {user_id}."))

        page.update()

    get_recommendations_button = ft.ElevatedButton("Get Recommendations", on_click=fetch_recommendations)

    page.add(
        ft.Row([user_id_input, get_recommendations_button], alignment=ft.MainAxisAlignment.START),
        error_text,
        ft.Text("Recommendations:", weight=ft.FontWeight.BOLD, size=16),
        results_column,
    )

if __name__ == "__main__":
    ft.app(target=main)