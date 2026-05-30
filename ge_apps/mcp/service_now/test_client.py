"""Verification script for ServiceNow Client.

This script loads the local .env file and executes live integration checks
for both Incidents and Knowledge Base operations in ServiceNow.
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
        # ======================================================================
        # Part 1: Testing Incidents Operations
        # ======================================================================
        print("\n==================================================")
        print("Testing ServiceNow INCIDENTS Integration")
        print("==================================================")

        print("\n--- 1. Testing list_recent_incidents ---")
        incidents = servicenow_client.list_recent_incidents(limit=3)
        print(f"Successfully retrieved {len(incidents)} incidents.")
        for inc in incidents:
            print(f"  - {inc.get('number')}: {inc.get('short_description')} (State: {inc.get('state')})")
        
        if not incidents:
            print("No incidents found in the instance. Skipping detail tests.")
        else:
            target_ticket = incidents[0].get("number")
            print(f"\nUsing ticket {target_ticket} for detail and comment write tests.")

            print("\n--- 2. Testing get_incident_details ---")
            details = servicenow_client.get_incident_details(target_ticket)
            print("Incident Details:")
            print(f"  - Sys ID: {details.get('sys_id')}")
            print(f"  - Short Description: {details.get('short_description')}")
            print(f"  - Priority: {details.get('priority')} | Urgency: {details.get('urgency')}")

            print("\n--- 3. Testing get_incident_comments ---")
            comments = servicenow_client.get_incident_comments(target_ticket)
            print(f"Retrieved {len(comments)} comments.")

            print("\n--- 4. Testing add_incident_comment (Live Write Test) ---")
            unique_token = f"Verification token: {int(time.time())}"
            test_comment = f"Verification check by test_client.py. {unique_token}"
            add_res = servicenow_client.add_incident_comment(target_ticket, test_comment)
            print(f"Add Result: {add_res}")

            # Verify and resolve the sys_id
            print("\nVerifying comment creation...")
            updated_comments = servicenow_client.get_incident_comments(target_ticket)
            comment_sys_id = None
            for comm in updated_comments:
                if unique_token in comm.get("value", ""):
                    comment_sys_id = comm.get("sys_id")
                    print(f"Found matching comment! sys_id: {comment_sys_id}")
                    break
            
            if not comment_sys_id:
                raise Exception("Comment write test failed: Added comment not found!")

            print("\n--- 5. Testing delete_comment (Live Cleanup Test) ---")
            del_res = servicenow_client.delete_comment(comment_sys_id)
            print(f"Delete Result: {del_res}")

        # ======================================================================
        # Part 2: Testing Knowledge Base Operations
        # ======================================================================
        print("\n==================================================")
        print("Testing ServiceNow KNOWLEDGE BASE Integration")
        print("==================================================")

        print("\n--- 6. Testing create_knowledge_article (Live Write Test) ---")
        kb_unique_token = f"KB Verification token: {int(time.time())}"
        kb_title = f"Test Article - {kb_unique_token}"
        kb_text = f"<p>This is a test article created by the integration suite. Verification token: {kb_unique_token}</p>"
        
        kb_create_res = servicenow_client.create_knowledge_article(kb_title, kb_text)
        print(f"Create KB Article Result: {kb_create_res}")
        
        target_art_number = kb_create_res.get("number")
        target_art_sys_id = kb_create_res.get("sys_id")
        print(f"Created Article sys_id: {target_art_sys_id} | Number: {target_art_number}")

        print("\n--- 7. Testing get_knowledge_article ---")
        # Query by sys_id directly to prevent sequential number collision with pre-existing PDI demo data
        kb_details = servicenow_client.get_knowledge_article(target_art_sys_id)
        print("Knowledge Article Details:")
        print(f"  - Number: {kb_details.get('number')}")
        print(f"  - Title: {kb_details.get('short_description')}")
        print(f"  - Content length: {len(kb_details.get('text', ''))} chars")

        print("\n--- 8. Testing search_knowledge_base ---")
        search_query = "Test Article"
        search_results = servicenow_client.search_knowledge_base(search_query, limit=3)
        print(f"Search for '{search_query}' returned {len(search_results)} matches.")
        for art in search_results:
            print(f"  - {art.get('number')}: {art.get('short_description')}")
            if art.get("number") == target_art_number:
                print("    (Successfully located our newly created test article in search results!)")

        print("\n--- 9. Testing delete_knowledge_article (Live Cleanup Test) ---")
        kb_del_res = servicenow_client.delete_knowledge_article(target_art_sys_id)
        print(f"Delete KB Article Result: {kb_del_res}")

        # Double check it is gone
        print("\nVerifying KB article deletion...")
        try:
            servicenow_client.get_knowledge_article(target_art_sys_id)
            raise Exception("Verification failed: KB article still exists after deletion!")
        except Exception as e:
            if "no record found" in str(e).lower() or "not found" in str(e).lower() or "404" in str(e).lower():
                print("Success! KB Article successfully verified as deleted from the database.")
            else:
                raise e



        print("\n==================================================")
        print("Verification Complete: ALL TESTS PASSED SUCCESSFUL! ")
        print("==================================================")

    except Exception as e:
        print(f"\n Verification FAILED with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
