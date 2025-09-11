#!/usr/bin/env python3
"""Quick coverage check"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(url, key)

print("CURRENT COVERAGE IN foods_canonical:")
print("="*50)

# Total
resp = supabase.table('foods_canonical').select("*", count='exact', head=True).execute()
total = resp.count or 0
print(f"Total products: {total:,}")

# Form
resp = supabase.table('foods_canonical').select("*", count='exact', head=True).not_.is_('form', 'null').execute()
form_pct = (resp.count or 0) / total * 100 if total > 0 else 0
print(f"Form coverage: {form_pct:.1f}%")

# Life stage
resp = supabase.table('foods_canonical').select("*", count='exact', head=True).not_.is_('life_stage', 'null').execute()
life_pct = (resp.count or 0) / total * 100 if total > 0 else 0
print(f"Life stage coverage: {life_pct:.1f}%")

# Ingredients
resp = supabase.table('foods_canonical').select("*", count='exact', head=True).not_.is_('ingredients_tokens', 'null').execute()
ing_pct = (resp.count or 0) / total * 100 if total > 0 else 0
print(f"Ingredients coverage: {ing_pct:.1f}%")

# Valid kcal
resp = supabase.table('foods_canonical').select("*", count='exact', head=True).gte('kcal_per_100g', 200).lte('kcal_per_100g', 600).execute()
kcal_pct = (resp.count or 0) / total * 100 if total > 0 else 0
print(f"Valid kcal (200-600): {kcal_pct:.1f}%")

print("\nGATE STATUS:")
print(f"Form ≥ 90%: {'✅' if form_pct >= 90 else '❌'}")
print(f"Life stage ≥ 95%: {'✅' if life_pct >= 95 else '❌'}")
print(f"Ingredients ≥ 85%: {'✅' if ing_pct >= 85 else '❌'}")
print(f"Kcal valid ≥ 90%: {'✅' if kcal_pct >= 90 else '❌'}")