#!/usr/bin/env python3
"""
Detect size and pack variants in the database
Generates report for review before migration
"""

import os
import re
import json
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class VariantDetector:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.products = []
        self.variant_groups = []
        
        # Patterns for detection
        self.size_pattern = re.compile(r'\b\d+(?:\.\d+)?\s*(?:kg|g|lb|oz|ml|l)\b', re.IGNORECASE)
        self.pack_pattern = re.compile(r'\b\d+\s*x\s*\d+(?:\.\d+)?(?:\s*(?:kg|g|lb|oz|ml|l|cans?|pouches?|tins?|sachets?))?', re.IGNORECASE)
        
        # Patterns to preserve (not consider as variants)
        self.life_stage_pattern = re.compile(r'\b(?:puppy|junior|adult|senior|mature)\b', re.IGNORECASE)
        self.breed_size_pattern = re.compile(r'\b(?:small|medium|large|mini|maxi|giant|toy)\s*(?:breed|dog|size)?\b', re.IGNORECASE)
    
    def load_products(self):
        """Load all products from database"""
        print("📥 Loading products from database...")
        
        offset = 0
        batch_size = 1000
        
        while True:
            batch = self.supabase.table('foods_canonical').select(
                'product_key, brand, product_name, product_url, form, '
                'ingredients_raw, protein_percent, fat_percent, fiber_percent, '
                'ash_percent, moisture_percent'
            ).range(offset, offset + batch_size - 1).execute()
            
            if not batch.data:
                break
            
            self.products.extend(batch.data)
            offset += batch_size
            
            if offset % 5000 == 0:
                print(f"  Loaded {offset} products...")
        
        print(f"✅ Loaded {len(self.products)} products")
        return self.products
    
    def normalize_for_grouping(self, product_name: str) -> str:
        """
        Normalize product name by removing ONLY size and pack indicators
        Keep life stage and breed size information
        """
        if not product_name:
            return ""
        
        # Remove size indicators
        normalized = self.size_pattern.sub('', product_name)
        
        # Remove pack indicators
        normalized = self.pack_pattern.sub('', normalized)
        
        # Clean up extra spaces and punctuation
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'\s*[,\-]\s*$', '', normalized)
        normalized = normalized.strip()
        
        return normalized.lower()
    
    def extract_size_info(self, product_name: str) -> Dict:
        """Extract size and pack information from product name"""
        info = {
            'has_size': False,
            'has_pack': False,
            'size_value': None,
            'pack_value': None,
            'variant_type': None
        }
        
        # Check for size
        size_match = self.size_pattern.search(product_name)
        if size_match:
            info['has_size'] = True
            info['size_value'] = size_match.group(0)
            info['variant_type'] = 'size'
        
        # Check for pack
        pack_match = self.pack_pattern.search(product_name)
        if pack_match:
            info['has_pack'] = True
            info['pack_value'] = pack_match.group(0)
            info['variant_type'] = 'pack' if not info['variant_type'] else 'size_and_pack'
        
        return info
    
    def group_variants(self):
        """Group products by brand and normalized name"""
        print("\n🔍 Detecting variant groups...")
        
        groups = defaultdict(list)
        
        for product in self.products:
            brand = (product.get('brand') or '').strip()
            normalized_name = self.normalize_for_grouping(product.get('product_name', ''))
            
            if brand and normalized_name:
                # Add size/pack info to product
                size_info = self.extract_size_info(product.get('product_name', ''))
                product['_size_info'] = size_info
                
                key = f"{brand}|{normalized_name}"
                groups[key].append(product)
        
        # Filter to only groups with size/pack variants
        variant_groups = []
        
        for key, products in groups.items():
            if len(products) > 1:
                # Check if this group actually has size/pack differences
                has_size_variants = any(p['_size_info']['has_size'] for p in products)
                has_pack_variants = any(p['_size_info']['has_pack'] for p in products)
                
                if has_size_variants or has_pack_variants:
                    brand, base_name = key.split('|', 1)
                    
                    variant_groups.append({
                        'brand': brand,
                        'base_name': base_name,
                        'products': products,
                        'count': len(products),
                        'has_size_variants': has_size_variants,
                        'has_pack_variants': has_pack_variants
                    })
        
        # Sort by number of variants
        variant_groups.sort(key=lambda x: x['count'], reverse=True)
        
        self.variant_groups = variant_groups
        print(f"✅ Found {len(variant_groups)} variant groups")
        
        return variant_groups
    
    def select_parent_product(self, group: Dict) -> Dict:
        """Select the best product to be the parent"""
        products = group['products']
        
        # Scoring system for parent selection
        scores = []
        
        for product in products:
            score = 0
            
            # Prefer products with ingredients
            if product.get('ingredients_raw'):
                score += 10
            
            # Prefer products with complete nutrition
            if all(product.get(field) for field in 
                   ['protein_percent', 'fat_percent', 'fiber_percent']):
                score += 5
            
            # Prefer products without size/pack in name (more generic)
            if not product['_size_info']['has_size'] and not product['_size_info']['has_pack']:
                score += 3
            
            # Prefer products with simpler names (shorter)
            score -= len(product.get('product_name', '')) * 0.01
            
            scores.append((score, product))
        
        # Sort by score and return best
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[0][1]
    
    def analyze_data_consistency(self, group: Dict) -> Dict:
        """Analyze data consistency within a variant group"""
        products = group['products']
        
        analysis = {
            'ingredients_consistent': True,
            'nutrition_consistent': True,
            'unique_ingredients': 0,
            'unique_nutrition': 0,
            'products_with_ingredients': 0,
            'products_with_nutrition': 0
        }
        
        # Check ingredients
        ingredients_set = set()
        for p in products:
            if p.get('ingredients_raw'):
                analysis['products_with_ingredients'] += 1
                # Normalize for comparison (first 200 chars)
                normalized = (p['ingredients_raw'][:200].lower().strip())
                ingredients_set.add(normalized)
        
        analysis['unique_ingredients'] = len(ingredients_set)
        analysis['ingredients_consistent'] = len(ingredients_set) <= 1
        
        # Check nutrition
        nutrition_set = set()
        for p in products:
            nutrition = (
                p.get('protein_percent'),
                p.get('fat_percent'),
                p.get('fiber_percent')
            )
            if any(n is not None for n in nutrition):
                analysis['products_with_nutrition'] += 1
                nutrition_set.add(nutrition)
        
        analysis['unique_nutrition'] = len(nutrition_set)
        analysis['nutrition_consistent'] = len(nutrition_set) <= 1
        
        return analysis
    
    def generate_report(self):
        """Generate comprehensive report of variant groups"""
        print("\n📊 Generating variant report...")
        
        report = {
            'summary': {
                'total_products': len(self.products),
                'variant_groups': len(self.variant_groups),
                'products_to_migrate': sum(g['count'] - 1 for g in self.variant_groups),
                'products_after_migration': len(self.products) - sum(g['count'] - 1 for g in self.variant_groups)
            },
            'groups': []
        }
        
        for group in self.variant_groups:
            # Select parent
            parent = self.select_parent_product(group)
            
            # Analyze consistency
            consistency = self.analyze_data_consistency(group)
            
            group_report = {
                'brand': group['brand'],
                'base_name': group['base_name'],
                'variant_count': group['count'],
                'selected_parent': {
                    'product_key': parent['product_key'],
                    'product_name': parent['product_name'],
                    'has_ingredients': bool(parent.get('ingredients_raw')),
                    'has_nutrition': bool(parent.get('protein_percent'))
                },
                'data_consistency': consistency,
                'variants': []
            }
            
            # Add variant details
            for product in group['products']:
                variant_info = {
                    'product_key': product['product_key'],
                    'product_name': product['product_name'],
                    'size_info': product['_size_info'],
                    'has_ingredients': bool(product.get('ingredients_raw')),
                    'has_nutrition': bool(product.get('protein_percent')),
                    'is_parent': product['product_key'] == parent['product_key']
                }
                group_report['variants'].append(variant_info)
            
            report['groups'].append(group_report)
        
        return report
    
    def save_report(self, report: Dict):
        """Save report to files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON report
        json_file = f'data/variant_detection_report_{timestamp}.json'
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"  ✅ Saved JSON report to {json_file}")
        
        # Create CSV for easy review
        csv_data = []
        for group in report['groups']:
            for variant in group['variants']:
                csv_data.append({
                    'brand': group['brand'],
                    'base_name': group['base_name'],
                    'variant_count': group['variant_count'],
                    'product_key': variant['product_key'],
                    'product_name': variant['product_name'],
                    'is_parent': variant['is_parent'],
                    'has_size': variant['size_info']['has_size'],
                    'size_value': variant['size_info']['size_value'],
                    'has_pack': variant['size_info']['has_pack'],
                    'pack_value': variant['size_info']['pack_value'],
                    'has_ingredients': variant['has_ingredients'],
                    'has_nutrition': variant['has_nutrition'],
                    'ingredients_consistent': group['data_consistency']['ingredients_consistent'],
                    'nutrition_consistent': group['data_consistency']['nutrition_consistent']
                })
        
        df = pd.DataFrame(csv_data)
        csv_file = f'data/variant_detection_report_{timestamp}.csv'
        df.to_csv(csv_file, index=False)
        print(f"  ✅ Saved CSV report to {csv_file}")
        
        return json_file, csv_file
    
    def print_summary(self, report: Dict):
        """Print summary of findings"""
        print("\n" + "=" * 60)
        print("📋 VARIANT DETECTION SUMMARY")
        print("=" * 60)
        
        s = report['summary']
        print(f"Total products: {s['total_products']:,}")
        print(f"Variant groups found: {s['variant_groups']}")
        print(f"Products to migrate: {s['products_to_migrate']}")
        print(f"Products after migration: {s['products_after_migration']:,}")
        print(f"Reduction: {s['products_to_migrate']/s['total_products']*100:.1f}%")
        
        # Show top variant groups
        print("\n🔝 Top 10 Variant Groups:")
        for i, group in enumerate(report['groups'][:10], 1):
            print(f"\n{i}. {group['brand']}: {group['base_name'][:50]}")
            print(f"   {group['variant_count']} variants")
            print(f"   Parent: {group['selected_parent']['product_name'][:60]}")
            print(f"   Data: Ingredients={'✓' if group['selected_parent']['has_ingredients'] else '✗'}, "
                  f"Nutrition={'✓' if group['selected_parent']['has_nutrition'] else '✗'}")
            
            # Show consistency warnings
            if not group['data_consistency']['ingredients_consistent']:
                print(f"   ⚠️  Different ingredients across variants!")
            if not group['data_consistency']['nutrition_consistent']:
                print(f"   ⚠️  Different nutrition across variants!")
        
        # Show data preservation stats
        print("\n📊 Data Preservation:")
        groups_with_ingredients = sum(1 for g in report['groups'] 
                                     if any(v['has_ingredients'] for v in g['variants']))
        groups_with_nutrition = sum(1 for g in report['groups'] 
                                   if any(v['has_nutrition'] for v in g['variants']))
        
        print(f"  Groups with ingredients: {groups_with_ingredients}/{s['variant_groups']}")
        print(f"  Groups with nutrition: {groups_with_nutrition}/{s['variant_groups']}")
        
        # Warnings
        inconsistent_ingredients = sum(1 for g in report['groups'] 
                                      if not g['data_consistency']['ingredients_consistent'])
        inconsistent_nutrition = sum(1 for g in report['groups'] 
                                    if not g['data_consistency']['nutrition_consistent'])
        
        if inconsistent_ingredients > 0:
            print(f"\n⚠️  {inconsistent_ingredients} groups have inconsistent ingredients")
        if inconsistent_nutrition > 0:
            print(f"⚠️  {inconsistent_nutrition} groups have inconsistent nutrition")

def main():
    detector = VariantDetector()
    
    # Load and analyze
    detector.load_products()
    detector.group_variants()
    
    # Generate report
    report = detector.generate_report()
    
    # Save report
    json_file, csv_file = detector.save_report(report)
    
    # Print summary
    detector.print_summary(report)
    
    print("\n✅ Detection complete!")
    print(f"📄 Review the reports:")
    print(f"   - {csv_file} (for spreadsheet review)")
    print(f"   - {json_file} (detailed data)")

if __name__ == "__main__":
    main()