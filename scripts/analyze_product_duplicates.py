#!/usr/bin/env python3
"""
Analyze database for duplicate products, variants, and similar entries
Identify patterns causing duplication
"""

import os
import re
from collections import defaultdict, Counter
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
from difflib import SequenceMatcher

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class DuplicateAnalyzer:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.products = []
        self.duplicates = defaultdict(list)
        
    def load_all_products(self):
        """Load all products from database"""
        print("📥 Loading all products from database...")
        
        # Load in batches
        batch_size = 1000
        offset = 0
        
        while True:
            batch = self.supabase.table('foods_canonical').select(
                'product_key, brand, product_name, product_url, form, ingredients_raw'
            ).range(offset, offset + batch_size - 1).execute()
            
            if not batch.data:
                break
                
            self.products.extend(batch.data)
            offset += batch_size
            print(f"  Loaded {len(self.products)} products...")
            
        print(f"✅ Loaded {len(self.products)} total products")
        return self.products
    
    def normalize_product_name(self, name: str) -> str:
        """Normalize product name for comparison"""
        if not name:
            return ""
        
        # Remove size/weight indicators
        name = re.sub(r'\b\d+\s*(?:kg|g|lb|oz|ml|l)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b\d+\s*x\s*\d+\s*(?:kg|g|lb|oz|ml|l)\b', '', name, flags=re.IGNORECASE)
        
        # Remove pack sizes
        name = re.sub(r'\b(?:pack of |saver pack|trial pack|mixed pack|variety pack)\s*\d*\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b\d+\s*(?:pack|cans?|pouches?|trays?)\b', '', name, flags=re.IGNORECASE)
        
        # Remove common suffixes
        name = re.sub(r'\b(?:adult|puppy|junior|senior|small|medium|large|mini|maxi)\b', '', name, flags=re.IGNORECASE)
        
        # Clean up
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip().lower()
    
    def extract_base_url(self, url: str) -> str:
        """Extract base URL without variant parameters"""
        if not url:
            return ""
        
        # Remove activeVariant parameter
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]
        
        # Remove trailing numbers that might be variant IDs
        url = re.sub(r'/\d{6,}$', '', url)
        
        return url.rstrip('/')
    
    def find_exact_duplicates(self):
        """Find products with identical product keys"""
        print("\n🔍 Finding exact duplicates (same product_key)...")
        
        key_counts = Counter(p['product_key'] for p in self.products)
        
        exact_dupes = {k: v for k, v in key_counts.items() if v > 1}
        
        if exact_dupes:
            print(f"  Found {len(exact_dupes)} product keys with duplicates:")
            for key, count in sorted(exact_dupes.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"    {key}: {count} copies")
        else:
            print("  No exact duplicates found")
        
        return exact_dupes
    
    def find_url_variants(self):
        """Find products that are variants based on URL patterns"""
        print("\n🔍 Finding URL variants...")
        
        url_groups = defaultdict(list)
        
        for product in self.products:
            if product.get('product_url'):
                base_url = self.extract_base_url(product['product_url'])
                url_groups[base_url].append(product)
        
        # Find groups with multiple products
        variant_groups = {url: products for url, products in url_groups.items() 
                         if len(products) > 1 and url}
        
        print(f"  Found {len(variant_groups)} base URLs with multiple variants")
        
        # Show examples
        examples = sorted(variant_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        for base_url, variants in examples:
            print(f"\n  Base URL: {base_url.split('/')[-1] if '/' in base_url else base_url}")
            print(f"    {len(variants)} variants:")
            for v in variants[:3]:
                print(f"      - {v['product_name'][:60]}")
        
        return variant_groups
    
    def find_name_duplicates(self):
        """Find products with very similar names"""
        print("\n🔍 Finding products with similar names...")
        
        # Group by brand first
        brand_products = defaultdict(list)
        for product in self.products:
            if product.get('brand'):
                brand_products[product['brand']].append(product)
        
        similar_groups = []
        
        for brand, products in brand_products.items():
            if len(products) < 2:
                continue
            
            # Normalize names
            for p in products:
                p['normalized_name'] = self.normalize_product_name(p.get('product_name', ''))
            
            # Group by normalized name
            name_groups = defaultdict(list)
            for p in products:
                if p['normalized_name']:
                    name_groups[p['normalized_name']].append(p)
            
            # Find groups with multiple products
            for norm_name, group in name_groups.items():
                if len(group) > 1:
                    similar_groups.append({
                        'brand': brand,
                        'normalized_name': norm_name,
                        'products': group
                    })
        
        print(f"  Found {len(similar_groups)} groups of similar products")
        
        # Show examples
        examples = sorted(similar_groups, key=lambda x: len(x['products']), reverse=True)[:5]
        for group in examples:
            print(f"\n  Brand: {group['brand']}")
            print(f"  Base name: {group['normalized_name']}")
            print(f"  {len(group['products'])} similar products:")
            for p in group['products'][:3]:
                print(f"    - {p['product_name'][:60]}")
        
        return similar_groups
    
    def find_ingredient_duplicates(self):
        """Find products with identical ingredients but different names"""
        print("\n🔍 Finding products with identical ingredients...")
        
        # Group products by brand and ingredients
        ingredient_groups = defaultdict(list)
        
        for product in self.products:
            if product.get('brand') and product.get('ingredients_raw'):
                # Clean ingredients for comparison
                ingredients = product['ingredients_raw'][:500].lower()
                ingredients = re.sub(r'\s+', ' ', ingredients)
                
                key = f"{product['brand']}|{ingredients}"
                ingredient_groups[key].append(product)
        
        # Find groups with multiple products
        duplicate_ingredients = {k: v for k, v in ingredient_groups.items() 
                                if len(v) > 1}
        
        print(f"  Found {len(duplicate_ingredients)} groups with identical ingredients")
        
        # Show examples
        examples = sorted(duplicate_ingredients.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        for key, products in examples:
            brand = products[0]['brand']
            print(f"\n  Brand: {brand}")
            print(f"  {len(products)} products with same ingredients:")
            for p in products[:3]:
                print(f"    - {p['product_name'][:60]}")
            print(f"  Ingredients: {products[0]['ingredients_raw'][:100]}...")
        
        return duplicate_ingredients
    
    def analyze_patterns(self):
        """Analyze patterns in duplicates"""
        print("\n📊 DUPLICATION PATTERNS ANALYSIS")
        print("=" * 60)
        
        # Check for size variants
        size_pattern = re.compile(r'\b(\d+(?:\.\d+)?)\s*(kg|g|lb|oz|ml|l)\b', re.IGNORECASE)
        pack_pattern = re.compile(r'\b(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*(kg|g|lb|oz|ml|l|cans?|pouches?)\b', re.IGNORECASE)
        
        products_with_sizes = 0
        products_with_packs = 0
        
        for product in self.products:
            name = product.get('product_name', '')
            if size_pattern.search(name):
                products_with_sizes += 1
            if pack_pattern.search(name):
                products_with_packs += 1
        
        print(f"Products with size indicators: {products_with_sizes} ({products_with_sizes/len(self.products)*100:.1f}%)")
        print(f"Products with pack indicators: {products_with_packs} ({products_with_packs/len(self.products)*100:.1f}%)")
        
        # Check for life stage variants
        life_stages = ['puppy', 'junior', 'adult', 'senior', 'mature']
        life_stage_products = sum(1 for p in self.products 
                                 if any(stage in p.get('product_name', '').lower() 
                                       for stage in life_stages))
        
        print(f"Products with life stage: {life_stage_products} ({life_stage_products/len(self.products)*100:.1f}%)")
        
        # Check for breed size variants
        breed_sizes = ['small', 'medium', 'large', 'mini', 'maxi', 'giant']
        breed_size_products = sum(1 for p in self.products 
                                 if any(size in p.get('product_name', '').lower() 
                                       for size in breed_sizes))
        
        print(f"Products with breed size: {breed_size_products} ({breed_size_products/len(self.products)*100:.1f}%)")
        
    def estimate_true_unique_products(self):
        """Estimate the actual number of unique products"""
        print("\n🎯 ESTIMATING TRUE UNIQUE PRODUCTS")
        print("=" * 60)
        
        # Create unique groups based on brand + normalized name
        unique_groups = set()
        
        for product in self.products:
            brand = product.get('brand') or ''
            brand = brand.lower() if brand else ''
            norm_name = self.normalize_product_name(product.get('product_name', ''))
            
            if brand and norm_name:
                unique_groups.add(f"{brand}|{norm_name}")
        
        print(f"Total products in database: {len(self.products)}")
        print(f"Estimated unique products: {len(unique_groups)}")
        print(f"Estimated duplicates/variants: {len(self.products) - len(unique_groups)}")
        print(f"Duplication rate: {(1 - len(unique_groups)/len(self.products))*100:.1f}%")
        
        return len(unique_groups)
    
    def generate_report(self):
        """Generate comprehensive duplication report"""
        print("\n" + "=" * 60)
        print("📋 DUPLICATE ANALYSIS REPORT")
        print("=" * 60)
        
        # Load data
        self.load_all_products()
        
        # Run analyses
        exact_dupes = self.find_exact_duplicates()
        url_variants = self.find_url_variants()
        name_dupes = self.find_name_duplicates()
        ingredient_dupes = self.find_ingredient_duplicates()
        
        # Analyze patterns
        self.analyze_patterns()
        
        # Estimate unique products
        unique_estimate = self.estimate_true_unique_products()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        
        print(f"Total products analyzed: {len(self.products)}")
        print(f"Exact duplicates (same key): {sum(v-1 for v in exact_dupes.values())} extra copies")
        print(f"URL variant groups: {len(url_variants)}")
        print(f"Similar name groups: {len(name_dupes)}")
        print(f"Identical ingredient groups: {len(ingredient_dupes)}")
        print(f"\nEstimated true unique products: ~{unique_estimate}")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("=" * 60)
        print("1. Implement variant detection during import")
        print("2. Use base product concept with size/pack variants")
        print("3. Normalize product names before creating keys")
        print("4. Check for existing products with same ingredients")
        print("5. Consider creating a 'product_variants' table")
        
        return {
            'total_products': len(self.products),
            'exact_duplicates': exact_dupes,
            'url_variants': len(url_variants),
            'name_duplicates': len(name_dupes),
            'ingredient_duplicates': len(ingredient_dupes),
            'estimated_unique': unique_estimate
        }

def main():
    analyzer = DuplicateAnalyzer()
    results = analyzer.generate_report()
    
    # Save detailed results
    print("\n💾 Saving detailed analysis...")
    
    # Create a summary CSV
    import pandas as pd
    
    # Get some examples for CSV
    examples = []
    for product in analyzer.products[:100]:
        examples.append({
            'product_key': product['product_key'],
            'brand': product['brand'],
            'product_name': product['product_name'],
            'normalized_name': analyzer.normalize_product_name(product.get('product_name', '')),
            'has_size': bool(re.search(r'\b\d+\s*(?:kg|g|lb|oz|ml|l)\b', product.get('product_name', ''), re.IGNORECASE)),
            'has_pack': bool(re.search(r'\b\d+\s*x\s*\d+', product.get('product_name', ''), re.IGNORECASE)),
            'url': product.get('product_url', '')
        })
    
    df = pd.DataFrame(examples)
    df.to_csv('data/duplicate_analysis_sample.csv', index=False)
    print("  Saved sample to data/duplicate_analysis_sample.csv")

if __name__ == "__main__":
    main()