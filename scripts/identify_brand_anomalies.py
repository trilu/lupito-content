#!/usr/bin/env python3
"""
Identify and fix brand anomalies in the database where brand field
contains IDs or incorrect values instead of actual brand names.
"""

import os
import re
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class BrandAnomalyDetector:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.anomalies = []
        self.brand_corrections = {}
        
    def detect_numeric_brands(self) -> List[Dict]:
        """Find products where brand field contains only numbers"""
        print("\n🔍 Detecting numeric brand anomalies...")
        
        # Get all products
        all_products = []
        offset = 0
        batch_size = 1000
        
        while True:
            batch = self.supabase.table('foods_canonical').select(
                'product_key, brand, product_name, product_url'
            ).range(offset, offset + batch_size - 1).execute()
            
            if not batch.data:
                break
            
            all_products.extend(batch.data)
            offset += batch_size
            
            if offset % 5000 == 0:
                print(f"  Processed {offset} products...")
        
        # Find anomalies
        numeric_brands = []
        for product in all_products:
            brand = product.get('brand', '')
            
            # Check if brand is numeric or looks like an ID
            if brand and (brand.isdigit() or re.match(r'^\d+$', brand)):
                numeric_brands.append(product)
        
        print(f"  Found {len(numeric_brands)} products with numeric brands")
        return numeric_brands
    
    def extract_brand_from_name(self, product_name: str) -> str:
        """Extract likely brand name from product name"""
        
        # Known brand patterns (add more as needed)
        known_brands = [
            'IAMS', 'Royal Canin', 'Purina', 'Hills', "Hill's", 'Pedigree',
            'Wellness', 'Acana', 'Orijen', 'Blue Buffalo', 'Eukanuba',
            'Advance', 'Taste of the Wild', 'Applaws', 'Almo Nature',
            'Bozita', 'Carnilove', 'Wolf of Wilderness', 'Rocco', 'Rinti',
            'Animonda', 'Lukullus', 'MAC\'s', 'Smilla', 'Greenwoods',
            'Briantos', 'Markus-Mühle', 'Josera', 'Bosch', 'Happy Dog',
            'Brit', 'Brit Care', 'Concept for Life', 'Wild Freedom'
        ]
        
        # Check each known brand
        for brand in known_brands:
            if brand.upper() in product_name.upper():
                return brand
        
        # Try to extract first word(s) before common product descriptors
        patterns = [
            r'^([A-Z][A-Za-z&\'\s]+?)\s+(?:Adult|Puppy|Senior|Junior|Large|Small|Medium|Mini)',
            r'^([A-Z][A-Za-z&\'\s]+?)\s+(?:Dry|Wet|Fresh|Raw|Grain)',
            r'^([A-Z][A-Za-z&\'\s]+?)\s+(?:Dog|Cat|Pet)',
            r'^([A-Z]+)\s+',  # All caps first word
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+',  # Title case first words
        ]
        
        for pattern in patterns:
            match = re.match(pattern, product_name)
            if match:
                potential_brand = match.group(1).strip()
                # Filter out common non-brand words
                if potential_brand not in ['The', 'A', 'An', 'New', 'Best', 'Premium']:
                    return potential_brand
        
        return None
    
    def analyze_anomalies(self, anomalies: List[Dict]) -> Dict:
        """Analyze anomalies to find patterns and suggest corrections"""
        print("\n📊 Analyzing anomalies...")
        
        analysis = {
            'total_anomalies': len(anomalies),
            'by_brand_value': Counter(),
            'suggested_corrections': {},
            'url_patterns': defaultdict(list),
            'extracted_brands': Counter()
        }
        
        for product in anomalies:
            brand_value = product.get('brand', '')
            product_name = product.get('product_name', '')
            product_url = product.get('product_url', '')
            
            # Count occurrences of each anomalous brand value
            analysis['by_brand_value'][brand_value] += 1
            
            # Try to extract real brand from product name
            extracted_brand = self.extract_brand_from_name(product_name)
            if extracted_brand:
                analysis['extracted_brands'][extracted_brand] += 1
                
                # Store suggestion
                if brand_value not in analysis['suggested_corrections']:
                    analysis['suggested_corrections'][brand_value] = Counter()
                analysis['suggested_corrections'][brand_value][extracted_brand] += 1
            
            # Analyze URL patterns
            if product_url:
                # Extract path segment that might indicate brand
                match = re.search(r'/shop/dogs/[^/]+/([^/]+)/', product_url)
                if match:
                    url_segment = match.group(1)
                    analysis['url_patterns'][brand_value].append(url_segment)
        
        # Finalize suggestions (take most common extraction for each anomalous brand)
        final_corrections = {}
        for brand_value, suggestions in analysis['suggested_corrections'].items():
            if suggestions:
                most_common = suggestions.most_common(1)[0][0]
                final_corrections[brand_value] = most_common
        
        analysis['final_corrections'] = final_corrections
        
        return analysis
    
    def print_analysis(self, analysis: Dict, sample_products: List[Dict]):
        """Print analysis results"""
        print("\n" + "=" * 60)
        print("📋 BRAND ANOMALY ANALYSIS REPORT")
        print("=" * 60)
        
        print(f"\n🔢 Total anomalies found: {analysis['total_anomalies']}")
        
        print("\n🏷️ Top anomalous brand values:")
        for brand_value, count in analysis['by_brand_value'].most_common(10):
            print(f"  '{brand_value}': {count} products")
        
        print("\n✅ Suggested corrections:")
        for brand_value, correction in analysis['final_corrections'].items():
            count = analysis['by_brand_value'][brand_value]
            print(f"  '{brand_value}' -> '{correction}' ({count} products)")
        
        print("\n📦 Sample affected products:")
        for i, product in enumerate(sample_products[:10], 1):
            brand_value = product.get('brand', '')
            product_name = product.get('product_name', '')
            extracted = self.extract_brand_from_name(product_name)
            print(f"  {i}. Current brand: '{brand_value}'")
            print(f"     Product: {product_name[:60]}...")
            print(f"     Suggested: '{extracted or 'Could not extract'}'")
            print()
        
        print("\n🎯 Most commonly extracted brands:")
        for brand, count in analysis['extracted_brands'].most_common(10):
            print(f"  {brand}: {count} occurrences")
    
    def generate_fix_script(self, analysis: Dict, anomalies: List[Dict]):
        """Generate SQL script to fix the anomalies"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        script_file = f"sql/fix_brand_anomalies_{timestamp}.sql"
        
        with open(script_file, 'w') as f:
            f.write("-- Script to fix brand anomalies\n")
            f.write(f"-- Generated: {datetime.now()}\n")
            f.write(f"-- Total anomalies: {analysis['total_anomalies']}\n\n")
            
            f.write("BEGIN;\n\n")
            
            # Group updates by correction
            for brand_value, correction in analysis['final_corrections'].items():
                affected_products = [p for p in anomalies if p.get('brand') == brand_value]
                
                f.write(f"-- Fix '{brand_value}' -> '{correction}' ({len(affected_products)} products)\n")
                f.write(f"UPDATE foods_canonical\n")
                f.write(f"SET brand = '{correction}'\n")
                f.write(f"WHERE brand = '{brand_value}';\n\n")
            
            # Also fix products with no brand but clear brand in name
            f.write("-- Fix products with NULL/empty brand but clear brand in name\n")
            for product in anomalies:
                if not product.get('brand') or product.get('brand') == '':
                    extracted = self.extract_brand_from_name(product.get('product_name', ''))
                    if extracted:
                        f.write(f"UPDATE foods_canonical\n")
                        f.write(f"SET brand = '{extracted}'\n")
                        f.write(f"WHERE product_key = '{product['product_key']}';\n")
            
            f.write("\n-- Verify changes before committing\n")
            f.write("-- ROLLBACK; -- Uncomment to rollback\n")
            f.write("-- COMMIT; -- Uncomment to commit\n")
        
        print(f"\n💾 Fix script saved to: {script_file}")
        return script_file
    
    def save_detailed_report(self, anomalies: List[Dict], analysis: Dict):
        """Save detailed CSV report of all anomalies"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"data/brand_anomalies_{timestamp}.csv"
        
        # Prepare data for CSV
        report_data = []
        for product in anomalies:
            brand_value = product.get('brand', '')
            product_name = product.get('product_name', '')
            extracted = self.extract_brand_from_name(product_name)
            
            report_data.append({
                'product_key': product.get('product_key'),
                'current_brand': brand_value,
                'product_name': product_name,
                'extracted_brand': extracted or '',
                'suggested_correction': analysis['final_corrections'].get(brand_value, extracted or ''),
                'product_url': product.get('product_url', '')
            })
        
        # Save to CSV
        df = pd.DataFrame(report_data)
        df.to_csv(report_file, index=False)
        
        print(f"📄 Detailed report saved to: {report_file}")
        return report_file
    
    def run_detection(self):
        """Run the full anomaly detection process"""
        print("🚀 BRAND ANOMALY DETECTION")
        print("=" * 60)
        
        # Detect numeric brands
        numeric_anomalies = self.detect_numeric_brands()
        
        # Also check for other patterns
        print("\n🔍 Detecting other anomaly patterns...")
        
        # Get products with very short brands (likely wrong)
        short_brand_result = self.supabase.table('foods_canonical').select(
            'product_key, brand, product_name, product_url'
        ).execute()
        
        other_anomalies = []
        for product in short_brand_result.data:
            brand = product.get('brand', '')
            # Check for suspiciously short brands or all lowercase
            if brand and (len(brand) <= 2 or brand.islower() or brand == 'null' or brand == 'None'):
                other_anomalies.append(product)
        
        print(f"  Found {len(other_anomalies)} products with suspicious brand values")
        
        # Combine all anomalies
        all_anomalies = numeric_anomalies + other_anomalies
        
        # Remove duplicates
        seen = set()
        unique_anomalies = []
        for product in all_anomalies:
            key = product['product_key']
            if key not in seen:
                seen.add(key)
                unique_anomalies.append(product)
        
        print(f"\n📊 Total unique anomalies: {len(unique_anomalies)}")
        
        if unique_anomalies:
            # Analyze anomalies
            analysis = self.analyze_anomalies(unique_anomalies)
            
            # Print analysis
            self.print_analysis(analysis, unique_anomalies)
            
            # Save detailed report
            self.save_detailed_report(unique_anomalies, analysis)
            
            # Generate fix script
            self.generate_fix_script(analysis, unique_anomalies)
        else:
            print("✅ No brand anomalies detected!")
        
        return unique_anomalies, analysis if unique_anomalies else {}

def main():
    detector = BrandAnomalyDetector()
    detector.run_detection()

if __name__ == "__main__":
    main()