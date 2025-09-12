#!/usr/bin/env python3
"""
AADF Data Staging V2 - Fixed columns and dry-run matching
"""

import os
import re
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from pathlib import Path
from supabase import create_client, Client
import yaml
from difflib import SequenceMatcher
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_brand_maps() -> Tuple[Dict, Dict]:
    """Load brand normalization maps"""
    brand_map = {}
    brand_phrase_map = {}
    
    # Load canonical brand map
    if Path('data/canonical_brand_map.yaml').exists():
        with open('data/canonical_brand_map.yaml', 'r') as f:
            canonical_map = yaml.safe_load(f) or {}
            for canonical, variations in canonical_map.items():
                if isinstance(variations, list):
                    for variation in variations:
                        brand_map[variation.lower()] = canonical
                elif variations:  # Single value
                    brand_map[str(variations).lower()] = canonical
    
    # Load brand phrase map
    if Path('data/brand_phrase_map.csv').exists():
        df = pd.read_csv('data/brand_phrase_map.csv')
        for _, row in df.iterrows():
            if pd.notna(row.get('phrase')) and pd.notna(row.get('brand')):
                brand_phrase_map[row['phrase'].lower()] = row['brand']
    
    return brand_map, brand_phrase_map

def extract_brand_product(url: str, description: str) -> Tuple[str, str]:
    """Extract brand and product from AADF URL with improved logic"""
    brand = ""
    product = ""
    
    if pd.notna(url) and 'allaboutdogfood.co.uk' in url and '/dog-food-reviews/' in url:
        # Extract the product slug from URL
        parts = url.split('/')
        if len(parts) >= 6:
            product_slug = parts[-1]  # e.g., "forthglade-complete-meal-with-brown-rice-adult"
            
            # Known multi-word brands
            multi_word_brands = {
                'royal-canin': 'Royal Canin',
                'barking-heads': 'Barking Heads',
                'lily-s-kitchen': "Lily's Kitchen",
                'lilys-kitchen': "Lily's Kitchen",
                'natures-menu': "Nature's Menu",
                'natures-deli': "Nature's Deli",
                'james-wellbeloved': 'James Wellbeloved',
                'country-pursuit': 'Country Pursuit',
                'alpha-spirit': 'Alpha Spirit',
                'millies-wolfheart': "Millies Wolfheart",
                'wolf-of-wilderness': 'Wolf of Wilderness',
                'farmina-natural': 'Farmina Natural',
                'arden-grange': 'Arden Grange',
                'pro-plan': 'Pro Plan',
                'concept-for': 'Concept For',
                'pooch-mutt': 'Pooch & Mutt',
                'country-dog': 'Country Dog',
                'hills-science': "Hill's Science",
                'wainwrights-dry': 'Wainwrights',
                'wainwrights-trays': 'Wainwrights',
                'wainwrights-sensitive': 'Wainwrights',
                'southend-dog': 'Southend Dog',
                'noochy-poochy': 'Noochy Poochy',
                'calibra-expert': 'Calibra Expert',
                'pets-at-home': 'Pets at Home',
                'bob-and-lush': 'Bob and Lush',
                'dr-veneta': 'Dr Veneta'
            }
            
            # Check for multi-word brands first
            brand_found = False
            for pattern, brand_name in multi_word_brands.items():
                if product_slug.startswith(pattern):
                    brand = brand_name
                    # Remove brand part from product
                    product = product_slug[len(pattern):].strip('-')
                    product = product.replace('-', ' ')
                    brand_found = True
                    break
            
            # If no multi-word brand found, try single word
            if not brand_found:
                words = product_slug.split('-')
                if words:
                    # Special cases and common brands
                    first_word = words[0].lower()
                    if first_word == 'csj':
                        brand = 'CSJ'
                        product = ' '.join(words[1:])
                    elif first_word in ['fish4dogs', 'scrumbles', 'forthglade', 'ava', 'eukanuba', 
                                        'nutribalance', 'nutro', 'icepaw', 'essential', 'feelwells',
                                        'salters', 'husse', 'calibra', 'paleo', 'burns', 'purina',
                                        'acana', 'orijen', 'wellness', 'canagan', 'harringtons',
                                        'rocco', 'cooper', 'beta', 'wildways', 'gentle', 'omni',
                                        'primal', 'webbox', 'lifestage', 'gelert', 'natural',
                                        'skinners', 'butchers', 'natures', 'pooch', 'josera',
                                        'europa', 'leader', 'wainwrights']:
                        brand = words[0].title()
                        # Special capitalization
                        if first_word == 'csj':
                            brand = 'CSJ'
                        elif first_word == 'fish4dogs':
                            brand = 'Fish4Dogs'
                        product = ' '.join(words[1:])
                    else:
                        # Default: first word is brand
                        brand = words[0].title()
                        product = ' '.join(words[1:])
    
    # Fallback to description if no brand from URL
    if not brand and pd.notna(description):
        # Clean description
        desc_clean = re.sub(r'^\d+[k]?\s+\d+.*?days?\s+', '', str(description), flags=re.IGNORECASE)
        desc_clean = desc_clean.strip(' "')
        
        # Try to extract from description
        words = desc_clean.split()
        if words and words[0].lower() not in ['made', 'here', 'at', 'our']:
            brand = words[0].title()
            product = ' '.join(words[1:5]) if len(words) > 1 else ""
    
    return brand.strip(), product.strip()

def normalize_brand(brand: str, brand_map: Dict, phrase_map: Dict) -> str:
    """Normalize brand using mapping"""
    if not brand:
        return ""
    
    brand_lower = brand.lower().strip()
    
    # Direct map lookup
    if brand_lower in brand_map:
        return brand_map[brand_lower]
    
    # Check phrase map
    for phrase, canonical in phrase_map.items():
        if phrase in brand_lower:
            return canonical
    
    # Clean up common patterns
    brand_clean = re.sub(r'\s+', ' ', brand)
    brand_clean = re.sub(r'[^\w\s&-]', '', brand_clean)
    
    return brand_clean.strip()

def normalize_product_name(product: str) -> str:
    """Normalize product name - remove size/weight/flavor suffixes"""
    if not product:
        return ""
    
    # Remove common suffixes
    product = re.sub(r'\b\d+\.?\d*\s*(kg|g|lb|oz)\b', '', product, flags=re.IGNORECASE)
    product = re.sub(r'\b(chicken|beef|lamb|salmon|turkey|duck|fish)\s*(flavor|recipe|formula)?\b', '', product, flags=re.IGNORECASE)
    product = re.sub(r'\b(puppy|adult|senior|junior)\b', '', product, flags=re.IGNORECASE)
    product = re.sub(r'\b(small|medium|large|giant)\s*(breed)?\b', '', product, flags=re.IGNORECASE)
    product = re.sub(r'\b(dry|wet|raw|freeze[\s-]?dried)\s*(food|dog food)?\b', '', product, flags=re.IGNORECASE)
    
    # Clean up
    product = re.sub(r'\s+', ' ', product)
    product = re.sub(r'[^\w\s]', '', product)
    
    return product.lower().strip()

def detect_form(text: str) -> str:
    """Detect food form from text"""
    text_lower = str(text).lower()
    
    if 'freeze' in text_lower and 'dried' in text_lower:
        return 'freeze_dried'
    elif 'raw' in text_lower and ('frozen' in text_lower or 'fresh' in text_lower):
        return 'raw'
    elif any(w in text_lower for w in ['can', 'tin', 'pouch', 'tray', 'wet']):
        return 'wet'
    elif any(w in text_lower for w in ['kibble', 'dry', 'biscuit', 'pellet']):
        return 'dry'
    
    return 'unknown'

def detect_life_stage(text: str) -> str:
    """Detect life stage from text"""
    text_lower = str(text).lower()
    
    if any(w in text_lower for w in ['puppy', 'junior', 'growth']):
        return 'puppy'
    elif any(w in text_lower for w in ['senior', 'mature', 'aged', '7+']):
        return 'senior'
    elif any(w in text_lower for w in ['adult', 'maintenance']):
        return 'adult'
    
    return 'unknown'

def detect_language(ingredients: str) -> str:
    """Detect language of ingredients"""
    if not ingredients or pd.isna(ingredients):
        return 'unknown'
    
    ingredients_lower = str(ingredients).lower()
    
    # English indicators
    if any(w in ingredients_lower for w in ['chicken', 'beef', 'rice', 'protein', 'vitamins']):
        return 'en'
    
    # German indicators
    if any(w in ingredients_lower for w in ['huhn', 'rind', 'reis', 'eiweiß', 'vitamine']):
        return 'de'
    
    # French indicators
    if any(w in ingredients_lower for w in ['poulet', 'boeuf', 'riz', 'protéine', 'vitamines']):
        return 'fr'
    
    return 'en'  # Default to English

def extract_nutrition(row: pd.Series) -> Dict:
    """Extract nutrition values from row"""
    nutrition = {}
    
    # Extract kcal from price_per_day if it contains kcal info
    if pd.notna(row.get('price_per_day-0')):
        price_text = str(row['price_per_day-0'])
        kcal_match = re.search(r'(\d+\.?\d*)\s*kcal', price_text, re.IGNORECASE)
        if kcal_match:
            nutrition['kcal_per_100g'] = float(kcal_match.group(1))
    
    # Extract analytical constituents from ingredients or description
    for field in ['ingredients-0', 'manufacturer_description-0']:
        if pd.notna(row.get(field)):
            text = str(row[field])
            
            # Protein
            protein_match = re.search(r'protein[:\s]+(\d+\.?\d*)%', text, re.IGNORECASE)
            if protein_match:
                nutrition['protein_percent'] = float(protein_match.group(1))
            
            # Fat
            fat_match = re.search(r'fat[:\s]+(\d+\.?\d*)%', text, re.IGNORECASE)
            if fat_match:
                nutrition['fat_percent'] = float(fat_match.group(1))
            
            # Fiber
            fiber_match = re.search(r'fib(?:re|er)[:\s]+(\d+\.?\d*)%', text, re.IGNORECASE)
            if fiber_match:
                nutrition['fiber_percent'] = float(fiber_match.group(1))
            
            # Ash
            ash_match = re.search(r'ash[:\s]+(\d+\.?\d*)%', text, re.IGNORECASE)
            if ash_match:
                nutrition['ash_percent'] = float(ash_match.group(1))
            
            # Moisture
            moisture_match = re.search(r'moisture[:\s]+(\d+\.?\d*)%', text, re.IGNORECASE)
            if moisture_match:
                nutrition['moisture_percent'] = float(moisture_match.group(1))
    
    return nutrition

def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate string similarity score"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def generate_product_key(brand: str, product: str, form: str = None) -> str:
    """Generate unique product key"""
    components = [brand.lower(), product.lower()]
    if form:
        components.append(form)
    
    key_string = '|'.join(filter(None, components))
    return hashlib.md5(key_string.encode()).hexdigest()[:16]

def main():
    print("=== AADF Data Staging V2 ===")
    print(f"Started: {datetime.now()}")
    
    # Load brand maps
    print("\n1. Loading brand normalization maps...")
    brand_map, phrase_map = load_brand_maps()
    print(f"   Loaded {len(brand_map)} brand mappings")
    
    # Load CSV
    print("\n2. Loading AADF dataset...")
    df = pd.read_csv('data/aadf/aadf-dataset.csv')
    print(f"   Loaded {len(df)} rows")
    
    # Process each row
    print("\n3. Processing rows...")
    processed_data = []
    
    for idx, row in df.iterrows():
        # Extract brand and product
        url = row.get('data-page-selector-href', '')
        description = row.get('manufacturer_description-0', '')
        brand_raw, product_raw = extract_brand_product(url, description)
        
        # Normalize
        brand_slug = normalize_brand(brand_raw, brand_map, phrase_map)
        product_norm = normalize_product_name(product_raw)
        
        # Detect attributes
        combined_text = f"{description} {row.get('type_of_food-0', '')} {product_raw}"
        form = detect_form(combined_text)
        life_stage = detect_life_stage(f"{combined_text} {row.get('dog_ages-0', '')}")
        
        # Extract nutrition
        nutrition = extract_nutrition(row)
        
        # Detect ingredient language
        ingredients = row.get('ingredients-0', '')
        lang = detect_language(ingredients)
        
        # Generate keys
        row_content = f"{brand_raw}|{product_raw}|{ingredients}"
        row_hash = hashlib.md5(row_content.encode()).hexdigest()
        product_key = generate_product_key(brand_slug or brand_raw, product_norm or product_raw, form)
        
        processed_data.append({
            'brand_raw': brand_raw,
            'brand_slug': brand_slug,
            'product_name_raw': product_raw,
            'product_name_norm': product_norm,
            'url': url,
            'image_url': None,  # Not in AADF data
            'form_guess': form,
            'life_stage_guess': life_stage,
            'ingredients_raw': ingredients,
            'ingredients_language': lang,
            'kcal_per_100g': nutrition.get('kcal_per_100g'),
            'protein_percent': nutrition.get('protein_percent'),
            'fat_percent': nutrition.get('fat_percent'),
            'fiber_percent': nutrition.get('fiber_percent'),
            'ash_percent': nutrition.get('ash_percent'),
            'moisture_percent': nutrition.get('moisture_percent'),
            'pack_sizes': None,  # Not extracted yet
            'gtin': None,  # Not in AADF data
            'source': 'aadf',
            'ingested_at': datetime.now().isoformat(),
            'row_hash': row_hash,
            'product_key_candidate': product_key
        })
    
    # Create DataFrame
    staging_df = pd.DataFrame(processed_data)
    
    # Save to CSV for inspection
    staging_df.to_csv('data/staging/aadf_staging_v2.csv', index=False)
    print(f"\n4. Saved {len(staging_df)} processed rows to data/staging/aadf_staging_v2.csv")
    
    # Create SQL for table
    sql_create = """
-- Drop and recreate staging table v2
DROP TABLE IF EXISTS retailer_staging_aadf_v2 CASCADE;

CREATE TABLE retailer_staging_aadf_v2 (
    brand_raw TEXT,
    brand_slug VARCHAR(255),
    product_name_raw TEXT,
    product_name_norm VARCHAR(255),
    url TEXT,
    image_url TEXT,
    form_guess VARCHAR(50),
    life_stage_guess VARCHAR(50),
    ingredients_raw TEXT,
    ingredients_language VARCHAR(10),
    kcal_per_100g DECIMAL(6,2),
    protein_percent DECIMAL(5,2),
    fat_percent DECIMAL(5,2),
    fiber_percent DECIMAL(5,2),
    ash_percent DECIMAL(5,2),
    moisture_percent DECIMAL(5,2),
    pack_sizes TEXT,
    gtin VARCHAR(20),
    source VARCHAR(20) DEFAULT 'aadf',
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    row_hash VARCHAR(64),
    product_key_candidate VARCHAR(32) PRIMARY KEY
);

-- Create indexes
CREATE INDEX idx_aadf_v2_brand_slug ON retailer_staging_aadf_v2(brand_slug);
CREATE INDEX idx_aadf_v2_form ON retailer_staging_aadf_v2(form_guess);
CREATE INDEX idx_aadf_v2_life_stage ON retailer_staging_aadf_v2(life_stage_guess);
CREATE INDEX idx_aadf_v2_row_hash ON retailer_staging_aadf_v2(row_hash);
"""
    
    with open('sql/create_aadf_staging_v2.sql', 'w') as f:
        f.write(sql_create)
    print("\n5. Created SQL DDL: sql/create_aadf_staging_v2.sql")
    
    # Dry-run matching against foods_canonical
    print("\n6. Performing dry-run matching against foods_canonical...")
    
    # Fetch canonical products
    response = supabase.table('foods_canonical').select('brand, product_name, name_slug').execute()
    canonical_products = pd.DataFrame(response.data)
    
    matches = []
    for _, staged in staging_df.iterrows():
        if not staged['brand_slug'] or not staged['product_name_norm']:
            matches.append({'score': 0, 'category': 'no-match'})
            continue
        
        best_score = 0
        best_match = None
        
        # Find products with same brand
        brand_matches = canonical_products[
            canonical_products['brand'].str.lower() == staged['brand_slug'].lower()
        ]
        
        for _, canonical in brand_matches.iterrows():
            # Calculate similarity
            score = calculate_similarity(
                staged['product_name_norm'],
                canonical.get('name_slug', '') or canonical.get('product_name', '')
            )
            
            if score > best_score:
                best_score = score
                best_match = canonical
        
        # Categorize
        if best_score >= 0.80:
            category = 'high'
        elif best_score >= 0.65:
            category = 'review'
        else:
            category = 'no-match'
        
        matches.append({
            'score': best_score,
            'category': category,
            'canonical_match': best_match.to_dict() if best_match is not None else None
        })
    
    staging_df['match_score'] = [m['score'] for m in matches]
    staging_df['match_category'] = [m['category'] for m in matches]
    
    # Generate coverage stats
    coverage_stats = {
        'total_rows': len(staging_df),
        'brand_coverage': (staging_df['brand_slug'].notna().sum() / len(staging_df)) * 100,
        'product_coverage': (staging_df['product_name_norm'].notna().sum() / len(staging_df)) * 100,
        'form_coverage': ((staging_df['form_guess'] != 'unknown').sum() / len(staging_df)) * 100,
        'life_stage_coverage': ((staging_df['life_stage_guess'] != 'unknown').sum() / len(staging_df)) * 100,
        'ingredients_coverage': (staging_df['ingredients_raw'].notna().sum() / len(staging_df)) * 100,
        'nutrition_coverage': (staging_df['kcal_per_100g'].notna().sum() / len(staging_df)) * 100
    }
    
    # Match statistics
    match_stats = staging_df['match_category'].value_counts().to_dict()
    
    # Generate reports
    print("\n7. Generating reports...")
    
    # Updated STAGE AUDIT report
    audit_report = f"""# AADF STAGE AUDIT V2
Generated: {datetime.now().isoformat()}

## Dataset Overview
- **Total rows**: {coverage_stats['total_rows']}
- **CSV file**: data/aadf/aadf-dataset.csv
- **Staging table**: retailer_staging_aadf_v2
- **Processing complete**: ✅

## Coverage Analysis

| Field | Count | Coverage % | Status |
|-------|-------|------------|--------|
| Brand (brand_slug) | {staging_df['brand_slug'].notna().sum()} | {coverage_stats['brand_coverage']:.1f}% | {'✅' if coverage_stats['brand_coverage'] >= 90 else '⚠️'} |
| Product (product_name_norm) | {staging_df['product_name_norm'].notna().sum()} | {coverage_stats['product_coverage']:.1f}% | {'✅' if coverage_stats['product_coverage'] >= 90 else '⚠️'} |
| Form (form_guess) | {(staging_df['form_guess'] != 'unknown').sum()} | {coverage_stats['form_coverage']:.1f}% | {'✅' if coverage_stats['form_coverage'] >= 80 else '⚠️'} |
| Life Stage (life_stage_guess) | {(staging_df['life_stage_guess'] != 'unknown').sum()} | {coverage_stats['life_stage_coverage']:.1f}% | {'✅' if coverage_stats['life_stage_coverage'] >= 80 else '⚠️'} |
| Ingredients (ingredients_raw) | {staging_df['ingredients_raw'].notna().sum()} | {coverage_stats['ingredients_coverage']:.1f}% | ✅ |
| Nutrition (kcal_per_100g) | {staging_df['kcal_per_100g'].notna().sum()} | {coverage_stats['nutrition_coverage']:.1f}% | {'✅' if coverage_stats['nutrition_coverage'] >= 50 else '⚠️'} |

## Top Brands by Product Count

| Rank | Brand | Products | % of Total |
|------|-------|----------|------------|
"""
    
    brand_counts = staging_df.groupby('brand_slug').size().sort_values(ascending=False).head(20)
    for i, (brand, count) in enumerate(brand_counts.items(), 1):
        audit_report += f"| {i} | {brand} | {count} | {(count/len(staging_df)*100):.1f}% |\n"
    
    audit_report += f"""
## Form Distribution

| Form | Count | Percentage |
|------|-------|------------|
"""
    form_dist = staging_df['form_guess'].value_counts()
    for form, count in form_dist.items():
        audit_report += f"| {form} | {count} | {(count/len(staging_df)*100):.1f}% |\n"
    
    audit_report += f"""
## Life Stage Distribution

| Life Stage | Count | Percentage |
|------------|-------|------------|
"""
    life_dist = staging_df['life_stage_guess'].value_counts()
    for stage, count in life_dist.items():
        audit_report += f"| {stage} | {count} | {(count/len(staging_df)*100):.1f}% |\n"
    
    audit_report += f"""
## Processing Summary

- Records successfully processed: {len(staging_df)}
- Unique row hashes: {staging_df['row_hash'].nunique()}
- Product keys generated: {staging_df['product_key_candidate'].nunique()}
- Staging CSV: data/staging/aadf_staging_v2.csv
- SQL DDL: sql/create_aadf_staging_v2.sql

## Data Quality Gates

**All Required Gates**: {'✅ PASSED' if all([
    coverage_stats['brand_coverage'] >= 90,
    coverage_stats['product_coverage'] >= 90,
    coverage_stats['form_coverage'] >= 80,
    coverage_stats['life_stage_coverage'] >= 80
]) else '⚠️ REVIEW NEEDED'}

- Brand/product extraction ≥ 90%: {'✅' if coverage_stats['brand_coverage'] >= 90 and coverage_stats['product_coverage'] >= 90 else '❌'}
- Form/life_stage classification ≥ 80%: {'✅' if coverage_stats['form_coverage'] >= 80 and coverage_stats['life_stage_coverage'] >= 80 else '❌'}
- Ingredients coverage (100% expected): {'✅' if coverage_stats['ingredients_coverage'] == 100 else '⚠️'}
"""
    
    with open('reports/AADF_STAGE_AUDIT_V2.md', 'w') as f:
        f.write(audit_report)
    print("   Created: reports/AADF_STAGE_AUDIT_V2.md")
    
    # MATCH FEASIBILITY report
    feasibility_report = f"""# AADF MATCH FEASIBILITY REPORT
Generated: {datetime.now().isoformat()}

## Executive Summary

Dry-run matching of {len(staging_df)} AADF products against foods_canonical catalog.

## Match Distribution

| Category | Count | Percentage | Action |
|----------|-------|------------|--------|
| High (≥0.80) | {match_stats.get('high', 0)} | {(match_stats.get('high', 0)/len(staging_df)*100):.1f}% | Auto-merge candidate |
| Review (0.65-0.79) | {match_stats.get('review', 0)} | {(match_stats.get('review', 0)/len(staging_df)*100):.1f}% | Manual review needed |
| No Match (<0.65) | {match_stats.get('no-match', 0)} | {(match_stats.get('no-match', 0)/len(staging_df)*100):.1f}% | New products |
| **Total** | {len(staging_df)} | 100.0% | - |

## Brand-Level Match Analysis

| Brand | Total Products | High Matches | Review | No Match |
|-------|---------------|--------------|---------|----------|
"""
    
    # Brand-level analysis
    brand_matches = staging_df.groupby('brand_slug').agg({
        'match_category': lambda x: {
            'high': (x == 'high').sum(),
            'review': (x == 'review').sum(),
            'no-match': (x == 'no-match').sum(),
            'total': len(x)
        }
    }).reset_index()
    
    brand_matches = brand_matches.sort_values(
        by='match_category',
        key=lambda x: x.apply(lambda d: d['total']),
        ascending=False
    ).head(20)
    
    for _, row in brand_matches.iterrows():
        stats = row['match_category']
        feasibility_report += f"| {row['brand_slug']} | {stats['total']} | {stats['high']} | {stats['review']} | {stats['no-match']} |\n"
    
    # Sample high-confidence matches
    high_matches = staging_df[staging_df['match_category'] == 'high'].head(10)
    
    feasibility_report += f"""
## Sample High-Confidence Matches (Top 10)

| Brand | Product (Staged) | Match Score | Form | Life Stage |
|-------|-----------------|-------------|------|------------|
"""
    
    for _, row in high_matches.iterrows():
        feasibility_report += f"| {row['brand_slug']} | {row['product_name_norm'][:40]} | {row['match_score']:.2f} | {row['form_guess']} | {row['life_stage_guess']} |\n"
    
    # Sample no-matches (potential new products)
    no_matches = staging_df[staging_df['match_category'] == 'no-match'].head(10)
    
    feasibility_report += f"""
## Sample No-Match Products (Potential New Additions)

| Brand | Product | Form | Life Stage | Has Ingredients |
|-------|---------|------|------------|-----------------|
"""
    
    for _, row in no_matches.iterrows():
        feasibility_report += f"| {row['brand_slug']} | {row['product_name_norm'][:40]} | {row['form_guess']} | {row['life_stage_guess']} | {'✅' if pd.notna(row['ingredients_raw']) else '❌'} |\n"
    
    feasibility_report += f"""
## Enrichment Potential

### High-Value Additions (No-Match with Complete Data)
Products that don't match existing catalog but have complete information:
- **Count**: {len(staging_df[(staging_df['match_category'] == 'no-match') & (staging_df['ingredients_raw'].notna())])}
- **Unique brands**: {staging_df[(staging_df['match_category'] == 'no-match') & (staging_df['ingredients_raw'].notna())]['brand_slug'].nunique()}

### Data Enhancement Opportunities (High Matches)
Existing products that can be enriched with AADF data:
- **With ingredients**: {len(staging_df[(staging_df['match_category'] == 'high') & (staging_df['ingredients_raw'].notna())])}
- **With nutrition data**: {len(staging_df[(staging_df['match_category'] == 'high') & (staging_df['kcal_per_100g'].notna())])}

## Recommendations

1. **Immediate Actions**:
   - Review and approve {match_stats.get('high', 0)} high-confidence matches for enrichment
   - These matches can safely add ingredients/nutrition data to existing products

2. **Manual Review Required**:
   - {match_stats.get('review', 0)} products need manual verification
   - Focus on brands with highest product counts first

3. **New Product Additions**:
   - {match_stats.get('no-match', 0)} products appear to be new to the catalog
   - Prioritize those with complete ingredient data ({len(staging_df[(staging_df['match_category'] == 'no-match') & (staging_df['ingredients_raw'].notna())])})

## Next Steps

1. Create merge script for high-confidence matches (score ≥ 0.80)
2. Generate review queue for medium-confidence matches (0.65-0.79)
3. Validate brand normalization for no-match products
4. Execute enrichment in staged batches with rollback capability
"""
    
    with open('reports/AADF_MATCH_FEASIBILITY.md', 'w') as f:
        f.write(feasibility_report)
    print("   Created: reports/AADF_MATCH_FEASIBILITY.md")
    
    # Save enhanced staging data with match scores
    staging_df.to_csv('data/staging/aadf_staging_v2_with_matches.csv', index=False)
    print("   Saved enriched data: data/staging/aadf_staging_v2_with_matches.csv")
    
    print(f"\n=== Processing Complete ===")
    print(f"Finished: {datetime.now()}")
    print(f"\nSummary:")
    print(f"  - Processed: {len(staging_df)} rows")
    print(f"  - High matches: {match_stats.get('high', 0)}")
    print(f"  - Review needed: {match_stats.get('review', 0)}")
    print(f"  - New products: {match_stats.get('no-match', 0)}")
    print(f"\nReports generated:")
    print(f"  - reports/AADF_STAGE_AUDIT_V2.md")
    print(f"  - reports/AADF_MATCH_FEASIBILITY.md")

if __name__ == "__main__":
    main()