#!/usr/bin/env python3
"""
Prompt 5: Acceptance gates & go/no-go for promotion
Goal: Decide what gets promoted from Preview → Prod safely
"""

import os
import json
from datetime import datetime
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Dict, List, Tuple

load_dotenv()

class AcceptanceGateChecker:
    def __init__(self):
        self.supabase = self._init_supabase()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Food-ready gates
        self.gates = {
            'life_stage': 95,      # ≥95%
            'form': 90,            # ≥90%
            'ingredients': 85,     # ≥85%
            'kcal_valid': 90,      # ≥90%
            'kcal_outliers': 0     # Must be 0
        }
        
    def _init_supabase(self) -> Client:
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        return create_client(url, key)
    
    def check_food_ready_gates(self) -> pd.DataFrame:
        """Check which brands meet all Food-ready gates"""
        print("\n" + "="*60)
        print(f"PROMPT 5: ACCEPTANCE GATES & GO/NO-GO")
        print(f"Timestamp: {self.timestamp}")
        print("="*60)
        
        print("\n🔍 CHECKING FOOD-READY GATES")
        print("-" * 40)
        print("Gates required:")
        print(f"  • Life Stage ≥ {self.gates['life_stage']}%")
        print(f"  • Form ≥ {self.gates['form']}%")
        print(f"  • Ingredients ≥ {self.gates['ingredients']}%")
        print(f"  • Kcal Valid (200-600) ≥ {self.gates['kcal_valid']}%")
        print(f"  • Kcal Outliers = {self.gates['kcal_outliers']}")
        
        # Fetch all data from Preview
        print("\nFetching Preview data...")
        response = self.supabase.table('foods_published_preview').select('*').execute()
        df = pd.DataFrame(response.data)
        print(f"✓ Fetched {len(df)} rows from foods_published_preview")
        
        # Calculate metrics per brand
        brand_metrics = []
        
        for brand_slug in df['brand_slug'].unique():
            if pd.isna(brand_slug):
                continue
            
            brand_df = df[df['brand_slug'] == brand_slug]
            brand_name = brand_df['brand'].iloc[0] if len(brand_df) > 0 else brand_slug
            
            # Calculate coverage percentages
            total = len(brand_df)
            
            # Form coverage
            form_count = brand_df['form'].notna().sum()
            form_pct = (form_count / total) * 100 if total > 0 else 0
            
            # Life stage coverage
            life_stage_count = brand_df['life_stage'].notna().sum()
            life_stage_pct = (life_stage_count / total) * 100 if total > 0 else 0
            
            # Ingredients coverage (check if list is not empty)
            ingredients_count = 0
            for idx, row in brand_df.iterrows():
                ingredients = row.get('ingredients_tokens', [])
                if isinstance(ingredients, (list, str)):
                    if isinstance(ingredients, str):
                        try:
                            ingredients = json.loads(ingredients)
                        except:
                            ingredients = []
                    if len(ingredients) > 0:
                        ingredients_count += 1
            ingredients_pct = (ingredients_count / total) * 100 if total > 0 else 0
            
            # Kcal validation
            kcal_valid_count = 0
            kcal_outliers = 0
            for kcal in brand_df['kcal_per_100g']:
                if pd.notna(kcal):
                    if 200 <= kcal <= 600:
                        kcal_valid_count += 1
                    else:
                        kcal_outliers += 1
            
            kcal_valid_pct = (kcal_valid_count / total) * 100 if total > 0 else 0
            
            # Check if meets all gates
            meets_gates = (
                life_stage_pct >= self.gates['life_stage'] and
                form_pct >= self.gates['form'] and
                ingredients_pct >= self.gates['ingredients'] and
                kcal_valid_pct >= self.gates['kcal_valid'] and
                kcal_outliers == self.gates['kcal_outliers']
            )
            
            brand_metrics.append({
                'brand_slug': brand_slug,
                'brand_name': brand_name,
                'sku_count': total,
                'form_pct': form_pct,
                'life_stage_pct': life_stage_pct,
                'ingredients_pct': ingredients_pct,
                'kcal_valid_pct': kcal_valid_pct,
                'kcal_outliers': kcal_outliers,
                'meets_all_gates': meets_gates
            })
        
        metrics_df = pd.DataFrame(brand_metrics)
        metrics_df = metrics_df.sort_values(['meets_all_gates', 'sku_count'], ascending=[False, False])
        
        return metrics_df
    
    def generate_promotion_candidates(self, metrics_df: pd.DataFrame) -> List[Dict]:
        """Generate list of brands ready for promotion"""
        print("\n✅ PROMOTION CANDIDATES")
        print("-" * 40)
        
        candidates = metrics_df[metrics_df['meets_all_gates'] == True]
        
        if len(candidates) == 0:
            print("⚠️  No brands currently meet all gates for promotion")
            return []
        
        print(f"Found {len(candidates)} brands meeting all gates:\n")
        
        promotion_list = []
        for _, row in candidates.iterrows():
            print(f"  • {row['brand_name']} ({row['brand_slug']})")
            print(f"    - SKUs: {row['sku_count']}")
            print(f"    - Form: {row['form_pct']:.1f}%")
            print(f"    - Life Stage: {row['life_stage_pct']:.1f}%")
            print(f"    - Ingredients: {row['ingredients_pct']:.1f}%")
            print(f"    - Kcal Valid: {row['kcal_valid_pct']:.1f}%")
            print()
            
            promotion_list.append({
                'brand_slug': row['brand_slug'],
                'brand_name': row['brand_name'],
                'sku_count': row['sku_count']
            })
        
        return promotion_list
    
    def draft_promotion_sql(self, promotion_list: List[Dict]) -> str:
        """Draft SQL to promote brands to ACTIVE status"""
        print("\n📝 DRAFT PROMOTION SQL")
        print("-" * 40)
        
        if len(promotion_list) == 0:
            print("No brands to promote")
            return None
        
        sql = """-- Promotion SQL for brands meeting all gates
-- Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """

BEGIN;

-- Update brand_allowlist to ACTIVE for qualified brands
"""
        
        for brand in promotion_list:
            sql += f"""
-- Promote {brand['brand_name']} ({brand['sku_count']} SKUs)
INSERT INTO brand_allowlist (brand_slug, brand_name, status, updated_at)
VALUES ('{brand['brand_slug']}', '{brand['brand_name']}', 'ACTIVE', NOW())
ON CONFLICT (brand_slug) 
DO UPDATE SET 
    status = 'ACTIVE',
    updated_at = NOW()
WHERE brand_allowlist.status != 'ACTIVE';
"""
        
        sql += """

-- Refresh materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_preview_mv;
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_prod_mv;

-- Verify the promotion
SELECT 
    brand_slug,
    brand_name,
    status,
    updated_at
FROM brand_allowlist
WHERE status = 'ACTIVE'
ORDER BY updated_at DESC;

COMMIT;

-- Rollback command (if needed):
-- UPDATE brand_allowlist SET status = 'PENDING' WHERE brand_slug IN (""" + \
    ', '.join([f"'{b['brand_slug']}'" for b in promotion_list]) + """);
"""
        
        sql_file = f"sql/promotion_sql_{self.timestamp}.sql"
        os.makedirs("sql", exist_ok=True)
        with open(sql_file, 'w') as f:
            f.write(sql)
        
        print(f"✅ SQL saved to: {sql_file}")
        print("\n⚠️  DO NOT EXECUTE YET - Review GO/NO-GO summary first")
        
        return sql_file
    
    def generate_go_no_go_summary(self, metrics_df: pd.DataFrame, promotion_list: List[Dict]):
        """Generate GO/NO-GO decision summary"""
        print("\n" + "="*40)
        print("🚦 GO/NO-GO SUMMARY")
        print("="*40)
        
        # Current Prod stats
        try:
            prod_response = self.supabase.table('foods_published_prod').select('brand_slug').execute()
            current_prod_skus = len(prod_response.data)
            current_prod_brands = len(set([r['brand_slug'] for r in prod_response.data if r.get('brand_slug')]))
        except:
            current_prod_skus = 0
            current_prod_brands = 0
        
        # Calculate impact
        new_skus = sum([b['sku_count'] for b in promotion_list])
        new_brands = len(promotion_list)
        
        print(f"\n📊 CURRENT STATE:")
        print(f"  • Production SKUs: {current_prod_skus:,}")
        print(f"  • Production Brands: {current_prod_brands}")
        
        print(f"\n📈 AFTER PROMOTION:")
        print(f"  • New SKUs to add: +{new_skus:,}")
        print(f"  • New brands to activate: +{new_brands}")
        print(f"  • Total Production SKUs: {current_prod_skus + new_skus:,}")
        
        # Safety checks
        print(f"\n🔒 SAFETY CHECKS:")
        
        safety_passed = True
        
        # Check 1: Will Prod have content?
        if current_prod_skus + new_skus > 0:
            print(f"  ✅ Food will have {current_prod_skus + new_skus:,} SKUs after promotion")
        else:
            print(f"  ❌ WARNING: Food would be empty after promotion!")
            safety_passed = False
        
        # Check 2: Are we promoting quality brands?
        if new_brands > 0:
            avg_completion = metrics_df[metrics_df['meets_all_gates']]['life_stage_pct'].mean()
            print(f"  ✅ Average life_stage coverage of promoted brands: {avg_completion:.1f}%")
        else:
            print(f"  ⚠️  No brands to promote")
        
        # Check 3: Verify key brands
        key_brands = ['royal_canin', 'hills', 'purina', 'purina_pro_plan']
        print(f"\n🔍 KEY BRAND STATUS:")
        for brand in key_brands:
            brand_data = metrics_df[metrics_df['brand_slug'] == brand]
            if len(brand_data) > 0:
                row = brand_data.iloc[0]
                if row['meets_all_gates']:
                    print(f"  ✅ {brand}: Ready for promotion ({row['sku_count']} SKUs)")
                else:
                    issues = []
                    if row['life_stage_pct'] < self.gates['life_stage']:
                        issues.append(f"life_stage {row['life_stage_pct']:.1f}%")
                    if row['form_pct'] < self.gates['form']:
                        issues.append(f"form {row['form_pct']:.1f}%")
                    print(f"  ⚠️  {brand}: Not ready - {', '.join(issues)}")
            else:
                print(f"  ❌ {brand}: Not found in catalog")
        
        # Final decision
        print(f"\n{'='*40}")
        if safety_passed and new_brands > 0:
            print("✅ GO - Safe to proceed with promotion")
            print(f"   {new_brands} brands with {new_skus:,} SKUs ready")
        elif new_brands == 0:
            print("⚠️  NO-GO - No brands meet all gates")
            print("   Continue enrichment to improve coverage")
        else:
            print("❌ NO-GO - Safety checks failed")
            print("   Review issues before proceeding")
        print("="*40)
        
        # Generate detailed report
        report_file = f"reports/GO_NO_GO_DECISION_{self.timestamp}.md"
        os.makedirs("reports", exist_ok=True)
        
        content = f"""# GO/NO-GO DECISION REPORT

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Acceptance Gates
- Life Stage ≥ {self.gates['life_stage']}%
- Form ≥ {self.gates['form']}%
- Ingredients ≥ {self.gates['ingredients']}%
- Kcal Valid ≥ {self.gates['kcal_valid']}%
- Kcal Outliers = {self.gates['kcal_outliers']}

## Promotion Candidates

### Brands Meeting All Gates ({len(promotion_list)})
"""
        
        if promotion_list:
            for brand in promotion_list:
                content += f"- **{brand['brand_name']}**: {brand['sku_count']} SKUs\n"
        else:
            content += "None - no brands meet all gates\n"
        
        content += f"""

## Impact Analysis

| Metric | Current Prod | After Promotion | Change |
|--------|-------------|-----------------|--------|
| Total SKUs | {current_prod_skus:,} | {current_prod_skus + new_skus:,} | +{new_skus:,} |
| Active Brands | {current_prod_brands} | {current_prod_brands + new_brands} | +{new_brands} |

## Brands Not Ready

### Top Brands Failing Gates
"""
        
        failing = metrics_df[metrics_df['meets_all_gates'] == False].head(10)
        for _, row in failing.iterrows():
            issues = []
            if row['life_stage_pct'] < self.gates['life_stage']:
                issues.append(f"life_stage: {row['life_stage_pct']:.1f}%")
            if row['form_pct'] < self.gates['form']:
                issues.append(f"form: {row['form_pct']:.1f}%")
            if row['ingredients_pct'] < self.gates['ingredients']:
                issues.append(f"ingredients: {row['ingredients_pct']:.1f}%")
            if row['kcal_valid_pct'] < self.gates['kcal_valid']:
                issues.append(f"kcal: {row['kcal_valid_pct']:.1f}%")
            if row['kcal_outliers'] > 0:
                issues.append(f"outliers: {row['kcal_outliers']}")
            
            content += f"- **{row['brand_name']}** ({row['sku_count']} SKUs): {', '.join(issues)}\n"
        
        content += f"""

## Decision

**{"✅ GO" if safety_passed and new_brands > 0 else "❌ NO-GO"}**

{"Proceed with promotion of " + str(new_brands) + " brands" if safety_passed and new_brands > 0 else "Continue enrichment before promotion"}

## Next Steps

"""
        
        if safety_passed and new_brands > 0:
            content += f"""1. Review the promotion SQL script
2. Execute the promotion in Supabase
3. Verify Production view has {current_prod_skus + new_skus:,} SKUs
4. Run Prompt 6 for truth checks
"""
        else:
            content += """1. Continue enrichment to improve coverage
2. Focus on high-value brands with low coverage
3. Re-run acceptance gates after improvements
"""
        
        with open(report_file, 'w') as f:
            f.write(content)
        
        print(f"\n✅ Decision report saved: {report_file}")
        
        return report_file
    
    def run(self):
        """Execute acceptance gate checks"""
        # Check gates
        metrics_df = self.check_food_ready_gates()
        
        # Generate promotion candidates
        promotion_list = self.generate_promotion_candidates(metrics_df)
        
        # Draft SQL
        sql_file = self.draft_promotion_sql(promotion_list)
        
        # Generate GO/NO-GO summary
        report_file = self.generate_go_no_go_summary(metrics_df, promotion_list)
        
        print("\n" + "="*60)
        print("PROMPT 5 COMPLETE")
        print("="*60)
        
        if promotion_list:
            print(f"\n✅ {len(promotion_list)} brands ready for promotion")
            print(f"📋 Review: {report_file}")
            print(f"📝 SQL: {sql_file}")
        else:
            print("\n⚠️  No brands currently meet all gates")
            print("Continue with enrichment to improve coverage")
        
        return {
            'metrics': metrics_df,
            'candidates': promotion_list,
            'sql_file': sql_file,
            'report': report_file
        }

if __name__ == "__main__":
    checker = AcceptanceGateChecker()
    checker.run()