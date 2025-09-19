#!/usr/bin/env python3
"""
Reverse-engineer the production filtering logic that reduces products
from 9,339 (preview) to 3,119 (production) - a 66% filter rate.

This script analyzes the differences between foods_published_preview
and foods_published_prod tables to identify exact filtering criteria.
"""

import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from collections import Counter
import json

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

print("="*80)
print("PRODUCTION FILTERING LOGIC ANALYSIS")
print("="*80)

# Step 1: Get basic row counts
print("\n1. ROW COUNTS:")
print("-"*40)

try:
    preview_count = supabase.table('foods_published_preview').select('product_key', count='exact').execute()
    prod_count = supabase.table('foods_published_prod').select('product_key', count='exact').execute()

    preview_total = preview_count.count
    prod_total = prod_count.count
    filter_rate = ((preview_total - prod_total) / preview_total) * 100

    print(f"Preview table: {preview_total:,} products")
    print(f"Production table: {prod_total:,} products")
    print(f"Filtered out: {preview_total - prod_total:,} products ({filter_rate:.1f}%)")

except Exception as e:
    print(f"Error getting row counts: {e}")
    exit(1)

# Step 2: Check table schemas
print("\n2. TABLE SCHEMAS:")
print("-"*40)

def get_table_columns(table_name):
    try:
        response = supabase.table(table_name).select('*').limit(1).execute()
        if response.data:
            return list(response.data[0].keys())
        return []
    except Exception as e:
        print(f"Error getting {table_name} schema: {e}")
        return []

preview_cols = get_table_columns('foods_published_preview')
prod_cols = get_table_columns('foods_published_prod')

print(f"Preview columns ({len(preview_cols)}): {sorted(preview_cols)}")
print(f"Production columns ({len(prod_cols)}): {sorted(prod_cols)}")

# Check for column differences
preview_only = set(preview_cols) - set(prod_cols)
prod_only = set(prod_cols) - set(preview_cols)

if preview_only:
    print(f"Columns only in preview: {preview_only}")
if prod_only:
    print(f"Columns only in production: {prod_only}")

# Step 3: Get all product keys from both tables
print("\n3. COMPARING PRODUCT KEYS:")
print("-"*40)

try:
    # Get all product keys from preview
    preview_keys_response = supabase.table('foods_published_preview').select('product_key').execute()
    preview_keys = set([item['product_key'] for item in preview_keys_response.data])

    # Get all product keys from production
    prod_keys_response = supabase.table('foods_published_prod').select('product_key').execute()
    prod_keys = set([item['product_key'] for item in prod_keys_response.data])

    # Find differences
    filtered_out = preview_keys - prod_keys
    prod_only_keys = prod_keys - preview_keys

    print(f"Products in preview only (filtered out): {len(filtered_out)}")
    print(f"Products in production only: {len(prod_only_keys)}")

    if prod_only_keys:
        print(f"Warning: {len(prod_only_keys)} products exist in production but not preview!")
        print(f"Sample production-only keys: {list(prod_only_keys)[:5]}")

except Exception as e:
    print(f"Error comparing product keys: {e}")
    filtered_out = set()

# Step 4: Analyze sample data from both tables
print("\n4. ANALYZING SAMPLE DATA:")
print("-"*40)

def get_sample_data(table_name, limit=1000):
    try:
        response = supabase.table(table_name).select('*').limit(limit).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        print(f"Error getting sample from {table_name}: {e}")
        return pd.DataFrame()

preview_sample = get_sample_data('foods_published_preview', 2000)
prod_sample = get_sample_data('foods_published_prod', 2000)

if not preview_sample.empty and not prod_sample.empty:
    print(f"Preview sample: {len(preview_sample)} records")
    print(f"Production sample: {len(prod_sample)} records")

    # Compare key fields
    key_fields = ['brand_slug', 'form', 'life_stage', 'kcal_per_100g', 'protein', 'fat', 'carbohydrates', 'fiber']

    for field in key_fields:
        if field in preview_sample.columns and field in prod_sample.columns:
            print(f"\n--- {field.upper()} ANALYSIS ---")

            # Non-null percentages
            preview_notnull = (preview_sample[field].notna().sum() / len(preview_sample)) * 100
            prod_notnull = (prod_sample[field].notna().sum() / len(prod_sample)) * 100

            print(f"Non-null values - Preview: {preview_notnull:.1f}%, Production: {prod_notnull:.1f}%")

            # Value distributions for categorical fields
            if field in ['brand_slug', 'form', 'life_stage']:
                preview_counts = preview_sample[field].value_counts().head(10)
                prod_counts = prod_sample[field].value_counts().head(10)

                print(f"Top values in preview: {dict(preview_counts)}")
                print(f"Top values in production: {dict(prod_counts)}")

                # Check for missing values in production
                preview_values = set(preview_sample[field].dropna().unique())
                prod_values = set(prod_sample[field].dropna().unique())
                missing_in_prod = preview_values - prod_values

                if missing_in_prod:
                    print(f"Values present in preview but missing in production: {missing_in_prod}")

# Step 5: Analyze filtered out products specifically
if filtered_out and len(filtered_out) > 0:
    print(f"\n5. ANALYZING FILTERED OUT PRODUCTS ({len(filtered_out)} products):")
    print("-"*40)

    # Get a sample of filtered out products
    sample_filtered_keys = list(filtered_out)[:500]  # Sample for analysis

    try:
        # Get data for filtered out products from preview table
        keys_str = "','".join(sample_filtered_keys)
        query = f"product_key.in.({keys_str})"

        # Try to get filtered products using IN clause
        try:
            filtered_data_response = supabase.table('foods_published_preview').select('*').filter('product_key', 'in', f'({",".join([f'"{k}"' for k in sample_filtered_keys])})').execute()
        except:
            filtered_data_response = None

        if not filtered_data_response or not filtered_data_response.data:
            # Try a different approach - get data one by one for first few
            print("Trying alternative approach for filtered products...")
            filtered_products = []
            for key in sample_filtered_keys[:50]:  # Just first 50
                try:
                    response = supabase.table('foods_published_preview').select('*').eq('product_key', key).execute()
                    if response.data:
                        filtered_products.extend(response.data)
                except:
                    continue

            if filtered_products:
                filtered_df = pd.DataFrame(filtered_products)
                print(f"Analyzed {len(filtered_products)} filtered products")

                # Analyze patterns in filtered products
                print("\nFiltered products analysis:")

                for field in ['brand_slug', 'form', 'life_stage']:
                    if field in filtered_df.columns:
                        null_pct = (filtered_df[field].isna().sum() / len(filtered_df)) * 100
                        print(f"{field} null percentage: {null_pct:.1f}%")

                        if null_pct < 100:
                            top_values = filtered_df[field].value_counts().head(5)
                            print(f"Top {field} values in filtered: {dict(top_values)}")

                # Check for data quality issues
                print("\nData quality analysis for filtered products:")

                # Check nutrition completeness
                nutrition_fields = ['kcal_per_100g', 'protein', 'fat', 'carbohydrates']
                for field in nutrition_fields:
                    if field in filtered_df.columns:
                        null_pct = (filtered_df[field].isna().sum() / len(filtered_df)) * 100
                        print(f"{field} missing in filtered products: {null_pct:.1f}%")

                # Check ingredients
                if 'ingredients_tokens' in filtered_df.columns:
                    has_ingredients = filtered_df['ingredients_tokens'].apply(
                        lambda x: x is not None and len(x) > 0 if isinstance(x, list) else False
                    ).sum()
                    ingredients_pct = (has_ingredients / len(filtered_df)) * 100
                    print(f"Products with ingredients in filtered: {ingredients_pct:.1f}%")

    except Exception as e:
        print(f"Error analyzing filtered products: {e}")

# Step 6: Look for quality score patterns
print("\n6. QUALITY SCORE ANALYSIS:")
print("-"*40)

# Check if there are any score-related fields
score_fields = [col for col in preview_cols if 'score' in col.lower() or 'quality' in col.lower() or 'rating' in col.lower()]
if score_fields:
    print(f"Found potential quality fields: {score_fields}")

    for field in score_fields:
        if field in preview_sample.columns and field in prod_sample.columns:
            preview_scores = preview_sample[field].dropna()
            prod_scores = prod_sample[field].dropna()

            if len(preview_scores) > 0 and len(prod_scores) > 0:
                print(f"\n{field}:")
                print(f"Preview - min: {preview_scores.min()}, max: {preview_scores.max()}, mean: {preview_scores.mean():.2f}")
                print(f"Production - min: {prod_scores.min()}, max: {prod_scores.max()}, mean: {prod_scores.mean():.2f}")
else:
    print("No obvious quality score fields found")

# Step 7: Check source-based filtering
print("\n7. SOURCE-BASED FILTERING ANALYSIS:")
print("-"*40)

source_fields = [col for col in preview_cols if 'source' in col.lower()]
if source_fields:
    print(f"Found source fields: {source_fields}")

    for field in source_fields:
        if field in preview_sample.columns:
            preview_sources = preview_sample[field].value_counts()
            print(f"\nPreview {field} distribution:")
            print(preview_sources.head(10))

            if field in prod_sample.columns:
                prod_sources = prod_sample[field].value_counts()
                print(f"\nProduction {field} distribution:")
                print(prod_sources.head(10))

                # Compare sources
                preview_source_set = set(preview_sources.index)
                prod_source_set = set(prod_sources.index)
                missing_sources = preview_source_set - prod_source_set

                if missing_sources:
                    print(f"Sources in preview but not production: {missing_sources}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)

print("\nSUMMARY:")
print(f"• {preview_total:,} products in preview → {prod_total:,} in production ({filter_rate:.1f}% filtered)")
print(f"• {len(filtered_out):,} products were filtered out")

if prod_only_keys:
    print(f"• WARNING: {len(prod_only_keys)} products exist in production but not preview")

print("\nNext steps:")
print("1. Examine specific filtered products for patterns")
print("2. Check for brand allowlists or blocklists")
print("3. Look for data completeness thresholds")
print("4. Investigate source-based filtering rules")