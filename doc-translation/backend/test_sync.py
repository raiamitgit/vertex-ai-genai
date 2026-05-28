import os
import asyncio
from google.cloud import translate_v3 as translate
import google.auth
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "data-n-models")

def run_test():
    credentials, _ = google.auth.default()
    translate_client = translate.TranslationServiceClient(credentials=credentials)
    
    parent = f"projects/{PROJECT_ID}/locations/us-central1"
    
    with open('/Users/raiamit/Downloads/Alpha Genome EAP.pptx', 'rb') as f:
        document_content = f.read()

    document_input_config = translate.DocumentInputConfig(
        content=document_content,
        mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    request = translate.TranslateDocumentRequest(
        parent=parent,
        source_language_code="en",
        target_language_code="ja",
        document_input_config=document_input_config,
    )
    
    print("Calling sync translate on simple_test.pptx...")
    try:
        response = translate_client.translate_document(request=request)
        print("Success.")
        with open('translated_simple.pptx', 'wb') as f:
             f.write(response.document_translation.byte_stream_outputs[0])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_test()
