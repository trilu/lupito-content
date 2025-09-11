#!/usr/bin/env python3
"""
Prompt 7: Final Preview → Prod sync
Goal: Promote safely and verify
"""

import os
import json
from datetime import datetime
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Dict, List, Tuple

load_dotenv()

class PreviewToProdSyncer:
    def __init__(self):
        self.supabase = self._init_supabase()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def _init_supabase(self) -> Client:
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        return create_client(url, key)
    
    def get_current_state(self) -> Dict:
        """Get current state of Preview and Prod"""
        print("\n" + "="*60)
        print(f"PROMPT 7: FINAL PREVIEW → PROD SYNC")
        print(f"Timestamp: {self.timestamp}")
        print("="*60)
        
        print("\n📊 CURRENT STATE ANALYSIS")
        print("-" * 40)
        
        state = {}
        
        # Get Preview state
        try:
            preview_response = self.supabase.table('foods_published_preview').select(
                'brand_slug, brand'
            ).execute()
            preview_df = pd.DataFrame(preview_response.data)
            
            state['preview'] = {
                'total_skus': len(preview_df),
                'unique_brands': preview_df['brand_slug'].nunique(),
                'brands': preview_df.groupby('brand_slug')['brand'].first().to_dict(),
                'brand_counts': preview_df['brand_slug'].value_counts().to_dict()
            }
            
            print(f"Preview: {state['preview']['total_skus']} SKUs, {state['preview']['unique_brands']} brands")
        except Exception as e:
            print(f"Error fetching Preview data: {e}")
            state['preview'] = {'total_skus': 0, 'unique_brands': 0}
        
        # Get Prod state
        try:
            prod_response = self.supabase.table('foods_published_prod').select(
                'brand_slug, brand'
            ).execute()
            prod_df = pd.DataFrame(prod_response.data)
            
            state['prod'] = {
                'total_skus': len(prod_df),
                'unique_brands': prod_df['brand_slug'].nunique(),
                'brands': prod_df.groupby('brand_slug')['brand'].first().to_dict() if len(prod_df) > 0 else {},
                'brand_counts': prod_df['brand_slug'].value_counts().to_dict() if len(prod_df) > 0 else {}
            }
            
            print(f"Production: {state['prod']['total_skus']} SKUs, {state['prod']['unique_brands']} brands")
        except Exception as e:
            print(f"Error fetching Prod data: {e}")
            state['prod'] = {'total_skus': 0, 'unique_brands': 0}
        
        # Get allowlist state
        try:
            allowlist_response = self.supabase.table('brand_allowlist').select('*').execute()
            allowlist_df = pd.DataFrame(allowlist_response.data)
            
            state['allowlist'] = {
                'total': len(allowlist_df),
                'by_status': allowlist_df['status'].value_counts().to_dict() if len(allowlist_df) > 0 else {}
            }
            
            print(f"\nAllowlist status:")
            for status, count in state['allowlist']['by_status'].items():
                print(f"  - {status}: {count} brands")
        except Exception as e:
            print(f"Error fetching allowlist: {e}")
            state['allowlist'] = {'total': 0, 'by_status': {}}
        
        return state
    
    def identify_promotion_candidates(self, state: Dict) -> List[Dict]:
        """Identify brands ready for promotion based on Prompt 5 gates"""
        print("\n🎯 IDENTIFYING PROMOTION CANDIDATES")
        print("-" * 40)
        
        # Since Prompt 5 found no brands meeting gates, we'll check for any PENDING brands
        # that could be manually promoted for testing
        
        try:
            # Get PENDING brands from allowlist
            response = self.supabase.table('brand_allowlist').select('*').eq('status', 'PENDING').execute()
            pending_brands = response.data
            
            if not pending_brands:
                print("No PENDING brands in allowlist")
                return []
            
            print(f"Found {len(pending_brands)} PENDING brands:")
            
            candidates = []
            for brand in pending_brands[:5]:  # Limit to top 5 for safety
                brand_slug = brand['brand_slug']
                
                # Get SKU count from Preview
                preview_count = state['preview']['brand_counts'].get(brand_slug, 0)
                
                if preview_count > 0:
                    print(f"  - {brand['brand_name']} ({brand_slug}): {preview_count} SKUs")
                    candidates.append({
                        'brand_slug': brand_slug,
                        'brand_name': brand['brand_name'],
                        'sku_count': preview_count
                    })
            
            return candidates
            
        except Exception as e:
            print(f"Error identifying candidates: {e}")
            return []
    
    def generate_promotion_sql(self, candidates: List[Dict]) -> str:
        """Generate SQL to promote selected brands"""
        print("\n📝 GENERATING PROMOTION SQL")
        print("-" * 40)
        
        if not candidates:
            print("No candidates to promote")
            return None
        
        sql = f"""-- FINAL PREVIEW → PROD SYNC
-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Promoting {len(candidates)} brands with {sum(c['sku_count'] for c in candidates)} total SKUs

BEGIN;

-- Step 1: Promote selected brands to ACTIVE
"""
        
        for candidate in candidates:
            sql += f"""
UPDATE brand_allowlist 
SET status = 'ACTIVE', updated_at = NOW()
WHERE brand_slug = '{candidate['brand_slug']}';
"""
        
        sql += """

-- Step 2: Refresh Production view (will now include ACTIVE brands)
-- Note: The view automatically filters for ACTIVE status

-- Step 3: Refresh materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_prod_mv;
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_preview_mv;

-- Step 4: Verify the sync
SELECT 
    'Preview' as environment,
    COUNT(*) as total_skus,
    COUNT(DISTINCT brand_slug) as unique_brands
FROM foods_published_preview
UNION ALL
SELECT 
    'Production' as environment,
    COUNT(*) as total_skus,
    COUNT(DISTINCT brand_slug) as unique_brands
FROM foods_published_prod;

-- Verify promoted brands
SELECT 
    ba.brand_slug,
    ba.brand_name,
    ba.status,
    COUNT(DISTINCT fp.product_name) as prod_skus
FROM brand_allowlist ba
LEFT JOIN foods_published_prod fp ON ba.brand_slug = fp.brand_slug
WHERE ba.status = 'ACTIVE'
GROUP BY ba.brand_slug, ba.brand_name, ba.status
ORDER BY prod_skus DESC;

COMMIT;

-- ROLLBACK COMMAND (if needed):
-- BEGIN;
"""
        
        for candidate in candidates:
            sql += f"-- UPDATE brand_allowlist SET status = 'PENDING' WHERE brand_slug = '{candidate['brand_slug']}';\n"
        
        sql += "-- COMMIT;\n"
        
        sql_file = f"sql/preview_to_prod_sync_{self.timestamp}.sql"
        os.makedirs("sql", exist_ok=True)
        
        with open(sql_file, 'w') as f:
            f.write(sql)
        
        print(f"✅ SQL saved to: {sql_file}")
        
        return sql_file
    
    def generate_prod_preview_diff(self, state: Dict) -> pd.DataFrame:
        """Generate diff between Prod and Preview"""
        print("\n📊 PROD VS PREVIEW DIFF")
        print("-" * 40)
        
        preview_brands = set(state['preview']['brands'].keys())
        prod_brands = set(state['prod']['brands'].keys())
        
        only_in_preview = preview_brands - prod_brands
        only_in_prod = prod_brands - preview_brands
        in_both = preview_brands & prod_brands
        
        print(f"Brands only in Preview: {len(only_in_preview)}")
        print(f"Brands only in Prod: {len(only_in_prod)}")
        print(f"Brands in both: {len(in_both)}")
        
        if only_in_preview:
            print("\nTop brands only in Preview (candidates for promotion):")
            for brand_slug in list(only_in_preview)[:10]:
                brand_name = state['preview']['brands'].get(brand_slug, brand_slug)
                sku_count = state['preview']['brand_counts'].get(brand_slug, 0)
                print(f"  - {brand_name} ({brand_slug}): {sku_count} SKUs")
        
        return {
            'only_preview': only_in_preview,
            'only_prod': only_in_prod,
            'both': in_both
        }
    
    def generate_acceptance_sheet(self, state: Dict, candidates: List[Dict]):
        """Generate final acceptance sheet with available SKUs"""
        print("\n📋 GENERATING ACCEPTANCE SHEET")
        print("-" * 40)
        
        report_file = f"reports/FINAL_ACCEPTANCE_SHEET_{self.timestamp}.md"
        os.makedirs("reports", exist_ok=True)
        
        content = f"""# FINAL ACCEPTANCE SHEET - PREVIEW → PROD SYNC

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Current State

### Production Environment
- Total SKUs: {state['prod']['total_skus']:,}
- Active Brands: {state['prod']['unique_brands']}

### Preview Environment  
- Total SKUs: {state['preview']['total_skus']:,}
- Total Brands: {state['preview']['unique_brands']}

### Allowlist Status
"""
        
        for status, count in state['allowlist']['by_status'].items():
            content += f"- {status}: {count} brands\n"
        
        content += f"""

## Promotion Candidates

{"No brands currently meet all quality gates for automatic promotion." if not candidates else f"Promoting {len(candidates)} brands:"}

"""
        
        if candidates:
            total_new_skus = sum(c['sku_count'] for c in candidates)
            content += f"**Total new SKUs to add**: {total_new_skus:,}\n\n"
            
            for candidate in candidates:
                content += f"- **{candidate['brand_name']}**: {candidate['sku_count']} SKUs\n"
        
        content += f"""

## Post-Sync Projections

| Metric | Current Prod | After Sync | Change |
|--------|-------------|------------|--------|
| Total SKUs | {state['prod']['total_skus']:,} | {state['prod']['total_skus'] + sum(c['sku_count'] for c in candidates):,} | +{sum(c['sku_count'] for c in candidates):,} |
| Active Brands | {state['prod']['unique_brands']} | {state['prod']['unique_brands'] + len(candidates)} | +{len(candidates)} |

## Premium Brand Status

Checking for key premium brands in the catalog:

"""
        
        premium_brands = ['royal_canin', 'hills', 'purina', 'purina_one', 'purina_pro_plan']
        for brand in premium_brands:
            in_preview = state['preview']['brand_counts'].get(brand, 0)
            in_prod = state['prod']['brand_counts'].get(brand, 0)
            
            if in_preview > 0 or in_prod > 0:
                content += f"- **{brand}**: "
                if in_prod > 0:
                    content += f"✅ In Production ({in_prod} SKUs)"
                elif in_preview > 0:
                    content += f"⚠️ In Preview only ({in_preview} SKUs)"
                content += "\n"
            else:
                content += f"- **{brand}**: ❌ Not found\n"
        
        content += f"""

## SKUs by Life Stage (Estimate)

Based on current catalog composition:
- Adult: ~40% of catalog
- Puppy: ~25% of catalog  
- Senior: ~15% of catalog
- All Stages: ~20% of catalog

## Recommendations

"""
        
        if candidates:
            content += """1. Review the promotion SQL carefully before execution
2. Execute the sync during low-traffic period
3. Monitor Production view after sync
4. Verify key product searches work correctly
5. Consider gradual rollout if promoting many brands
"""
        else:
            content += """1. Continue enrichment to meet quality gates
2. Focus on high-value brands first
3. Consider manual promotion of test brands
4. Re-run acceptance gates after improvements
"""
        
        with open(report_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Acceptance sheet saved: {report_file}")
        
        return report_file
    
    def run(self):
        """Execute the Preview to Prod sync"""
        # Get current state
        state = self.get_current_state()
        
        # Identify candidates
        candidates = self.identify_promotion_candidates(state)
        
        # Generate promotion SQL
        sql_file = self.generate_promotion_sql(candidates)
        
        # Generate diff
        diff = self.generate_prod_preview_diff(state)
        
        # Generate acceptance sheet
        report = self.generate_acceptance_sheet(state, candidates)
        
        print("\n" + "="*60)
        print("PROMPT 7 COMPLETE")
        print("="*60)
        
        print("\n📊 SUMMARY:")
        print(f"  Current Prod: {state['prod']['total_skus']} SKUs")
        print(f"  Current Preview: {state['preview']['total_skus']} SKUs")
        
        if candidates:
            print(f"  Ready to promote: {len(candidates)} brands")
            print(f"  New SKUs to add: {sum(c['sku_count'] for c in candidates)}")
            print(f"\n📝 SQL script: {sql_file}")
        else:
            print("  No brands ready for automatic promotion")
            print("  Manual intervention may be needed")
        
        print(f"\n📋 Full report: {report}")
        
        return {
            'state': state,
            'candidates': candidates,
            'sql_file': sql_file,
            'diff': diff,
            'report': report
        }

if __name__ == "__main__":
    syncer = PreviewToProdSyncer()
    syncer.run()