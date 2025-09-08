#!/usr/bin/env python3
"""
Check existing AKC tables in Supabase
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_akc_tables():
    """Check what AKC tables exist in Supabase"""
    
    # Load environment variables
    load_dotenv()
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not url or not key:
        logger.error("Missing Supabase credentials in .env file")
        return None
    
    try:
        # Create Supabase client
        logger.info("Connecting to Supabase...")
        supabase = create_client(url, key)
        
        # List of potential AKC table names to check
        potential_tables = [
            'akc_breeds',
            'akc_breed_data',
            'akc_scraped_breeds',
            'akc_raw_html',
            'akc_breed_details',
            'akc_breed_content'
        ]
        
        existing_tables = []
        
        for table_name in potential_tables:
            try:
                # Try to query each table
                response = supabase.table(table_name).select('*').limit(1).execute()
                existing_tables.append(table_name)
                logger.info(f"✅ Found table: {table_name}")
                
                # Get column info by checking the first row
                if response.data:
                    columns = list(response.data[0].keys())
                    logger.info(f"   Columns: {', '.join(columns[:10])}{'...' if len(columns) > 10 else ''}")
                
            except Exception as e:
                if '404' not in str(e) and 'does not exist' not in str(e):
                    logger.debug(f"   Table {table_name} not found or error: {e}")
        
        return existing_tables
        
    except Exception as e:
        logger.error(f"Error checking tables: {e}")
        return None

def main():
    """Main function"""
    print("=" * 80)
    print("🔍 CHECKING AKC TABLES IN SUPABASE")
    print("=" * 80)
    print()
    
    tables = check_akc_tables()
    
    if tables:
        print()
        print("=" * 80)
        print(f"Found {len(tables)} AKC table(s):")
        for table in tables:
            print(f"  - {table}")
        print("=" * 80)
    else:
        print()
        print("=" * 80)
        print("No AKC-specific tables found")
        print("=" * 80)
    
    return tables

if __name__ == "__main__":
    main()