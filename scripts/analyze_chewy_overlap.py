#!/usr/bin/env python3
"""
Analyze Chewy dataset for overlap with current database
"""

import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class ChewyAnalyzer:
    def __init__(self, chewy_file: str):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.chewy_file = chewy_file
        self.chewy_data = []
        self.db_products = {}
        
    def load_chewy_data(self):
        """Load Chewy dataset"""
        print("📂 Loading Chewy dataset...")
        with open(self.chewy_file, 'r', encoding='utf-8') as f:
            self.chewy_data = json.load(f)
        print(f"  ✅ Loaded {len(self.chewy_data)} Chewy products")
        
    def load_database_products(self):
        """Load current database products"""
        print("\n📊 Loading current database...")
        
        all_products = []
        offset = 0
        batch_size = 1000
        
        while True:
            batch = self.supabase.table('foods_canonical').select(
                'product_key, brand, product_name, ingredients_raw, '
                'protein_percent, fat_percent, fiber_percent, '
                'ash_percent, moisture_percent, product_url'
            ).range(offset, offset + batch_size - 1).execute()
            
            if not batch.data:
                break
                
            all_products.extend(batch.data)
            offset += batch_size
            
            if offset % 5000 == 0:
                print(f"  Loaded {offset} products...")
        
        # Index by normalized brand and product name
        for product in all_products:
            brand = self.normalize_brand(product.get('brand', ''))
            name = self.normalize_product_name(product.get('product_name', ''))
            key = f"{brand}|{name}"
            self.db_products[key] = product
        
        print(f"  ✅ Loaded {len(all_products)} database products")
        print(f"  ✅ Created {len(self.db_products)} unique product keys")
        
    def normalize_brand(self, brand: str) -> str:
        """Normalize brand name for comparison"""
        if not brand:
            return ''
        
        # Clean and lowercase
        brand = brand.lower().strip()
        brand = re.sub(r'[^a-z0-9\s]', '', brand)
        brand = re.sub(r'\s+', ' ', brand).strip()
        
        # Extract core brand name (before sub-brands)
        # This helps match "Purina Dog Chow" with "Purina Pro Plan"
        core_brands = {
            'purina': ['purina dog chow', 'purina pro plan', 'purina one', 'purina beyond'],
            'hills': ['hills science diet', 'hills science plan', 'hills prescription diet'],
            'royal canin': ['royal canin veterinary diet', 'royal canin breed', 'royal canin size'],
            'wellness': ['wellness core', 'wellness complete'],
            'blue': ['blue buffalo', 'blue wilderness'],
            'stella and chewys': ['stella chewys', 'stella & chewys'],
            'taste of the wild': ['taste of the wild', 'tasteofthewild']
        }
        
        for core, variants in core_brands.items():
            for variant in variants:
                if variant in brand:
                    return core
        
        return brand
    
    def normalize_product_name(self, name: str) -> str:
        """Normalize product name for comparison"""
        if not name:
            return ''
        
        # Remove size/pack variations
        name = re.sub(r'\b\d+(?:\.\d+)?\s*(?:oz|lb|kg|g|ml|l|pound|ounce)s?\b', '', name, flags=re.I)
        name = re.sub(r'\b\d+\s*(?:count|pack|ct|pk)\b', '', name, flags=re.I)
        name = re.sub(r'\b\d+\s*x\s*\d+(?:\.\d+)?', '', name, flags=re.I)
        
        # Clean up
        name = name.lower().strip()
        name = re.sub(r'[^a-z0-9\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Remove common suffixes
        name = re.sub(r'\s+(dog food|cat food|food|topper|mixer|treats?)$', '', name, flags=re.I)
        
        return name
    
    def extract_chewy_brand(self, product: Dict) -> str:
        """Extract brand from Chewy product"""
        if 'brand' in product and 'slogan' in product['brand']:
            return product['brand']['slogan']
        return ''
    
    def extract_ingredients(self, description: str) -> str:
        """Try to extract ingredients from description"""
        # Look for common ingredient patterns
        patterns = [
            r'ingredients?:([^.]+)',
            r'made with ([^.]+)',
            r'contains? ([^.]+)',
            r'crafted with ([^.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.I)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def analyze_overlap(self) -> Dict:
        """Analyze overlap between Chewy and database"""
        print("\n🔍 ANALYZING OVERLAP")
        print("=" * 60)
        
        results = {
            'exact_matches': [],
            'brand_matches': defaultdict(list),
            'potential_improvements': [],
            'new_products': [],
            'new_brands': set(),
            'statistics': {}
        }
        
        chewy_brands = set()
        db_brands = set()
        
        # Extract unique brands from database
        for key in self.db_products:
            brand = key.split('|')[0]
            if brand:
                db_brands.add(brand)
        
        # Process each Chewy product
        for chewy_product in self.chewy_data:
            brand = self.normalize_brand(self.extract_chewy_brand(chewy_product))
            name = self.normalize_product_name(chewy_product.get('name', ''))
            
            if brand:
                chewy_brands.add(brand)
            
            # Check for exact match
            key = f"{brand}|{name}"
            if key in self.db_products:
                db_product = self.db_products[key]
                
                # Check if Chewy could improve this product
                if not db_product.get('ingredients_raw'):
                    # Try to extract ingredients from Chewy description
                    chewy_ingredients = self.extract_ingredients(
                        chewy_product.get('description', '')
                    )
                    if chewy_ingredients:
                        results['potential_improvements'].append({
                            'db_product': db_product['product_name'],
                            'db_brand': db_product.get('brand'),
                            'chewy_url': chewy_product.get('url'),
                            'missing': 'ingredients',
                            'chewy_has': True
                        })
                
                if not db_product.get('protein_percent'):
                    # Check if Chewy description mentions nutrition
                    if 'protein' in chewy_product.get('description', '').lower():
                        results['potential_improvements'].append({
                            'db_product': db_product['product_name'],
                            'db_brand': db_product.get('brand'),
                            'chewy_url': chewy_product.get('url'),
                            'missing': 'nutrition',
                            'chewy_might_have': True
                        })
                
                results['exact_matches'].append({
                    'brand': brand,
                    'product': name,
                    'db_key': db_product['product_key'],
                    'chewy_url': chewy_product.get('url')
                })
            else:
                # Check if brand exists but product is new
                brand_exists = False
                for db_key in self.db_products:
                    if db_key.startswith(f"{brand}|"):
                        brand_exists = True
                        results['brand_matches'][brand].append({
                            'chewy_product': chewy_product.get('name'),
                            'chewy_url': chewy_product.get('url')
                        })
                        break
                
                if not brand_exists and brand:
                    # Completely new brand
                    results['new_brands'].add(brand)
                    results['new_products'].append({
                        'brand': brand,
                        'product': chewy_product.get('name'),
                        'url': chewy_product.get('url'),
                        'price': chewy_product.get('offers', {}).get('price')
                    })
                elif not brand_exists:
                    # Product without clear brand
                    results['new_products'].append({
                        'brand': 'Unknown',
                        'product': chewy_product.get('name'),
                        'url': chewy_product.get('url'),
                        'price': chewy_product.get('offers', {}).get('price')
                    })
        
        # Calculate statistics
        results['statistics'] = {
            'total_chewy_products': len(self.chewy_data),
            'total_db_products': len(self.db_products),
            'exact_matches': len(results['exact_matches']),
            'brands_with_new_products': len(results['brand_matches']),
            'potential_improvements': len(results['potential_improvements']),
            'completely_new_products': len(results['new_products']),
            'new_brands': len(results['new_brands']),
            'chewy_brands': len(chewy_brands),
            'db_brands': len(db_brands),
            'common_brands': len(chewy_brands.intersection(db_brands))
        }
        
        return results
    
    def print_analysis(self, results: Dict):
        """Print analysis results"""
        stats = results['statistics']
        
        print("\n" + "=" * 60)
        print("📊 ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"\n📦 Dataset Sizes:")
        print(f"  Chewy products: {stats['total_chewy_products']:,}")
        print(f"  Database products: {stats['total_db_products']:,}")
        
        print(f"\n🔗 Overlap Statistics:")
        print(f"  Exact matches: {stats['exact_matches']:,} ({stats['exact_matches']/stats['total_chewy_products']*100:.1f}%)")
        print(f"  Products that could be improved: {stats['potential_improvements']:,}")
        print(f"  Brands with new products: {stats['brands_with_new_products']:,}")
        print(f"  Completely new products: {stats['completely_new_products']:,}")
        
        print(f"\n🏷️ Brand Analysis:")
        print(f"  Chewy brands: {stats['chewy_brands']:,}")
        print(f"  Database brands: {stats['db_brands']:,}")
        print(f"  Common brands: {stats['common_brands']:,}")
        print(f"  New brands in Chewy: {stats['new_brands']:,}")
        
        if results['new_brands']:
            print(f"\n🆕 Top New Brands:")
            for i, brand in enumerate(sorted(list(results['new_brands']))[:10], 1):
                print(f"  {i}. {brand.title()}")
        
        if results['potential_improvements']:
            print(f"\n📈 Sample Products That Could Be Improved:")
            for i, improvement in enumerate(results['potential_improvements'][:5], 1):
                print(f"  {i}. {improvement['db_brand']} - {improvement['db_product'][:50]}")
                print(f"     Missing: {improvement['missing']}")
                print(f"     Chewy URL: {improvement['chewy_url'][:60]}...")
        
        if results['brand_matches']:
            print(f"\n🔄 Brands With New Products (Top 5):")
            sorted_brands = sorted(results['brand_matches'].items(), 
                                 key=lambda x: len(x[1]), reverse=True)[:5]
            for brand, products in sorted_brands:
                print(f"  {brand.title()}: {len(products)} new products")
                for product in products[:2]:  # Show first 2 products
                    print(f"    - {product['chewy_product'][:60]}")
        
        print(f"\n💡 Key Insights:")
        overlap_rate = stats['exact_matches'] / stats['total_chewy_products'] * 100
        if overlap_rate < 10:
            print(f"  • Low overlap ({overlap_rate:.1f}%) - Chewy has many unique products")
        elif overlap_rate < 30:
            print(f"  • Moderate overlap ({overlap_rate:.1f}%) - Good expansion opportunity")
        else:
            print(f"  • High overlap ({overlap_rate:.1f}%) - Databases share many products")
        
        if stats['potential_improvements'] > 100:
            print(f"  • {stats['potential_improvements']} products could be enriched with Chewy data")
        
        if stats['new_brands'] > 10:
            print(f"  • {stats['new_brands']} completely new brands available from Chewy")
        
        improvement_rate = stats['potential_improvements'] / stats['exact_matches'] * 100 if stats['exact_matches'] > 0 else 0
        if improvement_rate > 20:
            print(f"  • {improvement_rate:.1f}% of matching products lack data we might get from Chewy")
    
    def save_report(self, results: Dict):
        """Save detailed report to file"""
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"data/chewy_analysis_{timestamp}.json"
        
        # Prepare report data
        report = {
            'timestamp': timestamp,
            'statistics': results['statistics'],
            'new_brands': list(results['new_brands']),
            'exact_matches': results['exact_matches'][:100],  # First 100
            'potential_improvements': results['potential_improvements'][:100],
            'new_products_sample': results['new_products'][:100],
            'brands_with_new_products': {
                brand: len(products) 
                for brand, products in results['brand_matches'].items()
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Also save CSV for easy viewing
        csv_file = f"data/chewy_new_products_{timestamp}.csv"
        if results['new_products']:
            df = pd.DataFrame(results['new_products'])
            df.to_csv(csv_file, index=False)
            print(f"📄 New products CSV saved to: {csv_file}")
    
    def run_analysis(self):
        """Run complete analysis"""
        print("🚀 CHEWY DATASET ANALYSIS")
        print("=" * 60)
        
        # Load data
        self.load_chewy_data()
        self.load_database_products()
        
        # Analyze
        results = self.analyze_overlap()
        
        # Print results
        self.print_analysis(results)
        
        # Save report
        self.save_report(results)
        
        return results

def main():
    analyzer = ChewyAnalyzer('data/chewy/chewy-dataset.json')
    analyzer.run_analysis()

if __name__ == "__main__":
    main()