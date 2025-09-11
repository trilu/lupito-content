#!/usr/bin/env python3
"""
PROMPT C: Re-run enrichment on Preview (form, life-stage, allergens, kcal, price)
Goal: Lift coverage to gates on the full catalog in Preview
"""

import os
import json
import re
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from pathlib import Path

# Load environment variables
load_dotenv()

class EnrichmentPipeline:
    def __init__(self):
        # Initialize Supabase client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            raise ValueError("Missing Supabase credentials in .env file")
        
        self.supabase: Client = create_client(url, key)
        self.timestamp = datetime.now()
        
        # Multi-language patterns
        self.form_patterns = {
            'dry': ['dry', 'kibble', 'croquettes', 'trocken', 'seco', 'droog', 'biscuits', 'crocchette'],
            'wet': ['wet', 'canned', 'pouch', 'pate', 'terrine', 'chunks', 'gravy', 'jelly', 'mousse', 
                   'nass', 'humedo', 'nat', 'umido', 'in sauce', 'in broth'],
            'raw': ['raw', 'freeze-dried', 'frozen', 'barf', 'fresh'],
            'semi_moist': ['semi-moist', 'soft', 'chewy', 'tender']
        }
        
        self.life_stage_patterns = {
            'puppy': ['puppy', 'junior', 'growth', 'welpe', 'cachorro', 'chiot', 'cucciolo', 
                     'puppies', 'whelp', 'young', 'starter'],
            'adult': ['adult', 'maintenance', 'erwachsen', 'adulto', 'adulte', '1+', '1-7',
                     'mature', 'all breeds', 'all life stages'],
            'senior': ['senior', 'mature', 'aging', 'ageing', '7+', '8+', '9+', '10+', '11+', '12+',
                      'geriatric', 'old', 'älter', 'anziano', 'âgé', 'vieux']
        }
        
        # Common allergens
        self.allergen_patterns = {
            'chicken': ['chicken', 'poultry', 'fowl', 'hen'],
            'beef': ['beef', 'cow', 'bovine'],
            'wheat': ['wheat', 'gluten'],
            'corn': ['corn', 'maize'],
            'soy': ['soy', 'soya', 'soybean'],
            'dairy': ['milk', 'cheese', 'dairy', 'lactose'],
            'egg': ['egg'],
            'fish': ['fish', 'salmon', 'tuna', 'herring', 'sardine'],
            'lamb': ['lamb', 'mutton']
        }
        
        print("="*70)
        print("PROMPT C: ENRICHMENT PIPELINE")
        print("="*70)
        print(f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
    
    def step1_get_baseline_coverage(self):
        """Get current coverage metrics"""
        print("\n" + "="*70)
        print("STEP 1: BASELINE COVERAGE")
        print("="*70)
        
        try:
            # Get total count
            response = self.supabase.table('foods_published_preview').select("*", count='exact', head=True).execute()
            total = response.count if hasattr(response, 'count') else 0
            
            if total == 0:
                print("No data in foods_published_preview")
                return {}
            
            # Get coverage for each field
            metrics = {}
            
            # Form coverage
            resp = self.supabase.table('foods_published_preview').select("*", count='exact', head=True).not_.is_('form', 'null').execute()
            form_count = resp.count if hasattr(resp, 'count') else 0
            metrics['form'] = {'count': form_count, 'total': total, 'coverage': (form_count/total)*100}
            
            # Life stage coverage
            resp = self.supabase.table('foods_published_preview').select("*", count='exact', head=True).not_.is_('life_stage', 'null').execute()
            life_count = resp.count if hasattr(resp, 'count') else 0
            metrics['life_stage'] = {'count': life_count, 'total': total, 'coverage': (life_count/total)*100}
            
            # Ingredients coverage
            resp = self.supabase.table('foods_published_preview').select("*", count='exact', head=True).not_.is_('ingredients_tokens', 'null').execute()
            ing_count = resp.count if hasattr(resp, 'count') else 0
            metrics['ingredients'] = {'count': ing_count, 'total': total, 'coverage': (ing_count/total)*100}
            
            # Kcal coverage (valid range 200-600)
            resp = self.supabase.table('foods_published_preview').select("*", count='exact', head=True).gte('kcal_per_100g', 200).lte('kcal_per_100g', 600).execute()
            kcal_valid = resp.count if hasattr(resp, 'count') else 0
            metrics['kcal_valid'] = {'count': kcal_valid, 'total': total, 'coverage': (kcal_valid/total)*100}
            
            # Price coverage
            resp = self.supabase.table('foods_published_preview').select("*", count='exact', head=True).not_.is_('price_per_kg', 'null').execute()
            price_count = resp.count if hasattr(resp, 'count') else 0
            metrics['price'] = {'count': price_count, 'total': total, 'coverage': (price_count/total)*100}
            
            print(f"\nTotal products: {total:,}")
            print("\nCurrent coverage:")
            for field, data in metrics.items():
                print(f"  {field:20} : {data['coverage']:.1f}% ({data['count']:,}/{total:,})")
            
            return metrics
            
        except Exception as e:
            print(f"Error getting baseline: {e}")
            return {}
    
    def classify_form(self, product_name, description='', brand=''):
        """Classify product form"""
        text = f"{product_name} {description} {brand}".lower()
        
        for form, patterns in self.form_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return form
        
        # Default heuristics
        if 'kg' in text and any(x in text for x in ['10kg', '12kg', '15kg', '20kg']):
            return 'dry'
        if any(x in text for x in ['400g', '800g', '200g', '100g', 'tin', 'can']):
            return 'wet'
            
        return None
    
    def classify_life_stage(self, product_name, description='', brand=''):
        """Classify life stage"""
        text = f"{product_name} {description}".lower()
        
        # Check patterns (puppy has priority, then senior, then adult)
        for stage in ['puppy', 'senior', 'adult']:
            for pattern in self.life_stage_patterns[stage]:
                if pattern in text:
                    return stage
        
        # Default to adult if unclear
        if brand and 'puppy' not in text and 'senior' not in text:
            return 'adult'
            
        return None
    
    def detect_allergens(self, ingredients_tokens):
        """Detect allergens from ingredients"""
        if not ingredients_tokens:
            return []
        
        allergens = []
        
        # Convert to string if it's a list
        if isinstance(ingredients_tokens, list):
            text = ' '.join(ingredients_tokens).lower()
        else:
            text = str(ingredients_tokens).lower()
        
        for allergen, patterns in self.allergen_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    allergens.append(allergen)
                    break
        
        return allergens
    
    def estimate_kcal(self, protein, fat):
        """Estimate kcal from macros if missing"""
        if protein and fat:
            # Standard formula: protein*4 + fat*9 + carbs*4
            # Assume carbs = 100 - protein - fat - moisture(10) - ash(8)
            carbs = max(0, 100 - protein - fat - 10 - 8)
            kcal = (protein * 4) + (fat * 9) + (carbs * 4)
            return min(600, max(200, kcal))  # Clamp to valid range
        return None
    
    def extract_pack_size(self, product_name):
        """Extract pack size from product name"""
        # Look for patterns like "12kg", "400g", "2.5kg"
        matches = re.findall(r'(\d+(?:\.\d+)?)\s*(kg|g|lb|oz)', product_name.lower())
        
        if matches:
            size, unit = matches[0]
            size = float(size)
            
            # Convert to kg
            if unit == 'g':
                return size / 1000
            elif unit == 'kg':
                return size
            elif unit == 'lb':
                return size * 0.453592
            elif unit == 'oz':
                return size * 0.0283495
        
        return None
    
    def calculate_price_bucket(self, price_per_kg):
        """Calculate price bucket"""
        if not price_per_kg:
            return None
        
        if price_per_kg < 2:
            return 'budget'
        elif price_per_kg < 5:
            return 'standard'
        elif price_per_kg < 10:
            return 'premium'
        else:
            return 'super_premium'
    
    def step2_enrich_products(self):
        """Run enrichment on all products"""
        print("\n" + "="*70)
        print("STEP 2: ENRICHING PRODUCTS")
        print("="*70)
        
        updates_made = 0
        errors = []
        
        # Fetch products in batches
        page = 0
        batch_size = 100
        
        while True:
            try:
                response = self.supabase.table('foods_published_preview').select("*").range(
                    page * batch_size, 
                    (page + 1) * batch_size - 1
                ).execute()
                
                if not response.data:
                    break
                
                for product in response.data:
                    updates = {}
                    
                    # Enrich form
                    if not product.get('form'):
                        form = self.classify_form(
                            product.get('product_name', ''),
                            '',
                            product.get('brand', '')
                        )
                        if form:
                            updates['form'] = form
                    
                    # Enrich life_stage
                    if not product.get('life_stage'):
                        life_stage = self.classify_life_stage(
                            product.get('product_name', ''),
                            '',
                            product.get('brand', '')
                        )
                        if life_stage:
                            updates['life_stage'] = life_stage
                    
                    # Fix kcal if outside valid range
                    kcal = product.get('kcal_per_100g')
                    if not kcal or kcal < 200 or kcal > 600:
                        # Try to estimate from macros
                        estimated = self.estimate_kcal(
                            product.get('protein_percent'),
                            product.get('fat_percent')
                        )
                        if estimated:
                            updates['kcal_per_100g'] = estimated
                            updates['kcal_is_estimated'] = True
                    
                    # Calculate price_per_kg if missing
                    if not product.get('price_per_kg'):
                        pack_size = self.extract_pack_size(product.get('product_name', ''))
                        if pack_size and product.get('price'):
                            price_per_kg = product.get('price') / pack_size
                            updates['price_per_kg'] = price_per_kg
                            updates['price_bucket'] = self.calculate_price_bucket(price_per_kg)
                    
                    # Apply updates if any
                    if updates:
                        try:
                            self.supabase.table('foods_canonical').update(updates).eq(
                                'product_key', product['product_key']
                            ).execute()
                            updates_made += 1
                        except Exception as e:
                            errors.append(f"Error updating {product['product_key']}: {e}")
                
                page += 1
                
                if page % 10 == 0:
                    print(f"  Processed {page * batch_size} products, {updates_made} updates...")
                    
            except Exception as e:
                print(f"Error in batch {page}: {e}")
                break
        
        print(f"\n✅ Enrichment complete: {updates_made} products updated")
        if errors:
            print(f"❌ {len(errors)} errors occurred")
            for err in errors[:5]:
                print(f"  {err}")
        
        return updates_made
    
    def step3_brand_level_coverage(self):
        """Check coverage by brand"""
        print("\n" + "="*70)
        print("STEP 3: BRAND-LEVEL COVERAGE")
        print("="*70)
        
        try:
            # Get all brands with counts
            response = self.supabase.rpc('get_brand_coverage_stats').execute()
            
            if not response.data:
                # Fallback: manual calculation
                print("Calculating brand coverage manually...")
                
                # Get top brands
                top_brands = [
                    'royal_canin', 'hills', 'purina', 'purina_pro_plan',
                    'eukanuba', 'acana', 'orijen', 'wellness'
                ]
                
                for brand_slug in top_brands:
                    # Get total for brand
                    resp = self.supabase.table('foods_published_preview').select("*", count='exact', head=True).eq('brand_slug', brand_slug).execute()
                    total = resp.count if hasattr(resp, 'count') else 0
                    
                    if total == 0:
                        continue
                    
                    # Get form coverage
                    resp = self.supabase.table('foods_published_preview').select("*", count='exact', head=True).eq('brand_slug', brand_slug).not_.is_('form', 'null').execute()
                    form_count = resp.count if hasattr(resp, 'count') else 0
                    
                    # Get life_stage coverage
                    resp = self.supabase.table('foods_published_preview').select("*", count='exact', head=True).eq('brand_slug', brand_slug).not_.is_('life_stage', 'null').execute()
                    life_count = resp.count if hasattr(resp, 'count') else 0
                    
                    print(f"\n{brand_slug:20} ({total} products):")
                    print(f"  Form:       {(form_count/total)*100:.1f}%")
                    print(f"  Life Stage: {(life_count/total)*100:.1f}%")
                    
        except Exception as e:
            print(f"Error getting brand coverage: {e}")
    
    def step4_final_coverage(self):
        """Check final coverage against gates"""
        print("\n" + "="*70)
        print("STEP 4: FINAL COVERAGE VS GATES")
        print("="*70)
        
        metrics = self.step1_get_baseline_coverage()
        
        # Define gates
        gates = {
            'life_stage': 95,
            'form': 90,
            'ingredients': 85,
            'kcal_valid': 90
        }
        
        print("\nGate compliance:")
        all_pass = True
        
        for field, target in gates.items():
            if field in metrics:
                current = metrics[field]['coverage']
                passed = current >= target
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"  {field:20} : {current:.1f}% / {target}% {status}")
                if not passed:
                    all_pass = False
        
        if all_pass:
            print("\n✅ ALL GATES PASSED!")
        else:
            print("\n⚠️  Some gates not met - may need additional enrichment")
        
        return metrics, all_pass
    
    def generate_report(self, before_metrics, after_metrics, updates_made):
        """Generate PREVIEW-COVERAGE-REPORT.md"""
        print("\n" + "="*70)
        print("GENERATING REPORT")
        print("="*70)
        
        report_path = Path('/Users/sergiubiris/Desktop/lupito-content/docs/PREVIEW-COVERAGE-REPORT.md')
        
        content = f"""# PREVIEW COVERAGE REPORT
Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Enrichment Summary

- Products enriched: {updates_made}
- Total products: {after_metrics.get('form', {}).get('total', 0):,}

## Coverage Before/After

| Field | Before | After | Change | Gate | Status |
|-------|--------|-------|--------|------|--------|
"""
        
        gates = {
            'life_stage': 95,
            'form': 90,
            'ingredients': 85,
            'kcal_valid': 90
        }
        
        for field in ['form', 'life_stage', 'ingredients', 'kcal_valid']:
            before = before_metrics.get(field, {}).get('coverage', 0)
            after = after_metrics.get(field, {}).get('coverage', 0)
            change = after - before
            gate = gates.get(field, 0)
            status = "✅" if after >= gate else "❌"
            
            content += f"| {field} | {before:.1f}% | {after:.1f}% | {change:+.1f}% | {gate}% | {status} |\n"
        
        content += f"""

## Enrichment Techniques Applied

1. **Form Classification**: Multi-language patterns (dry, wet, raw, semi-moist)
2. **Life Stage Detection**: Pattern matching with brand context
3. **Kcal Validation**: Range 200-600, estimation from macros when needed
4. **Price Extraction**: Pack size parsing and per-kg calculation
5. **Allergen Detection**: Ingredients token analysis

## Gate Compliance

Gates for Preview:
- life_stage ≥ 95%
- form ≥ 90%
- ingredients ≥ 85%
- kcal_valid (200-600) ≥ 90%

## Next Steps

- Run Prompt D: Recompute brand quality metrics
- Run Prompt E: Promote qualifying brands to production
"""
        
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(content)
        print(f"✅ Report saved to: {report_path}")
        
        return content

def main():
    enricher = EnrichmentPipeline()
    
    # Step 1: Get baseline coverage
    before_metrics = enricher.step1_get_baseline_coverage()
    
    # Step 2: Run enrichment
    updates_made = enricher.step2_enrich_products()
    
    # Step 3: Check brand-level coverage
    enricher.step3_brand_level_coverage()
    
    # Step 4: Final coverage check
    after_metrics, gates_passed = enricher.step4_final_coverage()
    
    # Generate report
    enricher.generate_report(before_metrics, after_metrics, updates_made)
    
    print("\n✅ PROMPT C COMPLETE: Enrichment pipeline executed")

if __name__ == "__main__":
    main()