import urllib.parse
import urllib.request
import json
import time
import ssl
import random
import os

# Global context for SSL
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}

def get_json(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return "RATE_LIMIT"
        print(f"  HTTP {e.code} for {url}")
        time.sleep(1)
    except urllib.error.URLError as e:
        print(f"  Network Error {e} for {url}")
        time.sleep(2)
        return "RETRY"
    except Exception as e:
        print(f"  Error {e} for {url}")
    return None

def search_open_library(query):
    base_url = "https://openlibrary.org/search.json"
    params = {"q": query}
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    retries = 3
    data = None
    for _ in range(retries):
        data = get_json(url)
        if data == "RETRY":
            continue
        if data == "RATE_LIMIT":
            return "RATE_LIMIT"
        break
        
    if data and isinstance(data, dict) and "docs" in data:
        # Iterate through first 5 docs to find one with a cover
        for doc in data["docs"][:5]:
            cover_i = doc.get("cover_i")
            if cover_i:
                return f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"
    return None

def search_google_books(query):
    base_url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query, "maxResults": 1}
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    data = get_json(url)
    if data and isinstance(data, dict) and "items" in data:
        for item in data["items"]:
            volume_info = item.get("volumeInfo", {})
            image_links = volume_info.get("imageLinks", {})
            # Try to get high res versions, fallback to thumbnail
            thumbnail = image_links.get("extraLarge") or image_links.get("large") or image_links.get("medium") or image_links.get("thumbnail")
            if thumbnail:
                # Force https
                return thumbnail.replace("http://", "https://")
    return None

def search_book_cover(query, title=None):
    # Try OpenLibrary
    res = search_open_library(query)
    if res and res != "RATE_LIMIT":
        return res
    
    # Try Google Books
    res = search_google_books(query)
    if res:
        return res
    
    # Try title only as fallback
    if title:
        res = search_google_books(title)
        if res: return res
        res = search_open_library(title)
        if res and res != "RATE_LIMIT": return res
        
    return None

def clean_query(line):
    # Parse "Title by Author"
    line = line.strip()
    if " by " in line:
        parts = line.split(" by ")
        title = parts[0].strip()
        author = parts[1].strip()
        
        # Handle "Last, First" -> "First Last"
        if "," in author:
            names = author.split(",")
            if len(names) == 2:
                author = f"{names[1].strip()} {names[0].strip()}"
                
        return f"{title} {author}"
    return line

def generate_html(books):
    # Start the HTML file
    os.makedirs("covers", exist_ok=True)
    
    header = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Book Covers Gallery</title>
    <style>
        body { font-family: system-ui; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .gallery { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); 
            gap: 15px; 
        }
        .book-card { 
            background: white; 
            padding: 8px; 
            border-radius: 6px; 
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .book-cover { 
            width: 100%; 
            height: 180px; 
            object-fit: contain; 
            background: #eee;
            margin-bottom: 5px;
        }
        .book-title { font-size: 11px; line-height: 1.3; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Book Collection</h1>
        <div id="status">Generating...</div>
        <div class="gallery" id="gallery">
"""
    
    with open("book_gallery.html", "w") as f:
        f.write(header)
    
    found = 0
    total = len(books)
    
    for i, line in enumerate(books):
        original_line = line.strip()
        if not original_line: continue
        
        if not original_line: continue
        
        # Create a safe filename for possible download
        safe_title = "".join(c for c in original_line if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(" ", "_")[:50]
        local_filename = f"covers/{i+1:03d}_{safe_title}.jpg"
        
        # Check if file already exists
        if os.path.exists(local_filename) and os.path.getsize(local_filename) > 0:
            print(f"[{i+1}/{total}] File exists: {local_filename}")
            card_html = f"""
            <div class="book-card">
                <img src="file://{os.path.abspath(local_filename)}" class="book-cover" loading="lazy">
            </div>
            """
            found += 1
            # Append to file
            with open("book_gallery.html", "a") as f:
                f.write(card_html)
            continue

        query = clean_query(original_line)
        title_only = original_line.split(" by ")[0] if " by " in original_line else original_line
        print(f"[{i+1}/{total}] Searching: {query}")
        
        img_url = search_book_cover(query, title=title_only)
        
        card_html = ""
            
        if img_url:
            print(f"  -> Found: {img_url}")
            
            # Check if file already exists
            if os.path.exists(local_filename) and os.path.getsize(local_filename) > 0:
                print("  -> File exists, skipping download.")
                card_html = f"""
                <div class="book-card">
                    <img src="file://{os.path.abspath(local_filename)}" class="book-cover" loading="lazy">
                </div>
                """
                found += 1
            else:
                try:
                    # Download with headers
                    req = urllib.request.Request(img_url, headers=HEADERS)
                    with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                        with open(local_filename, "wb") as img_file:
                            img_file.write(response.read())
                    
                    # Verify file size > 0
                    if os.path.exists(local_filename) and os.path.getsize(local_filename) > 0:
                        found += 1
                        card_html = f"""
                        <div class="book-card">
                            <img src="file://{os.path.abspath(local_filename)}" class="book-cover" loading="lazy">
                        </div>
                        """
                    else:
                        print("  -> Downloaded file was empty or missing.")
                        raise Exception("Empty download")

                except Exception as e:
                    print(f"  -> Failed to download image: {e}")
                    card_html = f"""
                    <div class="book-card">
                        <div class="book-cover" style="display:flex;align-items:center;justify-content:center;color:#999">Download Failed</div>
                    </div>
                    """
        else:
            print("  -> No cover found")
            card_html = f"""
            <div class="book-card">
                <div class="book-cover" style="display:flex;align-items:center;justify-content:center;color:#999">No Image</div>
            </div>
            """
        
        # Append to file
        with open("book_gallery.html", "a") as f:
            f.write(card_html)
        
        # Polite delay
        time.sleep(random.uniform(0.5, 1.0))
        
    footer = """
        </div>
    </div>
    <script>
        document.getElementById('status').innerText = "Gallery Generation Complete";
    </script>
</body>
</html>
"""
    with open("book_gallery.html", "a") as f:
        f.write(footer)
    print(f"Done. Found {found}/{total}")

if __name__ == "__main__":
    # Test read
    if os.path.exists("book_list.txt"):
        with open("book_list.txt", "r") as f:
            lines = f.readlines()
        generate_html(lines)
    else:
        print("book_list.txt not found")
