#!/usr/bin/env python3
"""
Check the actual columns in each food table
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

tables = ['food_candidates', 'food_candidates_sc', 'food_brands']

for table in tables:
    try:
        # Get one row to see columns
        response = supabase.table(table).select('*').limit(1).execute()
        
        if response.data and len(response.data) > 0:
            columns = list(response.data[0].keys())
            print(f"\n{table} columns:")
            for col in sorted(columns):
                print(f"  - {col}")
        else:
            print(f"\n{table}: No data")
            
    except Exception as e:
        print(f"\n{table}: Error - {e}")