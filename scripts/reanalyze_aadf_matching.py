#!/usr/bin/env python3
"""
Re-analyze AADF matching with improved brand normalization
Find additional products that could be matched
"""

import os
import re
import csv
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from supabase import create_client
from dotenv import load_dotenv
from difflib import SequenceMatcher

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class AADFMatcher:
    def __init__(self):
        self.supabase = supabase
        self.brand_normalizations = self._load_brand_normalizations()
        self.stats = {
            'total_aadf': 0,
            'already_matched': 0,
            'new_matches_found': 0,
            'unmatched': 0,
            'brands_not_in_db': set()
        }
        
    def _load_brand_normalizations(self) -> Dict[str, str]:
        """Load comprehensive brand normalization mappings"""
        mappings = {
            # Common variations
            'hills': "Hill's Science Plan",
            'hills science plan': "Hill's Science Plan",
            'hills prescription diet': "Hill's Prescription Diet",
            'royal canin': 'Royal Canin',
            'royal': 'Royal Canin',
            'natures menu': "Nature's Menu",
            'natures': "Nature's Menu",
            'james wellbeloved': 'James Wellbeloved',
            'james': 'James Wellbeloved',
            'wolf of wilderness': 'Wolf Of Wilderness',
            'wolf': 'Wolf Of Wilderness',
            'butchers': "Butcher's",
            'lilys kitchen': "Lily's Kitchen",
            'lily': "Lily's Kitchen",
            'millies wolfheart': "Millie's Wolfheart",
            'wainwrights': "Wainwright's",
            'harringtons': "Harrington's",
            'barking heads': 'Barking Heads',
            'pooch mutt': 'Pooch & Mutt',
            'taste of the wild': 'Taste of the Wild',
            'vets kitchen': "Vet's Kitchen",
            'pure pet food': 'Pure',
            'tails.com': 'Tails',
            'forthglade': 'Forthglade',
            'fish4dogs': 'Fish4Dogs',
            'arden grange': 'Arden Grange',
            'pro plan': 'Pro Plan',
            'purina pro plan': 'Pro Plan',
            'purina one': 'Purina ONE',
            'happy dog': 'Happy Dog',
            'happy': 'Happy Dog',
            'greenies': 'Greenies',
            'solid gold': 'Solid Gold',
            'terra canis': 'Terra Canis',
            'wellness core': 'Wellness CORE',
            'step up': 'Step Up',
            'the dogs table': "The Dog's Table",
            'natures diet': 'Nature Diet',
            'billy margot': 'Billy + Margot',
        }
        return mappings
        
    def extract_brand_from_url(self, url: str) -> Optional[str]:
        """Extract and normalize brand from AADF URL"""
        if not url:
            return None
            
        # Extract path
        path = urlparse(url).path.lower()
        
        # Known brand patterns in URLs
        brand_patterns = {
            'forthglade': 'Forthglade',
            'ava': 'AVA',
            'fish4dogs': 'Fish4Dogs',
            'royal-canin': 'Royal Canin',
            'hills': "Hill's Science Plan",
            'james-wellbeloved': 'James Wellbeloved',
            'purina': 'Purina',
            'eukanuba': 'Eukanuba',
            'iams': 'IAMS',
            'bakers': 'Bakers',
            'butchers': "Butcher's",
            'pedigree': 'Pedigree',
            'wainwrights': "Wainwright's",
            'harringtons': "Harrington's",
            'burns': 'Burns',
            'lily': "Lily's Kitchen",
            'lilys-kitchen': "Lily's Kitchen",
            'canagan': 'Canagan',
            'aatu': 'Aatu',
            'akela': 'Akela',
            'applaws': 'Applaws',
            'barking-heads': 'Barking Heads',
            'beco': 'Beco',
            'brit': 'Brit',
            'eden': 'Eden',
            'gentle': 'Gentle',
            'guru': 'Guru',
            'millies-wolfheart': "Millie's Wolfheart",
            'natures-menu': "Nature's Menu",
            'orijen': 'Orijen',
            'piccolo': 'Piccolo',
            'pooch-mutt': 'Pooch & Mutt',
            'pure': 'Pure',
            'symply': 'Symply',
            'tails': 'Tails',
            'taste-of-the-wild': 'Taste of the Wild',
            'tribal': 'Tribal',
            'wellness': 'Wellness',
            'wolf-of-wilderness': 'Wolf Of Wilderness',
            'yarrah': 'Yarrah',
            'ziwipeak': 'ZiwiPeak',
            'acana': 'Acana',
            'advance': 'Advance',
            'arden-grange': 'Arden Grange',
            'arkwrights': 'Arkwrights',
            'autarky': 'Autarky',
            'benevo': 'Benevo',
            'beta': 'Beta',
            'blink': 'Blink',
            'burgess': 'Burgess',
            'cesar': 'Cesar',
            'chappie': 'Chappie',
            'encore': 'Encore',
            'greenies': 'Greenies',
            'hilife': 'HiLife',
            'husse': 'Husse',
            'josera': 'Josera',
            'lukullus': 'Lukullus',
            'merrick': 'Merrick',
            'naturediet': 'Nature Diet',
            'nutriment': 'Nutriment',
            'platinum': 'Platinum',
            'pro-plan': 'Pro Plan',
            'pro-pac': 'Pro Pac',
            'purina-one': 'Purina ONE',
            'rocco': 'Rocco',
            'scrumbles': 'Scrumbles',
            'skinners': 'Skinners',
            'solid-gold': 'Solid Gold',
            'step-up': 'Step Up',
            'terra-canis': 'Terra Canis',
            'the-dogs-table': "The Dog's Table",
            'thrive': 'Thrive',
            'vets-kitchen': "Vet's Kitchen",
            'wagg': 'Wagg',
            'webbox': 'Webbox',
            'wellness-core': 'Wellness CORE',
            'winalot': 'Winalot',
            'billy-margot': 'Billy + Margot',
            'belcando': 'Belcando',
            'briantos': 'Briantos',
        }
        
        # Check patterns
        for pattern, brand in brand_patterns.items():
            if pattern in path:
                return brand
                
        # Try to extract from slug
        if '/dog-food-reviews/' in path:
            parts = path.split('/')
            if len(parts) >= 4:
                slug = parts[3]
                # First part is often the brand
                first_part = slug.split('-')[0]
                
                # Try normalizations
                if first_part in self.brand_normalizations:
                    return self.brand_normalizations[first_part]
                    
                return first_part.title()
                
        return None
        
    def normalize_name(self, name: str) -> str:
        """Normalize product name for matching"""
        if not name:
            return ""
            
        # Convert to lowercase and remove special characters
        normalized = re.sub(r'[^\w\s]', ' ', name.lower())
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        # Remove common words that don't help with matching
        stop_words = ['with', 'and', 'for', 'in', 'the', 'a', 'an']
        words = [w for w in normalized.split() if w not in stop_words]
        
        return ' '.join(words)
        
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, str1, str2).ratio()
        
    def extract_product_features(self, url: str) -> Dict[str, str]:
        """Extract product features from URL"""
        features = {}
        
        if not url:
            return features
            
        path = urlparse(url).path.lower()
        
        # Extract life stage
        if 'puppy' in path or 'junior' in path:
            features['life_stage'] = 'puppy'
        elif 'senior' in path or 'mature' in path:
            features['life_stage'] = 'senior'
        elif 'adult' in path:
            features['life_stage'] = 'adult'
            
        # Extract size
        if 'small' in path:
            features['size'] = 'small'
        elif 'large' in path:
            features['size'] = 'large'
        elif 'medium' in path:
            features['size'] = 'medium'
            
        # Extract special diets
        if 'grain-free' in path or 'grainfree' in path:
            features['grain_free'] = True
        if 'hypoallergenic' in path:
            features['hypoallergenic'] = True
        if 'sensitive' in path:
            features['sensitive'] = True
        if 'light' in path or 'weight' in path:
            features['light'] = True
            
        return features
        
    def find_best_match(self, brand: str, url: str, ingredients: str, db_products: List[Dict]) -> Optional[Tuple[Dict, float]]:
        """Find best matching product from database"""
        if not brand or not db_products:
            return None
            
        # Extract features from URL
        url_features = self.extract_product_features(url)
        url_normalized = self.normalize_name(url)
        
        best_match = None
        best_score = 0
        
        for product in db_products:
            # Skip if already has ingredients
            if product.get('ingredients_raw'):
                continue
                
            score = 0
            
            # Name similarity
            product_normalized = self.normalize_name(product.get('product_name', ''))
            name_similarity = self.calculate_similarity(url_normalized, product_normalized)
            score += name_similarity * 0.5
            
            # Feature matching
            if url_features.get('life_stage') and product.get('life_stage'):
                if url_features['life_stage'] == product['life_stage'].lower():
                    score += 0.2
                    
            if url_features.get('size') and 'small' in product_normalized and url_features['size'] == 'small':
                score += 0.1
            if url_features.get('size') and 'large' in product_normalized and url_features['size'] == 'large':
                score += 0.1
                
            if url_features.get('grain_free') and 'grain free' in product_normalized:
                score += 0.1
                
            # Check for key ingredient matches
            if ingredients:
                key_ingredients = ['chicken', 'beef', 'lamb', 'salmon', 'turkey', 'duck']
                for ingredient in key_ingredients:
                    if ingredient in ingredients.lower() and ingredient in product_normalized:
                        score += 0.05
                        
            if score > best_score:
                best_score = score
                best_match = product
                
        if best_match and best_score >= 0.4:  # Lower threshold for matching
            return (best_match, best_score)
            
        return None
        
    def analyze_matches(self):
        """Analyze AADF data for potential new matches"""
        
        print("="*60)
        print("RE-ANALYZING AADF MATCHING")
        print("="*60)
        
        # Load all products from database
        print("\nLoading products from database...")
        all_products = []
        offset = 0
        limit = 1000
        
        while True:
            response = supabase.table('foods_canonical').select('*').range(offset, offset + limit - 1).execute()
            batch = response.data
            if not batch:
                break
            all_products.extend(batch)
            offset += limit
            
        print(f"Loaded {len(all_products)} products")
        
        # Create brand index
        products_by_brand = {}
        for product in all_products:
            brand = product.get('brand', '')
            if brand:
                if brand not in products_by_brand:
                    products_by_brand[brand] = []
                products_by_brand[brand].append(product)
                
        # Also create normalized brand index
        for brand in list(products_by_brand.keys()):
            brand_lower = brand.lower()
            if brand_lower in self.brand_normalizations:
                normalized = self.brand_normalizations[brand_lower]
                if normalized not in products_by_brand and normalized != brand:
                    products_by_brand[normalized] = products_by_brand.get(brand, [])
                    
        print(f"Found {len(products_by_brand)} unique brands in database")
        
        # Process AADF CSV
        print("\nProcessing AADF data...")
        
        new_matches = []
        unmatched = []
        already_matched = []
        
        with open('data/aadf/aadf-dataset.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, 1):
                if row_num % 100 == 0:
                    print(f"  Processed {row_num} rows...", end='\r')
                    
                self.stats['total_aadf'] += 1
                
                # Extract data
                url = row.get('data-page-selector-href', '').strip()
                ingredients = row.get('ingredients-0', '').strip()
                
                if not ingredients or not url:
                    continue
                    
                # Extract brand
                brand = self.extract_brand_from_url(url)
                if not brand:
                    continue
                    
                # Try multiple brand variations
                brands_to_try = [brand]
                
                # Add normalized version
                brand_lower = brand.lower()
                if brand_lower in self.brand_normalizations:
                    normalized = self.brand_normalizations[brand_lower]
                    if normalized not in brands_to_try:
                        brands_to_try.append(normalized)
                        
                # Try each brand variation
                match_found = False
                for try_brand in brands_to_try:
                    if try_brand in products_by_brand:
                        result = self.find_best_match(try_brand, url, ingredients, products_by_brand[try_brand])
                        
                        if result:
                            product, score = result
                            
                            # Check if already has ingredients
                            if product.get('ingredients_raw'):
                                already_matched.append({
                                    'brand': try_brand,
                                    'product': product['product_name'],
                                    'score': score
                                })
                                self.stats['already_matched'] += 1
                            else:
                                new_matches.append({
                                    'product_key': product['product_key'],
                                    'brand': try_brand,
                                    'name': product['product_name'],
                                    'score': score,
                                    'ingredients': ingredients,
                                    'url': url
                                })
                                self.stats['new_matches_found'] += 1
                            
                            match_found = True
                            break
                            
                if not match_found:
                    # Track unmatched
                    self.stats['brands_not_in_db'].add(brand)
                    unmatched.append({
                        'brand': brand,
                        'url': url,
                        'ingredients': ingredients[:100] + '...' if len(ingredients) > 100 else ingredients
                    })
                    self.stats['unmatched'] += 1
                    
        print(f"\n\nAnalysis complete!")
        
        # Show results
        print("\n" + "="*60)
        print("MATCHING ANALYSIS RESULTS")
        print("="*60)
        print(f"Total AADF products: {self.stats['total_aadf']}")
        print(f"Already matched (have ingredients): {self.stats['already_matched']}")
        print(f"New matches found: {self.stats['new_matches_found']}")
        print(f"Still unmatched: {self.stats['unmatched']}")
        print(f"Brands not in database: {len(self.stats['brands_not_in_db'])}")
        
        # Show top new matches
        if new_matches:
            print(f"\n📊 Top New Matches (by confidence score):")
            sorted_matches = sorted(new_matches, key=lambda x: x['score'], reverse=True)
            
            for match in sorted_matches[:20]:
                print(f"  [{match['score']:.2f}] {match['brand']}: {match['name']}")
                
            print(f"\nTotal new matches with different confidence levels:")
            high_conf = len([m for m in new_matches if m['score'] >= 0.7])
            med_conf = len([m for m in new_matches if 0.5 <= m['score'] < 0.7])
            low_conf = len([m for m in new_matches if m['score'] < 0.5])
            
            print(f"  High confidence (≥0.7): {high_conf}")
            print(f"  Medium confidence (0.5-0.7): {med_conf}")
            print(f"  Low confidence (<0.5): {low_conf}")
            
        # Show unmatched brands
        if self.stats['brands_not_in_db']:
            print(f"\n⚠️ Brands in AADF but not in database:")
            for brand in sorted(self.stats['brands_not_in_db'])[:20]:
                print(f"  - {brand}")
                
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if new_matches:
            report_file = f"data/aadf_new_matches_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump({
                    'timestamp': timestamp,
                    'stats': {
                        'total_aadf': self.stats['total_aadf'],
                        'already_matched': self.stats['already_matched'],
                        'new_matches_found': self.stats['new_matches_found'],
                        'unmatched': self.stats['unmatched']
                    },
                    'new_matches': sorted_matches,
                    'brands_not_in_db': sorted(self.stats['brands_not_in_db'])
                }, f, indent=2)
                
            print(f"\n📄 New matches saved to: {report_file}")
            
        return new_matches

def main():
    import sys
    
    matcher = AADFMatcher()
    new_matches = matcher.analyze_matches()
    
    # Ask if user wants to apply high-confidence matches
    if new_matches:
        high_conf = [m for m in new_matches if m['score'] >= 0.7]
        
        if high_conf and '--apply' in sys.argv:
            print(f"\n🚀 Applying {len(high_conf)} high-confidence matches...")
            
            for i, match in enumerate(high_conf, 1):
                try:
                    # Parse ingredients
                    ingredients_tokens = []
                    if match['ingredients']:
                        parts = re.split(r'[,;]', match['ingredients'])
                        for part in parts[:50]:
                            part = re.sub(r'[^\w\s-]', ' ', part).strip()
                            if part and len(part) > 1:
                                ingredients_tokens.append(part.lower())
                    
                    response = supabase.table('foods_canonical').update({
                        'ingredients_raw': match['ingredients'],
                        'ingredients_source': 'site',
                        'ingredients_tokens': ingredients_tokens
                    }).eq('product_key', match['product_key']).execute()
                    
                    print(f"  [{i}/{len(high_conf)}] ✅ {match['brand']}: {match['name']}")
                    
                except Exception as e:
                    print(f"  [{i}/{len(high_conf)}] ❌ Failed: {match['name']}")
                    print(f"      Error: {e}")
                    
            print("\n✅ High-confidence matches applied!")
        elif high_conf:
            print(f"\n💡 Found {len(high_conf)} high-confidence matches (≥0.7)")
            print("   Run with --apply flag to update these products")
            
    print("\n✅ AADF re-analysis completed!")

if __name__ == "__main__":
    main()