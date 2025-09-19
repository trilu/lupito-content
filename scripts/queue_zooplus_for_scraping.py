#!/usr/bin/env python3
"""
Queue Zooplus products for ingredient scraping
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def main():
    print("🎯 QUEUING ZOOPLUS PRODUCTS FOR SCRAPING")
    print("=" * 60)
    
    # Connect to Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get Zooplus products without ingredients
    print("Finding Zooplus products without ingredients...")
    
    # Query products with Zooplus URLs but no ingredients
    products_to_scrape = supabase.table('foods_canonical').select(
        'product_key, brand, product_name, product_url'
    ).ilike('product_url', '%zooplus%')\
     .is_('ingredients_raw', 'null')\
     .execute()
    
    print(f"  Found {len(products_to_scrape.data)} products needing ingredients")
    
    # Check if scraping table exists and create if needed
    print("\nChecking scraping queue table...")
    
    # Prepare scraping records
    scraping_records = []
    for product in products_to_scrape.data:
        if not product.get('product_url'):
            continue
            
        scraping_records.append({
            'product_key': product['product_key'],
            'brand': product['brand'],
            'product_name': product['product_name'],
            'product_url': product['product_url'],
            'source': 'zooplus_import_queue',
            'status': 'pending',
            'priority': 1,  # Normal priority
            'created_at': datetime.now().isoformat(),
            'attempts': 0
        })
    
    print(f"  Prepared {len(scraping_records)} products for scraping queue")
    
    # Group by domain for statistics
    print("\nURL distribution:")
    domains = {}
    for record in scraping_records:
        url = record['product_url']
        if 'zooplus.de' in url:
            domain = 'zooplus.de'
        elif 'zooplus.co.uk' in url:
            domain = 'zooplus.co.uk'
        elif 'zooplus.fr' in url:
            domain = 'zooplus.fr'
        elif 'zooplus.it' in url:
            domain = 'zooplus.it'
        elif 'zooplus.es' in url:
            domain = 'zooplus.es'
        else:
            domain = 'zooplus.com'
        
        domains[domain] = domains.get(domain, 0) + 1
    
    for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
        print(f"  {domain}: {count} products")
    
    # Sample products
    print("\nSample products to scrape:")
    for product in scraping_records[:5]:
        print(f"  - {product['brand']}: {product['product_name'][:50]}")
        print(f"    URL: {product['product_url'][:80]}...")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SCRAPING QUEUE SUMMARY")
    print(f"  Total products to scrape: {len(scraping_records)}")
    print(f"  Estimated time (at 2 sec/product): {len(scraping_records) * 2 / 60:.1f} minutes")
    print(f"  Estimated time (at 5 sec/product): {len(scraping_records) * 5 / 60:.1f} minutes")
    
    # Create CSV for scraping
    print("\nCreating scraping CSV...")
    import pandas as pd
    
    df = pd.DataFrame([{
        'product_key': r['product_key'],
        'brand': r['brand'],
        'product_name': r['product_name'],
        'product_url': r['product_url']
    } for r in scraping_records])
    
    output_file = 'data/zooplus_to_scrape.csv'
    df.to_csv(output_file, index=False)
    print(f"  ✅ Saved {len(df)} products to {output_file}")
    
    # Also get products from staging that need scraping
    print("\nChecking staging table for products without ingredients...")
    staging_need_scraping = supabase.table('zooplus_staging').select(
        'product_key, brand, product_name, product_url'
    ).eq('has_ingredients', False)\
     .eq('processed', True)\
     .execute()
    
    if staging_need_scraping.data:
        print(f"  Found {len(staging_need_scraping.data)} additional products in staging")
        
        # Create combined CSV
        staging_df = pd.DataFrame(staging_need_scraping.data)
        combined_df = pd.concat([df, staging_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['product_url'])
        
        combined_file = 'data/zooplus_all_to_scrape.csv'
        combined_df.to_csv(combined_file, index=False)
        print(f"  ✅ Saved {len(combined_df)} total products to {combined_file}")
        
        print(f"\n  Total unique products to scrape: {len(combined_df)}")
        print(f"  Estimated time (at 2 sec/product): {len(combined_df) * 2 / 60:.1f} minutes")
    
    print("\n✅ Scraping queue prepared!")
    print("📝 Next steps:")
    print("  1. Review data/zooplus_to_scrape.csv")
    print("  2. Run scraping script to collect ingredients")
    print("  3. Update database with scraped data")

if __name__ == "__main__":
    main()