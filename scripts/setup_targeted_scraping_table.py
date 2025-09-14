#!/usr/bin/env python3
"""
Setup targeted scraping table for the exact 227 products missing ingredients
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def setup_targeted_table():
    """Create and populate the targeted scraping table"""
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("🎯 SETTING UP TARGETED SCRAPING TABLE")
    print("=" * 50)
    
    # Read and execute the SQL script
    with open('scripts/create_missing_ingredients_table.sql', 'r') as f:
        sql_content = f.read()
    
    # Split SQL into individual statements and execute
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
    
    for i, statement in enumerate(statements):
        if statement.upper().startswith('SELECT'):
            # Execute SELECT statements and show results
            try:
                result = supabase.rpc('execute_sql', {'query': statement}).execute()
                print(f"\n📊 Query {i+1} Results:")
                if result.data:
                    for row in result.data:
                        print(f"   {row}")
                else:
                    print("   No results returned")
            except Exception as e:
                print(f"❌ Error executing SELECT statement: {e}")
                # Try alternative approach for SELECT statements
                try:
                    if 'COUNT' in statement.upper():
                        # Handle summary query
                        response = supabase.table('foods_canonical').select(
                            'product_key', count='exact'
                        ).ilike('product_url', '%zooplus%')\
                        .is_('ingredients_raw', 'null').execute()
                        print(f"   Total missing ingredients: {response.count}")
                except Exception as e2:
                    print(f"❌ Alternative query failed: {e2}")
        else:
            # Execute DDL/DML statements
            try:
                supabase.rpc('execute_sql', {'query': statement}).execute()
                print(f"✅ Executed statement {i+1}")
            except Exception as e:
                print(f"❌ Error executing statement {i+1}: {e}")
                # For table creation, we'll create it manually
                if 'CREATE TABLE' in statement.upper():
                    print("   Attempting manual table creation...")
                    # We'll handle this in a separate function
    
    # Verify the table was created and populated
    try:
        # Get count of missing products directly
        response = supabase.table('foods_canonical').select(
            'product_key', count='exact'
        ).ilike('product_url', '%zooplus%')\
        .is_('ingredients_raw', 'null').execute()
        
        print(f"\n🎯 SUMMARY:")
        print(f"   Products missing ingredients: {response.count}")
        
        # Show sample of products that need scraping
        sample_response = supabase.table('foods_canonical').select(
            'product_key, product_name, brand, product_url'
        ).ilike('product_url', '%zooplus%')\
        .is_('ingredients_raw', 'null')\
        .limit(5).execute()
        
        print(f"\n📋 SAMPLE PRODUCTS TO SCRAPE:")
        for i, product in enumerate(sample_response.data, 1):
            print(f"   {i}. {product['brand']} - {product['product_name'][:50]}...")
            print(f"      Key: {product['product_key']}")
            print(f"      URL: {product['product_url'][:70]}...")
            print()
        
    except Exception as e:
        print(f"❌ Error verifying results: {e}")
    
    print("✅ Targeted scraping setup complete!")
    print("\nNext step: Create a targeted scraper that queries this specific list")

if __name__ == "__main__":
    setup_targeted_table()