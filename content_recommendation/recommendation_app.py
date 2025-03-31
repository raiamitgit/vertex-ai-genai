"""
Flet UI application to display content recommendations based on user profiles.

Fetches user details and recommendations from BigQuery using vector search.
"""
import flet as ft
import os
import sys
import yaml
from dotenv import load_dotenv
from google.cloud import bigquery
from typing import List, Dict, Optional, Any

# --- Setup Project Root Path ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Import project modules ---
from utils.bigquery_utils import get_bigquery_client, fetch_bq_results

# --- Constants ---
SNIPPET_LENGTH = 200 # Max characters for content snippet in list view

# --- Global variables ---
APP_CONFIG: Optional[Dict[str, Any]] = None
BQ_CLIENT: Optional[bigquery.Client] = None
INITIAL_ERROR: Optional[str] = None

# --- UI Controls ---
user_id_input = ft.TextField(
    label="Enter User ID (e.g., user_001)",
    hint_text="Try user_001 or user_002",
    width=300,
    border_radius=10,
    disabled=True
)
recommendations_list = ft.ListView(
    expand=True,
    spacing=10,
    padding=10,
    auto_scroll=True,
)
progress_bar = ft.ProgressBar(visible=False, width=400)
error_text = ft.Text(color=ft.colors.RED, visible=False)
status_text = ft.Text("Enter a User ID to get recommendations.", italic=True)
submit_button = ft.ElevatedButton(
    "Find Recommendations",
    icon=ft.icons.SEARCH,
    disabled=True
)
user_details_id = ft.Text("-", weight=ft.FontWeight.BOLD)
user_details_experience = ft.Text("-")
user_details_goals = ft.Text("-")
user_details_summary = ft.Text("-", italic=True, selectable=True)
user_details_container = ft.Container(
    content=ft.Column([
        ft.Row([ft.Text("User ID:", weight=ft.FontWeight.W_500), user_details_id]),
        ft.Row([ft.Text("Experience:", weight=ft.FontWeight.W_500), user_details_experience]),
        ft.Row([ft.Text("Goals:", weight=ft.FontWeight.W_500), user_details_goals]),
        ft.Divider(height=10),
        ft.Text("AI Summary:", weight=ft.FontWeight.W_500),
        ft.Container(user_details_summary, padding=ft.padding.only(left=10))
    ]),
    padding=15,
    margin=ft.margin.only(top=10, bottom=10)
)
results_tabs = ft.Tabs(
    selected_index=0,
    animation_duration=300,
    tabs=[],
    expand=True,
    visible=False
)

# --- Functions ---

def load_configuration() -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Loads configuration from YAML and .env files.

    Returns:
        tuple[Optional[str], Optional[Dict[str, Any]]]: A tuple containing the
            GCP Project ID and the application configuration dictionary, or
            (None, None) if loading fails.
    """
    dotenv_path = os.path.join(PROJECT_ROOT, '.env')
    config_path = os.path.join(PROJECT_ROOT, 'config.yaml')

    load_dotenv(dotenv_path=dotenv_path)
    project_id = os.getenv("PROJECT_ID")

    if not project_id:
        print("FATAL ERROR: GCP PROJECT_ID environment variable is not set.")
        return None, None

    try:
        print(f"Loading configuration from: {config_path}")
        with open(config_path, "r", encoding='utf-8') as f:
            app_config = yaml.safe_load(f)
        return project_id, app_config
    except FileNotFoundError:
         print(f"FATAL ERROR: config.yaml not found at {config_path}")
         return project_id, None
    except Exception as e:
        print(f"FATAL ERROR loading config.yaml: {e}")
        return project_id, None

def get_recommendations(user_id: str, bq_client: bigquery.Client, config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Fetches user embedding and runs VECTOR_SEARCH to get recommendations.

    Args:
        user_id (str): The ID of the user for whom to get recommendations.
        bq_client (bigquery.Client): Authenticated BigQuery client.
        config (Dict[str, Any]): Application configuration dictionary.

    Returns:
        Optional[List[Dict[str, Any]]]: A list of recommendation dictionaries
            (including media_id, rank, title, etc.), an empty list if no
            recommendations are found, or None if an error occurs.
    """
    global error_text, status_text # Allow updating UI elements

    try:
        bq_config = config['bigquery']
        reco_config = config['recommendations']
        project_id = os.getenv("PROJECT_ID")
        dataset_name = bq_config['dataset_name']
        user_embeddings_table = f"`{project_id}.{dataset_name}.{bq_config['user_embeddings_table_name']}`"
        media_embeddings_table = f"`{project_id}.{dataset_name}.{bq_config['media_embeddings_table_name']}`"
        media_content_table = f"`{project_id}.{dataset_name}.{bq_config['media_table_name']}`"
        top_n = int(reco_config.get('top_n', 10))
        distance_measure = reco_config.get('distance_measure', 'COSINE').upper()

        print(f"Fetching embedding for user: {user_id}")

        # 1. Fetch User Embedding
        user_embedding_query = f"""
        SELECT embedding
        FROM {user_embeddings_table}
        WHERE user_id = '{user_id}'
        LIMIT 1
        """
        user_embedding_result = fetch_bq_results(bq_client, user_embedding_query)

        if not user_embedding_result:
             msg = f"User ID '{user_id}' embedding not found."
             print(f"ERROR: {msg}")
             error_text.value = msg
             error_text.visible = True
             status_text.visible = False
             return None

        user_embedding = user_embedding_result[0]['embedding']
        if not user_embedding or not isinstance(user_embedding, list) or len(user_embedding) == 0:
             msg = f"Embedding for user ID '{user_id}' is invalid or missing."
             print(f"ERROR: {msg}")
             error_text.value = msg
             error_text.visible = True
             status_text.visible = False
             return None

        user_embedding_str = '[' + ','.join(map(lambda x: f"{float(x):.8f}", user_embedding)) + ']'
        print(f"User embedding fetched (first few dims): {user_embedding[:3]}...")

        # 2. Run Vector Search
        print(f"Running VECTOR_SEARCH for top {top_n} recommendations (using brute force)...")
        vector_search_sql = f"""
        SELECT
            vs.base.media_id AS recommended_media_id,
            vs.distance
        FROM
            VECTOR_SEARCH(
                TABLE {media_embeddings_table},
                'embedding',
                (SELECT {user_embedding_str} AS embedding),
                top_k => {top_n},
                distance_type => '{distance_measure}',
                OPTIONS => '{{ \\"use_brute_force\\": true }}'
            ) AS vs
        ORDER BY vs.distance ASC;
        """
        search_results = fetch_bq_results(bq_client, vector_search_sql)

        if search_results is None:
            msg = "Vector search query failed. Check BigQuery logs."
            print(f"ERROR: {msg}")
            error_text.value = msg
            error_text.visible = True
            status_text.visible = False
            return None
        if not search_results:
            print("No recommendations found via vector search.")
            return []

        # Extract results & Assign rank
        ranked_results = []
        for i, row in enumerate(search_results):
            media_id_key = 'recommended_media_id'
            if media_id_key not in row or row[media_id_key] is None:
                 print(f"WARN: '{media_id_key}' not found or is NULL in VECTOR_SEARCH result row: {row}. Skipping.")
                 continue
            ranked_results.append({
                "media_id": row[media_id_key],
                "distance": row['distance'],
                "rank": i + 1
            })
        print(f"Found {len(ranked_results)} potential recommendations.")

        # 3. Fetch Content Details for Recommended IDs
        if not ranked_results:
            return []

        recommended_media_ids = [row['media_id'] for row in ranked_results]
        formatted_ids = ", ".join([f"'{media_id}'" for media_id in recommended_media_ids])
        if not formatted_ids:
            return []

        content_details_query = f"""
        SELECT media_id, title, main_text, type, author_creator
        FROM {media_content_table}
        WHERE media_id IN ({formatted_ids})
        """
        content_details = fetch_bq_results(bq_client, content_details_query)

        if content_details is None:
             msg = "Failed to fetch content details for recommendations."
             print(f"ERROR: {msg}")
             error_text.value = msg
             error_text.visible = True
             status_text.visible = False
             return None

        # 4. Combine results and create snippets/full text data
        final_recommendations = []
        content_map = {row['media_id']: row for row in content_details}

        for item in ranked_results:
            media_id = item['media_id']
            details = content_map.get(media_id)
            if details:
                full_text = details.get('main_text', '') or ''
                snippet = full_text
                if len(snippet) > SNIPPET_LENGTH:
                    snippet = snippet[:SNIPPET_LENGTH] + "..."
                elif not snippet:
                     snippet = "(No content preview available)"

                final_recommendations.append({
                    "media_id": media_id,
                    "rank": item['rank'],
                    "title": details.get('title', 'No Title'),
                    "type": details.get('type', 'N/A'),
                    "author_creator": details.get('author_creator', 'N/A'),
                    "snippet": snippet,
                    "main_text": full_text,
                    "distance_score": item['distance']
                })
            else:
                 print(f"WARN: Could not find content details for media_id: {media_id}")

        return final_recommendations

    except (TypeError, ValueError) as format_err:
        msg = f"Invalid embedding data for user '{user_id}'."
        print(f"ERROR formatting embedding for user '{user_id}': {format_err}")
        error_text.value = msg
        error_text.visible = True
        status_text.visible = False
        return None
    except Exception as e:
        msg = f"An unexpected error occurred for user '{user_id}'."
        print(f"ERROR in get_recommendations for user '{user_id}': {e}")
        import traceback
        traceback.print_exc()
        error_text.value = msg
        error_text.visible = True
        status_text.visible = False
        return None

def main(page: ft.Page):
    """Main function to build and run the Flet application UI.

    Args:
        page (ft.Page): The Flet Page object provided by ft.app().
    """
    # Use global UI/config variables
    global user_id_input, recommendations_list, progress_bar, error_text, status_text, submit_button
    global user_details_container, user_details_id, user_details_experience, user_details_goals, user_details_summary
    global results_tabs
    global APP_CONFIG, BQ_CLIENT, INITIAL_ERROR

    page.title = "Content Recommendation Demo"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.window_width = 700
    page.window_height = 850

    # --- Event Handler ---
    def find_recommendations_on_click(e):
        """Handles the click event of the 'Find Recommendations' button."""
        user_id = user_id_input.value.strip()
        # Reset UI state
        error_text.visible = False
        status_text.visible = True
        recommendations_list.controls.clear()
        results_tabs.visible = False
        page.update()

        if not user_id:
            error_text.value = "Please enter a User ID."
            error_text.visible = True
            status_text.visible = False
            page.update()
            return

        if INITIAL_ERROR or not BQ_CLIENT or not APP_CONFIG:
             error_text.value = f"Application Error: {INITIAL_ERROR or 'Unknown setup issue.'}"
             error_text.visible = True
             status_text.visible = False
             page.update()
             return

        print(f"Button clicked for user_id: {user_id}")
        status_text.value = f"Fetching details for {user_id}..."
        progress_bar.visible = True
        submit_button.disabled = True
        page.update()

        user_data = None
        results = None
        try:
            # Fetch User Details FIRST
            bq_config = APP_CONFIG['bigquery']
            project_id = os.getenv("PROJECT_ID")
            dataset_name = bq_config['dataset_name']
            users_table = f"`{project_id}.{dataset_name}.{bq_config['users_table_name']}`"
            user_details_query = f"""
            SELECT user_id, experience_level, trading_goal, profile_summary
            FROM {users_table}
            WHERE user_id = '{user_id}'
            LIMIT 1
            """
            user_details_result = fetch_bq_results(BQ_CLIENT, user_details_query)

            if not user_details_result:
                msg = f"User ID '{user_id}' not found in users table."
                print(f"ERROR: {msg}")
                error_text.value = msg
                error_text.visible = True
                status_text.visible = False
                progress_bar.visible = False
                submit_button.disabled = False
                page.update()
                return

            # Update User Details UI Controls
            user_data = user_details_result[0]
            user_details_id.value = user_data.get('user_id', 'N/A')
            user_details_experience.value = user_data.get('experience_level', 'N/A')
            user_details_goals.value = user_data.get('trading_goal', 'N/A')
            user_details_summary.value = user_data.get('profile_summary', '(No summary generated)') or "(Summary is empty)"

            status_text.value = f"Fetching recommendations for {user_id}..."
            page.update()

            # Get recommendations
            results = get_recommendations(user_id, BQ_CLIENT, APP_CONFIG)

            progress_bar.visible = False

            # Check recommendation results and update UI
            if results is None:
                 # Error text set by get_recommendations
                 pass
            elif not results:
                status_text.value = f"No recommendations found for {user_id}."
                results_tabs.selected_index = 0 # Show profile tab
            else:
                status_text.value = f"Showing results for {user_id}:"
                # Populate recommendations list
                for item in results:
                    recommendations_list.controls.append(
                        ft.ExpansionTile(
                            title=ft.Text(f"{item.get('rank')}. {item.get('title', 'N/A')}", weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(item.get('snippet', '')),
                            leading=ft.Icon(ft.icons.ARTICLE if item.get('type') == 'article' else ft.icons.ONDEMAND_VIDEO),
                            affinity=ft.TileAffinity.PLATFORM,
                            maintain_state=True,
                            initially_expanded=False,
                            controls=[
                                ft.ListTile(
                                    title=ft.Text(f"By: {item.get('author_creator', 'N/A')}", italic=True, size=12),
                                ),
                                ft.Divider(height=1),
                                ft.Container(
                                     content=ft.Text(item.get('main_text', 'No content available.'), selectable=True),
                                     padding=ft.padding.all(10)
                                )
                            ],
                            trailing=ft.Text(f"Dist: {item.get('distance_score', 0.0):.4f}", size=10, italic=True),
                        )
                    )
                results_tabs.selected_index = 1 # Switch to recommendations tab

            # Make Tabs visible
            results_tabs.visible = True

        except Exception as ex:
             print(f"Unexpected error in UI handler: {ex}")
             error_text.value = "An unexpected application error occurred in UI."
             error_text.visible = True
             status_text.visible = False
             progress_bar.visible = False
             results_tabs.visible = False

        submit_button.disabled = False
        page.update()

    submit_button.on_click = find_recommendations_on_click

    # --- Define Tabs ---
    tab_profile = ft.Tab(
        text="User Profile",
        icon=ft.icons.PERSON_OUTLINED,
        content=user_details_container
    )
    tab_recos = ft.Tab(
        text="Recommendations",
        icon=ft.icons.RECOMMEND_OUTLINED,
        content=ft.Container(
            content=recommendations_list,
            border=ft.border.all(1, ft.colors.OUTLINE),
            border_radius=ft.border_radius.all(10),
            padding=5,
            expand=True,
            bgcolor=ft.colors.BACKGROUND
        )
    )
    results_tabs.tabs = [tab_profile, tab_recos]

    # --- Page Layout ---
    page.add(
        ft.Column(
            [
                ft.Row(
                    [ft.Icon(ft.icons.RECOMMEND, size=40, color=ft.colors.BLUE_600),
                     ft.Text("Trading Content Recommendations", size=30, weight=ft.FontWeight.BOLD)],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                ft.Container(height=10),
                ft.Row(
                    [user_id_input, submit_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=10),
                ft.Column(
                    [status_text, error_text, progress_bar],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                 ft.Container(height=5),
                results_tabs
            ],
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

    # Display initial error if setup failed and enable/disable controls
    controls_disabled = INITIAL_ERROR is not None
    user_id_input.disabled = controls_disabled
    submit_button.disabled = controls_disabled
    if INITIAL_ERROR:
        error_text.value = f"Application Initialization Error: {INITIAL_ERROR}"
        error_text.visible = True
        status_text.visible = False
    page.update()


# --- Run the App ---
if __name__ == "__main__":
    print("Initializing application...")
    project_id, APP_CONFIG = load_configuration()
    if not project_id or not APP_CONFIG:
        INITIAL_ERROR = "Failed to load configuration. Check .env and config.yaml."
        print(f"ERROR: {INITIAL_ERROR}")
    else:
        BQ_CLIENT = get_bigquery_client(project_id)
        if not BQ_CLIENT:
             INITIAL_ERROR = f"Failed to initialize BigQuery client for project {project_id}."
             print(f"ERROR: {INITIAL_ERROR}")

    print("Starting Flet application...")
    try:
        ft.app(target=main)
        print("Flet application stopped.")
    except Exception as app_ex:
         print(f"ERROR running Flet application: {app_ex}")
