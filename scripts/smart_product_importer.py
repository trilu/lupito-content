#!/usr/bin/env python3
"""
Smart Product Importer with Variant Detection
Prevents duplicate imports by detecting size/pack variants
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class SmartProductImporter:
    """
    Intelligent product importer that detects and handles variants
    """
    
    def __init__(self, auto_consolidate: bool = True):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.auto_consolidate = auto_consolidate
        
        # Compile patterns for performance
        self.size_pattern = re.compile(r'\b\d+(?:\.\d+)?\s*(?:kg|g|lb|oz|ml|l)\b', re.IGNORECASE)
        self.pack_pattern = re.compile(r'\b\d+\s*x\s*\d+(?:\.\d+)?(?:\s*(?:kg|g|lb|oz|ml|l|cans?|pouches?|tins?))?\b', re.IGNORECASE)
        self.life_pattern = re.compile(r'\b(?:puppy|junior|adult|senior|mature)\b', re.IGNORECASE)
        self.breed_pattern = re.compile(r'\b(?:small|medium|large|mini|maxi|giant|toy)\s*(?:breed|dog|size)?\b', re.IGNORECASE)
        
        # Brand normalization mappings
        self.brand_mappings = {
            'royal canin': ['royalcanin', 'royal-canin', 'royal_canin', 'royal canin veterinary'],
            'hills': ['hills', "hill's", 'hills science plan', 'hills-science-plan', 'hills science diet'],
            'purina': ['purina', 'purina-pro-plan', 'purina pro plan', 'purina one', 'purina-one'],
            'advance': ['advance', 'advance-veterinary-diets', 'advance veterinary', 'advance vet'],
            'eukanuba': ['eukanuba', 'euk'],
            'wolf of wilderness': ['wolf of wilderness', 'wolf-of-wilderness', 'wow'],
        }
        
        # Statistics
        self.stats = {
            'products_processed': 0,
            'new_products': 0,
            'variants_detected': 0,
            'data_consolidated': 0,
            'duplicates_prevented': 0,
            'errors': 0
        }
    
    def normalize_brand(self, brand: str) -> str:
        """Normalize brand name to standard form"""
        if not brand:
            return None
        
        clean = brand.lower().strip()
        clean = re.sub(r'[^\w\s-]', '', clean)
        clean = re.sub(r'\s+', ' ', clean)
        
        # Check mappings
        for standard, variants in self.brand_mappings.items():
            if clean in variants or clean == standard:
                return standard.title()
        
        return clean.title()
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL for consistent storage"""
        if not url:
            return None
        
        # Remove variant parameters
        if '?activeVariant=' in url:
            url = url.split('?activeVariant=')[0]
        
        # Remove trailing slashes and numbers
        url = url.rstrip('/')
        url = re.sub(r'/\d{6,}$', '', url)
        
        return url
    
    def get_base_name(self, product_name: str) -> str:
        """Get base product name without size/pack indicators"""
        if not product_name:
            return ""
        
        # Remove size indicators
        name = self.size_pattern.sub('', product_name)
        
        # Remove pack indicators
        name = self.pack_pattern.sub('', name)
        
        # Clean up
        name = re.sub(r'\s*[,\-]\s*$', '', name)
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()
    
    def detect_variant_type(self, product_name: str) -> Dict:
        """Detect what type of variant this might be"""
        variant_info = {
            'has_size': bool(self.size_pattern.search(product_name)),
            'has_pack': bool(self.pack_pattern.search(product_name)),
            'has_life_stage': bool(self.life_pattern.search(product_name)),
            'has_breed_size': bool(self.breed_pattern.search(product_name)),
            'should_consolidate': False
        }
        
        # Only consolidate size/pack variants, not life stage or breed
        if (variant_info['has_size'] or variant_info['has_pack']) and \
           not (variant_info['has_life_stage'] or variant_info['has_breed_size']):
            variant_info['should_consolidate'] = True
        
        return variant_info
    
    def find_existing_product(self, brand: str, base_name: str, url: str = None) -> Optional[Dict]:
        """Find existing product that might be the parent"""
        
        # Try URL match first (most reliable)
        if url:
            normalized_url = self.normalize_url(url)
            result = self.supabase.table('foods_canonical').select('*')\
                .ilike('product_url', f'%{normalized_url}%').limit(1).execute()
            
            if result.data:
                return result.data[0]
        
        # Try brand + base name match
        if brand and base_name:
            # Search for products with similar names
            result = self.supabase.table('foods_canonical').select('*')\
                .eq('brand', brand).ilike('product_name', f'%{base_name[:30]}%').limit(10).execute()
            
            if result.data:
                # Find best match
                for product in result.data:
                    product_base = self.get_base_name(product['product_name'])
                    if product_base.lower() == base_name.lower():
                        return product
        
        return None
    
    def consolidate_data(self, parent: Dict, new_product: Dict) -> Dict:
        """Consolidate data from new product into parent"""
        updates = {}
        
        # Take ingredients if parent doesn't have them
        if not parent.get('ingredients_raw') and new_product.get('ingredients_raw'):
            updates['ingredients_raw'] = new_product['ingredients_raw']
            updates['ingredients_tokens'] = new_product.get('ingredients_tokens')
            updates['ingredients_source'] = new_product.get('ingredients_source', 'consolidated')
            self.stats['data_consolidated'] += 1
        
        # Take nutrition if parent doesn't have it
        nutrition_fields = ['protein_percent', 'fat_percent', 'fiber_percent', 
                          'ash_percent', 'moisture_percent']
        
        if not parent.get('protein_percent') and new_product.get('protein_percent'):
            for field in nutrition_fields:
                if new_product.get(field) is not None:
                    updates[field] = new_product[field]
            updates['macros_source'] = new_product.get('macros_source', 'consolidated')
            self.stats['data_consolidated'] += 1
        
        # Update URL if better (no variant parameters)
        if new_product.get('product_url') and '?activeVariant=' not in new_product['product_url']:
            if not parent.get('product_url') or '?activeVariant=' in parent['product_url']:
                updates['product_url'] = new_product['product_url']
        
        # Update timestamp
        updates['updated_at'] = datetime.now().isoformat()
        
        return updates
    
    def import_product(self, product_data: Dict) -> Dict:
        """
        Import a single product with variant detection
        Returns: {'status': 'imported'|'variant'|'error', 'message': str, 'product_key': str}
        """
        self.stats['products_processed'] += 1
        
        try:
            # 1. Normalize data
            brand = self.normalize_brand(product_data.get('brand'))
            product_name = product_data.get('product_name', '').strip()
            url = self.normalize_url(product_data.get('product_url'))
            
            if not product_name:
                self.stats['errors'] += 1
                return {'status': 'error', 'message': 'Missing product name'}
            
            # 2. Get base name and variant info
            base_name = self.get_base_name(product_name)
            variant_info = self.detect_variant_type(product_name)
            
            # 3. Check for existing product
            existing = self.find_existing_product(brand, base_name, url)
            
            if existing:
                if variant_info['should_consolidate']:
                    # This is a size/pack variant - consolidate
                    self.stats['variants_detected'] += 1
                    
                    if self.auto_consolidate:
                        # Update parent with any new data
                        updates = self.consolidate_data(existing, product_data)
                        
                        if updates:
                            self.supabase.table('foods_canonical').update(updates)\
                                .eq('product_key', existing['product_key']).execute()
                        
                        # Add to variants table
                        self.add_to_variants(product_data, existing['product_key'], variant_info)
                        
                        self.stats['duplicates_prevented'] += 1
                        return {
                            'status': 'variant',
                            'message': f"Consolidated to parent: {existing['product_key']}",
                            'parent_key': existing['product_key']
                        }
                    else:
                        return {
                            'status': 'variant',
                            'message': 'Variant detected but not consolidated',
                            'parent_key': existing['product_key']
                        }
                else:
                    # Life stage or breed variant - check if truly duplicate
                    if existing['product_name'].lower() == product_name.lower():
                        self.stats['duplicates_prevented'] += 1
                        return {
                            'status': 'duplicate',
                            'message': 'Exact duplicate found',
                            'product_key': existing['product_key']
                        }
            
            # 4. Import as new product
            # Generate product key
            product_key = self.generate_product_key(brand, product_name, product_data.get('form'))
            
            # Prepare product data
            product_data['product_key'] = product_key
            product_data['brand'] = brand
            product_data['product_name'] = product_name
            product_data['product_url'] = url
            product_data['updated_at'] = datetime.now().isoformat()
            
            # Insert to database
            result = self.supabase.table('foods_canonical').insert(product_data).execute()
            
            self.stats['new_products'] += 1
            return {
                'status': 'imported',
                'message': 'New product imported',
                'product_key': product_key
            }
            
        except Exception as e:
            self.stats['errors'] += 1
            return {
                'status': 'error',
                'message': str(e)[:200]
            }
    
    def add_to_variants(self, product_data: Dict, parent_key: str, variant_info: Dict):
        """Add product to variants table"""
        try:
            # Extract size/pack values
            size_value = None
            pack_value = None
            
            if variant_info['has_size']:
                size_match = self.size_pattern.search(product_data['product_name'])
                if size_match:
                    size_value = size_match.group(0)
            
            if variant_info['has_pack']:
                pack_match = self.pack_pattern.search(product_data['product_name'])
                if pack_match:
                    pack_value = pack_match.group(0)
            
            # Determine variant type
            if variant_info['has_size'] and variant_info['has_pack']:
                variant_type = 'size_and_pack'
            elif variant_info['has_size']:
                variant_type = 'size'
            else:
                variant_type = 'pack'
            
            # Create variant record
            variant_record = {
                'parent_product_key': parent_key,
                'variant_product_key': self.generate_product_key(
                    product_data.get('brand'),
                    product_data['product_name'],
                    product_data.get('form')
                ),
                'variant_type': variant_type,
                'size_value': size_value,
                'pack_value': pack_value,
                'product_name': product_data['product_name'],
                'product_url': product_data.get('product_url'),
                'original_data': product_data
            }
            
            self.supabase.table('product_variants').insert(variant_record).execute()
            
        except Exception as e:
            print(f"Error adding variant: {e}")
    
    def generate_product_key(self, brand: str, product_name: str, form: str = None) -> str:
        """Generate unique product key"""
        parts = []
        
        if brand:
            parts.append(re.sub(r'[^\w]', '', brand.lower()))
        
        if product_name:
            name_part = re.sub(r'[^\w\s]', '', product_name.lower())
            name_part = re.sub(r'\s+', '_', name_part)[:50]
            parts.append(name_part)
        
        if form:
            parts.append(form.lower())
        
        return '|'.join(parts)
    
    def import_batch(self, products: List[Dict]) -> Dict:
        """Import a batch of products"""
        print(f"🔄 Processing batch of {len(products)} products...")
        
        results = {
            'imported': [],
            'variants': [],
            'errors': [],
            'duplicates': []
        }
        
        for product in products:
            result = self.import_product(product)
            
            if result['status'] == 'imported':
                results['imported'].append(result)
            elif result['status'] == 'variant':
                results['variants'].append(result)
            elif result['status'] == 'duplicate':
                results['duplicates'].append(result)
            else:
                results['errors'].append(result)
        
        return results
    
    def print_stats(self):
        """Print import statistics"""
        print("\n" + "=" * 60)
        print("📊 IMPORT STATISTICS")
        print("=" * 60)
        print(f"Products processed: {self.stats['products_processed']}")
        print(f"New products imported: {self.stats['new_products']}")
        print(f"Variants detected: {self.stats['variants_detected']}")
        print(f"Data consolidated: {self.stats['data_consolidated']}")
        print(f"Duplicates prevented: {self.stats['duplicates_prevented']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['products_processed'] > 0:
            variant_rate = (self.stats['variants_detected'] / self.stats['products_processed']) * 100
            print(f"\nVariant detection rate: {variant_rate:.1f}%")

def test_importer():
    """Test the smart importer with sample data"""
    
    importer = SmartProductImporter(auto_consolidate=True)
    
    # Test cases
    test_products = [
        {
            'brand': 'Royal Canin',
            'product_name': 'Royal Canin Adult Medium 3kg',
            'product_url': 'https://www.zooplus.com/royal-canin-adult-medium',
            'ingredients_raw': 'Chicken, rice, corn...',
            'protein_percent': 25.0
        },
        {
            'brand': 'Royal-Canin',  # Different formatting
            'product_name': 'Royal Canin Adult Medium 15kg',  # Size variant
            'product_url': 'https://www.zooplus.com/royal-canin-adult-medium?activeVariant=123',
            'fat_percent': 14.0  # Has different nutrition data
        },
        {
            'brand': 'Royal Canin',
            'product_name': 'Royal Canin Puppy Medium',  # Life stage - should be separate
            'product_url': 'https://www.zooplus.com/royal-canin-puppy-medium',
            'ingredients_raw': 'Chicken, rice, fish oil...'
        },
        {
            'brand': 'Purina',
            'product_name': 'Purina One Adult 6x400g',
            'product_url': 'https://www.zooplus.com/purina-one-adult'
        },
        {
            'brand': 'Purina',
            'product_name': 'Purina One Adult 12x400g',  # Pack variant
            'product_url': 'https://www.zooplus.com/purina-one-adult?activeVariant=456'
        }
    ]
    
    print("🧪 TESTING SMART IMPORTER")
    print("=" * 60)
    
    for i, product in enumerate(test_products, 1):
        print(f"\n[{i}] Testing: {product['product_name']}")
        result = importer.import_product(product)
        print(f"   Result: {result['status']} - {result['message']}")
    
    importer.print_stats()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Product Importer')
    parser.add_argument('--test', action='store_true', help='Run test import')
    parser.add_argument('--csv', help='Import from CSV file')
    parser.add_argument('--no-consolidate', action='store_true', 
                       help='Detect variants but do not consolidate')
    
    args = parser.parse_args()
    
    if args.test:
        test_importer()
    elif args.csv:
        importer = SmartProductImporter(auto_consolidate=not args.no_consolidate)
        
        # Load CSV
        df = pd.read_csv(args.csv)
        products = df.to_dict('records')
        
        # Import batch
        results = importer.import_batch(products)
        
        # Print results
        print(f"\n✅ Imported: {len(results['imported'])}")
        print(f"🔄 Variants handled: {len(results['variants'])}")
        print(f"⚠️  Duplicates prevented: {len(results['duplicates'])}")
        print(f"❌ Errors: {len(results['errors'])}")
        
        importer.print_stats()
    else:
        print("Use --test for testing or --csv <file> to import from CSV")