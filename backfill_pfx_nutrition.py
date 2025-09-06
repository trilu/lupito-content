#!/usr/bin/env python3
"""
Backfill nutrition data for existing PFX products
Fetches HTML and extracts nutrition for products missing this data
"""
import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

import requests
from supabase import create_client
from dotenv import load_dotenv

# Add path for imports
sys.path.append(str(Path(__file__).parent))
from etl.nutrition_parser import parse_nutrition_from_html

load_dotenv()

class PFXNutritionBackfill:
    def __init__(self):
        self.client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        self.stats = {
            'processed': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0,
            'nutrition_found': 0
        }
    
    def get_products_missing_nutrition(self, limit: Optional[int] = None):
        """Get PFX products missing nutrition data"""
        query = self.client.table('food_candidates')\
            .select('id, brand, product_name, source_url')\
            .eq('source_domain', 'petfoodexpert.com')\
            .is_('kcal_per_100g', 'null')
        
        if limit:
            query = query.limit(limit)
            
        result = query.execute()
        return result.data
    
    def fetch_and_extract_nutrition(self, url: str) -> Dict[str, Optional[float]]:
        """Fetch page and extract nutrition data"""
        try:
            # Rate limiting - be polite to PFX
            time.sleep(random.uniform(1.0, 2.0))
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Extract nutrition using our parser
            nutrition = parse_nutrition_from_html(response.text)
            return nutrition or {}
            
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            return {}
    
    def update_product_nutrition(self, product_id: str, nutrition: Dict) -> bool:
        """Update product with nutrition data"""
        try:
            update_data = {
                'protein_percent': nutrition.get('protein_percent'),
                'fat_percent': nutrition.get('fat_percent'),
                'fiber_percent': nutrition.get('fiber_percent'),
                'ash_percent': nutrition.get('ash_percent'),
                'moisture_percent': nutrition.get('moisture_percent'),
                'kcal_per_100g': nutrition.get('kcal_per_100g'),
                'kcal_basis': nutrition.get('kcal_basis'),
                'last_seen_at': datetime.now().isoformat()
            }
            
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            if not update_data or len(update_data) <= 1:  # Only last_seen_at
                return False
                
            result = self.client.table('food_candidates')\
                .update(update_data)\
                .eq('id', product_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            print(f"❌ Database update error: {e}")
            return False
    
    def backfill_nutrition(self, limit: Optional[int] = None):
        """Backfill nutrition for all missing products"""
        print("🔍 Finding products missing nutrition data...")
        products = self.get_products_missing_nutrition(limit)
        
        if not products:
            print("✅ No products missing nutrition data")
            return
            
        total = len(products)
        print(f"📊 Found {total} products missing nutrition data")
        print(f"🚀 Starting backfill process...")
        print()
        
        for i, product in enumerate(products, 1):
            print(f"[{i}/{total}] Processing: {product['brand']} {product['product_name']}")
            self.stats['processed'] += 1
            
            # Extract nutrition from HTML
            nutrition = self.fetch_and_extract_nutrition(product['source_url'])
            
            if nutrition:
                self.stats['nutrition_found'] += 1
                # Update database
                if self.update_product_nutrition(product['id'], nutrition):
                    self.stats['updated'] += 1
                    print(f"  ✅ Updated with: kcal={nutrition.get('kcal_per_100g')}, protein={nutrition.get('protein_percent')}%, fat={nutrition.get('fat_percent')}%")
                else:
                    self.stats['errors'] += 1
                    print(f"  ❌ Database update failed")
            else:
                self.stats['skipped'] += 1
                print(f"  ⚠️  No nutrition data found")
            
            # Progress update every 5 items
            if i % 5 == 0:
                self.print_progress()
                
        self.print_final_stats()
    
    def print_progress(self):
        """Print current progress"""
        print(f"  📈 Progress: {self.stats['processed']} processed, {self.stats['updated']} updated, {self.stats['errors']} errors")
        print()
    
    def print_final_stats(self):
        """Print final statistics"""
        print("\n" + "="*60)
        print("PFX NUTRITION BACKFILL REPORT")
        print("="*60)
        print(f"Processed:        {self.stats['processed']}")
        print(f"Updated:          {self.stats['updated']}")
        print(f"Nutrition found:  {self.stats['nutrition_found']}")
        print(f"Skipped (no data):{self.stats['skipped']}")
        print(f"Errors:           {self.stats['errors']}")
        
        if self.stats['processed'] > 0:
            success_rate = (self.stats['updated'] / self.stats['processed']) * 100
            print(f"Success rate:     {success_rate:.1f}%")
        
        print("="*60)
        
        # Show updated nutrition coverage
        self.show_nutrition_coverage()
    
    def show_nutrition_coverage(self):
        """Show updated nutrition coverage statistics"""
        try:
            total_result = self.client.table('food_candidates')\
                .select('*', count='exact')\
                .eq('source_domain', 'petfoodexpert.com')\
                .execute()
            total = total_result.count
            
            kcal_result = self.client.table('food_candidates')\
                .select('*', count='exact')\
                .eq('source_domain', 'petfoodexpert.com')\
                .not_.is_('kcal_per_100g', 'null')\
                .execute()
            with_kcal = kcal_result.count
            
            protein_result = self.client.table('food_candidates')\
                .select('*', count='exact')\
                .eq('source_domain', 'petfoodexpert.com')\
                .not_.is_('protein_percent', 'null')\
                .execute()
            with_protein = protein_result.count
            
            print("\n📊 UPDATED NUTRITION COVERAGE:")
            print(f"Total PFX products: {total}")
            print(f"With kcal:          {with_kcal} ({with_kcal/total*100:.1f}%)")
            print(f"With protein:       {with_protein} ({with_protein/total*100:.1f}%)")
            
        except Exception as e:
            print(f"❌ Error checking coverage: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Backfill PFX nutrition data')
    parser.add_argument('--limit', type=int, help='Limit number of products to process')
    
    args = parser.parse_args()
    
    backfiller = PFXNutritionBackfill()
    backfiller.backfill_nutrition(limit=args.limit)

if __name__ == '__main__':
    main()