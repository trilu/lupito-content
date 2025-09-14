#!/usr/bin/env python3
"""
Export the exact list of 227 products missing ingredients to a file
"""

import os
import json
import csv
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def export_missing_ingredients_list():
    """Export the 227 products to JSON and CSV files"""
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("🎯 EXPORTING 227 PRODUCTS MISSING INGREDIENTS")
    print("=" * 50)
    
    # Get all products missing ingredients
    response = supabase.table('foods_canonical').select(
        'product_key, product_name, brand, product_url'
    ).ilike('product_url', '%zooplus%')\
    .is_('ingredients_raw', 'null')\
    .order('product_key').execute()
    
    products = response.data
    
    print(f"Found {len(products)} products missing ingredients")
    
    # Export to JSON
    json_filename = f"zooplus_missing_ingredients_{datetime.now().strftime('%Y%m%d')}.json"
    json_path = f"data/{json_filename}"
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "export_date": datetime.now().isoformat(),
            "total_products": len(products),
            "description": "Zooplus products missing ingredients data - need to scrape to achieve 95% coverage",
            "products": products
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ JSON exported to: {json_path}")
    
    # Export to CSV
    csv_filename = f"zooplus_missing_ingredients_{datetime.now().strftime('%Y%m%d')}.csv"
    csv_path = f"data/{csv_filename}"
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        if products:
            fieldnames = ['product_key', 'product_name', 'brand', 'product_url']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)
    
    print(f"✅ CSV exported to: {csv_path}")
    
    # Export to simple text file for easy viewing
    txt_filename = f"zooplus_missing_ingredients_{datetime.now().strftime('%Y%m%d')}.txt"
    txt_path = f"data/{txt_filename}"
    
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"ZOOPLUS PRODUCTS MISSING INGREDIENTS - {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"Total: {len(products)} products\n")
        f.write("=" * 80 + "\n\n")
        
        for i, product in enumerate(products, 1):
            f.write(f"{i:3d}. {product['brand']} - {product['product_name']}\n")
            f.write(f"     Key: {product['product_key']}\n")
            f.write(f"     URL: {product['product_url']}\n")
            f.write("\n")
    
    print(f"✅ Text file exported to: {txt_path}")
    
    # Show summary
    print(f"\n📊 EXPORT SUMMARY:")
    print(f"   Total products: {len(products)}")
    print(f"   Files created:")
    print(f"     - {json_path} (JSON format)")
    print(f"     - {csv_path} (CSV format)")
    print(f"     - {txt_path} (Text format)")
    
    # Show first few products
    print(f"\n📋 FIRST 5 PRODUCTS:")
    for i, product in enumerate(products[:5], 1):
        print(f"   {i}. {product['brand']} - {product['product_name'][:60]}...")
        print(f"      URL: {product['product_url'][:80]}...")
        print()

if __name__ == "__main__":
    export_missing_ingredients_list()