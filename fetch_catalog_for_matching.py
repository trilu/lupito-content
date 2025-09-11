#!/usr/bin/env python3
"""Quick script to fetch catalog data for OPFF matching"""

import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Get credentials
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("ERROR: Supabase credentials not found")
    exit(1)

print("Connecting to Supabase...")
supabase = create_client(supabase_url, supabase_key)

print("Fetching foods_published catalog...")
response = supabase.table('foods_published').select(
    "product_key,brand,brand_slug,product_name,ingredients_tokens,form,life_stage,kcal_per_100g"
).limit(5000).execute()

df = pd.DataFrame(response.data)
print(f"Fetched {len(df)} products")

# Save to CSV
output_file = "reports/02_foods_published_sample.csv"
df.to_csv(output_file, index=False)
print(f"Saved to {output_file}")

# Show sample
print("\nSample data:")
print(df[['brand', 'product_name']].head())