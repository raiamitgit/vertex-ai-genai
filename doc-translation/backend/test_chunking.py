import requests
import os

url = "http://localhost:8000/api/translate"
filename = "../simple_test.pptx"

if not os.path.exists(filename):
    print(f"Test file {filename} not found.")
    exit(1)

print(f"Uploading {filename} to {url}...")
with open(filename, "rb") as f:
    files = {"file": f}
    data = {
        "source_language": "en",
        "target_language": "es"
    }
    response = requests.post(url, files=files, data=data)

if response.status_code == 200:
    print("Translation successful! Saving to output.pptx...")
    with open("output.pptx", "wb") as f:
        f.write(response.content)
else:
    print(f"Error {response.status_code}: {response.text}")
