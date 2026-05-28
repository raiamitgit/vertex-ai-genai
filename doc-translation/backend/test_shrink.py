import io
import zipfile
import os

def shrink_pptx_bytes(pptx_bytes):
    # Read the pptx bytes as a zip file
    in_zip = zipfile.ZipFile(io.BytesIO(pptx_bytes), "r")
    out_io = io.BytesIO()
    
    with zipfile.ZipFile(out_io, "w", zipfile.ZIP_DEFLATED) as out_zip:
        for item in in_zip.infolist():
            # Skip media files to save space for translation
            if item.filename.startswith("ppt/media/"):
                continue
            # Also skip embedded objects if they are large
            if item.filename.startswith("ppt/embeddings/"):
                continue
                
            data = in_zip.read(item.filename)
            out_zip.writestr(item, data)
            
    in_zip.close()
    return out_io.getvalue()

if __name__ == "__main__":
    filename = "../Alpha Genome EAP.pptx"
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            b = f.read()
        print(f"Original size: {len(b) / 1024 / 1024:.2f} MB")
        
        shrunk_b = shrink_pptx_bytes(b)
        print(f"Shrunk size: {len(shrunk_b) / 1024 / 1024:.2f} MB")
        
        with open("shrunk.pptx", "wb") as f:
            f.write(shrunk_b)
        print("Saved shrunk.pptx")
