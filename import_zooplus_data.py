#!/usr/bin/env python3
"""
Import Zooplus scraped data from JSON into food_candidates_sc table
"""
import json
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from supabase import create_client, Client
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://cibjeqgftuxuezarjsdl.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk')


class ZooplusImporter:
    """Import Zooplus product data into food_candidates_sc table"""
    
    def __init__(self, json_file: str):
        """Initialize importer with JSON file path"""
        self.json_file = json_file
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.stats = {
            'total': 0,
            'imported': 0,
            'updated': 0,
            'failed': 0,
            'skipped': 0,
            'with_nutrition': 0,
            'brands': set()
        }
        
    def load_data(self) -> List[Dict]:
        """Load JSON data from file"""
        logger.info(f"Loading data from {self.json_file}")
        with open(self.json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} products")
        return data
    
    def extract_brand(self, product: Dict) -> Optional[str]:
        """Extract real brand name from product data"""
        # First try breadcrumbs (most reliable)
        breadcrumbs = product.get('breadcrumbs', [])
        if len(breadcrumbs) > 2:
            # Third element is usually the brand
            brand = breadcrumbs[2]
            # Clean up brand name
            if brand and not any(skip in brand.lower() for skip in ['x ', 'kg', 'ml', 'g)', 'pack']):
                return brand
        
        # Fallback to brand field if not "zooplus logo"
        brand_field = product.get('brand', '')
        if brand_field and 'logo' not in brand_field.lower():
            return brand_field
        
        # Try to extract from product name
        name = product.get('name', '')
        # Common brand patterns at start of name
        known_brands = [
            'Royal Canin', 'Hill\'s', 'Purina', 'Eukanuba', 'Pro Plan',
            'Rocco', 'Wolf of Wilderness', 'Lukullus', 'Animonda', 
            'Almo Nature', 'Concept for Life', 'James Wellbeloved',
            'Affinity', 'Advance', 'Ultima', 'Acana', 'Orijen'
        ]
        
        for brand in known_brands:
            if name.startswith(brand):
                return brand
        
        return None
    
    def parse_nutrition_value(self, value: str) -> Optional[float]:
        """Parse nutrition percentage from string like '10.2 %'"""
        if not value:
            return None
        
        # Remove % and whitespace
        value = value.replace('%', '').strip()
        
        # Handle comma as decimal separator
        value = value.replace(',', '.')
        
        try:
            return float(value)
        except ValueError:
            return None
    
    def extract_pack_sizes(self, name: str) -> List[str]:
        """Extract pack sizes from product name"""
        sizes = []
        
        # Pattern: 6 x 400g, 24 x 800g, 2.5kg, etc.
        patterns = [
            r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)',  # 6 x 400g
            r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l)(?:\s|$)',      # 2.5kg
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, name, re.IGNORECASE)
            for match in matches:
                if len(match) == 3:  # Multi-pack
                    sizes.append(f"{match[0]} x {match[1]}{match[2]}")
                elif len(match) == 2:  # Single pack
                    sizes.append(f"{match[0]}{match[1]}")
        
        return sizes
    
    def determine_form(self, product: Dict) -> str:
        """Determine product form (dry, wet, raw, etc.)"""
        category = product.get('category', '').lower()
        name = product.get('name', '').lower()
        
        if 'dry' in category or 'kibble' in name:
            return 'dry'
        elif 'wet' in category or 'canned' in category or 'can' in name or 'pouch' in name:
            return 'wet'
        elif 'raw' in category or 'raw' in name:
            return 'raw'
        else:
            # Default based on moisture content if available
            moisture = product.get('attributes', {}).get('moisture')
            if moisture:
                moisture_val = self.parse_nutrition_value(moisture)
                if moisture_val:
                    if moisture_val > 60:
                        return 'wet'
                    elif moisture_val < 20:
                        return 'dry'
        
        return 'dry'  # Default to dry
    
    def transform_product(self, product: Dict) -> Optional[Dict]:
        """Transform Zooplus product to database format"""
        # Extract brand
        brand = self.extract_brand(product)
        if not brand:
            logger.debug(f"Skipping product without valid brand: {product.get('name')}")
            return None
        
        # Get nutrition data
        attributes = product.get('attributes', {})
        
        # Build database record
        record = {
            # Basic info
            'brand': brand,
            'product_name': product.get('name', ''),
            'form': self.determine_form(product),
            
            # Nutrition
            'protein_percent': self.parse_nutrition_value(attributes.get('protein')),
            'fat_percent': self.parse_nutrition_value(attributes.get('fat')),
            'fiber_percent': self.parse_nutrition_value(attributes.get('fibre')),
            'ash_percent': self.parse_nutrition_value(attributes.get('ash')),
            'moisture_percent': self.parse_nutrition_value(attributes.get('moisture')),
            
            # Ingredients (description contains ingredient info)
            'ingredients_raw': product.get('description', ''),
            
            # Package info
            'pack_sizes': self.extract_pack_sizes(product.get('name', '')),
            'gtin': product.get('gtin'),
            
            # Retailer info
            'retailer_source': 'zooplus',
            'retailer_url': product.get('url', ''),
            'retailer_product_id': product.get('sku', ''),
            'retailer_sku': product.get('sku', ''),
            'retailer_price_eur': product.get('price'),
            'retailer_original_price_eur': product.get('regular_price') if product.get('regular_price', 0) > 0 else None,
            'retailer_currency': product.get('currency', 'EUR'),
            'retailer_in_stock': product.get('in_stock', False),
            'retailer_rating': product.get('rating_value'),
            'retailer_review_count': product.get('review_count'),
            
            # Images
            'image_url': product.get('main_image'),
            'image_urls': product.get('images', []),
            
            # Metadata
            'data_source': 'scraper',
            'last_scraped_at': product.get('scraped_at'),
            
            # Data quality
            'data_complete': False  # Will update after checking
        }
        
        # Check if data is complete
        has_nutrition = any([
            record['protein_percent'],
            record['fat_percent'],
            record['fiber_percent']
        ])
        
        record['data_complete'] = (
            bool(record['brand']) and
            bool(record['product_name']) and
            has_nutrition and
            bool(record['retailer_price_eur'])
        )
        
        if has_nutrition:
            self.stats['with_nutrition'] += 1
        
        return record
    
    def import_batch(self, products: List[Dict]) -> int:
        """Import a batch of products to database"""
        imported = 0
        
        for product_data in products:
            try:
                record = self.transform_product(product_data)
                if not record:
                    self.stats['skipped'] += 1
                    continue
                
                # Track brand
                self.stats['brands'].add(record['brand'])
                
                # Try to insert (upsert)
                try:
                    # Check if exists
                    existing = self.supabase.table('food_candidates_sc').select('id').eq(
                        'brand', record['brand']
                    ).eq(
                        'product_name', record['product_name']
                    ).eq(
                        'retailer_source', 'zooplus'
                    ).execute()
                    
                    if existing.data:
                        # Update existing
                        response = self.supabase.table('food_candidates_sc').update(record).eq(
                            'id', existing.data[0]['id']
                        ).execute()
                        self.stats['updated'] += 1
                        logger.debug(f"Updated: {record['brand']} - {record['product_name']}")
                    else:
                        # Insert new
                        response = self.supabase.table('food_candidates_sc').insert(record).execute()
                        self.stats['imported'] += 1
                        imported += 1
                        logger.debug(f"Imported: {record['brand']} - {record['product_name']}")
                        
                except Exception as e:
                    logger.error(f"Database error for {record['product_name']}: {str(e)[:200]}")
                    self.stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Transform error: {str(e)[:200]}")
                self.stats['failed'] += 1
        
        return imported
    
    def run_import(self, batch_size: int = 100):
        """Run the full import process"""
        logger.info("Starting Zooplus data import...")
        
        # Load data
        products = self.load_data()
        self.stats['total'] = len(products)
        
        # Process in batches
        total_batches = (len(products) + batch_size - 1) // batch_size
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} products)")
            imported = self.import_batch(batch)
            
            # Progress update
            processed = min(i + batch_size, len(products))
            logger.info(f"Progress: {processed}/{len(products)} products processed")
        
        # Final report
        self.print_summary()
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Total products in file: {self.stats['total']}")
        print(f"Successfully imported: {self.stats['imported']}")
        print(f"Updated existing: {self.stats['updated']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Skipped (no brand): {self.stats['skipped']}")
        print(f"Products with nutrition: {self.stats['with_nutrition']}")
        print(f"Unique brands: {len(self.stats['brands'])}")
        
        if self.stats['brands']:
            print(f"\nTop brands imported:")
            brand_list = sorted(self.stats['brands'])[:20]
            for brand in brand_list:
                print(f"  - {brand}")
        
        success_rate = ((self.stats['imported'] + self.stats['updated']) / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")
        print("="*60)


def main():
    """Main entry point"""
    json_file = 'docs/dataset_zooplus-scraper_2025-09-08_15-48-47-523.json'
    
    if not os.path.exists(json_file):
        logger.error(f"File not found: {json_file}")
        sys.exit(1)
    
    importer = ZooplusImporter(json_file)
    importer.run_import()


if __name__ == "__main__":
    main()