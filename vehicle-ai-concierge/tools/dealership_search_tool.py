import json
import os
import math
from typing import List, Dict, Any

# --- Data Loading ---

def _load_data(file_name: str) -> Dict:
    """
    Loads data from a JSON file using a robust path.
    
    Args:
        file_name: The name of the JSON file to load (e.g., "dealerships.json").

    Returns:
        A dictionary containing the loaded data.
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        json_path = os.path.join(project_root, 'data', file_name)
        
        with open(json_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file_name}'.")
        return {}

# Load data once when the module is imported
DEALERSHIPS_DATA = _load_data("dealerships.json").get("dealerships", [])
ZIP_CODES_DATA = _load_data("zip_codes.json").get("zip_codes", {})

# --- Tool Function ---

def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the distance between two lat/lon points in miles.
    """
    R = 3958.8  # Earth radius in miles
    
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    
    a = math.sin(dLat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dLon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def find_dealerships(zip_code: str) -> Dict[str, Any]:
    """
    Finds the 5 closest dealerships to a given zip code.

    Args:
        zip_code: The user's 5-digit zip code.

    Returns:
        A dictionary containing a list of the 5 closest dealerships, sorted by distance.
    """
    if not DEALERSHIPS_DATA or not ZIP_CODES_DATA:
        return {"count": 0, "dealerships": [], "message": "Dealership database is not loaded."}
        
    user_location = ZIP_CODES_DATA.get(zip_code)
    
    if not user_location:
        return {"count": 0, "dealerships": [], "message": f"Sorry, I couldn't find location information for the zip code {zip_code}."}

    user_lat = user_location['lat']
    user_lon = user_location['lon']
    
    # Calculate distance for each dealership
    dealers_with_distance = []
    for dealer in DEALERSHIPS_DATA:
        distance = _haversine_distance(user_lat, user_lon, dealer['lat'], dealer['lon'])
        # Add the calculated distance to the dealer's dictionary for sorting
        dealer_copy = dealer.copy()
        dealer_copy['distance_miles'] = round(distance, 2)
        dealers_with_distance.append(dealer_copy)
        
    # Sort dealerships by distance
    sorted_dealers = sorted(dealers_with_distance, key=lambda d: d['distance_miles'])
    
    # Return the top 5
    closest_dealers = sorted_dealers[:5]
    
    return {"count": len(closest_dealers), "dealerships": closest_dealers}

if __name__ == '__main__':
    print("--- Testing Dealership Search Tool ---")

    # Test Case 1: Find dealerships near Dearborn, MI (48126)
    test_zip = "48126"
    print(f"\n--- Finding dealerships near zip code: {test_zip} ---")
    
    results = find_dealerships(test_zip)
    
    print(f"Found {results['count']} dealerships:")
    for dealer in results.get("dealerships", []):
        print(f"- {dealer['name']} ({dealer['address']}) - Approx. {dealer['distance_miles']} miles away")

    # Test Case 2: Zip code not in our data
    test_zip_2 = "90210"
    print(f"\n--- Finding dealerships near zip code: {test_zip_2} (not in data) ---")
    results_2 = find_dealerships(test_zip_2)
    print(results_2.get("message"))
    
    print("\n--- Testing complete ---")
