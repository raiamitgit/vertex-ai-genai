import os
import json
from typing import Dict, Any, Optional

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core import exceptions as api_exceptions
from dotenv import load_dotenv

# Load environment variables for standalone testing and configuration
load_dotenv()

# --- Configuration ---
PROJECT_ID = os.getenv("VERTEX_AI_PROJECT_ID")
LOCATION = os.getenv("VERTEX_AI_LOCATION")
ENGINE_ID = os.getenv("VERTEX_AI_ENGINE_ID")

# --- Client Initialization ---
# Configure client options based on location
client_options = (
    ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
    if LOCATION and LOCATION != "global"
    else None
)
# Initialize the search client once to be reused
search_client = discoveryengine.SearchServiceClient(client_options=client_options)


def _configure_search_request(
    serving_config: str,
    search_query: str,
    session: Optional[str] = None,
) -> discoveryengine.SearchResponse:
    """
    Builds and executes a detailed search request to the Discovery Engine API.
    """
    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),

        # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest.ContentSearchSpec.SummarySpec
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=10,
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=False,
            ignore_low_relevant_content=False,
            ignore_jail_breaking_query=True,
            use_semantic_chunks=True,
            model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                preamble=""
            ),
            model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                version="stable",
            ),
        ),
        # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest.ContentSearchSpec.ExtractiveContentSpec
        extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
        max_extractive_answer_count=5,
        max_extractive_segment_count=5,
        return_extractive_segment_score=False),
        search_result_mode=discoveryengine.SearchRequest.ContentSearchSpec.SearchResultMode.DOCUMENTS,
    )

    # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest.QueryExpansionSpec
    query_expansion_spec = discoveryengine.SearchRequest.QueryExpansionSpec(
        condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        pin_unexpanded_results=True,
    )

    spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
        mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
    )

    # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest.RelevanceScoreSpec
    relevance_score_spec = discoveryengine.SearchRequest.RelevanceScoreSpec(
        return_relevance_score=True
    )

    # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest.RelevanceThreshold
    relevance_threshold = discoveryengine.SearchRequest.RelevanceThreshold.MEDIUM

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        session=session,
        query=search_query,
        page_size=10,
        content_search_spec=content_search_spec,
        query_expansion_spec=query_expansion_spec,
        spell_correction_spec=spell_correction_spec,
        relevance_score_spec=relevance_score_spec,
        relevance_threshold=relevance_threshold,
        params={"search_type": 1}, # Enable image search
    )

    return search_client.search(request)


def _parse_search_response(
    response: discoveryengine.SearchResponse,
) -> Dict[str, Any]:
    """
    Parses a SearchResponse object into a structured dictionary.
    """

    out = {
        "summary": response.summary.summary_text if response.summary else None,
        "results": [
            {
                "title": result.document.derived_struct_data.get("title"),
                "pageUrl": result.document.derived_struct_data.get("link"),
                "imageUrl": result.document.derived_struct_data.get("image", {}).get("link"),
                "snippets": [
                    s.get("snippet")
                    for s in result.document.derived_struct_data.get("snippets", [])
                ],
                "extractive_answers": [
                    a.get("content")
                    for a in result.document.derived_struct_data.get("extractive_answers", [])
                ],
            }
            for result in response.results
        ],
    }

    return out


def search(query: str) -> Dict[str, Any]:
    """
    Performs a search on the website datastore using advanced configurations.

    Args:
        query: The user's search query.

    Returns:
        A dictionary containing the structured search results.
    """
    if not all([PROJECT_ID, LOCATION, ENGINE_ID]):
        return {
            "summary": "Search is not configured. Missing PROJECT_ID, LOCATION, or ENGINE_ID.",
            "results": [],
        }
    serving_config = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/engines/{ENGINE_ID}/servingConfigs/default_config"

    try:
        response = _configure_search_request(
            serving_config=serving_config, search_query=query
        )
        return _parse_search_response(response)

    except api_exceptions.ServiceUnavailable as e:
        print(f"ERROR: Could not connect to the search service. Details: {e}")
        return {
            "summary": "I am currently unable to connect to the website search service. Please check your network connection and try again later.",
            "results": [],
        }
    except Exception as e:
        print(f"An unexpected error occurred during search: {e}")
        return {
            "summary": "An unexpected error occurred while searching the website.",
            "results": [],
        }


if __name__ == "__main__":
    print("--- Testing Refactored Website Search & Answer Tool ---")
    if PROJECT_ID and ENGINE_ID:
        test_query = "What SUVs does Buick offer?"
        print(f"Query: '{test_query}'")
        result = search(test_query)
        print("\n--- Tool Response ---")
        print(f"Summary:\n{result.get('summary')}\n")
        print(f"Found {len(result.get('results', []))} results.")
    else:
        print("Please set VERTEX_AI_PROJECT_ID and VERTEX_AI_ENGINE_ID before testing.")
