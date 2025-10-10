import json
import os
import sys

from tools.physna_tool import (
        search_parts_by_asset_id,
        search_parts_by_image
    )

# --- Test Data ---
# Ensure these exist in your tenant/filesystem
SOURCE_ASSET_ID = "2de46464-b13f-4312-a3c9-6ef0b050e18f"
TEST_IMAGE_PATH = "agentspace/sample_bracket.jpg" # Ensure this path exists locally

def print_separator(title):
    print(f"\n{'='*60}")
    print(f"=== {title.upper()} ===")
    print(f"{'='*60}")

def test_asset_id_workflow():
    """
    Tests 'Part search with asset id':
    1) execute search 2) extract data 3) Generate URLs 4) Output JSON
    """
    print_separator("Testing: Part Search with Asset ID")
    print(f"Input Asset ID: {SOURCE_ASSET_ID}")

    try:
        # Execute the new agent tool
        result = search_parts_by_asset_id(SOURCE_ASSET_ID)

        print("\n--- \u2705 Search Successful ---")
        
        # Verify output structure (Requirement 5: JSON output with details)
        source_url = result.get('source_asset_url')
        count = result.get('results_count', 0)
        results = result.get('results', [])

        print(f"Source Asset Web URL: {source_url}")
        print(f"Total Matches Found: {count}")

        if count > 0:
            # Verify Requirements 2, 3, & 4 on the first result
            first_match = results[0]
            print("\n[Inspection of First Result]")
            print(f"  ID:       {first_match.get('asset_id')}")
            print(f"  Name:     {first_match.get('name')}")
            print(f"  Match %:  {first_match.get('match_percentage')}")
            
            # Check Metadata Extraction (Req 2)
            meta = first_match.get('metadata', {})
            print(f"  Metadata Keys Found: {list(meta.keys()) if meta else 'None'}")

            # Check URL Generation (Req 3 & 4)
            urls = first_match.get('urls', {})
            print(f"  \u2794 Part Details URL:   {urls.get('asset_details')}")
            print(f"  \u2794 Comparison Web URL: {urls.get('comparison_vs_source')}")

            # Validate URLs look correct
            if not urls.get('comparison_vs_source', '').startswith('http'):
                 print("\n\u26A0\uFE0F WARNING: Comparison URL seems malformed.")
        else:
            print("No matches found based on current filter settings.")

    except Exception as e:
        print(f"\n\u274C Test Failed with error: {e}")

def test_image_workflow():
    """
    Tests 'Part Search with image':
    1) Image search & extract 1st result 2) Follow asset search steps.
    """
    print_separator("Testing: Part Search with Image")

    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"\n\u26A0\uFE0F Skipping Test: Image not found at {TEST_IMAGE_PATH}")
        print("Please update TEST_IMAGE_PATH to a valid local file.")
        return

    print(f"Input Image: {TEST_IMAGE_PATH}")

    try:
        # Execute the new agent tool
        result = search_parts_by_image(TEST_IMAGE_PATH)

        # Check for tool-defined error (e.g., image yielded no 3D matches)
        if result.get("status") == "error":
             print(f"\n--- Tool returned expected error ---")
             print(f"Message: {result.get('message')}")
             return

        print("\n--- \u2705 Search Successful ---")

        # Verify Requirement 1 (Extract 1st result from image search as source)
        origin = result.get('search_origin', {})
        print("\n[Step 1: Image to 3D Result]")
        print(f"  Identified Source Name: {origin.get('identified_source_asset')}")
        print(f"  Intermediate Asset ID:  {result.get('source_asset_id')}")

        # Verify subsequent asset search results
        count = result.get('results_count', 0)
        print(f"\n[Step 2: Geometric Search Results]")
        print(f"Found {count} parts similar to the identified 3D source.")

        if count > 0:
            first_match = result['results'][0]
            urls = first_match.get('urls', {})
            print(f"  First Match Name: {first_match.get('name')}")
            print(f"  \u2794 Comparison Web URL: {urls.get('comparison_vs_source')}")
            
            # Optional: Dump full JSON to see structure
            # print("\nFull JSON Response (Debug):")
            # print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"\n\u274C Test Failed with error: {e}")

if __name__ == "__main__":
    # Environment check
    required_envs = ["PHYSNA_TENANT_ID", "PHYSNA_CLIENT_ID", "PHYSNA_CLIENT_SECRET", "AUTH_URL"]
    missing_envs = [env for env in required_envs if not os.getenv(env)]
    
    if missing_envs:
        print(f"ERROR: Missing environment variables in .env: {missing_envs}")
        exit(1)
        
    # Run updated workflow tests
    test_asset_id_workflow()
    test_image_workflow()
    print("\n================ DONE ================")