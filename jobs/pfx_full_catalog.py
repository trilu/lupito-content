#!/usr/bin/env python3
"""
PetFoodExpert Full Catalog Scraper
Uses API pagination to discover and harvest all ~3,804 products with complete nutrition data
"""
import os
import sys
import json
import time
import random
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import yaml
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from etl.normalize_foods import (
    parse_energy, parse_percent, parse_pack_size,
    tokenize_ingredients, check_contains_chicken,
    parse_price, normalize_currency, generate_fingerprint,
    normalize_form, normalize_life_stage, extract_gtin, clean_text,
    estimate_kcal_from_analytical, contains, derive_form, derive_life_stage
)
from etl.json_path import (
    resolve_path, resolve_multiple, extract_all, extract_values,
    safe_float, safe_bool
)
from etl.nutrition_parser import parse_nutrition_from_html

# Load environment variables
load_dotenv()

class PFXFullCatalogScraper:
    def __init__(self):
        """Initialize the full catalog scraper"""
        self.session = self._setup_session()
        self.supabase = self._setup_supabase()
        
        # Load configuration
        self.config = {
            'api_base': 'https://petfoodexpert.com/api/products',
            'rate_limit_seconds': 1.5,  # Be respectful
            'timeout': 30,
            'batch_size': 50  # Process in batches for better monitoring
        }
        
        self.stats = {
            'api_pages_fetched': 0,
            'products_discovered': 0,
            'products_processed': 0,
            'products_new': 0,
            'products_updated': 0,
            'products_skipped': 0,
            'nutrition_extracted': 0,
            'errors': 0
        }

    def _setup_session(self) -> requests.Session:
        """Setup requests session with headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0)',
            'Accept': 'application/json',
            'Referer': 'https://petfoodexpert.com/',
            'Origin': 'https://petfoodexpert.com'
        })
        return session

    def _setup_supabase(self) -> Client:
        """Setup Supabase client"""
        return create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )

    def _rate_limit(self):
        """Apply rate limiting"""
        time.sleep(self.config['rate_limit_seconds'] + random.uniform(-0.2, 0.2))

    def discover_all_products(self) -> List[Dict[str, Any]]:
        """Discover all products using API pagination"""
        print("🔍 Discovering all products via API pagination...")
        
        all_products = []
        page = 1
        
        while True:
            try:
                self._rate_limit()
                
                # Fetch page
                url = f"{self.config['api_base']}?species=dog&page={page}"
                print(f"  📄 Fetching page {page}...")
                
                response = self.session.get(url, timeout=self.config['timeout'])
                response.raise_for_status()
                
                data = response.json()
                products = data.get('data', [])
                
                all_products.extend(products)
                self.stats['api_pages_fetched'] += 1
                
                # No pagination metadata in API response - continue until empty
                print(f"  📊 Page {page}, Found {len(products)} products, Total discovered: {len(all_products)}")
                
                # Break if no products found (reached end)
                if not products:
                    print(f"  ✅ No products found on page {page}, stopping")
                    break
                    
                page += 1
                
                # Safety limit to prevent infinite loops  
                if page > 250:
                    print("  ⚠️  Safety limit reached at page 250")
                    break
                    
            except Exception as e:
                print(f"  ❌ Error fetching page {page}: {e}")
                self.stats['errors'] += 1
                if page == 1:
                    raise  # Critical error on first page
                break
        
        self.stats['products_discovered'] = len(all_products)
        print(f"🎯 Discovery complete: {len(all_products)} products found across {self.stats['api_pages_fetched']} pages")
        return all_products

    def extract_nutrition_from_html(self, url: str) -> Dict[str, Any]:
        """Extract nutrition data from product HTML page"""
        try:
            self._rate_limit()
            
            response = self.session.get(url, timeout=self.config['timeout'])
            response.raise_for_status()
            
            # Extract using our robust parser
            nutrition = parse_nutrition_from_html(response.text)
            return nutrition or {}
            
        except Exception as e:
            print(f"    ❌ Error extracting nutrition from {url}: {e}")
            return {}

    def process_product(self, product_data: Dict[str, Any]) -> bool:
        """Process a single product from API data"""
        try:
            # Extract basic info from API
            name = product_data.get('name', '')
            brand_data = product_data.get('brand', {})
            brand = brand_data.get('name', '') if brand_data else ''
            url = product_data.get('url', '')
            slug = product_data.get('slug', '')
            
            if not all([name, brand, url]):
                print(f"    ⚠️  Missing required data for product {name}")
                return False
            
            print(f"  📦 Processing: {brand} {name}")
            
            # Extract food data
            food_data = product_data.get('food', {})
            ingredients = food_data.get('ingredients', '')
            form_raw = food_data.get('moisture_level', '')  # 'Dry' or 'Wet'
            form = normalize_form(form_raw.lower() if form_raw else '')
            
            # Extract life stage
            animal_data = product_data.get('animal', {})
            life_stage_data = animal_data.get('life_stage', {})
            life_stage_string = life_stage_data.get('string', '') if life_stage_data else ''
            life_stage = normalize_life_stage(life_stage_string)
            
            # Extract pack sizes and pricing
            variations = product_data.get('variations', [])
            pack_sizes = []
            price_gbp = None
            
            for variation in variations:
                weight_label = variation.get('weight_label', '')
                price = variation.get('variation_price')
                
                if weight_label:
                    pack_sizes.append(weight_label)
                
                if price and not price_gbp:  # Use first price found
                    price_gbp = price
            
            # Convert price to EUR
            price_eur = None
            if price_gbp:
                price_eur = round(price_gbp * 1.17, 2)  # GBP to EUR conversion
            
            # Build base product data
            candidate_data = {
                'source_domain': 'petfoodexpert.com',
                'source_url': url,
                'brand': clean_text(brand),
                'product_name': clean_text(name),
                'form': form,
                'life_stage': life_stage,
                'ingredients_raw': clean_text(ingredients) if ingredients else None,
                'pack_sizes': pack_sizes if pack_sizes else None,
                'price_currency': 'GBP',
                'price_eur': price_eur,
                'available_countries': ['UK', 'EU']
            }
            
            # Add derived fields
            if ingredients:
                candidate_data['ingredients_tokens'] = tokenize_ingredients(ingredients)
                candidate_data['contains_chicken'] = check_contains_chicken(ingredients)
            
            # Extract nutrition from HTML (API doesn't provide this)
            print(f"    🧪 Extracting nutrition from HTML...")
            nutrition = self.extract_nutrition_from_html(url)
            
            if nutrition:
                candidate_data.update(nutrition)
                self.stats['nutrition_extracted'] += 1
                print(f"    ✅ Nutrition found: kcal={nutrition.get('kcal_per_100g')}, protein={nutrition.get('protein_percent')}%")
            else:
                print(f"    ⚠️  No nutrition data extracted")
            
            # Generate fingerprint
            fingerprint = generate_fingerprint(
                candidate_data['brand'],
                candidate_data['product_name'], 
                candidate_data['ingredients_raw'] or ''
            )
            candidate_data['fingerprint'] = fingerprint
            
            # Save to database
            return self._save_to_database(candidate_data)
            
        except Exception as e:
            print(f"    ❌ Error processing product: {e}")
            self.stats['errors'] += 1
            return False

    def _save_to_database(self, candidate_data: Dict[str, Any]) -> bool:
        """Save product data to database"""
        try:
            # Save raw data
            raw_record = {
                'raw_type': 'json',
                'source_domain': candidate_data['source_domain'],
                'source_url': candidate_data['source_url'],
                'raw_data': json.dumps({k: v for k, v in candidate_data.items() if k not in ['fingerprint']})
            }
            
            # Check for existing candidate
            existing = self.supabase.table('food_candidates')\
                .select('id, kcal_per_100g, protein_percent, fat_percent')\
                .eq('fingerprint', candidate_data['fingerprint'])\
                .execute()
            
            if existing.data:
                # Update existing record
                update_data = {k: v for k, v in candidate_data.items() 
                              if k not in ['fingerprint', 'first_seen_at']}
                update_data['last_seen_at'] = datetime.now().isoformat()
                
                self.supabase.table('food_candidates')\
                    .update(update_data)\
                    .eq('fingerprint', candidate_data['fingerprint'])\
                    .execute()
                
                self.stats['products_updated'] += 1
                print(f"    ✅ Updated existing product")
            else:
                # Insert new record
                candidate_data['first_seen_at'] = datetime.now().isoformat()
                candidate_data['last_seen_at'] = datetime.now().isoformat()
                
                self.supabase.table('food_candidates').insert(candidate_data).execute()
                self.stats['products_new'] += 1
                print(f"    ✅ Added new product")
            
            # Skip raw data insertion for now due to schema issues
            # raw_record['fingerprint'] = candidate_data['fingerprint']
            # self.supabase.table('food_raw')\
            #     .upsert(raw_record, on_conflict='source_url')\
            #     .execute()
            
            return True
            
        except Exception as e:
            print(f"    ❌ Database error: {e}")
            self.stats['errors'] += 1
            return False

    def run_full_catalog_harvest(self):
        """Run the complete catalog harvest"""
        print("🚀 Starting PetFoodExpert Full Catalog Harvest")
        print("="*60)
        
        # Discover all products
        all_products = self.discover_all_products()
        
        if not all_products:
            print("❌ No products discovered. Exiting.")
            return
        
        print(f"\n📋 Processing {len(all_products)} products...")
        print("="*60)
        
        # Process products in batches
        batch_size = self.config['batch_size']
        total = len(all_products)
        
        for i in range(0, total, batch_size):
            batch = all_products[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} products)")
            print("-" * 40)
            
            for j, product in enumerate(batch, 1):
                overall_progress = i + j
                print(f"[{overall_progress}/{total}] ", end="")
                
                if self.process_product(product):
                    self.stats['products_processed'] += 1
                else:
                    self.stats['products_skipped'] += 1
            
            # Progress summary every batch
            print(f"\n  📈 Batch {batch_num} complete. Overall: {self.stats['products_processed']} processed, {self.stats['products_new']} new, {self.stats['products_updated']} updated")
        
        self._print_final_report()

    def _print_final_report(self):
        """Print final harvest report"""
        print("\n" + "="*60)
        print("🎯 PETFOODEXPERT FULL CATALOG HARVEST REPORT")
        print("="*60)
        print(f"API pages fetched:      {self.stats['api_pages_fetched']}")
        print(f"Products discovered:    {self.stats['products_discovered']}")
        print(f"Products processed:     {self.stats['products_processed']}")
        print(f"New products added:     {self.stats['products_new']}")
        print(f"Products updated:       {self.stats['products_updated']}")
        print(f"Products skipped:       {self.stats['products_skipped']}")
        print(f"Nutrition extracted:    {self.stats['nutrition_extracted']}")
        print(f"Errors encountered:     {self.stats['errors']}")
        
        if self.stats['products_processed'] > 0:
            nutrition_rate = (self.stats['nutrition_extracted'] / self.stats['products_processed']) * 100
            print(f"Nutrition success rate: {nutrition_rate:.1f}%")
        
        print("="*60)
        
        # Show database totals
        self._show_database_summary()

    def _show_database_summary(self):
        """Show final database summary"""
        try:
            total = self.supabase.table('food_candidates')\
                .select('*', count='exact')\
                .eq('source_domain', 'petfoodexpert.com')\
                .execute()
            
            with_kcal = self.supabase.table('food_candidates')\
                .select('*', count='exact')\
                .eq('source_domain', 'petfoodexpert.com')\
                .not_.is_('kcal_per_100g', 'null')\
                .execute()
            
            with_nutrition = self.supabase.table('food_candidates')\
                .select('*', count='exact')\
                .eq('source_domain', 'petfoodexpert.com')\
                .not_.is_('kcal_per_100g', 'null')\
                .not_.is_('protein_percent', 'null')\
                .not_.is_('fat_percent', 'null')\
                .execute()
            
            print(f"\n📊 DATABASE SUMMARY:")
            print(f"Total PFX products:     {total.count}")
            print(f"With kcal data:         {with_kcal.count} ({with_kcal.count/total.count*100:.1f}%)")
            print(f"Complete nutrition:     {with_nutrition.count} ({with_nutrition.count/total.count*100:.1f}%)")
            
        except Exception as e:
            print(f"❌ Error getting database summary: {e}")

def main():
    scraper = PFXFullCatalogScraper()
    scraper.run_full_catalog_harvest()

if __name__ == '__main__':
    main()