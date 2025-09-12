#!/usr/bin/env python3
"""
Extract ingredients from Zooplus product descriptions
Only ~27 products have actual ingredients listed
"""

import os
import json
import re
from typing import List, Optional, Dict
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class ZooplusIngredientsExtractor:
    def __init__(self):
        self.supabase = supabase
        self.stats = {
            'total_processed': 0,
            'ingredients_found': 0,
            'products_updated': 0,
            'products_skipped': 0,
            'samples': []
        }
        
    def parse_ingredients_from_text(self, text: str) -> Optional[Dict]:
        """Extract ingredients from description text"""
        if not text:
            return None
        
        # Look for ingredients section
        patterns = [
            r'Ingredients:\s*([^.]+(?:\.[^.]+)*?)(?:Analytical|Nutritional|Feeding|$)',
            r'Composition:\s*([^.]+(?:\.[^.]+)*?)(?:Analytical|Nutritional|Feeding|$)',
            r'Contains:\s*([^.]+(?:\.[^.]+)*?)(?:Analytical|Nutritional|Feeding|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                ingredients_text = match.group(1).strip()
                
                # Clean up the text
                ingredients_text = re.sub(r'\n+', ' ', ingredients_text)
                ingredients_text = re.sub(r'\s+', ' ', ingredients_text)
                
                # Parse into tokens
                ingredients_tokens = self.tokenize_ingredients(ingredients_text)
                
                if ingredients_tokens:
                    return {
                        'raw': ingredients_text[:2000],  # Limit length
                        'tokens': ingredients_tokens
                    }
        
        # Try to extract from marketing text with percentages
        if re.search(r'\d+%', text):
            # Look for patterns like "60% meat", "chicken (25%)"
            meat_patterns = [
                r'(\d+%\s+(?:meat|chicken|beef|lamb|fish|turkey|duck|salmon))',
                r'((?:meat|chicken|beef|lamb|fish|turkey|duck|salmon)\s*\(\d+%\))',
                r'((?:meat|chicken|beef|lamb|fish|turkey|duck|salmon)\s+\d+%)',
            ]
            
            found_ingredients = []
            for pattern in meat_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                found_ingredients.extend(matches)
            
            if found_ingredients:
                # Create pseudo-ingredients list
                ingredients_text = ', '.join(found_ingredients)
                ingredients_tokens = self.tokenize_ingredients(ingredients_text)
                
                if ingredients_tokens:
                    return {
                        'raw': f"Extracted from description: {ingredients_text}"[:2000],
                        'tokens': ingredients_tokens,
                        'is_partial': True
                    }
        
        return None
    
    def tokenize_ingredients(self, text: str) -> List[str]:
        """Convert ingredients text to tokens"""
        if not text:
            return []
        
        # Remove percentages and parentheses
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\d+\.?\d*%', '', text)
        
        # Split by comma or semicolon
        parts = re.split(r'[,;]', text)
        
        tokens = []
        for part in parts[:50]:  # Limit to 50 ingredients
            # Clean the part
            part = re.sub(r'[^\\w\\s-]', ' ', part)
            part = ' '.join(part.split())
            part = part.strip().lower()
            
            # Skip very short or very long tokens
            if part and 2 < len(part) < 50:
                tokens.append(part)
        
        return tokens
    
    def extract_from_zooplus_json(self):
        """Extract ingredients from Zooplus JSON file"""
        print("Extracting ingredients from Zooplus descriptions...")
        print("="*60)
        
        # Load JSON
        with open('data/zooplus/Zooplus.json', 'r') as f:
            data = json.load(f)
        
        print(f"Processing {len(data)} products...")
        
        products_with_ingredients = []
        
        for product in data:
            self.stats['total_processed'] += 1
            
            # Get description
            description = product.get('description', '')
            if not description:
                continue
            
            # Try to extract ingredients
            ingredients_data = self.parse_ingredients_from_text(description)
            
            if ingredients_data:
                self.stats['ingredients_found'] += 1
                
                # Get product info
                name = product.get('name', '')
                breadcrumbs = product.get('breadcrumbs', [])
                brand = breadcrumbs[2] if len(breadcrumbs) > 2 else ''
                
                # Clean brand name
                brand = brand.replace('_', ' ').title()
                
                # Store for update
                products_with_ingredients.append({
                    'name': name,
                    'brand': brand,
                    'url': product.get('url'),
                    'ingredients': ingredients_data,
                    'is_partial': ingredients_data.get('is_partial', False)
                })
                
                # Add to samples
                if len(self.stats['samples']) < 5:
                    self.stats['samples'].append({
                        'name': name,
                        'brand': brand,
                        'ingredients': ingredients_data['raw'][:200]
                    })
        
        print(f"\nFound ingredients in {self.stats['ingredients_found']} products")
        
        # Show samples
        if self.stats['samples']:
            print("\nSample extractions:")
            print("-"*40)
            for sample in self.stats['samples']:
                print(f"\n{sample['brand']}: {sample['name']}")
                print(f"Ingredients: {sample['ingredients']}...")
        
        # Now update products in database
        if products_with_ingredients:
            print(f"\nPreparing to update {len(products_with_ingredients)} products...")
            self.update_products_with_ingredients(products_with_ingredients)
        
        self.print_summary()
    
    def update_products_with_ingredients(self, products_data: List[Dict]):
        """Update products in database with extracted ingredients"""
        print("\nMatching and updating products in database...")
        
        # Get all Zooplus products from database
        zooplus_products = []
        offset = 0
        limit = 1000
        
        while True:
            response = supabase.table('foods_canonical').select(
                'product_key,brand,product_name,ingredients_raw,product_url'
            ).or_(
                'product_url.like.%zooplus%,brand.in.(Purizon,Rocco,Lukullus,Greenwoods,Wolf Of Wilderness,Concept for Life)'
            ).range(offset, offset + limit - 1).execute()
            
            if not response.data:
                break
            
            zooplus_products.extend(response.data)
            offset += limit
            
            if len(response.data) < limit:
                break
        
        print(f"Found {len(zooplus_products)} potential Zooplus products in database")
        
        # Create lookup by normalized name
        db_lookup = {}
        for product in zooplus_products:
            # Create normalized key
            brand_norm = re.sub(r'[^a-z0-9]', '', product['brand'].lower())
            name_norm = re.sub(r'[^a-z0-9]', '', product['product_name'].lower())[:30]
            key = f"{brand_norm}|{name_norm}"
            db_lookup[key] = product
        
        # Match and update
        updated = 0
        skipped = 0
        
        for product_data in products_data:
            # Normalize for matching
            brand_norm = re.sub(r'[^a-z0-9]', '', product_data['brand'].lower())
            
            # Extract core name (remove pack size)
            name = product_data['name']
            name = re.sub(r'\d+\s*x\s*\d+[kg|g|ml]', '', name)
            name = re.sub(r'\d+[kg|g|ml]', '', name)
            name_norm = re.sub(r'[^a-z0-9]', '', name.lower())[:30]
            
            key = f"{brand_norm}|{name_norm}"
            
            # Try to find match
            if key in db_lookup:
                db_product = db_lookup[key]
                
                # Only update if no ingredients or if this is better
                if not db_product.get('ingredients_raw') or not product_data['ingredients'].get('is_partial'):
                    try:
                        # Update product
                        response = supabase.table('foods_canonical').update({
                            'ingredients_raw': product_data['ingredients']['raw'],
                            'ingredients_tokens': product_data['ingredients']['tokens'],
                            'ingredients_source': 'site'
                        }).eq('product_key', db_product['product_key']).execute()
                        
                        updated += 1
                        self.stats['products_updated'] += 1
                        
                        if updated <= 3:
                            print(f"  ✅ Updated: {product_data['brand']}: {product_data['name'][:50]}")
                        
                    except Exception as e:
                        print(f"  ❌ Failed to update: {e}")
                        skipped += 1
                else:
                    skipped += 1
                    self.stats['products_skipped'] += 1
            else:
                skipped += 1
        
        print(f"\nUpdated {updated} products")
        print(f"Skipped {skipped} products")
    
    def print_summary(self):
        """Print extraction summary"""
        print("\n" + "="*60)
        print("ZOOPLUS INGREDIENTS EXTRACTION SUMMARY")
        print("="*60)
        print(f"Total products processed: {self.stats['total_processed']}")
        print(f"Products with ingredients found: {self.stats['ingredients_found']}")
        print(f"Products updated in database: {self.stats['products_updated']}")
        print(f"Products skipped: {self.stats['products_skipped']}")
        
        # Check coverage
        print("\nChecking ingredients coverage...")
        total = supabase.table('foods_canonical').select('*', count='exact').execute()
        with_ingredients = supabase.table('foods_canonical').select(
            '*', count='exact'
        ).not_.is_('ingredients_raw', 'null').execute()
        
        print(f"\nDatabase Status:")
        print(f"  Total products: {total.count}")
        print(f"  With ingredients: {with_ingredients.count} ({with_ingredients.count/total.count*100:.1f}%)")
        
        print("\n⚠️  Note: Zooplus data lacks detailed ingredient lists")
        print("    Only marketing descriptions available for most products")
        print("    ScrapingBee required for full ingredient extraction")

def main():
    extractor = ZooplusIngredientsExtractor()
    extractor.extract_from_zooplus_json()
    print("\n✅ Zooplus ingredients extraction completed!")

if __name__ == "__main__":
    main()