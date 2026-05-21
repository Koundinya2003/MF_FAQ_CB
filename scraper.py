import os
import json
import requests
from bs4 import BeautifulSoup

# Verified Mirae Asset Scheme URLs
FUND_URLS = [
    "https://www.miraeassetmf.co.in/mutual-fund-scheme/equity-fund/mirae-asset-large-cap-fund",
    "https://www.miraeassetmf.co.in/mutual-fund-scheme/equity-fund/mirae-asset-elss-tax-saver-fund",
    "https://www.miraeassetmf.co.in/mutual-fund-scheme/equity-fund/mirae-asset-flexi-cap-fund",
    "https://www.miraeassetmf.co.in/mutual-fund-scheme/equity-fund/mirae-asset-midcap-fund"
]

BLOCKLIST_PATTERNS = [
    "privacy policy", "terms of use", "copyright", "disclaimer",
    "navigational", "menu", "footer", "header", "login", "register"
]

def scrape_page(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        # Extract text
        text = soup.get_text(separator=' ')

        # Simple cleaning
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return {
            "url": url,
            "content": text
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def main():
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    scraped_data = []
    for url in FUND_URLS:
        print(f"Scraping {url}...")
        page_data = scrape_page(url)
        if page_data:
            scraped_data.append(page_data)

    output_file = os.path.join(data_dir, "scraped_data.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, indent=2)
    print(f"Saved {len(scraped_data)} pages to {output_file}")

if __name__ == "__main__":
    main()
