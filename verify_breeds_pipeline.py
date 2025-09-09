#!/usr/bin/env python3
"""
Verify breeds pipeline results - coverage, linkage, and quality metrics
"""

import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BreedsPipelineVerifier:
    def __init__(self):
        load_dotenv()
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase = create_client(url, key)
        
    def verify_pipeline(self):
        """Verify the complete breeds pipeline"""
        
        print("="*80)
        print("BREEDS PIPELINE VERIFICATION")
        print("="*80)
        
        # 1. Check row counts
        print("\n📊 ROW COUNTS:")
        print("-"*50)
        
        tables = [
            'breed_raw_compat',
            'breeds_compat', 
            'breeds_details_compat',
            'breeds_union_all',
            'breeds_canonical',
            'breeds_published'
        ]
        
        counts = {}
        for table in tables:
            try:
                response = self.supabase.table(table).select('*', count='exact').limit(0).execute()
                counts[table] = response.count
                print(f"✅ {table}: {response.count:,} rows")
            except Exception as e:
                print(f"❌ {table}: Not found")
                counts[table] = 0
        
        # 2. Check coverage metrics on breeds_published
        print("\n📈 COVERAGE METRICS (breeds_published):")
        print("-"*50)
        
        try:
            # Get all data from breeds_published
            response = self.supabase.table('breeds_published').select('*').execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                total = len(df)
                
                # Calculate coverage
                metrics = {
                    'size_category': df['size_category'].notna().sum() / total * 100,
                    'growth_end_months': df['growth_end_months'].notna().sum() / total * 100,
                    'senior_start_months': df['senior_start_months'].notna().sum() / total * 100,
                    'activity_baseline': df['activity_baseline'].notna().sum() / total * 100,
                    'energy_factor_mod': df['energy_factor_mod'].notna().sum() / total * 100,
                    'ideal_weight_min_kg': df['ideal_weight_min_kg'].notna().sum() / total * 100,
                    'ideal_weight_max_kg': df['ideal_weight_max_kg'].notna().sum() / total * 100
                }
                
                for field, coverage in metrics.items():
                    status = "✅" if coverage >= 90 else "⚠️" if coverage >= 70 else "❌"
                    print(f"{status} {field}: {coverage:.1f}%")
                
                # Distribution of key fields
                print("\n📊 DISTRIBUTIONS:")
                print("-"*50)
                
                # Size distribution
                print("\nSize categories:")
                size_dist = df['size_category'].value_counts()
                for size, count in size_dist.items():
                    print(f"  {size}: {count} ({count/total*100:.1f}%)")
                
                # Activity distribution
                print("\nActivity levels:")
                activity_dist = df['activity_baseline'].value_counts()
                for activity, count in activity_dist.items():
                    print(f"  {activity}: {count} ({count/total*100:.1f}%)")
                
        except Exception as e:
            print(f"❌ Error analyzing coverage: {e}")
        
        # 3. Check dogs linkage
        print("\n🐕 DOGS TABLE LINKAGE:")
        print("-"*50)
        
        try:
            # Get dogs data
            dogs_response = self.supabase.table('dogs').select('breed').execute()
            
            if dogs_response.data:
                dogs_df = pd.DataFrame(dogs_response.data)
                total_dogs = len(dogs_df)
                
                # Get breeds_published slugs
                breeds_response = self.supabase.table('breeds_published').select('breed_slug, breed_name').execute()
                breed_slugs = set()
                breed_names = set()
                
                if breeds_response.data:
                    for breed in breeds_response.data:
                        breed_slugs.add(breed['breed_slug'])
                        breed_names.add(breed['breed_name'].lower() if breed['breed_name'] else '')
                
                # Check linkage
                matched = 0
                unmatched_breeds = []
                
                for _, dog in dogs_df.iterrows():
                    breed = dog.get('breed')
                    if breed:
                        breed_lower = breed.lower().strip()
                        breed_slug = breed_lower.replace(' ', '-')
                        
                        if breed_slug in breed_slugs or breed_lower in breed_names:
                            matched += 1
                        else:
                            unmatched_breeds.append(breed)
                
                match_rate = matched / total_dogs * 100 if total_dogs > 0 else 0
                
                print(f"Total dogs: {total_dogs}")
                print(f"Dogs with breed: {dogs_df['breed'].notna().sum()}")
                print(f"Matched to canonical: {matched} ({match_rate:.1f}%)")
                
                if unmatched_breeds:
                    # Count unmapped breeds
                    from collections import Counter
                    unmapped_counts = Counter(unmatched_breeds)
                    
                    print(f"\n❌ Top unmapped breeds (need aliases):")
                    for breed, count in unmapped_counts.most_common(10):
                        suggested_slug = breed.lower().replace(' ', '-')
                        print(f"  '{breed}' ({count} dogs) → suggest: '{suggested_slug}'")
                    
                    # Generate SQL for aliases
                    print("\n📝 SQL to add missing aliases:")
                    print("```sql")
                    for breed, count in unmapped_counts.most_common(5):
                        suggested_slug = breed.lower().replace(' ', '-')
                        print(f"INSERT INTO breed_aliases (alias, canonical_slug, source) VALUES ('{breed}', '{suggested_slug}', 'dogs_table');")
                    print("```")
                
        except Exception as e:
            print(f"❌ Error checking dogs linkage: {e}")
        
        # 4. Sample data from breeds_published
        print("\n📋 SAMPLE DATA (breeds_published):")
        print("-"*50)
        
        try:
            sample_response = self.supabase.table('breeds_published').select('*').limit(10).execute()
            
            if sample_response.data:
                for i, breed in enumerate(sample_response.data, 1):
                    print(f"\n{i}. {breed['breed_name']} ({breed['breed_slug']})")
                    print(f"   Size: {breed['size_category']}, Activity: {breed['activity_baseline']}")
                    print(f"   Growth: {breed['growth_end_months']}mo, Senior: {breed['senior_start_months']}mo")
                    print(f"   Energy mod: {breed['energy_factor_mod']}")
                    
                    # Show provenance
                    if breed.get('sources'):
                        sources_list = breed['sources'] if isinstance(breed['sources'], list) else [breed['sources']]
                        source_names = [s.get('source', 'unknown') for s in sources_list if isinstance(s, dict)]
                        print(f"   Sources: {', '.join(source_names)}")
        
        except Exception as e:
            print(f"❌ Error getting sample data: {e}")
        
        # 5. Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        print(f"\n✅ Breeds published: {counts.get('breeds_published', 0):,} unique breeds")
        print(f"✅ Deduplication: {counts.get('breeds_union_all', 0) - counts.get('breeds_canonical', 0)} duplicates merged")
        
        return counts

if __name__ == "__main__":
    verifier = BreedsPipelineVerifier()
    verifier.verify_pipeline()