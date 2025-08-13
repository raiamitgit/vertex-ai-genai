# File: tools/website_search_tool.py
# Description: A tool for performing stateful searches on a Vertex AI Search datastore.

import os
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core import exceptions as api_exceptions # Import exceptions for error handling
from helpers import gemini_helper
from google.adk.tools import ToolContext # Import the ToolContext
from dotenv import load_dotenv

# Load environment variables for standalone testing
load_dotenv()

# --- Configuration ---
PROJECT_ID = os.getenv("VERTEX_AI_PROJECT_ID")
LOCATION = os.getenv("VERTEX_AI_LOCATION")
ENGINE_ID = os.getenv("VERTEX_AI_ENGINE_ID")

# --- Initialize Clients ---
search_client = discoveryengine.SearchServiceClient()


def search(query: str, tool_context: ToolContext) -> dict:
    """
    Performs a stateful search on the website datastore.

    Args:
        query: The user's latest query.
        tool_context: The context object provided by the ADK framework,
                      which contains session history.
    """
    # 1. Get chat history from the context and format it for the prompt.
    # CORRECTED: Access the session through the private _invocation_context attribute.
    raw_events = tool_context._invocation_context.session.events
    chat_history = []
    for event in raw_events:
        # We only care about user and model messages with text content for the history
        if event.author and event.content and event.content.parts and event.content.parts[0].text:
            role = "user" if event.author == "user" else "assistant"
            chat_history.append({"role": role, "content": event.content.parts[0].text})

    # 2. Rewrite the query for context using our corrected Gemini helper
    if chat_history:
        # Convert history to a simple string for the prompt
        history_str = "\n".join([f"{item['role']}: {item['content']}" for item in chat_history])
        contextual_query_prompt = f"""
        Based on the following chat history and the user's latest query,
        rewrite the query to be a standalone search query that can be sent to a
        search engine.

        Chat History:
        {history_str}

        Latest Query: "{query}"

        Rewritten Query:
        """
        rewritten_query = gemini_helper.generate_text(contextual_query_prompt)
        if not rewritten_query:
            rewritten_query = query # Fallback to original query on error
        
        print(f"Original Query: '{query}' -> Rewritten Query: '{rewritten_query}'")
    else:
        rewritten_query = query

    # 3. Perform the search using the rewritten query
    serving_config = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/engines/{ENGINE_ID}/servingConfigs/default_config"

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=10,
            include_citations=True,
        ),
        extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
        max_extractive_answer_count=5,
        max_extractive_segment_count=5)
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=rewritten_query,
        page_size=10,
        content_search_spec=content_search_spec,
        params={"search_type": 1}, # Enable image search
    )

    try:
        response = search_client.search(request)
    except api_exceptions.ServiceUnavailable as e:
        print(f"ERROR: Could not connect to the search service. Details: {e}")
        return {
            "summary": "I am currently unable to connect to the website search service. Please check your network connection and try again later.",
            "results": []
        }
    except Exception as e:
        print(f"An unexpected error occurred during search: {e}")
        return {
            "summary": "An unexpected error occurred while searching the website.",
            "results": []
        }

    # 4. Process and return the results, including images
    results = []
    for res in response.results:
        doc_data = res.document.derived_struct_data
        
        title = doc_data.get("title", "")
        image_url = doc_data.get("link", "")
        snippet = doc_data.get("snippets", [{}])[0].get("snippet", "")
        
        page_url = ""
        if "image" in doc_data and "contextLink" in doc_data["image"]:
            page_url = doc_data["image"]["contextLink"]

        results.append({
            "title": title,
            "link": page_url,
            "snippet": snippet,
            "image": image_url,
        })

    print(results)

    return {"summary": response.summary.summary_text, "results": results}

# --- Main function for standalone testing ---
if __name__ == '__main__':
    # Mock objects to simulate the ADK context for testing
    class MockPart:
        def __init__(self, text):
            self.text = text

    class MockContent:
        def __init__(self, role, text):
            self.parts = [MockPart(text)]
            self.role = role

    class MockEvent:
        def __init__(self, author, text):
            self.author = author
            self.content = MockContent(author, text)

    class MockSession:
        def __init__(self, events):
            self.events = events

    class MockInvocationContext:
        def __init__(self, events):
            self.session = MockSession(events)

    class MockToolContext:
        def __init__(self, events):
            # Use the private attribute name in the mock as well.
            self._invocation_context = MockInvocationContext(events)

    print("--- Testing website_search_tool.py ---")

    # Test case 1: Simple query with no history
    print("\n--- Test Case 1: Simple Query ---")
    mock_context_simple = MockToolContext(events=[])
    simple_query = "latest offers on the Encore GX"
    search_results = search(query=simple_query, tool_context=mock_context_simple)
    print(f"Summary: {search_results.get('summary', 'No summary found.')}")
    for res in search_results.get("results", []):
        print(f"- Title: {res['title']}")
        print(f"  Snippet: {res['snippet']}")
        print(f"  Image: {res['image']}")

    print("-" * 20)

    # Test case 2: Query with chat history
    print("\n--- Test Case 2: Query with History ---")
    mock_history = [
        MockEvent(author='user', text='Hi, I am interested in the new Buick Vehicle.'),
        MockEvent(author='model', text='Great, do yo have any specific model in mind?'),
    ]
    mock_context_history = MockToolContext(events=mock_history)
    history_query = "What SUVs do you have available?"
    search_results_history = search(query=history_query, tool_context=mock_context_history)
    print(f"Summary: {search_results_history.get('summary', 'No summary found.')}")
    for res in search_results_history.get("results", []):
        print(f"- Title: {res['title']}")
        print(f"  Snippet: {res['snippet']}")
        print(f"  Image: {res['image']}")
        
    print("\n--- Testing complete ---")
