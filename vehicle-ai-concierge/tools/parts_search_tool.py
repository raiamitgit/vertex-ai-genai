import json
import os
from typing import Optional, List, Dict, Any

# --- Data Loading ---

def _load_parts_data() -> List[Dict[str, Any]]:
    """
    Loads the parts data from the JSON file using a robust path.
    
    Returns:
        A list of dictionaries, where each dictionary represents a part.
    """
    try:
        # Construct a reliable path to the JSON file relative to this script's location
        # __file__ is the path to the current script (e.g., .../tools/parts_search_tool.py)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to the project root (e.g., .../)
        project_root = os.path.dirname(script_dir)
        # Construct the final path to the data file (e.g., .../data/parts.json)
        json_path = os.path.join(project_root, 'data', 'parts.json')
        
        with open(json_path, 'r') as f:
            return json.load(f).get("parts", [])
    except FileNotFoundError:
        print(f"Error: The file at the constructed path was not found. Please ensure 'data/parts.json' exists.")
        return []
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from data/parts.json.")
        return []

# Load the data once when the module is imported
PARTS_DATABASE = _load_parts_data()

# --- Tool Function ---

def search_parts(
    query: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Searches for parts and accessories based on various criteria.

    This function mocks an API call to a parts database. It filters the loaded
    parts data based on the provided query, model, and year.

    Args:
        query: A search term to match against the part's name or description.
        model: The vehicle model to filter by (e.g., "Enclave").
        year: The vehicle year to filter by.

    Returns:
        A dictionary containing the search results, including a count of
        matching items and a list of the items themselves.
    """
    if not PARTS_DATABASE:
        return {"count": 0, "results": [], "message": "Parts database is not loaded."}

    filtered_results = []
    
    # Normalize model name once if it exists
    lower_model = model.lower() if model else None

    for part in PARTS_DATABASE:
        # 1. Check if the query matches (if a query is provided)
        query_match = True # Assume it matches if no query is given
        if query:
            lower_query = query.lower()
            text_to_search = (part.get("name", "") + " " + part.get("description", "")).lower()
            
            # Check if all words in the query are present in the text
            query_words = lower_query.split()
            all_words_match = True
            for word in query_words:
                # Handle simple plurals for better matching (e.g., "brakes" should find "brake")
                singular_word = word.rstrip('s') if word.endswith('s') and len(word) > 3 else word
                
                if word not in text_to_search and singular_word not in text_to_search:
                    all_words_match = False
                    break
            query_match = all_words_match

        if not query_match:
            continue # Skip to the next part if the query doesn't match

        # 2. Check if the part is compatible with the model and year (if provided)
        compatibility_match = True # Assume it matches if no model or year is given
        if lower_model or year:
            compatibility_match = False # Must now find an explicit match
            for comp in part.get("compatibility", []):
                # Check if the model in the compatibility entry matches the requested model
                model_is_compatible = not lower_model or comp.get("model", "").lower() == lower_model
                
                # Check if the year in the compatibility entry matches the requested year
                year_is_compatible = not year or year in comp.get("years", [])

                if model_is_compatible and year_is_compatible:
                    compatibility_match = True
                    break # Found a matching compatibility entry, no need to check others for this part
        
        if compatibility_match:
            filtered_results.append(part)
            
    return {"count": len(filtered_results), "results": filtered_results}


if __name__ == '__main__':
    # This block will only execute when the script is run directly
    # You can use this for testing the module's functions
    print("--- Testing parts_search_tool.py ---")

    # Test Case 1: General query for "roof"
    print("\n--- Test Case 1: Searching for 'roof' ---")
    roof_parts = search_parts(query="roof")
    print(f"Found {roof_parts['count']} parts.")
    for part in roof_parts['results']:
        print(f"- {part['name']} (${part['price']})")

    # Test Case 2: Specific query for "Enclave" model
    print("\n--- Test Case 2: Searching for parts for 'Enclave' ---")
    enclave_parts = search_parts(model="Enclave")
    print(f"Found {enclave_parts['count']} parts for Enclave.")
    # print(f"First 5: {[p['name'] for p in enclave_parts['results'][:5]]}")


    # Test Case 3: Specific query for "Enclave" model in 2024
    print("\n--- Test Case 3: Searching for parts for 'Enclave' in 2024 ---")
    enclave_2024_parts = search_parts(model="Enclave", year=2024)
    print(f"Found {enclave_2024_parts['count']} parts for 2024 Enclave.")
    # for part in enclave_2024_parts['results']:
    #     print(f"- {part['name']}")
        
    # Test Case 4: Searching for "brakes" for a 2023 "Encore GX"
    print("\n--- Test Case 4: Searching for 'brakes' for a 2023 Encore GX ---")
    encore_brakes = search_parts(query="brakes", model="Encore GX", year=2023)
    print(f"Found {encore_brakes['count']} parts.")
    for part in encore_brakes['results']:
        print(f"- {part['name']} ({part['part_number']})")
        
    # Test Case 5: No results found
    print("\n--- Test Case 5: Searching for 'Flux Capacitor' ---")
    no_results = search_parts(query="Flux Capacitor")
    print(f"Found {no_results['count']} parts.")

    print("\n--- Testing complete ---")
