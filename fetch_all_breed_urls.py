#!/usr/bin/env python3
"""
Fetch all breed URLs from dogo.app
"""
import requests
from bs4 import BeautifulSoup
import time

def fetch_all_breed_urls():
    """Fetch all breed URLs from both pages of the breeds list"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; LupitoBreedBot/1.0)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    # Find all links that match the breed pattern
    breed_links = set()
    
    # Fetch from both pages
    pages = [
        "https://dogo.app/dog-breeds",
        "https://dogo.app/dog-breeds?27efb331_page=1",
        "https://dogo.app/dog-breeds?27efb331_page=2"
    ]
    
    for page_url in pages:
        print(f"Fetching breed URLs from: {page_url}")
        response = requests.get(page_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for all anchor tags
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Check if it's a breed URL
            if href.startswith('/dog-breeds/') and len(href.split('/')) == 3:
                # Convert to full URL
                full_url = f"https://dogo.app{href}"
                breed_links.add(full_url)
        
        # Small delay between requests
        time.sleep(1)
    
    # Sort alphabetically
    breed_urls = sorted(list(breed_links))
    
    print(f"Found {len(breed_urls)} breed URLs")
    
    # Save to file
    with open('all_breed_urls.txt', 'w') as f:
        f.write("# All Dog Breed URLs from dogo.app\n")
        f.write(f"# Total: {len(breed_urls)} breeds\n\n")
        for url in breed_urls:
            f.write(f"{url}\n")
    
    print(f"Saved to all_breed_urls.txt")
    
    # Also print first 10 for verification
    print("\nFirst 10 breed URLs:")
    for url in breed_urls[:10]:
        print(f"  - {url}")
    
    return breed_urls

if __name__ == "__main__":
    fetch_all_breed_urls()