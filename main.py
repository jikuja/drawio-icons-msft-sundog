
import requests
from bs4 import BeautifulSoup
import os

URL = 'https://web.archive.org/web/20240324020531/https://azure.microsoft.com/en-us/patterns/styles/glyphs-icons/'
OUTPUT_DIR = 'extracted_svgs'
CACHE_FILE = '.input.html'

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()

def load_html():
    if os.path.exists(CACHE_FILE):
        print(f"Using cached HTML from {CACHE_FILE}")
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        print(f"Fetching HTML from {URL}")
        response = requests.get(URL)
        response.raise_for_status()
        html = response.text
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML saved to {CACHE_FILE}")
        return html

def main():
    html = load_html()
    soup = BeautifulSoup(html, 'lxml')

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    svgs = soup.find_all('svg')
    print(f"Found {len(svgs)} SVG(s)")

    for svg in svgs:
        parent = svg.find_parent().find_parent()
        title_attr = parent.get('title', None)

        if not title_attr:
            print("⚠️ Skipping SVG with no title on parent.")
            continue

        filename = sanitize_filename(f"{title_attr}.svg")
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(svg))

        print(f"Saved: {filepath}")

if __name__ == "__main__":
    main()
