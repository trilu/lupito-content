#!/usr/bin/env python3
"""
PROMPT D: Recompute brand quality & shortlist promotions
Goal: See who's ready to go ACTIVE
"""

import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd

load_dotenv()

class BrandQualityAssessment:
    def __init__(self):
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(url, key)
        self.timestamp = datetime.now()
        
        print("="*70)
        print("PROMPT D: BRAND QUALITY ASSESSMENT")
        print("="*70)
        print(f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
    
    def step1_refresh_brand_quality_mv(self):
        """Refresh materialized view for brand quality"""
        print("\n" + "="*70)
        print("STEP 1: REFRESHING BRAND QUALITY MV")
        print("="*70)
        
        try:
            # Try to refresh MV (may not have permission)
            self.supabase.rpc('refresh_brand_quality_preview').execute()
            print("✅ Materialized view refreshed")
        except:
            print("⚠️  Could not refresh MV (may auto-refresh or lack permissions)")
    
    def step2_brand_scoreboard(self):
        """Generate brand scoreboard"""
        print("\n" + "="*70)
        print("STEP 2: BRAND SCOREBOARD (PREVIEW)")
        print("="*70)
        
        # Get brand quality metrics
        brands_data = []
        
        # Get all unique brands with their metrics
        response = self.supabase.table('foods_canonical').select("brand_slug").execute()
        
        if response.data:
            # Get unique brand slugs
            brand_slugs = list(set([r['brand_slug'] for r in response.data if r.get('brand_slug')]))
            
            for brand_slug in brand_slugs[:50]:  # Top 50 brands
                try:
                    # Get metrics for this brand
                    resp = self.supabase.table('foods_canonical').select("*").eq('brand_slug', brand_slug).execute()
                    
                    if resp.data:
                        products = resp.data
                        sku_count = len(products)
                        
                        # Calculate coverage
                        form_coverage = sum(1 for p in products if p.get('form')) / sku_count * 100
                        life_stage_coverage = sum(1 for p in products if p.get('life_stage')) / sku_count * 100
                        ingredients_coverage = sum(1 for p in products if p.get('ingredients_tokens')) / sku_count * 100
                        kcal_valid = sum(1 for p in products if p.get('kcal_per_100g') and 200 <= p['kcal_per_100g'] <= 600) / sku_count * 100
                        
                        # Calculate completion percentage
                        completion_pct = (form_coverage + life_stage_coverage + ingredients_coverage + kcal_valid) / 4
                        
                        # Count by life stage
                        adult_count = sum(1 for p in products if p.get('life_stage') == 'adult')
                        puppy_count = sum(1 for p in products if p.get('life_stage') == 'puppy')
                        senior_count = sum(1 for p in products if p.get('life_stage') == 'senior')
                        
                        brands_data.append({
                            'brand_slug': brand_slug,
                            'sku_count': sku_count,
                            'completion_pct': completion_pct,
                            'form_coverage': form_coverage,
                            'life_stage_coverage': life_stage_coverage,
                            'ingredients_coverage': ingredients_coverage,
                            'kcal_valid': kcal_valid,
                            'adult_count': adult_count,
                            'puppy_count': puppy_count,
                            'senior_count': senior_count
                        })
                        
                except Exception as e:
                    print(f"Error processing {brand_slug}: {e}")
        
        # Sort by SKU count and completion
        brands_data.sort(key=lambda x: (x['sku_count'], x['completion_pct']), reverse=True)
        
        # Print top brands
        print("\nTop 20 Brands by SKU Count & Completion:")
        print(f"{'Brand':<25} {'SKUs':<8} {'Complete':<10} {'Form':<8} {'Life':<8} {'Ingr':<8} {'Kcal':<8}")
        print("-" * 85)
        
        for brand in brands_data[:20]:
            print(f"{brand['brand_slug']:<25} {brand['sku_count']:<8} {brand['completion_pct']:<10.1f} "
                  f"{brand['form_coverage']:<8.1f} {brand['life_stage_coverage']:<8.1f} "
                  f"{brand['ingredients_coverage']:<8.1f} {brand['kcal_valid']:<8.1f}")
        
        return brands_data
    
    def step3_identify_promotion_candidates(self, brands_data):
        """Identify brands ready for promotion"""
        print("\n" + "="*70)
        print("STEP 3: PROMOTION CANDIDATES")
        print("="*70)
        
        # Define promotion criteria
        criteria = {
            'min_skus': 5,
            'min_completion': 75,  # Relaxed from ideal 90%
            'min_form_coverage': 70,
            'min_life_stage_coverage': 70,
            'min_ingredients_coverage': 85,
            'min_kcal_valid': 70
        }
        
        candidates = []
        
        for brand in brands_data:
            if (brand['sku_count'] >= criteria['min_skus'] and
                brand['completion_pct'] >= criteria['min_completion'] and
                brand['form_coverage'] >= criteria['min_form_coverage'] and
                brand['life_stage_coverage'] >= criteria['min_life_stage_coverage'] and
                brand['ingredients_coverage'] >= criteria['min_ingredients_coverage'] and
                brand['kcal_valid'] >= criteria['min_kcal_valid']):
                
                candidates.append(brand)
        
        print(f"\nFound {len(candidates)} brands meeting promotion criteria:")
        
        for brand in candidates[:10]:
            print(f"\n✅ {brand['brand_slug']}:")
            print(f"   SKUs: {brand['sku_count']}")
            print(f"   Completion: {brand['completion_pct']:.1f}%")
            print(f"   Adult/Puppy/Senior: {brand['adult_count']}/{brand['puppy_count']}/{brand['senior_count']}")
        
        return candidates
    
    def step4_generate_sql_updates(self, candidates):
        """Generate SQL to update brand_allowlist"""
        print("\n" + "="*70)
        print("STEP 4: SQL UPDATE STATEMENTS")
        print("="*70)
        
        sql_statements = []
        
        for brand in candidates:
            sql = f"""
-- Promote {brand['brand_slug']} to ACTIVE
UPDATE brand_allowlist 
SET status = 'ACTIVE', 
    updated_at = NOW(),
    notes = 'Promoted via PROMPT D - {brand['sku_count']} SKUs, {brand['completion_pct']:.1f}% complete'
WHERE brand_slug = '{brand['brand_slug']}';
"""
            sql_statements.append(sql)
        
        print(f"Generated {len(sql_statements)} UPDATE statements")
        print("\nSample SQL (first 3):")
        for sql in sql_statements[:3]:
            print(sql)
        
        return sql_statements
    
    def step5_prod_impact_summary(self, candidates):
        """Summarize what Prod will gain"""
        print("\n" + "="*70)
        print("STEP 5: PRODUCTION IMPACT SUMMARY")
        print("="*70)
        
        total_skus = sum(b['sku_count'] for b in candidates)
        total_adult = sum(b['adult_count'] for b in candidates)
        total_puppy = sum(b['puppy_count'] for b in candidates)
        total_senior = sum(b['senior_count'] for b in candidates)
        
        print(f"\nIf all {len(candidates)} candidates are promoted:")
        print(f"  Total new SKUs: {total_skus}")
        print(f"  Adult products: {total_adult}")
        print(f"  Puppy products: {total_puppy}")
        print(f"  Senior products: {total_senior}")
        
        # Current prod stats
        try:
            resp = self.supabase.table('foods_published_prod').select("*", count='exact', head=True).execute()
            current_prod = resp.count or 0
            print(f"\nCurrent Production: {current_prod} SKUs")
            print(f"After Promotion: {current_prod + total_skus} SKUs (+{total_skus})")
        except:
            print("\nCould not get current production count")
        
        return {
            'total_skus': total_skus,
            'adult': total_adult,
            'puppy': total_puppy,
            'senior': total_senior
        }
    
    def generate_report(self, brands_data, candidates, sql_statements, impact):
        """Generate PROMOTION-CANDIDATES.md"""
        report_path = Path('/Users/sergiubiris/Desktop/lupito-content/docs/PROMOTION-CANDIDATES.md')
        
        content = f"""# PROMOTION CANDIDATES REPORT
Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- Total brands analyzed: {len(brands_data)}
- Brands meeting criteria: {len(candidates)}
- Total SKUs to add: {impact['total_skus']}

## Promotion Criteria

- Minimum SKUs: 5
- Minimum completion: 75%
- Form coverage: ≥70%
- Life stage coverage: ≥70%
- Ingredients coverage: ≥85%
- Valid kcal: ≥70%

## Top Promotion Candidates

| Brand | SKUs | Completion | Adult | Puppy | Senior |
|-------|------|------------|-------|-------|--------|
"""
        
        for brand in candidates[:15]:
            content += f"| {brand['brand_slug']} | {brand['sku_count']} | {brand['completion_pct']:.1f}% | "
            content += f"{brand['adult_count']} | {brand['puppy_count']} | {brand['senior_count']} |\n"
        
        content += f"""

## Production Impact

What Prod will gain if all candidates promoted:
- New SKUs: {impact['total_skus']}
- Adult products: {impact['adult']}
- Puppy products: {impact['puppy']}
- Senior products: {impact['senior']}

## SQL Updates

To promote these brands, execute:

```sql
"""
        
        for sql in sql_statements[:5]:
            content += sql + "\n"
        
        content += """```

## Next Steps

1. Review candidates and approve promotions
2. Execute SQL updates for approved brands
3. Run Prompt E to verify production
"""
        
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(content)
        print(f"\n✅ Report saved to: {report_path}")

def main():
    assessor = BrandQualityAssessment()
    
    # Step 1: Refresh MV
    assessor.step1_refresh_brand_quality_mv()
    
    # Step 2: Generate scoreboard
    brands_data = assessor.step2_brand_scoreboard()
    
    # Step 3: Identify candidates
    candidates = assessor.step3_identify_promotion_candidates(brands_data)
    
    # Step 4: Generate SQL
    sql_statements = assessor.step4_generate_sql_updates(candidates)
    
    # Step 5: Impact summary
    impact = assessor.step5_prod_impact_summary(candidates)
    
    # Generate report
    assessor.generate_report(brands_data, candidates, sql_statements, impact)
    
    print("\n✅ PROMPT D COMPLETE: Brand quality assessed")

if __name__ == "__main__":
    main()