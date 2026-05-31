"""Local testing harness for verifying A2UI User Profile Agent."""

import asyncio
import json
import logging
import sys

# Configure logging to print clearly to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Import our executor from the active main module
from main import executor

async def run_local_test():
    print("==================================================")
    print("STARTING LOCAL AGENT VERIFICATION")
    print("==================================================")
    
    test_query = "Can you show me the profile"
    print(f"Sending Local Prompt: '{test_query}'\n")

    try:
        # Execute the parsed agent pipeline
        a2a_parts = await executor.execute(test_query)

        print("\n==================================================")
        print("SUCCESS: PARSED A2A RESPONSE PARTS")
        print("==================================================")
        print(json.dumps(a2a_parts, indent=2))
        print("==================================================")

    except Exception as e:
        print("\n[ERROR] TEST FAILED WITH ERROR:")
        logging.exception(e)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_local_test())
