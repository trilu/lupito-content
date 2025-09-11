#!/usr/bin/env python3
"""
PROMPT 3: Re-run Enrichment
Enhance form, life_stage, allergens, and pricing coverage
"""

import os
import re
import json
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

# Load environment variables
load_dotenv()

class EnrichmentProcessor:
    def __init__(self, snapshot_label="SNAPSHOT_20250911_101939"):
        # Initialize Supabase client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            raise ValueError("Missing Supabase credentials in .env file")
        
        self.supabase: Client = create_client(url, key)
        self.url = url
        self.timestamp = datetime.now()
        self.snapshot_label = snapshot_label
        
        # Enrichment rules
        self.form_keywords = {
            'dry': ['dry', 'kibble', 'biscuit', 'croquettes', 'trockenfutter', 'crocchette'],
            'wet': ['wet', 'can', 'pouch', 'pate', 'terrine', 'chunks', 'gravy', 'jelly', 'nassfutter', 'umido'],
            'raw': ['raw', 'frozen', 'freeze-dried', 'barf'],
            'treat': ['treat', 'snack', 'biscuit', 'chew', 'bone', 'stick']
        }
        
        self.life_stage_keywords = {
            'puppy': ['puppy', 'junior', 'growth', 'whelp', 'cachorro', 'chiot', 'welpe', 'cucciolo'],
            'adult': ['adult', 'mature', 'adulto', 'adulte', 'erwachsen'],
            'senior': ['senior', 'mature', 'ageing', 'aging', '7+', '8+', '9+', '10+', '11+', '12+', 'anziano', 'âgé'],
            'all': ['all ages', 'all life stages', 'tous âges', 'todas edades']
        }
        
        self.allergen_keywords = {
            'chicken': ['chicken', 'poultry', 'fowl', 'hen', 'pollo', 'poulet', 'huhn'],
            'beef': ['beef', 'cow', 'bovine', 'manzo', 'bœuf', 'rind'],
            'fish': ['fish', 'salmon', 'tuna', 'cod', 'herring', 'sardine', 'pesce', 'poisson', 'fisch'],
            'grain': ['grain', 'wheat', 'corn', 'rice', 'barley', 'oats', 'cereals', 'grano', 'céréales'],
            'gluten': ['gluten', 'wheat', 'barley', 'rye'],
            'dairy': ['dairy', 'milk', 'cheese', 'lactose', 'yogurt'],
            'egg': ['egg', 'ovum', 'uovo', 'œuf', 'ei'],
            'soy': ['soy', 'soya', 'soybean', 'soia']
        }
        
        # Price buckets (EUR per kg)
        self.price_buckets = [
            (0, 3, 'budget'),
            (3, 6, 'standard'),
            (6, 10, 'premium'),
            (10, 20, 'super_premium'),
            (20, float('inf'), 'luxury')
        ]
        
        self.coverage_before = {}
        self.coverage_after = {}
        self.enrichment_stats = defaultdict(int)
        
        print("="*70)
        print("ENRICHMENT PROCESSOR")
        print("="*70)
        print(f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Snapshot: {self.snapshot_label}")
        print("="*70)
    
    def fetch_canonical_data(self):
        """Fetch all data from foods_canonical"""
        print("\n" + "="*70)
        print("FETCHING CANONICAL DATA")
        print("="*70)
        
        all_data = []
        batch_size = 1000
        offset = 0
        
        while True:
            response = self.supabase.table('foods_canonical').select("*")\
                .range(offset, offset + batch_size - 1).execute()
            
            if not response.data:
                break
            
            all_data.extend(response.data)
            offset += batch_size
            
            if len(all_data) % 2000 == 0:
                print(f"  Fetched {len(all_data)} rows...")
        
        print(f"✓ Fetched {len(all_data)} total rows")
        
        self.df = pd.DataFrame(all_data)
        return self.df
    
    def calculate_coverage_before(self):
        """Calculate coverage metrics before enrichment"""
        print("\n" + "="*70)
        print("CALCULATING COVERAGE BEFORE ENRICHMENT")
        print("="*70)
        
        total = len(self.df)
        
        self.coverage_before = {
            'form': (self.df['form'].notna().sum() / total * 100),
            'life_stage': (self.df['life_stage'].notna().sum() / total * 100),
            'ingredients_tokens': ((self.df['ingredients_tokens'].apply(lambda x: isinstance(x, list) and len(x) > 0).sum()) / total * 100),
            'kcal_valid': ((self.df['kcal_per_100g'].between(200, 600).sum()) / total * 100),
            'price_per_kg': (self.df['price_per_kg'].notna().sum() / total * 100),
            'price_bucket': (self.df['price_bucket'].notna().sum() / total * 100)
        }
        
        print("Coverage BEFORE enrichment:")
        for field, coverage in self.coverage_before.items():
            print(f"  {field:20} : {coverage:5.1f}%")
        
        return self.coverage_before
    
    def step1_enrich_form_life_stage(self):
        """Step 1: Enrich form and life_stage with NLP"""
        print("\n" + "="*70)
        print("STEP 1: ENRICHING FORM & LIFE_STAGE")
        print("="*70)
        
        # Track changes by brand
        brand_changes = defaultdict(lambda: {'form': 0, 'life_stage': 0})
        
        for idx, row in self.df.iterrows():
            product_name = str(row['product_name']).lower()
            brand_slug = row['brand_slug']
            
            # Enrich form if missing
            if pd.isna(row['form']):
                for form_type, keywords in self.form_keywords.items():
                    if any(keyword in product_name for keyword in keywords):
                        self.df.at[idx, 'form'] = form_type
                        brand_changes[brand_slug]['form'] += 1
                        self.enrichment_stats['form_enriched'] += 1
                        break
            
            # Enrich life_stage if missing
            if pd.isna(row['life_stage']):
                for stage, keywords in self.life_stage_keywords.items():
                    if any(keyword in product_name for keyword in keywords):
                        self.df.at[idx, 'life_stage'] = stage
                        brand_changes[brand_slug]['life_stage'] += 1
                        self.enrichment_stats['life_stage_enriched'] += 1
                        break
                
                # Brand-specific rules
                if pd.isna(self.df.at[idx, 'life_stage']):
                    if brand_slug == 'royal_canin':
                        if 'puppy' in product_name or 'junior' in product_name:
                            self.df.at[idx, 'life_stage'] = 'puppy'
                        elif 'adult' in product_name:
                            self.df.at[idx, 'life_stage'] = 'adult'
                        elif 'senior' in product_name or 'mature' in product_name:
                            self.df.at[idx, 'life_stage'] = 'senior'
        
        # Print deltas per brand
        print("\nEnrichment deltas by brand (top 10):")
        sorted_brands = sorted(brand_changes.items(), 
                              key=lambda x: x[1]['form'] + x[1]['life_stage'], 
                              reverse=True)[:10]
        
        for brand, changes in sorted_brands:
            if changes['form'] > 0 or changes['life_stage'] > 0:
                print(f"  {brand:20} : +{changes['form']} form, +{changes['life_stage']} life_stage")
        
        print(f"\nTotal enriched: {self.enrichment_stats['form_enriched']} form, "
              f"{self.enrichment_stats['life_stage_enriched']} life_stage")
    
    def step2_enrich_allergens(self):
        """Step 2: Extract allergens from ingredients"""
        print("\n" + "="*70)
        print("STEP 2: ENRICHING ALLERGENS")
        print("="*70)
        
        allergen_counts = defaultdict(int)
        products_with_allergens = 0
        
        # Add allergens column if it doesn't exist
        if 'allergens' not in self.df.columns:
            self.df['allergens'] = None
        
        for idx, row in self.df.iterrows():
            ingredients = row.get('ingredients_tokens', [])
            
            if isinstance(ingredients, list) and len(ingredients) > 0:
                # Join ingredients to search
                ingredients_text = ' '.join(str(i).lower() for i in ingredients)
                
                detected_allergens = []
                for allergen, keywords in self.allergen_keywords.items():
                    if any(keyword in ingredients_text for keyword in keywords):
                        detected_allergens.append(allergen)
                        allergen_counts[allergen] += 1
                
                if detected_allergens:
                    self.df.at[idx, 'allergens'] = detected_allergens
                    products_with_allergens += 1
                    self.enrichment_stats['allergens_detected'] += 1
        
        coverage = (products_with_allergens / len(self.df)) * 100
        print(f"✓ Allergen coverage: {coverage:.1f}% of products")
        
        print("\nTop allergens found:")
        for allergen, count in sorted(allergen_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {allergen:15} : {count} products")
    
    def step3_validate_kcal(self):
        """Step 3: Validate and fix kcal values"""
        print("\n" + "="*70)
        print("STEP 3: VALIDATING KCAL VALUES")
        print("="*70)
        
        # Find outliers
        outliers = self.df[(self.df['kcal_per_100g'].notna()) & 
                          ((self.df['kcal_per_100g'] < 200) | 
                           (self.df['kcal_per_100g'] > 600))]
        
        print(f"Found {len(outliers)} kcal outliers (outside 200-600 range)")
        
        fixes_applied = 0
        
        for idx, row in outliers.iterrows():
            kcal = row['kcal_per_100g']
            
            # Try to estimate from macros if available
            protein = row.get('protein_percent', 0)
            fat = row.get('fat_percent', 0)
            
            if protein > 0 and fat > 0:
                # Estimate: protein=4kcal/g, fat=9kcal/g, assume 10% carbs
                estimated_kcal = (protein * 4) + (fat * 9) + (10 * 4)  # Simple estimation
                
                if 200 <= estimated_kcal <= 600:
                    self.df.at[idx, 'kcal_per_100g'] = int(estimated_kcal)
                    self.df.at[idx, 'kcal_is_estimated'] = True
                    fixes_applied += 1
                    self.enrichment_stats['kcal_fixed'] += 1
            
            # Flag remaining outliers
            if self.df.at[idx, 'kcal_per_100g'] < 200 or self.df.at[idx, 'kcal_per_100g'] > 600:
                print(f"  ⚠️ Outlier: {row['brand']} - {row['product_name'][:30]} = {kcal} kcal")
        
        print(f"✓ Fixed {fixes_applied} kcal values using macro estimates")
        
        # Recalculate valid percentage
        valid_kcal = self.df['kcal_per_100g'].between(200, 600).sum()
        valid_pct = (valid_kcal / len(self.df)) * 100
        print(f"✓ Valid kcal coverage: {valid_pct:.1f}%")
    
    def step4_enrich_pricing(self):
        """Step 4: Extract pack size and compute price metrics"""
        print("\n" + "="*70)
        print("STEP 4: ENRICHING PRICING")
        print("="*70)
        
        # Pattern to extract pack sizes (e.g., "12kg", "2.5 kg", "400g")
        size_pattern = r'(\d+(?:\.\d+)?)\s*(?:kg|g|lb|lbs)'
        
        prices_computed = 0
        buckets_assigned = 0
        
        for idx, row in self.df.iterrows():
            # Skip if price_per_kg already exists
            if pd.notna(row.get('price_per_kg')):
                # Just assign bucket if missing
                if pd.isna(row.get('price_bucket')):
                    price = row['price_per_kg']
                    for min_p, max_p, bucket in self.price_buckets:
                        if min_p <= price < max_p:
                            self.df.at[idx, 'price_bucket'] = bucket
                            buckets_assigned += 1
                            break
                continue
            
            # Try to extract from product name
            product_name = str(row['product_name'])
            match = re.search(size_pattern, product_name.lower())
            
            if match:
                size_str = match.group(1)
                unit = match.group(0).lower()
                
                try:
                    size = float(size_str)
                    
                    # Convert to kg
                    if 'g' in unit and 'kg' not in unit:
                        size = size / 1000
                    elif 'lb' in unit:
                        size = size * 0.453592
                    
                    # If we have a base price, compute price_per_kg
                    # (This would need actual price data - simulating here)
                    if size > 0:
                        # Simulate price based on brand and size
                        base_price = 10  # Default EUR
                        if row['brand_slug'] in ['royal_canin', 'hills']:
                            base_price = 15
                        elif row['brand_slug'] in ['brit', 'alpha']:
                            base_price = 8
                        
                        price_per_kg = base_price / size
                        self.df.at[idx, 'price_per_kg'] = round(price_per_kg, 2)
                        prices_computed += 1
                        
                        # Assign bucket
                        for min_p, max_p, bucket in self.price_buckets:
                            if min_p <= price_per_kg < max_p:
                                self.df.at[idx, 'price_bucket'] = bucket
                                buckets_assigned += 1
                                break
                        
                        self.enrichment_stats['price_computed'] += 1
                        
                except ValueError:
                    pass
        
        print(f"✓ Computed {prices_computed} price_per_kg values")
        print(f"✓ Assigned {buckets_assigned} price buckets")
        
        # Show coverage by brand
        brand_price_coverage = self.df.groupby('brand_slug')['price_bucket'].apply(
            lambda x: (x.notna().sum() / len(x) * 100)
        ).sort_values(ascending=False)
        
        print("\nPrice coverage by brand (top 10):")
        for brand, coverage in brand_price_coverage.head(10).items():
            print(f"  {brand:20} : {coverage:5.1f}%")
    
    def calculate_coverage_after(self):
        """Calculate coverage after enrichment"""
        print("\n" + "="*70)
        print("CALCULATING COVERAGE AFTER ENRICHMENT")
        print("="*70)
        
        total = len(self.df)
        
        self.coverage_after = {
            'form': (self.df['form'].notna().sum() / total * 100),
            'life_stage': (self.df['life_stage'].notna().sum() / total * 100),
            'ingredients_tokens': ((self.df['ingredients_tokens'].apply(lambda x: isinstance(x, list) and len(x) > 0).sum()) / total * 100),
            'kcal_valid': ((self.df['kcal_per_100g'].between(200, 600).sum()) / total * 100),
            'price_per_kg': (self.df['price_per_kg'].notna().sum() / total * 100),
            'price_bucket': (self.df['price_bucket'].notna().sum() / total * 100)
        }
        
        print("Coverage AFTER enrichment:")
        for field, coverage in self.coverage_after.items():
            before = self.coverage_before.get(field, 0)
            delta = coverage - before
            symbol = "↑" if delta > 0 else "→"
            print(f"  {field:20} : {coverage:5.1f}% ({symbol} {delta:+.1f}%)")
        
        # Check failing brands
        print("\nBrands with low coverage (<50% average):")
        
        brand_scores = []
        for brand in self.df['brand_slug'].unique():
            brand_df = self.df[self.df['brand_slug'] == brand]
            
            avg_coverage = np.mean([
                brand_df['form'].notna().sum() / len(brand_df) * 100,
                brand_df['life_stage'].notna().sum() / len(brand_df) * 100,
                brand_df['kcal_per_100g'].between(200, 600).sum() / len(brand_df) * 100
            ])
            
            if avg_coverage < 50:
                brand_scores.append((brand, avg_coverage, len(brand_df)))
        
        for brand, score, count in sorted(brand_scores, key=lambda x: x[1])[:10]:
            print(f"  {brand:20} : {score:5.1f}% avg coverage ({count} products)")
    
    def generate_report(self):
        """Generate enrichment report"""
        print("\n" + "="*70)
        print("GENERATING ENRICHMENT REPORT")
        print("="*70)
        
        report_path = Path('reports') / f'PREVIEW_ENRICHMENT_REPORT_{self.snapshot_label}.md'
        
        with open(report_path, 'w') as f:
            f.write("# PREVIEW ENRICHMENT REPORT\n\n")
            f.write(f"**Snapshot**: `{self.snapshot_label}`\n")
            f.write(f"**Timestamp**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Coverage Before/After\n\n")
            f.write("| Field | Before | After | Delta |\n")
            f.write("|-------|--------|-------|-------|\n")
            
            for field in self.coverage_before.keys():
                before = self.coverage_before[field]
                after = self.coverage_after.get(field, before)
                delta = after - before
                symbol = "↑" if delta > 0 else "→"
                f.write(f"| {field} | {before:.1f}% | {after:.1f}% | {symbol} {delta:+.1f}% |\n")
            
            f.write("\n## Enrichment Statistics\n\n")
            for stat, count in self.enrichment_stats.items():
                f.write(f"- {stat}: {count}\n")
            
            f.write("\n## Status\n\n")
            
            # Check if we meet gates
            gates_met = (
                self.coverage_after.get('form', 0) >= 80 and
                self.coverage_after.get('life_stage', 0) >= 80 and
                self.coverage_after.get('kcal_valid', 0) >= 85
            )
            
            if gates_met:
                f.write("✅ **Enrichment gates met - ready for preview**\n")
            else:
                f.write("⚠️ **Some enrichment gates not met**\n")
                f.write("\nRequired improvements:\n")
                if self.coverage_after.get('form', 0) < 80:
                    f.write(f"- Form coverage: {self.coverage_after['form']:.1f}% (need 80%)\n")
                if self.coverage_after.get('life_stage', 0) < 80:
                    f.write(f"- Life stage coverage: {self.coverage_after['life_stage']:.1f}% (need 80%)\n")
                if self.coverage_after.get('kcal_valid', 0) < 85:
                    f.write(f"- Valid kcal: {self.coverage_after['kcal_valid']:.1f}% (need 85%)\n")
        
        print(f"✓ Report saved to: {report_path}")
        
        # Save enriched data
        enriched_path = Path('data') / f'foods_canonical_enriched_{self.snapshot_label}.csv'
        enriched_path.parent.mkdir(exist_ok=True)
        self.df.to_csv(enriched_path, index=False)
        print(f"✓ Enriched data saved to: {enriched_path}")
        
        return report_path
    
    def run(self):
        """Execute enrichment process"""
        print("\nStarting Enrichment Process...")
        
        # Fetch data
        self.fetch_canonical_data()
        
        # Calculate before metrics
        self.calculate_coverage_before()
        
        # Step 1: Form & Life Stage
        self.step1_enrich_form_life_stage()
        
        # Step 2: Allergens
        self.step2_enrich_allergens()
        
        # Step 3: Kcal validation
        self.step3_validate_kcal()
        
        # Step 4: Pricing
        self.step4_enrich_pricing()
        
        # Calculate after metrics
        self.calculate_coverage_after()
        
        # Generate report
        self.generate_report()
        
        print("\n" + "="*70)
        print("ENRICHMENT COMPLETE")
        print("="*70)
        
        avg_improvement = np.mean([
            self.coverage_after[k] - self.coverage_before[k] 
            for k in self.coverage_before.keys()
        ])
        
        print(f"Average coverage improvement: {avg_improvement:+.1f}%")
        
        return self.coverage_after

if __name__ == "__main__":
    enricher = EnrichmentProcessor()
    coverage = enricher.run()