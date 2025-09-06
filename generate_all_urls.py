#!/usr/bin/env python3
"""
Generate all PFX product URLs using API discovery
Then save them for the URL scraper to process
"""
import requests
import time

def main():
    print("🔍 Generating all PFX product URLs...")
    
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0)'})
    
    all_urls = []
    page = 1
    
    while page <= 200:  # Safety limit
        try:
            url = f"https://petfoodexpert.com/api/products?species=dog&page={page}"
            print(f"Page {page}: ", end="", flush=True)
            
            response = session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            products = data.get('data', [])
            
            if not products:
                print(f"EMPTY - Done at page {page}")
                break
            
            # Extract URLs
            page_urls = []
            for product in products:
                product_url = product.get('url', '')
                if product_url:
                    page_urls.append(product_url)
            
            all_urls.extend(page_urls)
            print(f"{len(page_urls)} URLs (Total: {len(all_urls)})")
            
            page += 1
            time.sleep(0.2)  # Small delay
            
        except Exception as e:
            print(f"ERROR: {e}")
            break
    
    # Save URLs to file
    output_file = 'all_pfx_urls.txt'
    with open(output_file, 'w') as f:
        for url in all_urls:
            f.write(url + '\n')
    
    print(f"\n✅ Generated {len(all_urls)} URLs")
    print(f"📁 Saved to: {output_file}")
    print(f"🚀 Ready for URL scraper!")

if __name__ == '__main__':
    main()