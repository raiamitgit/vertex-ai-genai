import os
import asyncio
import tempfile
import pathlib
import uuid
from typing import Annotated
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from google.cloud import translate_v3 as translate
from google.cloud import storage
import google.auth
from dotenv import load_dotenv
import document_chunker

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "data-n-models")
GCS_BUCKET_PATH = os.environ.get("GCS_BUCKET_PATH", "data-n-models-experiment/translation")

def get_translate_client():
    try:
        credentials, project_id = google.auth.default()
        client = translate.TranslationServiceClient(credentials=credentials)
        return client
    except Exception as e:
        print(f"Auth error: {e}")
        return None

def get_storage_client():
    try:
        credentials, project_id = google.auth.default()
        client = storage.Client(credentials=credentials, project=PROJECT_ID)
        return client
    except Exception as e:
        print(f"Auth error (Storage): {e}")
        return None

@app.post("/api/translate")
async def translate_document(
    file: Annotated[UploadFile, File(...)],
    source_language: Annotated[str, Form(...)],
    target_language: Annotated[str, Form(...)]
):
    translate_client = get_translate_client()
    storage_client = get_storage_client()
    
    if not translate_client or not storage_client:
        raise HTTPException(status_code=500, detail="Failed to authenticate with Google Cloud.")

    document_content = await file.read()
    file_size_bytes = len(document_content)
    is_large_file = file_size_bytes > 20 * 1024 * 1024
    
    mime_type = None
    if file.filename.endswith(".pdf"):
        mime_type = "application/pdf"
    elif file.filename.endswith(".docx"):
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif file.filename.endswith(".doc"):
        mime_type = "application/msword"
    elif file.filename.endswith(".pptx"):
        mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif file.filename.endswith(".ppt"):
        mime_type = "application/vnd.ms-powerpoint"
        
    if not mime_type:
        raise HTTPException(status_code=400, detail="Unsupported file format.")

    parent = f"projects/{PROJECT_ID}/locations/us-central1"
    suffix = pathlib.Path(file.filename).suffix
    name_part = file.filename.rsplit('.', 1)[0]
    translated_filename = f"{name_part}_{target_language}{suffix}"

    try:
        if not is_large_file:
            # Synchronous Translation (<= 20MB)
            document_input_config = translate.DocumentInputConfig(
                content=document_content,
                mime_type=mime_type,
            )
            request = translate.TranslateDocumentRequest(
                parent=parent,
                source_language_code=source_language,
                target_language_code=target_language,
                document_input_config=document_input_config,
            )
            response = translate_client.translate_document(request=request)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(response.document_translation.byte_stream_outputs[0])
            temp_file.close()

            return FileResponse(
                path=temp_file.name,
                filename=translated_filename,
                media_type=mime_type
            )
        
        else:
            print("--- Starting Large File Chunked Synchronous Translation ---")
            chunks = []
            if file.filename.endswith(".pdf"):
                chunks = document_chunker.split_pdf(document_content, chunk_size=10) # 10 pages per chunk
            elif file.filename.endswith((".pptx", ".ppt")):
                chunks = document_chunker.split_pptx(document_content, chunk_size=20) # 20 slides per chunk
            elif file.filename.endswith((".docx", ".doc")):
                chunks = document_chunker.split_docx(document_content)
                if len(chunks) == 1 and len(chunks[0]) > 20 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="DOCX files > 20MB are currently unsupported for chunking.")
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format for large file chunking.")

            translated_chunks = []
            print(f"File split into {len(chunks)} chunks. Translating sequentially...")
            
            for i, chunk in enumerate(chunks):
                print(f"Translating chunk {i+1}/{len(chunks)}...")
                chunk_bytes = chunk if not isinstance(chunk, dict) else chunk["bytes"]
                
                document_input_config = translate.DocumentInputConfig(
                    content=chunk_bytes,
                    mime_type=mime_type,
                )
                request = translate.TranslateDocumentRequest(
                    parent=parent,
                    source_language_code=source_language,
                    target_language_code=target_language,
                    document_input_config=document_input_config,
                )
                response = translate_client.translate_document(request=request)
                translated_bytes = response.document_translation.byte_stream_outputs[0]
                
                if isinstance(chunk, dict):
                    translated_chunks.append({
                        "bytes": translated_bytes,
                        "start_idx": chunk["start_idx"],
                        "end_idx": chunk["end_idx"]
                    })
                else:
                    translated_chunks.append(translated_bytes)
                    
            print("Merging translated chunks...")
            if file.filename.endswith(".pdf"):
                final_bytes = document_chunker.merge_pdfs(translated_chunks)
            elif file.filename.endswith((".pptx", ".ppt")):
                final_bytes = document_chunker.merge_pptx(document_content, translated_chunks)
            elif file.filename.endswith((".docx", ".doc")):
                final_bytes = document_chunker.merge_docx(translated_chunks)
                
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(final_bytes)
            temp_file.close()

            return FileResponse(
                path=temp_file.name,
                filename=translated_filename,
                media_type=mime_type
            )

    except Exception as e:
        print(f"Translation Error Header: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
