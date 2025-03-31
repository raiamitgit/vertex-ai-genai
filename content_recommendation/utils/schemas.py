"""
Central definitions for BigQuery table schemas using google.cloud.bigquery.SchemaField.

These schemas define the expected structure and data types for the tables
used in the recommendation system demo.
"""
from google.cloud import bigquery

# --- User Schema ---
USERS_SCHEMA = [
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED", description="Unique user identifier (e.g., user_001)"),
    bigquery.SchemaField("experience_level", "STRING", mode="NULLABLE", description="Trading experience level (e.g., Beginner, Intermediate)"),
    bigquery.SchemaField("trading_goal", "STRING", mode="NULLABLE", description="User's stated trading goals (comma-separated)"),
    bigquery.SchemaField("preferred_assets", "STRING", mode="NULLABLE", description="User's preferred assets (comma-separated)"),
    bigquery.SchemaField("account_age_months", "INTEGER", mode="NULLABLE", description="Age of the user's account in months"),
    bigquery.SchemaField("fav_instrument_1", "STRING", mode="NULLABLE", description="Primary favorite trading instrument symbol"),
    bigquery.SchemaField("fav_instrument_1_volume_perc", "INTEGER", mode="NULLABLE", description="Approx % volume in fav_instrument_1"),
    bigquery.SchemaField("fav_instrument_2", "STRING", mode="NULLABLE", description="Secondary favorite trading instrument symbol"),
    bigquery.SchemaField("fav_instrument_2_volume_perc", "INTEGER", mode="NULLABLE", description="Approx % volume in fav_instrument_2"),
    bigquery.SchemaField("avg_trade_duration_minutes", "INTEGER", mode="NULLABLE", description="Average trade duration in minutes"),
    bigquery.SchemaField("most_used_order_type", "STRING", mode="NULLABLE", description="Most frequently used order type"),
    bigquery.SchemaField("win_rate_perc", "FLOAT", mode="NULLABLE", description="Approximate win rate percentage"),
    bigquery.SchemaField("average_leverage_multiple", "FLOAT", mode="NULLABLE", description="Average leverage multiplier used"),
    bigquery.SchemaField("trading_frequency", "STRING", mode="NULLABLE", description="Trading frequency category (e.g., Low, Medium)"),
    bigquery.SchemaField("profile_summary", "STRING", mode="NULLABLE", description="AI-generated user profile summary"),
]

# --- Media Schema ---
MEDIA_SCHEMA = [
    bigquery.SchemaField("media_id", "STRING", mode="REQUIRED", description="Unique media item identifier"),
    bigquery.SchemaField("type", "STRING", mode="REQUIRED", description="Type of media ('article' or 'video')"),
    bigquery.SchemaField("title", "STRING", mode="NULLABLE", description="Title of the media item"),
    bigquery.SchemaField("author_creator", "STRING", mode="NULLABLE", description="Author or creator name"),
    bigquery.SchemaField("created_date", "TIMESTAMP", mode="NULLABLE", description="Publication date/time (UTC)"),
    bigquery.SchemaField("tags", "STRING", mode="NULLABLE", description="Comma-separated list of descriptive tags"),
    bigquery.SchemaField("content_length", "INTEGER", mode="NULLABLE", description="Word count (articles) or duration in seconds (videos)"),
    bigquery.SchemaField("main_text", "STRING", mode="NULLABLE", description="Full text content (article) or transcript (video)"),
]

# --- Recommendations Schema ---
# Note: This schema might not be explicitly used if recommendations are generated on-the-fly
# by the app, but it defines the structure if they were stored.
RECOMMENDATIONS_SCHEMA = [
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED", description="User the recommendation is for"),
    bigquery.SchemaField("recommended_media_id", "STRING", mode="REQUIRED", description="ID of the recommended media item"),
    bigquery.SchemaField("rank", "INTEGER", mode="REQUIRED", description="Rank of the recommendation (1 is highest)"),
    bigquery.SchemaField("distance_score", "FLOAT", mode="NULLABLE", description="Calculated distance score from vector search"),
    bigquery.SchemaField("processing_timestamp", "TIMESTAMP", mode="REQUIRED", description="Timestamp when the recommendation was generated"),
]

# --- User Embeddings Schema ---
USER_EMBEDDINGS_SCHEMA = [
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED", description="Unique user identifier (FK to users.user_id)"),
    bigquery.SchemaField("content", "STRING", mode="NULLABLE", description="User profile summary text used for embedding"),
    bigquery.SchemaField("embedding", "FLOAT", mode="REPEATED", description="User profile embedding vector"),
    bigquery.SchemaField("processing_timestamp", "TIMESTAMP", mode="NULLABLE", description="Timestamp when the embedding was generated"),
]

# --- Media Embeddings Schema ---
MEDIA_EMBEDDINGS_SCHEMA = [
    bigquery.SchemaField("media_id", "STRING", mode="REQUIRED", description="Unique media identifier (FK to media_content.media_id)"),
    bigquery.SchemaField("content", "STRING", mode="NULLABLE", description="Media text (article/transcript) used for embedding"),
    bigquery.SchemaField("embedding", "FLOAT", mode="REPEATED", description="Media content embedding vector"),
    bigquery.SchemaField("processing_timestamp", "TIMESTAMP", mode="NULLABLE", description="Timestamp when the embedding was generated"),
]