#!/usr/bin/env python3
"""
Discover ALL breed-related tables in Supabase
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# More comprehensive list of potential breed tables
potential_tables = [
    # Direct breed tables
    'breed_raw',
    'breeds', 
    'breed_data',
    'breed_catalog',
    'breeds_scraped',
    'breed_profiles',
    'breed_info',
    'breed_details',
    'breed_characteristics',
    
    # Source-specific tables
    'akc_breeds',
    'akc_breed_data',
    'bark_breeds',
    'wikipedia_breeds',
    'wiki_breeds',
    
    # Other patterns
    'dog_breeds',
    'canine_breeds',
    'breed_types',
    'breed_groups',
    'breed_standards',
    
    # Check for any table with 'breed' in name
    'breeds_temp',
    'breed_mapping',
    'breed_aliases',
    'breed_lookup'
]

print("="*80)
print("COMPREHENSIVE BREED TABLE DISCOVERY")
print("="*80)
print()

discovered = {}

for table in potential_tables:
    try:
        response = supabase.table(table).select('*', count='exact').limit(1).execute()
        
        if response:
            count = response.count
            columns = list(response.data[0].keys()) if response.data else []
            
            # Only show tables with data
            if count > 0:
                discovered[table] = {
                    'count': count,
                    'columns': len(columns),
                    'key_columns': [c for c in columns if any(k in c.lower() for k in 
                                   ['breed', 'name', 'size', 'weight', 'activity', 'energy'])][:10]
                }
                
                print(f"✅ {table}")
                print(f"   Rows: {count:,}")
                print(f"   Columns: {len(columns)}")
                print(f"   Key fields: {', '.join(discovered[table]['key_columns'])}")
                
                # Show sample data
                if response.data:
                    sample = response.data[0]
                    # Show meaningful fields
                    for key in ['breed_name', 'name', 'breed_slug', 'name_en', 'display_name']:
                        if key in sample and sample[key]:
                            print(f"   Sample {key}: {sample[key]}")
                            break
                print()
                
    except Exception as e:
        if '404' not in str(e) and 'does not exist' not in str(e):
            logger.debug(f"Error checking {table}: {e}")

print("="*80)
print(f"SUMMARY: Found {len(discovered)} breed tables with data")
print("="*80)

# Summary table
if discovered:
    print("\n| Table | Rows | Columns | Key Fields |")
    print("|-------|------|---------|------------|")
    for table, info in discovered.items():
        print(f"| {table} | {info['count']:,} | {info['columns']} | {', '.join(info['key_columns'][:3])} |")