#!/usr/bin/env python3
"""
Script to find official websites for dog food brands using web search.
This automates the process of finding brand websites before scraping.
"""
import os
import time
import json
from typing import List, Dict, Optional
from supabase import create_client, Client
import requests
from urllib.parse import urlparse, quote

# Initialize Supabase client
supabase_url = os.environ.get('SUPABASE_URL', 'https://cibjeqgftuxuezarjsdl.supabase.co')
supabase_key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk')

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

supabase: Client = create_client(supabase_url, supabase_key)

# ScrapingBee API key (for web search if needed)
SCRAPINGBEE_API_KEY = os.environ.get('SCRAPINGBEE_API_KEY', 'C88C79QGYUEPQ5GLFKKMYKV9JH0GK1C3ZGQD3KT8GDVXAACNFRW1VGR93K4OZXICDIZPHQGQB0QV6JW8')

def search_brand_website(brand_name: str) -> Optional[str]:
    """
    Search for a brand's official website using web search.
    Returns the most likely official website URL or None if not found.
    """
    # Common search queries to try
    search_queries = [
        f"{brand_name} dog food official website",
        f"{brand_name} pet food official site",
        f"{brand_name} dog food uk",
        f"{brand_name} dog food company"
    ]
    
    # Common domain patterns for dog food brands
    likely_domains = []
    brand_normalized = brand_name.lower().replace(' ', '').replace('-', '').replace('&', 'and')
    
    # Try common domain patterns
    common_patterns = [
        f"{brand_normalized}.com",
        f"{brand_normalized}.co.uk",
        f"{brand_normalized}dogfood.com",
        f"{brand_normalized}petfood.com",
        f"{brand_normalized}pet.com",
        f"{brand_normalized}-pet.com",
        f"{brand_normalized}-dogfood.com"
    ]
    
    print(f"\nSearching for {brand_name} website...")
    
    # Here you would implement actual web search logic
    # For now, returning a placeholder structure
    # In production, you might use:
    # 1. Google Custom Search API
    # 2. Bing Search API
    # 3. ScrapingBee with Google search
    # 4. DuckDuckGo API
    
    # Example structure for manual verification
    print(f"  Suggested searches:")
    for query in search_queries[:2]:
        print(f"    - {query}")
    
    print(f"  Likely domain patterns to check:")
    for pattern in common_patterns[:3]:
        print(f"    - https://{pattern}")
    
    return None

def get_brands_needing_websites(limit: int = 10) -> List[Dict]:
    """Get brands that don't have websites yet"""
    try:
        response = supabase.table('food_brands_sc').select('*').is_('official_website', 'null').order('scraping_priority', desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching brands: {e}")
        return []

def update_brand_website(brand_id: str, brand_name: str, website_url: str, method: str = 'web_search'):
    """Update a brand's official website in the database"""
    try:
        from datetime import datetime
        response = supabase.table('food_brands_sc').update({
            'official_website': website_url,
            'official_website_verified': False,  # Will need manual verification
            'website_discovery_method': method,
            'website_last_checked': datetime.utcnow().isoformat(),
            'scraping_status': 'ready',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', brand_id).execute()
        
        if response.data:
            print(f"  ✓ Updated {brand_name}: {website_url}")
            return True
    except Exception as e:
        print(f"  ✗ Error updating {brand_name}: {e}")
        return False

def process_brands_batch(batch_size: int = 5):
    """Process a batch of brands to find their websites"""
    brands = get_brands_needing_websites(batch_size)
    
    if not brands:
        print("No brands without websites found.")
        return
    
    print(f"Processing {len(brands)} brands...")
    
    results = {
        'found': [],
        'not_found': [],
        'manual_review': []
    }
    
    for brand in brands:
        brand_name = brand['brand_name']
        brand_id = brand['id']
        
        # Search for website
        website = search_brand_website(brand_name)
        
        if website:
            update_brand_website(brand_id, brand_name, website)
            results['found'].append(brand_name)
        else:
            results['manual_review'].append(brand_name)
        
        # Rate limiting
        time.sleep(1)
    
    # Print summary
    print("\n" + "="*80)
    print("SEARCH RESULTS SUMMARY")
    print("="*80)
    
    if results['found']:
        print(f"\n✓ Found websites for {len(results['found'])} brands:")
        for brand in results['found']:
            print(f"  - {brand}")
    
    if results['manual_review']:
        print(f"\n⚠ Need manual review for {len(results['manual_review'])} brands:")
        for brand in results['manual_review']:
            print(f"  - {brand}")
    
    print("="*80)

def generate_manual_search_list():
    """Generate a list of brands for manual website search"""
    brands = get_brands_needing_websites(100)
    
    if not brands:
        print("All brands have websites!")
        return
    
    # Create a CSV file for manual processing
    import csv
    from datetime import datetime
    
    filename = f"brands_needing_websites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['brand_name', 'brand_id', 'suggested_search', 'official_website', 'notes']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for brand in brands:
            writer.writerow({
                'brand_name': brand['brand_name'],
                'brand_id': brand['id'],
                'suggested_search': f"{brand['brand_name']} dog food official website",
                'official_website': '',
                'notes': ''
            })
    
    print(f"Created {filename} with {len(brands)} brands for manual website search")
    print("\nInstructions:")
    print("1. Open the CSV file")
    print("2. Search for each brand's official website")
    print("3. Add the URL in the 'official_website' column")
    print("4. Add any notes (e.g., 'no website found', 'brand defunct')")
    print("5. Run the import_manual_websites.py script to update the database")

def display_statistics():
    """Display current statistics about brand websites"""
    try:
        # Total brands
        total = supabase.table('food_brands_sc').select('id', count='exact').execute()
        print(f"\nTotal brands: {total.count}")
        
        # Brands with websites
        with_websites = supabase.table('food_brands_sc').select('id', count='exact').not_.is_('official_website', 'null').execute()
        without_websites = total.count - with_websites.count if total.count else 0
        
        print(f"Brands with websites: {with_websites.count}")
        print(f"Brands without websites: {without_websites}")
        
        if total.count:
            percentage = (with_websites.count / total.count) * 100
            print(f"Coverage: {percentage:.1f}%")
        
        # Brands ready for scraping
        ready = supabase.table('food_brands_sc').select('id', count='exact').eq('scraping_status', 'ready').execute()
        print(f"\nBrands ready for scraping: {ready.count}")
        
    except Exception as e:
        print(f"Error displaying statistics: {e}")

def main():
    print("="*80)
    print("BRAND WEBSITE FINDER")
    print("="*80)
    
    display_statistics()
    
    print("\n" + "="*80)
    print("OPTIONS:")
    print("="*80)
    print("1. Process batch (attempt to find websites automatically)")
    print("2. Generate manual search list (CSV for manual processing)")
    print("3. Display statistics only")
    print("="*80)
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        batch_size = input("How many brands to process? (default: 5): ").strip()
        batch_size = int(batch_size) if batch_size else 5
        process_brands_batch(batch_size)
    elif choice == '2':
        generate_manual_search_list()
    elif choice == '3':
        # Statistics already displayed
        pass
    else:
        print("Invalid option")

if __name__ == "__main__":
    main()