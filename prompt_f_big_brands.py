#!/usr/bin/env python3
"""
PROMPT F: Big-brand probe (RC / Hill's / Purina)
Goal: Confirm presence (or absence) by truth, not guesses
"""

import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class BigBrandProbe:
    def __init__(self):
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(url, key)
        self.timestamp = datetime.now()
        
        # Target big brands
        self.big_brands = [
            'royal_canin',
            'hills',
            'purina',
            'purina_one',
            'purina_pro_plan',
            'taste_of_the_wild'
        ]
        
        print("="*70)
        print("PROMPT F: BIG BRAND PROBE")
        print("="*70)
        print(f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
    
    def probe_brand(self, brand_slug):
        """Deep probe of a single brand"""
        print(f"\n{'='*50}")
        print(f"PROBING: {brand_slug}")
        print('='*50)
        
        # Check in Preview
        try:
            resp = self.supabase.table('foods_published_preview').select("*").eq('brand_slug', brand_slug).execute()
            
            if resp.data and len(resp.data) > 0:
                count = len(resp.data)
                print(f"✅ FOUND in Preview: {count} products")
                
                # Show top 10 product names as proof
                print("\nSample products (first 10):")
                for i, product in enumerate(resp.data[:10], 1):
                    print(f"  {i}. {product.get('product_name', 'N/A')}")
                
                # Life stage breakdown
                adult = sum(1 for p in resp.data if p.get('life_stage') == 'adult')
                puppy = sum(1 for p in resp.data if p.get('life_stage') == 'puppy')
                senior = sum(1 for p in resp.data if p.get('life_stage') == 'senior')
                print(f"\nLife stages: Adult={adult}, Puppy={puppy}, Senior={senior}")
                
                # Form breakdown
                dry = sum(1 for p in resp.data if p.get('form') == 'dry')
                wet = sum(1 for p in resp.data if p.get('form') == 'wet')
                print(f"Forms: Dry={dry}, Wet={wet}")
                
                return {'found': True, 'count': count, 'products': resp.data}
            else:
                print(f"❌ NOT FOUND in Preview")
                return {'found': False, 'count': 0}
                
        except Exception as e:
            print(f"Error probing {brand_slug}: {e}")
            return {'found': False, 'count': 0, 'error': str(e)}
    
    def check_alternative_names(self, brand_slug):
        """Check for alternative brand names"""
        print(f"\nChecking alternative names for {brand_slug}...")
        
        # Define alternative patterns
        alternatives = {
            'royal_canin': ['Royal Canin', 'ROYAL CANIN', 'Royal|Canin'],
            'hills': ["Hill's", 'Hills', "Hill's Science Plan", "Hill's Prescription Diet"],
            'purina': ['Purina', 'PURINA'],
            'purina_pro_plan': ['Purina Pro Plan', 'Pro Plan'],
            'purina_one': ['Purina ONE', 'Purina One'],
            'taste_of_the_wild': ['Taste of the Wild', 'Taste|of the Wild']
        }
        
        if brand_slug in alternatives:
            for alt_name in alternatives[brand_slug]:
                try:
                    resp = self.supabase.table('foods_published_preview').select("product_name,brand").ilike('brand', f'%{alt_name}%').limit(5).execute()
                    
                    if resp.data:
                        print(f"  Found with brand name '{alt_name}':")
                        for p in resp.data:
                            print(f"    - {p.get('brand')}: {p.get('product_name')}")
                except:
                    pass
    
    def suggest_harvest_sources(self, brand_slug):
        """Suggest where to harvest this brand"""
        print(f"\n📋 HARVEST SUGGESTIONS for {brand_slug}:")
        
        sources = {
            'royal_canin': [
                "https://www.royalcanin.com/uk",
                "https://www.zooplus.co.uk (search: Royal Canin)",
                "https://www.petsathome.com (brand: Royal Canin)"
            ],
            'hills': [
                "https://www.hillspet.co.uk",
                "https://www.zooplus.co.uk (search: Hill's)",
                "https://www.petsathome.com (brand: Hill's Science Plan)"
            ],
            'purina': [
                "https://www.purina.co.uk",
                "https://www.zooplus.co.uk (search: Purina)",
                "https://www.tesco.com (pet food section)"
            ],
            'purina_pro_plan': [
                "https://www.purina.co.uk/pro-plan",
                "https://www.zooplus.co.uk (search: Pro Plan)",
                "https://www.petsathome.com (brand: Purina Pro Plan)"
            ],
            'purina_one': [
                "https://www.purina.co.uk/one",
                "https://www.tesco.com (search: Purina ONE)",
                "https://www.amazon.co.uk (search: Purina ONE dog)"
            ],
            'taste_of_the_wild': [
                "https://www.tasteofthewildpetfood.com",
                "https://www.petsathome.com (search: Taste of the Wild)",
                "https://www.amazon.co.uk (search: Taste of the Wild)"
            ]
        }
        
        if brand_slug in sources:
            for source in sources[brand_slug]:
                print(f"  - {source}")
    
    def generate_report(self, results):
        """Generate big brand report"""
        report_path = Path('/Users/sergiubiris/Desktop/lupito-content/docs/BIG-BRAND-PROBE.md')
        
        content = f"""# BIG BRAND PROBE REPORT
Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Summary

Checking presence of major brands in Preview catalog.

## Brand Status

| Brand | Status | Count | Notes |
|-------|--------|-------|-------|
"""
        
        for brand_slug, data in results.items():
            status = "✅ Found" if data['found'] else "❌ Not Found"
            count = data['count']
            notes = "Ready" if data['found'] else "Needs harvest"
            content += f"| {brand_slug} | {status} | {count} | {notes} |\n"
        
        content += "\n## Harvest Queue\n\n"
        
        for brand_slug, data in results.items():
            if not data['found']:
                content += f"\n### {brand_slug}\n"
                content += "**Priority: HIGH**\n\n"
                content += "Suggested sources:\n"
                
                sources = {
                    'royal_canin': "- https://www.royalcanin.com/uk\n- Zooplus UK\n",
                    'purina': "- https://www.purina.co.uk\n- Major UK retailers\n",
                    'taste_of_the_wild': "- https://www.tasteofthewildpetfood.com\n- Amazon UK\n"
                }
                
                content += sources.get(brand_slug, "- Check brand website\n- Major pet retailers\n")
        
        content += "\n## Next Steps\n\n"
        content += "1. Harvest missing big brands from suggested sources\n"
        content += "2. Re-run canonicalization and enrichment\n"
        content += "3. Verify quality gates are met\n"
        content += "4. Promote to production\n"
        
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(content)
        print(f"\n✅ Report saved to: {report_path}")

def main():
    prober = BigBrandProbe()
    
    results = {}
    
    # Probe each big brand
    for brand_slug in prober.big_brands:
        result = prober.probe_brand(brand_slug)
        results[brand_slug] = result
        
        if not result['found']:
            prober.check_alternative_names(brand_slug)
            prober.suggest_harvest_sources(brand_slug)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    found_brands = [b for b, r in results.items() if r['found']]
    missing_brands = [b for b, r in results.items() if not r['found']]
    
    print(f"\n✅ Found brands ({len(found_brands)}):")
    for brand in found_brands:
        print(f"  - {brand}: {results[brand]['count']} products")
    
    if missing_brands:
        print(f"\n❌ Missing brands ({len(missing_brands)}):")
        for brand in missing_brands:
            print(f"  - {brand}: NOT HARVESTED YET")
        
        print("\n⚠️  TOP HARVEST QUEUE:")
        for brand in missing_brands[:3]:
            print(f"  1. {brand} - HIGH PRIORITY")
    
    # Generate report
    prober.generate_report(results)
    
    print("\n✅ PROMPT F COMPLETE: Big brand probe complete")

if __name__ == "__main__":
    main()