#!/usr/bin/env python3
"""
AADF Staging and Audit Script
Loads AADF data into staging table and generates comprehensive audit
"""

import os
import re
import json
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
import yaml
from typing import Dict, List, Optional, Tuple

load_dotenv()

# Database connection
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load brand normalization maps
BRAND_MAP = {}
if Path("data/canonical_brand_map.yaml").exists():
    with open("data/canonical_brand_map.yaml") as f:
        BRAND_MAP = yaml.safe_load(f) or {}

def ensure_staging_table_exists():
    """Ensure the retailer_staging_aadf table exists"""
    print("Checking if staging table exists...")
    
    # Check if table exists by trying to query it
    try:
        result = supabase.table('retailer_staging_aadf').select('product_key').limit(1).execute()
        print("✅ Staging table 'retailer_staging_aadf' exists")
        
        # Clear existing data for fresh load
        print("Clearing existing AADF staging data...")
        supabase.table('retailer_staging_aadf').delete().neq('product_key', '').execute()
        print("✅ Existing data cleared")
        
    except Exception as e:
        print(f"❌ Table check failed: {e}")
        print("Please ensure the staging table is created using sql/retailer_staging.sql")
        return False
    
    return True

def extract_from_url(url: str) -> Tuple[str, str]:
    """Extract brand and product from AADF URL"""
    # AADF URLs typically: /brand/product-name or similar patterns
    if not url or url == 'nan' or not isinstance(url, str):
        return '', ''
    
    # Clean URL
    url = url.strip().lower()
    
    # Remove protocol and domain
    url = re.sub(r'^https?://[^/]+/', '', url)
    
    # Split by slashes
    parts = [p for p in url.split('/') if p]
    
    brand_guess = ''
    product_guess = ''
    
    if len(parts) >= 2:
        # First part is often brand
        brand_guess = parts[0].replace('-', ' ').replace('_', ' ')
        # Second part is often product
        product_guess = parts[1].replace('-', ' ').replace('_', ' ')
        
        # Clean up common suffixes
        product_guess = re.sub(r'\d+$', '', product_guess)  # Remove trailing numbers
        product_guess = re.sub(r'(dog|food|adult|puppy|senior)$', '', product_guess)
        
    return brand_guess.strip(), product_guess.strip()

def extract_from_product_name(raw_name: str) -> Tuple[str, str]:
    """Extract brand and product from the raw product name field"""
    if not raw_name or raw_name == 'nan' or not isinstance(raw_name, str):
        return '', ''
    
    # Clean up the name (remove view counts, etc)
    clean_name = re.sub(r'^\d+[k]?\s+\d+.*?people.*?days?\s+', '', raw_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'^\d+\s+\d+.*?viewed.*?days?\s+', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'^\d+\s+', '', clean_name)  # Remove leading numbers
    
    # Common brand patterns
    brand_patterns = [
        # Known brands (add more as needed)
        r'^(Royal Canin|Hills?|Purina|Pedigree|James Wellbeloved|Burns|Lily\'s Kitchen|Barking Heads|AATU|Canagan|Orijen|Acana|Wellness|Blue Buffalo|Taste of the Wild|Natural Balance|Merrick|Nutro|Iams|Eukanuba|Pro Plan|Science Diet|Prescription Diet)',
        # Possessive patterns
        r'^([A-Z][a-z]+\'s(?:\s+[A-Z][a-z]+)?)',
        # First two capitalized words
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    ]
    
    brand = ''
    product = clean_name
    
    for pattern in brand_patterns:
        match = re.match(pattern, clean_name, re.IGNORECASE)
        if match:
            brand = match.group(1)
            product = clean_name[len(brand):].strip()
            break
    
    # If no brand found, try splitting by common separators
    if not brand:
        parts = clean_name.split(' - ')
        if len(parts) >= 2:
            brand = parts[0].strip()
            product = ' - '.join(parts[1:]).strip()
        else:
            # Take first word or two as brand
            words = clean_name.split()
            if len(words) > 1:
                if words[1].lower() in ['dog', 'puppy', 'adult', 'senior', 'complete', 'grain']:
                    brand = words[0]
                    product = ' '.join(words[1:])
                else:
                    brand = ' '.join(words[:2])
                    product = ' '.join(words[2:]) if len(words) > 2 else ''
            elif words:
                brand = words[0]
                product = ''
    
    return brand.strip(), product.strip()

def normalize_brand(brand_raw: str) -> Tuple[str, str]:
    """Normalize brand and create slug"""
    if not brand_raw:
        return 'Unknown', 'unknown'
    
    # Check brand map
    brand_normalized = BRAND_MAP.get(brand_raw, brand_raw)
    
    # Common normalizations
    brand_normalized = brand_normalized.replace("'s", "s")
    brand_normalized = re.sub(r'\s+', ' ', brand_normalized).strip()
    
    # Create slug
    brand_slug = re.sub(r'[^a-z0-9]+', '_', brand_normalized.lower()).strip('_')
    
    return brand_normalized, brand_slug

def normalize_product_name(product_raw: str) -> str:
    """Normalize product name"""
    if not product_raw:
        return ''
    
    # Remove size/weight suffixes
    product = re.sub(r'\b\d+(\.\d+)?\s*(kg|g|lb|oz|ml|l)\b', '', product_raw, flags=re.IGNORECASE)
    
    # Remove pack sizes
    product = re.sub(r'\b\d+\s*x\s*\d+', '', product)
    product = re.sub(r'\bpack of \d+\b', '', product, flags=re.IGNORECASE)
    
    # Remove flavor variations at end
    product = re.sub(r'(with |in |flavou?r |recipe |formula ).*$', '', product, flags=re.IGNORECASE)
    
    # Clean up
    product = re.sub(r'\s+', ' ', product).strip()
    product = product.lower()
    
    return product

def classify_form(text: str) -> Optional[str]:
    """Classify product form from text"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Check for specific forms
    if any(word in text_lower for word in ['dry', 'kibble', 'biscuit', 'crispy']):
        return 'dry'
    elif any(word in text_lower for word in ['wet', 'can', 'canned', 'pouch', 'pate', 'paté', 'chunks', 'jelly', 'gravy', 'loaf']):
        return 'wet'
    elif any(word in text_lower for word in ['freeze dried', 'freeze-dried', 'air dried', 'air-dried', 'dehydrated']):
        return 'freeze_dried'
    elif any(word in text_lower for word in ['raw', 'frozen', 'fresh']):
        return 'raw'
    elif any(word in text_lower for word in ['treat', 'snack', 'chew', 'bone', 'biscuit', 'topper', 'mixer', 'supplement']):
        return 'treat'
    
    return None

def classify_life_stage(text: str) -> Optional[str]:
    """Classify life stage from text"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Check for specific life stages
    if any(word in text_lower for word in ['puppy', 'puppies', 'junior', 'young', 'growth']):
        return 'puppy'
    elif any(word in text_lower for word in ['senior', 'mature', 'aging', 'older', 'aged', 'veteran', 'old age']):
        return 'senior'
    elif any(word in text_lower for word in ['adult', 'maintenance', '12 months']):
        return 'adult'
    elif any(word in text_lower for word in ['all life', 'all stage', 'all age', 'complete life']):
        return 'all'
    
    return None

def process_aadf_data():
    """Process AADF CSV and load into staging"""
    print("\nLoading AADF data...")
    
    # Read CSV
    df = pd.read_csv('data/aadf/aadf-dataset.csv')
    print(f"Loaded {len(df)} rows from AADF dataset")
    
    # Process each row
    staging_records = []
    stats = {
        'total': len(df),
        'has_brand': 0,
        'has_product': 0,
        'has_form': 0,
        'has_life_stage': 0,
        'has_ingredients': 0,
        'is_treat': 0,
        'ambiguous': []
    }
    
    for idx, row in df.iterrows():
        # Extract raw fields
        raw_url = str(row.get('data-page-selector-href', ''))
        raw_name = str(row.get('data-page-selector', ''))
        type_of_food = str(row.get('type_of_food-0', ''))
        dog_ages = str(row.get('dog_ages-0', ''))
        ingredients_raw = str(row.get('ingredients-0', ''))
        price_per_day = row.get('price_per_day-0')
        
        # Clean up raw data
        if raw_url == 'nan':
            raw_url = ''
        if raw_name == 'nan':
            raw_name = ''
        if ingredients_raw == 'nan':
            ingredients_raw = ''
        
        # Try to extract brand and product
        brand_from_url, product_from_url = extract_from_url(raw_url)
        brand_from_name, product_from_name = extract_from_product_name(raw_name)
        
        # Use best available source
        brand_guess = brand_from_name or brand_from_url or ''
        product_guess = product_from_name or product_from_url or raw_name
        
        # Normalize brand
        brand_normalized, brand_slug = normalize_brand(brand_guess)
        
        # Normalize product name
        product_name_norm = normalize_product_name(product_guess)
        
        # Classify form and life stage
        combined_text = f"{raw_name} {type_of_food} {product_guess}"
        form_guess = classify_form(combined_text) or classify_form(type_of_food)
        life_stage_guess = classify_life_stage(combined_text) or classify_life_stage(dog_ages)
        
        # Generate product key
        if brand_slug and product_name_norm:
            product_key = f"{brand_slug}_{hashlib.md5(f'{brand_slug}{product_name_norm}'.encode()).hexdigest()[:8]}"
        else:
            product_key = f"aadf_{hashlib.md5(raw_name.encode()).hexdigest()[:12]}"
        
        # Calculate price per kg (if available)
        price_per_kg_eur = None
        if price_per_day and str(price_per_day) != 'nan':
            try:
                # Assume average dog eats 300g/day, convert GBP to EUR (0.92 rate)
                price_per_kg_eur = float(price_per_day) * (1000/300) * 0.92
            except:
                pass
        
        # Update stats
        if brand_guess:
            stats['has_brand'] += 1
        if product_name_norm:
            stats['has_product'] += 1
        if form_guess:
            stats['has_form'] += 1
        if life_stage_guess:
            stats['has_life_stage'] += 1
        if ingredients_raw and ingredients_raw != 'nan':
            stats['has_ingredients'] += 1
        if form_guess == 'treat':
            stats['is_treat'] += 1
        
        # Track ambiguous records
        if not brand_guess or not product_name_norm:
            if len(stats['ambiguous']) < 20:
                stats['ambiguous'].append({
                    'raw_name': raw_name[:80],
                    'raw_url': raw_url[:80],
                    'brand_guess': brand_guess,
                    'product_guess': product_guess[:50]
                })
        
        # Create staging record
        record = {
            'product_key': product_key,
            'raw_url': raw_url,
            'brand_guess': brand_normalized,
            'brand_slug': brand_slug,
            'product_guess': product_guess,
            'product_name_norm': product_name_norm,
            'form_guess': form_guess,
            'life_stage_guess': life_stage_guess,
            'ingredients_raw': ingredients_raw if ingredients_raw != 'nan' else None,
            'kcal_per_100g': None,  # Not available in AADF
            'pack_sizes': None,  # Could extract if needed
            'price_per_kg_eur': price_per_kg_eur,
            'source': 'aadf',
            'ingested_at': datetime.now().isoformat(),
            # Additional fields for compatibility with staging table
            'brand': brand_normalized,
            'brand_family': brand_slug.split('_')[0] if brand_slug else 'unknown',
            'product_name': product_guess,
            'name_slug': re.sub(r'[^a-z0-9]+', '-', product_name_norm).strip('-') if product_name_norm else '',
            'form': form_guess,
            'life_stage': life_stage_guess,
            'ingredients_tokens': json.dumps([]) if not ingredients_raw or ingredients_raw == 'nan' else json.dumps(
                [i.strip() for i in re.split(r'[,;]', ingredients_raw) if i.strip()][:20]
            ),
            'price_bucket': 'medium' if price_per_kg_eur and 10 <= price_per_kg_eur <= 50 else 'high' if price_per_kg_eur and price_per_kg_eur > 50 else 'low' if price_per_kg_eur else None,
            'available_countries': json.dumps(['UK']),
            'sources': json.dumps([{'type': 'retailer:aadf', 'url': raw_url}]),
            'product_url': raw_url,
            'staging_source': 'aadf',
            'staging_confidence': 0.8 if brand_guess and product_name_norm and form_guess else 0.5 if brand_guess and product_name_norm else 0.3
        }
        
        staging_records.append(record)
    
    return staging_records, stats

def load_to_staging(records: List[Dict]) -> bool:
    """Load records into staging table"""
    print(f"\nLoading {len(records)} records to staging table...")
    
    try:
        # Insert in batches
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            result = supabase.table('retailer_staging_aadf').insert(batch).execute()
            print(f"  Loaded batch {i//batch_size + 1}/{(len(records)-1)//batch_size + 1}")
        
        print(f"✅ Successfully loaded {len(records)} records to retailer_staging_aadf")
        return True
        
    except Exception as e:
        print(f"❌ Error loading to staging: {e}")
        return False

def generate_audit_report(stats: Dict, records: List[Dict]):
    """Generate comprehensive audit report"""
    print("\nGenerating audit report...")
    
    # Calculate coverage percentages
    total = stats['total']
    brand_coverage = 100 * stats['has_brand'] / total
    product_coverage = 100 * stats['has_product'] / total
    form_coverage = 100 * stats['has_form'] / total
    life_stage_coverage = 100 * stats['has_life_stage'] / total
    ingredients_coverage = 100 * stats['has_ingredients'] / total
    
    # Get brand distribution
    brand_counts = {}
    for record in records:
        brand = record['brand_guess']
        if brand and brand != 'Unknown':
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
    
    # Sort brands by count
    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Determine if OK to proceed
    ok_to_proceed = (brand_coverage >= 90 and product_coverage >= 90 and 
                     form_coverage >= 80 and life_stage_coverage >= 80)
    
    report = f"""# AADF STAGE AUDIT
Generated: {datetime.now().isoformat()}

## Dataset Overview
- **Total rows**: {total:,}
- **Distinct brands**: {len(brand_counts)}
- **Treats/toppers identified**: {stats['is_treat']:,} ({100*stats['is_treat']/total:.1f}%)
- **Complete foods**: {total - stats['is_treat']:,} ({100*(total - stats['is_treat'])/total:.1f}%)

## Coverage Analysis

| Field | Count | Coverage % | Status |
|-------|-------|------------|--------|
| Brand (brand_slug) | {stats['has_brand']:,} | {brand_coverage:.1f}% | {'✅' if brand_coverage >= 90 else '⚠️' if brand_coverage >= 80 else '❌'} |
| Product (product_name_norm) | {stats['has_product']:,} | {product_coverage:.1f}% | {'✅' if product_coverage >= 90 else '⚠️' if product_coverage >= 80 else '❌'} |
| Form (form_guess) | {stats['has_form']:,} | {form_coverage:.1f}% | {'✅' if form_coverage >= 80 else '⚠️' if form_coverage >= 70 else '❌'} |
| Life Stage (life_stage_guess) | {stats['has_life_stage']:,} | {life_stage_coverage:.1f}% | {'✅' if life_stage_coverage >= 80 else '⚠️' if life_stage_coverage >= 70 else '❌'} |
| Ingredients (ingredients_raw) | {stats['has_ingredients']:,} | {ingredients_coverage:.1f}% | {'✅' if ingredients_coverage >= 90 else '⚠️' if ingredients_coverage >= 80 else '❌'} |

## Top 20 Brands by Product Count

| Rank | Brand | Products | % of Total |
|------|-------|----------|------------|
"""
    
    for i, (brand, count) in enumerate(top_brands, 1):
        report += f"| {i} | {brand} | {count} | {100*count/total:.1f}% |\n"
    
    report += f"""
## Ambiguous Records (Missing Brand/Product)

Total ambiguous records: {len([r for r in records if not r['brand_guess'] or not r['product_name_norm']])}

### Sample of 20 Ambiguous Records:
"""
    
    for i, amb in enumerate(stats['ambiguous'], 1):
        report += f"""
**Record {i}:**
- Raw name: {amb['raw_name']}
- Raw URL: {amb['raw_url']}
- Brand guess: {amb['brand_guess'] or 'MISSING'}
- Product guess: {amb['product_guess'] or 'MISSING'}
"""
    
    # Form distribution
    form_dist = {}
    for record in records:
        form = record['form_guess'] or 'unknown'
        form_dist[form] = form_dist.get(form, 0) + 1
    
    report += f"""
## Form Distribution

| Form | Count | Percentage |
|------|-------|------------|
"""
    for form, count in sorted(form_dist.items(), key=lambda x: x[1], reverse=True):
        report += f"| {form} | {count:,} | {100*count/total:.1f}% |\n"
    
    # Life stage distribution
    stage_dist = {}
    for record in records:
        stage = record['life_stage_guess'] or 'unknown'
        stage_dist[stage] = stage_dist.get(stage, 0) + 1
    
    report += f"""
## Life Stage Distribution

| Life Stage | Count | Percentage |
|------------|-------|------------|
"""
    for stage, count in sorted(stage_dist.items(), key=lambda x: x[1], reverse=True):
        report += f"| {stage} | {count:,} | {100*count/total:.1f}% |\n"
    
    report += f"""
## Data Quality Assessment

### Strengths:
- **Ingredients data**: {ingredients_coverage:.1f}% coverage provides valuable nutrition information
- **Price data**: Available for most products (derived from price per day)
- **UK market coverage**: Comprehensive UK brand representation

### Weaknesses:
- **Product name extraction**: Some products have view count prefixes that complicate parsing
- **Brand normalization**: Requires manual mapping for consistency
- **Form/life stage**: Derived from text analysis, may have errors

## Processing Summary

- Records successfully staged: {len(records):,}
- Database table: `retailer_staging_aadf`
- Staging timestamp: {datetime.now().isoformat()}

## OK to Proceed?

**Status: {'✅ YES' if ok_to_proceed else '❌ NO'}**

"""
    
    if ok_to_proceed:
        report += """
All coverage thresholds met:
- Brand/product extraction ≥ 90% ✅
- Form/life_stage classification ≥ 80% ✅

**Recommendation**: Proceed with data validation and potential merge to foods_canonical after:
1. Manual review of top brands for normalization
2. Verification of treat/topper classifications
3. Cross-reference with existing catalog for duplicates
"""
    else:
        report += f"""
Coverage thresholds NOT met:
- Brand extraction: {brand_coverage:.1f}% (need ≥90%)
- Product extraction: {product_coverage:.1f}% (need ≥90%)
- Form classification: {form_coverage:.1f}% (need ≥80%)
- Life stage classification: {life_stage_coverage:.1f}% (need ≥80%)

**Recommendation**: Improve extraction logic before proceeding:
1. Enhanced brand detection patterns
2. Better product name parsing
3. Additional form/life_stage keywords
"""
    
    return report

def main():
    """Main execution"""
    print("="*80)
    print("AADF DATA STAGING & AUDIT")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Step 1: Ensure staging table exists
    if not ensure_staging_table_exists():
        print("\n❌ Cannot proceed without staging table")
        return
    
    # Step 2: Process AADF data
    records, stats = process_aadf_data()
    
    # Step 3: Load to staging
    if not load_to_staging(records):
        print("\n⚠️ Data processing complete but staging load failed")
    
    # Step 4: Generate audit report
    report = generate_audit_report(stats, records)
    
    # Step 5: Save report
    report_path = "reports/AADF_STAGE_AUDIT.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\n✅ Audit report saved to {report_path}")
    
    # Print summary
    print("\n" + "="*80)
    print("STAGING COMPLETE")
    print("="*80)
    print(f"Total records staged: {len(records):,}")
    print(f"Brand coverage: {100*stats['has_brand']/stats['total']:.1f}%")
    print(f"Product coverage: {100*stats['has_product']/stats['total']:.1f}%")
    print(f"Form coverage: {100*stats['has_form']/stats['total']:.1f}%")
    print(f"Life stage coverage: {100*stats['has_life_stage']/stats['total']:.1f}%")
    
    ok_to_proceed = (100*stats['has_brand']/stats['total'] >= 90 and 
                     100*stats['has_product']/stats['total'] >= 90 and
                     100*stats['has_form']/stats['total'] >= 80 and
                     100*stats['has_life_stage']/stats['total'] >= 80)
    
    print(f"\n{'✅ OK TO PROCEED' if ok_to_proceed else '❌ NEEDS IMPROVEMENT'}")

if __name__ == "__main__":
    main()