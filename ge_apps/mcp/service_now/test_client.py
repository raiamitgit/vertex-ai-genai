"""Verification script for ServiceNow Client.

This script loads the local .env file, lists recent incidents, fetches details
for the most recent incident, retrieves its comments, and prints them to the console.
It serves as a happy-path verification for the client integration.
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables from local .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
if os.path.exists(env_path):
    print(f"Loading env from {env_path}")
    load_dotenv(dotenv_path=env_path)
else:
    print("WARNING: .env file not found in current directory!")

# Import the client
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
import servicenow_client

def run_verification():
    try:
        print("\n--- 1. Testing list_recent_incidents ---")
        incidents = servicenow_client.list_recent_incidents(limit=3)
        print(f"Successfully retrieved {len(incidents)} incidents.")
        for inc in incidents:
            print(f"  - {inc.get('number')}: {inc.get('short_description')} (State: {inc.get('state')})")
        
        if not incidents:
            print("No incidents found in the instance to perform detail tests.")
            return

        # Pick the first incident for further tests
        target_ticket = incidents[0].get("number")
        print(f"\nUsing ticket {target_ticket} for detail and comment tests.")

        print("\n--- 2. Testing get_incident_details ---")
        details = servicenow_client.get_incident_details(target_ticket)
        print("Incident Details:")
        print(f"  - Sys ID: {details.get('sys_id')}")
        print(f"  - Short Description: {details.get('short_description')}")
        print(f"  - Description: {details.get('description')}")
        print(f"  - Priority: {details.get('priority')}")
        print(f"  - Urgency: {details.get('urgency')}")
        print(f"  - Created: {details.get('sys_created_on')}")

        print("\n--- 3. Testing get_incident_comments ---")
        comments = servicenow_client.get_incident_comments(target_ticket)
        print(f"Retrieved {len(comments)} comments.")
        for i, comm in enumerate(comments, 1):
            print(f"  Comment #{i} by {comm.get('sys_created_by')} at {comm.get('sys_created_on')}:")
            print(f"    {comm.get('value')}")

        print("\n--- 4. Testing add_incident_comment (Live Write Test) ---")
        # Create a unique comment using timestamp to avoid conflicts
        unique_identifier = f"Verification test token: {int(time.time())}"
        test_comment_text = f"Simulated check by BYO-MCP Verification Script. {unique_identifier}"
        
        print(f"Adding unique comment: '{test_comment_text}'")
        add_res = servicenow_client.add_incident_comment(target_ticket, test_comment_text)
        print(f"Add Result: {add_res}")
        
        # Retrieve comments again to find the sys_id of our new comment
        print("\nVerifying comment creation and resolving its sys_id...")
        updated_comments = servicenow_client.get_incident_comments(target_ticket)
        
        target_comment_sys_id = None
        for comm in updated_comments:
            if unique_identifier in comm.get("value", ""):
                target_comment_sys_id = comm.get("sys_id")
                print(f"Found matching comment! sys_id: {target_comment_sys_id}")
                break
        
        if not target_comment_sys_id:
            raise Exception("Verification failed: Added comment was not found in the incident history!")

        print("\n--- 5. Testing delete_comment (Live Cleanup Test) ---")
        print(f"Deleting comment sys_id: {target_comment_sys_id}...")
        del_res = servicenow_client.delete_comment(target_comment_sys_id)
        print(f"Delete Result: {del_res}")

        # Verify it is gone
        print("\nVerifying comment deletion...")
        final_comments = servicenow_client.get_incident_comments(target_ticket)
        deleted_found = False
        for comm in final_comments:
            if target_comment_sys_id == comm.get("sys_id"):
                deleted_found = True
                break
        
        if deleted_found:
            raise Exception("Verification failed: Comment still exists in ServiceNow after deletion!")
        else:
            print("Success! Comment successfully verified as deleted.")

        print("\n--- Verification Complete: SUCCESS ---")

    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
