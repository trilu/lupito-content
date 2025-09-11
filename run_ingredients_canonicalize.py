#!/usr/bin/env python3
"""
Prompt 2: Tokenize + Canonicalize + Allergen Map
Rebuild ingredients processing for quality
"""

import os
import re
import yaml
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
from collections import Counter, defaultdict
import csv

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

print("="*80)
print("INGREDIENTS CANONICALIZATION & ALLERGEN MAPPING")
print("="*80)
print(f"Timestamp: {timestamp}")
print()

# Create canonical ingredients map
canonical_map = {
    # Proteins - Chicken variations
    'chicken meal': 'chicken',
    'dehydrated chicken': 'chicken',
    'chicken meat meal': 'chicken',
    'dried chicken': 'chicken',
    'fresh chicken': 'chicken',
    'chicken protein': 'chicken',
    'hydrolysed chicken': 'chicken',
    'chicken liver': 'chicken',
    
    # Proteins - Other meats
    'beef meal': 'beef',
    'dehydrated beef': 'beef',
    'lamb meal': 'lamb',
    'dehydrated lamb': 'lamb',
    'turkey meal': 'turkey',
    'dehydrated turkey': 'turkey',
    'duck meal': 'duck',
    'dehydrated duck': 'duck',
    'pork meal': 'pork',
    'dehydrated pork': 'pork',
    'venison meal': 'venison',
    'rabbit meal': 'rabbit',
    
    # Fish variations
    'salmon meal': 'salmon',
    'dehydrated salmon': 'salmon',
    'fresh salmon': 'salmon',
    'salmon oil': 'fish oil',
    'tuna meal': 'tuna',
    'dehydrated tuna': 'tuna',
    'herring meal': 'herring',
    'whitefish meal': 'whitefish',
    'ocean fish': 'fish',
    'fish meal': 'fish',
    
    # Grains
    'maize': 'corn',
    'corn meal': 'corn',
    'maize flour': 'corn',
    'corn gluten': 'corn',
    'ground corn': 'corn',
    'wheat flour': 'wheat',
    'wheat bran': 'wheat',
    'whole wheat': 'wheat',
    'rice flour': 'rice',
    'brown rice': 'rice',
    'white rice': 'rice',
    'brewers rice': 'rice',
    'oat meal': 'oats',
    'oat flour': 'oats',
    'whole oats': 'oats',
    'barley flour': 'barley',
    'pearl barley': 'barley',
    
    # Vegetables
    'sweet potato': 'sweet potato',
    'sweet potatoes': 'sweet potato',
    'potato': 'potato',
    'potatoes': 'potato',
    'pea protein': 'peas',
    'green peas': 'peas',
    'yellow peas': 'peas',
    'pea flour': 'peas',
    'split peas': 'peas',
    'whole peas': 'peas',
    'carrot': 'carrot',
    'carrots': 'carrot',
    'dried carrots': 'carrot',
    
    # Legumes
    'soybean meal': 'soy',
    'soy protein': 'soy',
    'soya': 'soy',
    'lentils': 'lentils',
    'red lentils': 'lentils',
    'green lentils': 'lentils',
    'chickpeas': 'chickpeas',
    'garbanzo beans': 'chickpeas',
    
    # Seeds and oils
    'linseed': 'flax',
    'flaxseed': 'flax',
    'flax seed': 'flax',
    'sunflower oil': 'sunflower',
    'sunflower seeds': 'sunflower',
    'canola oil': 'canola',
    'rapeseed oil': 'canola',
    
    # Others
    'beet pulp': 'beet pulp',
    'dried beet pulp': 'beet pulp',
    'sugar beet pulp': 'beet pulp',
    'animal fat': 'animal fat',
    'poultry fat': 'chicken fat',
    'chicken fat': 'chicken fat',
    'egg powder': 'egg',
    'dried egg': 'egg',
    'whole egg': 'egg',
    'milk powder': 'dairy',
    'dried milk': 'dairy',
    'whey': 'dairy',
    'cheese': 'dairy',
    'yogurt': 'dairy',
    
    # Supplements
    'vitamin a': 'vitamins',
    'vitamin d': 'vitamins',
    'vitamin e': 'vitamins',
    'vitamin c': 'vitamins',
    'vitamin mix': 'vitamins',
    'mineral mix': 'minerals',
    'calcium': 'minerals',
    'phosphorus': 'minerals',
    'zinc': 'minerals',
    'iron': 'minerals',
    
    # Common additives
    'yeast extract': 'yeast',
    'brewers yeast': 'yeast',
    'nutritional yeast': 'yeast',
    'cranberry extract': 'cranberry',
    'cranberries': 'cranberry',
    'dried cranberries': 'cranberry',
    'blueberry': 'blueberry',
    'blueberries': 'blueberry',
    'apple': 'apple',
    'apples': 'apple',
    'dried apple': 'apple',
}

# Define allergen groups
allergen_taxonomy = {
    'poultry': ['chicken', 'turkey', 'duck', 'goose', 'poultry'],
    'red_meat': ['beef', 'lamb', 'pork', 'venison', 'rabbit', 'bison'],
    'fish': ['salmon', 'tuna', 'herring', 'whitefish', 'fish', 'krill', 'anchovy', 'sardine'],
    'dairy': ['dairy', 'milk', 'cheese', 'whey', 'yogurt', 'lactose'],
    'egg': ['egg', 'eggs'],
    'grains': ['wheat', 'corn', 'rice', 'barley', 'oats', 'rye', 'millet', 'sorghum'],
    'legumes': ['soy', 'peas', 'lentils', 'chickpeas', 'beans'],
    'nuts': ['peanut', 'almond', 'cashew', 'walnut', 'pecan'],
    'seeds': ['flax', 'sunflower', 'sesame', 'chia', 'hemp'],
}

# Save canonical map
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
canonical_file = data_dir / "ingredients_canonical_map.yaml"

with open(canonical_file, 'w') as f:
    yaml.dump({
        'canonical_map': canonical_map,
        'allergen_taxonomy': allergen_taxonomy,
        'generated': datetime.now().isoformat(),
        'total_mappings': len(canonical_map)
    }, f, default_flow_style=False, sort_keys=False)

print(f"✅ Canonical map saved: {canonical_file}")
print(f"   Total mappings: {len(canonical_map)}")

def tokenize_ingredients(raw_text):
    """Tokenize and clean ingredients text"""
    if not raw_text:
        return []
    
    # Convert to lowercase
    text = raw_text.lower()
    
    # Remove percentages and numbers in parentheses
    text = re.sub(r'\([^)]*\d+[^)]*\)', '', text)
    
    # Remove other parentheses content
    text = re.sub(r'\([^)]*\)', '', text)
    
    # Split on commas and 'and'
    parts = re.split(r'[,;]|\sand\s', text)
    
    tokens = []
    for part in parts:
        # Clean whitespace and special chars
        part = re.sub(r'[^\w\s-]', ' ', part)
        part = ' '.join(part.split())
        
        if part and len(part) > 1:
            # Apply canonical mapping
            canonical = canonical_map.get(part, part)
            tokens.append(canonical)
    
    return tokens

def get_allergen_groups(tokens):
    """Map tokens to allergen groups"""
    groups = set()
    
    for token in tokens:
        for group, allergens in allergen_taxonomy.items():
            if token in allergens:
                groups.add(group)
                break
            # Check if token contains allergen
            for allergen in allergens:
                if allergen in token:
                    groups.add(group)
                    break
    
    return list(groups)

# Process tables
tables_to_process = ['food_candidates', 'food_candidates_sc']
all_tokens_counter = Counter()
unmapped_terms = Counter()
processing_stats = []

for table_name in tables_to_process:
    print(f"\n{'='*60}")
    print(f"📊 PROCESSING: {table_name}")
    print('='*60)
    
    stats = {
        'table': table_name,
        'total_rows': 0,
        'has_raw': 0,
        'tokenized': 0,
        'has_allergens': 0,
        'avg_tokens': 0
    }
    
    try:
        # Get data with ingredients_raw
        response = supabase.table(table_name).select('id, ingredients_raw, ingredients_tokens').execute()
        
        if not response.data:
            print(f"  ⚠️ No data found")
            continue
            
        df = pd.DataFrame(response.data)
        stats['total_rows'] = len(df)
        print(f"  Total rows: {stats['total_rows']:,}")
        
        updates = []
        
        for idx, row in df.iterrows():
            raw_text = row.get('ingredients_raw')
            
            if raw_text:
                stats['has_raw'] += 1
                
                # Tokenize
                tokens = tokenize_ingredients(raw_text)
                
                if tokens:
                    stats['tokenized'] += 1
                    all_tokens_counter.update(tokens)
                    
                    # Find unmapped terms
                    for token in tokens:
                        if token not in canonical_map.values():
                            unmapped_terms[token] += 1
                    
                    # Get allergen groups
                    allergen_groups = get_allergen_groups(tokens)
                    if allergen_groups:
                        stats['has_allergens'] += 1
                    
                    # Prepare update
                    updates.append({
                        'id': row['id'],
                        'ingredients_tokens': tokens,
                        'allergen_groups': allergen_groups
                    })
                    
                    if len(updates) >= 100:
                        # Batch update
                        for update in updates:
                            supabase.table(table_name).update({
                                'ingredients_tokens': update['ingredients_tokens']
                            }).eq('id', update['id']).execute()
                        print(f"  Updated batch of {len(updates)} rows")
                        updates = []
        
        # Final batch
        if updates:
            for update in updates:
                supabase.table(table_name).update({
                    'ingredients_tokens': update['ingredients_tokens']
                }).eq('id', update['id']).execute()
            print(f"  Updated final batch of {len(updates)} rows")
        
        # Calculate stats
        if stats['tokenized'] > 0:
            stats['avg_tokens'] = sum(len(u['ingredients_tokens']) for u in updates) / stats['tokenized']
        
        print(f"  ✅ Rows with raw text: {stats['has_raw']:,} ({stats['has_raw']/stats['total_rows']*100:.1f}%)")
        print(f"  ✅ Rows tokenized: {stats['tokenized']:,} ({stats['tokenized']/stats['total_rows']*100:.1f}%)")
        print(f"  ✅ Rows with allergens: {stats['has_allergens']:,}")
        print(f"  📊 Avg tokens per product: {stats['avg_tokens']:.1f}")
        
        processing_stats.append(stats)
        
    except Exception as e:
        print(f"  ❌ Error: {e}")

# Generate report
print("\n" + "="*80)
print("📊 GENERATING REPORT")
print("="*80)

report_dir = Path("reports")
report_dir.mkdir(exist_ok=True)
report_file = report_dir / "INGREDIENTS_CANONICALIZATION.md"

# Get top tokens
top_tokens = all_tokens_counter.most_common(100)
top_unmapped = unmapped_terms.most_common(50)

with open(report_file, 'w') as f:
    f.write("# Ingredients Canonicalization Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write("## Processing Summary\n\n")
    f.write("| Table | Total Rows | Has Raw | Tokenized | Coverage % | Has Allergens | Avg Tokens |\n")
    f.write("|-------|------------|---------|-----------|------------|---------------|------------|\n")
    
    for s in processing_stats:
        coverage = s['tokenized'] / s['total_rows'] * 100 if s['total_rows'] > 0 else 0
        f.write(f"| {s['table']} | {s['total_rows']:,} | {s['has_raw']:,} | ")
        f.write(f"{s['tokenized']:,} | {coverage:.1f}% | {s['has_allergens']:,} | {s['avg_tokens']:.1f} |\n")
    
    f.write("\n## Canonical Map Statistics\n\n")
    f.write(f"- Total canonical mappings: {len(canonical_map)}\n")
    f.write(f"- Allergen groups defined: {len(allergen_taxonomy)}\n")
    f.write(f"- Unique tokens found: {len(all_tokens_counter)}\n")
    f.write(f"- Total token occurrences: {sum(all_tokens_counter.values())}\n")
    
    f.write("\n## Top 100 Ingredient Tokens\n\n")
    f.write("| Rank | Token | Count | Canonical |\n")
    f.write("|------|-------|-------|----------|\n")
    
    for i, (token, count) in enumerate(top_tokens, 1):
        is_canonical = '✅' if token in canonical_map.values() else '❌'
        f.write(f"| {i} | {token} | {count:,} | {is_canonical} |\n")
    
    f.write("\n## Unmapped Terms (Need Canonical Mapping)\n\n")
    f.write("These terms appear frequently but don't have canonical mappings:\n\n")
    f.write("| Term | Occurrences | Suggested Canonical |\n")
    f.write("|------|-------------|--------------------|\n")
    
    for term, count in top_unmapped[:50]:
        # Suggest canonical based on similarity
        suggestion = ""
        if 'meal' in term and any(meat in term for meat in ['chicken', 'beef', 'lamb']):
            suggestion = term.replace(' meal', '')
        elif 'dried' in term:
            suggestion = term.replace('dried ', '')
        elif 'fresh' in term:
            suggestion = term.replace('fresh ', '')
        
        f.write(f"| {term} | {count} | {suggestion} |\n")
    
    f.write("\n## Allergen Group Coverage\n\n")
    f.write("Defined allergen groups and their triggers:\n\n")
    
    for group, allergens in allergen_taxonomy.items():
        f.write(f"- **{group}**: {', '.join(allergens[:5])}...\n")
    
    f.write("\n## Files Generated\n\n")
    f.write(f"- Canonical map: `{canonical_file}`\n")
    f.write(f"- Unmapped terms: `data/unmapped_terms.csv`\n")
    
    f.write("\n## Next Steps\n\n")
    f.write("1. Review unmapped terms and add to canonical map\n")
    f.write("2. Re-run tokenization for better coverage\n")
    f.write("3. Proceed to Prompt 3: Manufacturer Enrichment\n")

print(f"✅ Report saved to: {report_file}")

# Save unmapped terms CSV
unmapped_file = data_dir / "unmapped_terms.csv"
with open(unmapped_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['term', 'occurrences', 'suggested_canonical'])
    
    for term, count in top_unmapped:
        suggestion = ""
        if 'meal' in term:
            suggestion = term.replace(' meal', '')
        elif 'dried' in term:
            suggestion = term.replace('dried ', '')
        elif 'fresh' in term:
            suggestion = term.replace('fresh ', '')
        writer.writerow([term, count, suggestion])

print(f"✅ Unmapped terms saved to: {unmapped_file}")

print("\n" + "="*80)
print("✅ CANONICALIZATION COMPLETE")
print("="*80)
print(f"📄 Full report: {report_file}")
print(f"📝 Canonical map: {canonical_file}")
print(f"📋 Unmapped terms: {unmapped_file}")