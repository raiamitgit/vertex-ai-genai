"""
Provides functions for calculating similarity between embeddings
and getting top recommendations based on the similarity scores.
"""
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances

def calculate_similarity(user_embedding, media_embeddings, metric="cosine"):
    """Calculates similarity between a user embedding and a list of media embeddings."""
    user_embedding = np.array(user_embedding).reshape(1, -1)
    media_embeddings = np.array(media_embeddings)

    if metric == "cosine":
        similarities = cosine_similarity(user_embedding, media_embeddings)
    elif metric == "euclidean":
        # Negate Euclidean distance so higher values indicate greater similarity
        similarities = -euclidean_distances(user_embedding, media_embeddings)
    else:
        raise ValueError(f"Unsupported similarity metric: {metric}")

    return similarities[0]

def get_top_recommendations(user_embedding, media_df, media_embeddings, top_n=10, similarity_metric="cosine"):
    """Gets top N recommendations for a user."""
    if not media_embeddings:
        print("No media embeddings available.")
        return []

    similarities = calculate_similarity(user_embedding, media_embeddings, metric=similarity_metric)

    # Pair similarities with media IDs for sorting
    media_with_similarity = list(zip(media_df['media_id'], similarities))

    # Sort by similarity (descending)
    sorted_media = sorted(media_with_similarity, key=lambda x: x[1], reverse=True)

    # Get top N media IDs
    top_media_ids = [media_id for media_id, similarity in sorted_media[:top_n]]

    # Return the corresponding rows from the media DataFrame
    return media_df[media_df['media_id'].isin(top_media_ids)].to_dict('records')