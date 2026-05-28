import os
import google.auth
from google.cloud import translate_v3 as translate
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "data-n-models")

def list_operations():
    credentials, _ = google.auth.default()
    client = translate.TranslationServiceClient(credentials=credentials)
    
    parent = f"projects/{PROJECT_ID}/locations/us-central1"
    
    # Unfortunately, the standard translate_v3 client might not expose ListOperations directly
    # because it's a mixin or grpc raw.
    # We can use google-api-core operations client.
    operations_client = client.transport.operations_client
    
    request = {"name": parent, "filter": ""}
    print(f"Listing operations for {parent}...")
    try:
        response = operations_client.list_operations(name=parent, filter_="")
        ops = list(response)
        print(f"Found {len(ops)} operations.")
        for op in ops[:5]:
            print(f"Name: {op.name}")
            print(f"Done: {op.done}")
            if op.error.code:
                print(f"Error Code: {op.error.code}")
                print(f"Error Message: {op.error.message}")
            print("---")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_operations()
