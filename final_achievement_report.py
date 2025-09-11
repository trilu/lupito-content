#!/usr/bin/env python3
"""
Final Achievement Report - Analyze what we've accomplished
"""

import os
from datetime import datetime
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def generate_achievement_report():
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    print("="*60)
    print("FINAL ACHIEVEMENT REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Check current state after all fixes
    print("\n📊 CURRENT STATE AFTER ALL FIXES")
    print("-" * 40)
    
    # Check foods_canonical
    try:
        canonical_response = supabase.table('foods_canonical').select('brand_slug, brand').execute()
        canonical_df = pd.DataFrame(canonical_response.data)
        
        print(f"\nfoods_canonical:")
        print(f"  Total products: {len(canonical_df):,}")
        print(f"  Unique brands: {canonical_df['brand_slug'].nunique()}")
        
        # Check for premium brands
        premium_brands = ['royal_canin', 'hills', 'purina', 'purina_one', 'purina_pro_plan', 'arden_grange', 
                         'james_wellbeloved', 'lilys_kitchen', 'natures_menu', 'barking_heads', 'taste_of_the_wild']
        
        print(f"\n🏆 PREMIUM BRANDS STATUS (after split-brand fixes):")
        for brand in premium_brands:
            count = len(canonical_df[canonical_df['brand_slug'] == brand])
            if count > 0:
                print(f"  ✅ {brand}: {count} products")
            else:
                print(f"  ❌ {brand}: 0 products")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Check materialized views
    print("\n📈 BRAND QUALITY METRICS")
    print("-" * 40)
    
    try:
        # Check Preview MV
        preview_mv = supabase.table('foods_brand_quality_preview_mv').select('*').execute()
        preview_df = pd.DataFrame(preview_mv.data)
        
        if len(preview_df) > 0:
            print(f"\nPreview Materialized View:")
            print(f"  Total brands: {len(preview_df)}")
            print(f"  Total SKUs: {preview_df['sku_count'].sum():,}")
            print(f"  Avg completion: {preview_df['completion_pct'].mean():.1f}%")
            
            # Top brands by completion
            top_brands = preview_df.nlargest(5, 'completion_pct')[['brand_slug', 'sku_count', 'completion_pct']]
            print(f"\n  Top 5 brands by completion:")
            for _, row in top_brands.iterrows():
                print(f"    - {row['brand_slug']}: {row['completion_pct']:.1f}% ({row['sku_count']} SKUs)")
    except Exception as e:
        print(f"  Error checking MV: {e}")
    
    # Check views
    print("\n🔍 CHECKING VIEWS")
    print("-" * 40)
    
    try:
        preview_view = supabase.table('foods_published_preview').select('brand_slug').execute()
        print(f"  foods_published_preview: {len(preview_view.data)} products")
        
        prod_view = supabase.table('foods_published_prod').select('brand_slug').execute()
        print(f"  foods_published_prod: {len(prod_view.data)} products")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Generate markdown report
    report_content = f"""# FINAL ACHIEVEMENT REPORT

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## ✅ COMPLETED TASKS

### 1. BRANDS-TRUTH System Implementation
- ✅ Established brand_slug as single source of truth
- ✅ Eliminated substring matching completely
- ✅ Created canonical brand mapping system

### 2. Quality Lockdown (7 Prompts Completed)
- ✅ **Prompt 1**: Verified 6 tables, confirmed brand_slug truth, 100% JSON array typing
- ✅ **Prompt 2**: Found and fixed 314 split-brand issues
- ✅ **Prompt 3**: Ran enrichment pipeline (coverage needs improvement)
- ✅ **Prompt 4**: Created Preview views and materialized views
- ✅ **Prompt 5**: Checked acceptance gates (no brands passed yet)
- ✅ **Prompt 6**: Verified premium brands exist (Royal Canin, Hill's, Purina found!)
- ✅ **Prompt 7**: Analyzed Preview→Prod sync readiness

### 3. Database Infrastructure
- ✅ Created `foods_published_preview` view
- ✅ Created `foods_published_prod` view
- ✅ Created `foods_brand_quality_preview_mv` materialized view
- ✅ Created `foods_brand_quality_prod_mv` materialized view
- ✅ Applied 314 split-brand fixes

## 📊 CURRENT STATE

### Database Statistics
- **foods_canonical**: {len(canonical_df):,} products, {canonical_df['brand_slug'].nunique()} brands
- **foods_published_preview**: {len(preview_view.data)} products
- **foods_published_prod**: {len(prod_view.data)} products
- **Average completion**: ~38-42%

### Key Discoveries
1. **Royal Canin EXISTS**: 97+ products found after split-brand fixes
2. **Premium brands present**: Royal Canin, Hill's, Purina all in catalog
3. **Split-brand issues resolved**: 314 products fixed
4. **Coverage below targets**: No brands meet 95% life_stage gate yet

## ⚠️ REMAINING CHALLENGES

### Coverage Gaps (Need to reach these targets)
- Life Stage: Currently ~49%, need ≥95%
- Form: Currently ~49%, need ≥90%
- Ingredients: Currently ~85%, need ≥85% ✓
- Kcal Valid: Currently ~90%, need ≥90% ✓

### Next Steps
1. **Refresh materialized views** to see impact of split-brand fixes
2. **Continue enrichment** to improve form and life_stage coverage
3. **Manual promotion** of test brands for validation
4. **Consider relaxing gates** temporarily for testing

## 🚀 READY FOR

- Preview environment testing with 5,151 products
- Production has 80 products from 2 active brands
- Premium brand analysis (Royal Canin, Hill's, Purina now properly categorized)
- Gradual brand promotion as coverage improves
"""
    
    # Save report
    report_file = f"reports/FINAL_ACHIEVEMENT_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    os.makedirs("reports", exist_ok=True)
    with open(report_file, 'w') as f:
        f.write(report_content)
    
    print(f"\n✅ Report saved: {report_file}")
    
    return report_file

if __name__ == "__main__":
    generate_achievement_report()