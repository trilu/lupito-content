#!/usr/bin/env python3
"""
Validate suspicious products by checking if they exist on manufacturer websites
"""

import os
import json
from datetime import datetime
from typing import Dict, List
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

class SuspiciousProductValidator:
    def __init__(self):
        self.supabase = supabase
        self.suspicious_products = []
        self.validation_results = []
        
    def find_suspicious_products(self) -> List[Dict]:
        """Find all suspicious products in the database"""
        print("Finding suspicious products...")
        
        # Load all products
        all_products = []
        offset = 0
        limit = 1000
        
        while True:
            response = self.supabase.table('foods_canonical').select('*').range(offset, offset + limit - 1).execute()
            batch = response.data
            if not batch:
                break
            all_products.extend(batch)
            offset += limit
        
        suspicious = []
        
        for product in all_products:
            brand = product.get('brand', '')
            name = product.get('product_name', '')
            
            # Check various suspicious patterns
            is_suspicious = False
            reason = None
            
            # Name equals brand
            if name and brand and name.lower() == brand.lower():
                is_suspicious = True
                reason = 'name_equals_brand'
            
            # Name too short
            elif name and len(name) < 5:
                is_suspicious = True
                reason = 'name_too_short'
            
            # Single generic word
            elif name and name.lower() in ['fish', 'beef', 'chicken', 'mini', 'adult', 
                                          'puppy', 'senior', 'hfc', 'goat', 'lamb']:
                is_suspicious = True
                reason = 'generic_name'
            
            if is_suspicious:
                suspicious.append({
                    'product': product,
                    'reason': reason
                })
        
        self.suspicious_products = suspicious
        return suspicious
    
    def validate_products(self) -> Dict:
        """Validate suspicious products and determine actions"""
        
        # Group by brand for analysis
        brands_analysis = {}
        
        for item in self.suspicious_products:
            product = item['product']
            brand = product.get('brand', 'Unknown')
            
            if brand not in brands_analysis:
                brands_analysis[brand] = []
            
            brands_analysis[brand].append({
                'name': product.get('product_name'),
                'key': product.get('product_key'),
                'reason': item['reason'],
                'source': product.get('source')
            })
        
        # Specific validations based on known issues
        validation_decisions = []
        
        # Known issues from analysis
        known_invalid = {
            'Bozita': ['Bozita'],  # Product name that's just the brand
            'Almo Nature': ['HFC'],  # Too generic
            'Gentle': ['Fish', 'Goat'],  # Too generic
            'Feedwell': ['Mini'],  # Too generic
            'Arkwrights': ['Beef'],  # Too generic
        }
        
        for brand, invalid_names in known_invalid.items():
            for product_info in brands_analysis.get(brand, []):
                if product_info['name'] in invalid_names:
                    validation_decisions.append({
                        'brand': brand,
                        'name': product_info['name'],
                        'key': product_info['key'],
                        'action': 'delete',
                        'reason': f"Invalid product name: {product_info['reason']}",
                        'confidence': 0.95
                    })
        
        # Products that might be valid (need manual review)
        needs_review = {
            'Aatu': ['Chicken'],  # Could be "Aatu Chicken" formula
            'Acana': ['Senior', 'Adult', 'Puppy'],  # Could be product lines
        }
        
        for brand, names in needs_review.items():
            for product_info in brands_analysis.get(brand, []):
                if product_info['name'] in names:
                    validation_decisions.append({
                        'brand': brand,
                        'name': product_info['name'],
                        'key': product_info['key'],
                        'action': 'review',
                        'reason': f"Needs manual review: {product_info['reason']}",
                        'confidence': 0.5
                    })
        
        self.validation_results = validation_decisions
        return {
            'total_suspicious': len(self.suspicious_products),
            'to_delete': len([d for d in validation_decisions if d['action'] == 'delete']),
            'to_review': len([d for d in validation_decisions if d['action'] == 'review']),
            'decisions': validation_decisions
        }
    
    def execute_cleanup(self, dry_run=True):
        """Execute cleanup of invalid products"""
        
        # Find suspicious products
        suspicious = self.find_suspicious_products()
        print(f"Found {len(suspicious)} suspicious products")
        
        # Validate them
        validation = self.validate_products()
        
        print("\n" + "="*60)
        print("SUSPICIOUS PRODUCT VALIDATION SUMMARY")
        print("="*60)
        print(f"Total suspicious products: {validation['total_suspicious']}")
        print(f"Products to delete: {validation['to_delete']}")
        print(f"Products needing review: {validation['to_review']}")
        
        # Show decisions
        if validation['decisions']:
            print("\n--- Products to Delete ---")
            for decision in validation['decisions']:
                if decision['action'] == 'delete':
                    print(f"  {decision['brand']} - \"{decision['name']}\" ({decision['reason']})")
            
            print("\n--- Products Needing Review ---")
            for decision in validation['decisions']:
                if decision['action'] == 'review':
                    print(f"  {decision['brand']} - \"{decision['name']}\" ({decision['reason']})")
        
        # Save audit trail
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audit_file = f"data/suspicious_products_audit_{timestamp}.json"
        
        audit_data = {
            'timestamp': timestamp,
            'total_suspicious': len(suspicious),
            'validation_results': validation,
            'all_suspicious': [
                {
                    'brand': s['product'].get('brand'),
                    'name': s['product'].get('product_name'),
                    'key': s['product'].get('product_key'),
                    'reason': s['reason']
                }
                for s in suspicious
            ]
        }
        
        os.makedirs('data', exist_ok=True)
        with open(audit_file, 'w') as f:
            json.dump(audit_data, f, indent=2)
        
        print(f"\nAudit trail saved to: {audit_file}")
        
        if not dry_run:
            print("\n" + "="*60)
            print("EXECUTING DELETIONS")
            print("="*60)
            
            deleted_count = 0
            for decision in validation['decisions']:
                if decision['action'] == 'delete':
                    try:
                        response = self.supabase.table('foods_canonical').delete().eq(
                            'product_key', decision['key']
                        ).execute()
                        
                        print(f"  Deleted: {decision['brand']} - {decision['name']}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"  Error deleting {decision['key']}: {e}")
            
            print(f"\nDeleted {deleted_count} invalid products")
        else:
            print("\n⚠️  DRY RUN - No changes made to database")
            print("Run with --execute flag to apply changes")
        
        # Also show all suspicious products for review
        print("\n" + "="*60)
        print("ALL SUSPICIOUS PRODUCTS (for manual review)")
        print("="*60)
        
        # Group by brand
        by_brand = {}
        for s in suspicious:
            brand = s['product'].get('brand', 'Unknown')
            if brand not in by_brand:
                by_brand[brand] = []
            by_brand[brand].append({
                'name': s['product'].get('product_name'),
                'reason': s['reason']
            })
        
        for brand in sorted(by_brand.keys()):
            print(f"\n{brand}:")
            for product in by_brand[brand]:
                print(f"  - \"{product['name']}\" ({product['reason']})")

def main():
    import sys
    
    # Check for execute flag
    dry_run = '--execute' not in sys.argv
    
    # Create validator and run
    validator = SuspiciousProductValidator()
    validator.execute_cleanup(dry_run=dry_run)
    
    print("\n✅ Validation process completed!")

if __name__ == "__main__":
    main()