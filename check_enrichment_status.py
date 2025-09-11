#!/usr/bin/env python3
"""
Check Manufacturer Enrichment Status in Supabase
Monitors the progress and quality of the enrichment pipeline
"""

import os
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

def check_staging_table():
    """Check manufacturer_harvest_staging table status"""
    print("\n" + "="*80)
    print("📦 STAGING TABLE STATUS")
    print("="*80)
    
    try:
        # Count total records
        response = supabase.table('manufacturer_harvest_staging').select('*', count='exact').execute()
        total_count = response.count
        
        if total_count == 0:
            print("⚠️  Staging table is EMPTY - no harvest data loaded yet")
            return False
        
        print(f"✅ Total records in staging: {total_count}")
        
        # Get breakdown by brand
        response = supabase.table('manufacturer_harvest_staging').select('brand_slug').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            brand_counts = df['brand_slug'].value_counts()
            
            print("\n📊 Records by brand:")
            for brand, count in brand_counts.items():
                print(f"   {brand}: {count} products")
        
        # Get harvest batches
        response = supabase.table('manufacturer_harvest_staging').select('harvest_batch, harvest_timestamp').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            batches = df.groupby('harvest_batch')['harvest_timestamp'].agg(['min', 'max', 'count'])
            
            print("\n🕐 Harvest batches:")
            for batch, row in batches.iterrows():
                print(f"   {batch}: {row['count']} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking staging table: {e}")
        return False

def check_matches():
    """Check manufacturer_matches view"""
    print("\n" + "="*80)
    print("🔗 MATCHING STATUS")
    print("="*80)
    
    try:
        # Get match statistics
        query = """
        SELECT 
            COUNT(*) as total_matches,
            SUM(CASE WHEN match_confidence >= 0.9 THEN 1 ELSE 0 END) as high_confidence,
            SUM(CASE WHEN match_confidence >= 0.8 AND match_confidence < 0.9 THEN 1 ELSE 0 END) as medium_confidence,
            SUM(CASE WHEN match_confidence < 0.8 THEN 1 ELSE 0 END) as low_confidence
        FROM manufacturer_matches
        """
        
        # Execute raw SQL query
        response = supabase.rpc('execute_sql', {'query': query}).execute() if False else None
        
        # Fallback: sample the view
        response = supabase.table('manufacturer_matches').select('match_confidence').execute()
        
        if response and response.data:
            df = pd.DataFrame(response.data)
            total = len(df)
            high = len(df[df['match_confidence'] >= 0.9])
            medium = len(df[(df['match_confidence'] >= 0.8) & (df['match_confidence'] < 0.9)])
            low = len(df[df['match_confidence'] < 0.8])
            
            print(f"Total matches found: {total}")
            print(f"  🟢 High confidence (≥0.9): {high}")
            print(f"  🟡 Medium confidence (0.8-0.9): {medium}")
            print(f"  🔴 Low confidence (<0.8): {low}")
        else:
            print("⚠️  No matches found - check if staging table has data")
            
    except Exception as e:
        # View might not exist or be empty
        print(f"ℹ️  No matches yet (this is normal if staging is empty)")

def check_enrichment_progress():
    """Check enrichment progress in foods_published"""
    print("\n" + "="*80)
    print("📈 ENRICHMENT PROGRESS")
    print("="*80)
    
    try:
        # Get brands that have been enriched
        response = supabase.table('foods_published').select('brand_slug, sources').execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # Count enriched products
            enriched = df[df['sources'].notna() & df['sources'].apply(lambda x: 'manufacturer_harvest' in str(x) if x else False)]
            
            if len(enriched) > 0:
                enriched_brands = enriched['brand_slug'].value_counts()
                
                print(f"\n✅ Total products enriched: {len(enriched)}")
                print("\n📊 Enriched products by brand:")
                for brand, count in enriched_brands.items():
                    print(f"   {brand}: {count} products")
            else:
                print("⚠️  No products enriched yet")
                
        # Check specific test brands
        test_brands = ['eukanuba', 'brit', 'alpha']
        print(f"\n🔍 Checking test brands: {', '.join(test_brands)}")
        
        for brand in test_brands:
            response = supabase.table('foods_published_preview').select(
                'form, life_stage, kcal_per_100g, ingredients_tokens, price_per_kg'
            ).eq('brand_slug', brand).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                total = len(df)
                
                stats = {
                    'form': (df['form'].notna().sum() / total * 100),
                    'life_stage': (df['life_stage'].notna().sum() / total * 100),
                    'kcal': (df['kcal_per_100g'].notna().sum() / total * 100),
                    'ingredients': (df['ingredients_tokens'].notna().sum() / total * 100),
                    'price': (df['price_per_kg'].notna().sum() / total * 100)
                }
                
                print(f"\n   {brand.upper()} ({total} products):")
                for field, pct in stats.items():
                    status = "✅" if pct >= 95 else "🟡" if pct >= 70 else "❌"
                    print(f"     {status} {field}: {pct:.1f}%")
                    
    except Exception as e:
        print(f"❌ Error checking enrichment: {e}")

def check_quality_gates():
    """Check which brands meet quality gates"""
    print("\n" + "="*80)
    print("🎯 QUALITY GATES STATUS")
    print("="*80)
    
    print("\nQuality Gate Thresholds:")
    print("  • Form: ≥95%")
    print("  • Life Stage: ≥95%")
    print("  • Valid Kcal (200-600): ≥90%")
    print("  • Ingredients: ≥85%")
    print("  • Price: ≥70%")
    
    try:
        # Check enriched brands against quality gates
        test_brands = ['eukanuba', 'brit', 'alpha']
        
        results = []
        for brand in test_brands:
            response = supabase.table('foods_published_preview').select(
                'form, life_stage, kcal_per_100g, ingredients_tokens, price_per_kg'
            ).eq('brand_slug', brand).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                total = len(df)
                
                # Calculate gate metrics
                form_pct = df['form'].notna().sum() / total * 100
                life_pct = df['life_stage'].notna().sum() / total * 100
                
                # Valid kcal check
                valid_kcal = df['kcal_per_100g'].apply(
                    lambda x: x is not None and 200 <= x <= 600
                ).sum() / total * 100
                
                # Ingredients check
                ingredients_pct = df['ingredients_tokens'].apply(
                    lambda x: x is not None and len(x) > 0 if isinstance(x, list) else False
                ).sum() / total * 100
                
                price_pct = df['price_per_kg'].notna().sum() / total * 100
                
                # Check if passes all gates
                passes_all = (
                    form_pct >= 95 and 
                    life_pct >= 95 and 
                    valid_kcal >= 90 and 
                    ingredients_pct >= 85 and 
                    price_pct >= 70
                )
                
                results.append({
                    'Brand': brand.upper(),
                    'Products': total,
                    'Form %': f"{form_pct:.1f}",
                    'Life %': f"{life_pct:.1f}",
                    'Kcal %': f"{valid_kcal:.1f}",
                    'Ingr %': f"{ingredients_pct:.1f}",
                    'Price %': f"{price_pct:.1f}",
                    'Status': '✅ PASS' if passes_all else '❌ FAIL'
                })
        
        if results:
            # Print table header
            print("\n" + "-"*100)
            print(f"{'Brand':<10} {'Products':<10} {'Form %':<10} {'Life %':<10} {'Kcal %':<10} {'Ingr %':<10} {'Price %':<10} {'Status':<10}")
            print("-"*100)
            for r in results:
                print(f"{r['Brand']:<10} {r['Products']:<10} {r['Form %']:<10} {r['Life %']:<10} {r['Kcal %']:<10} {r['Ingr %']:<10} {r['Price %']:<10} {r['Status']:<10}")
            print("-"*100)
            
            # Summary
            passing = sum(1 for r in results if '✅' in r['Status'])
            print(f"\n📊 Summary: {passing}/{len(results)} brands pass all quality gates")
            
    except Exception as e:
        print(f"❌ Error checking quality gates: {e}")

def check_database_statistics():
    """Overall database statistics"""
    print("\n" + "="*80)
    print("📊 DATABASE STATISTICS")
    print("="*80)
    
    try:
        tables = ['foods_canonical', 'foods_published', 'foods_published_preview', 'manufacturer_harvest_staging']
        
        for table in tables:
            try:
                response = supabase.table(table).select('*', count='exact').execute()
                print(f"  {table}: {response.count:,} records")
            except:
                print(f"  {table}: N/A")
                
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")

def main():
    """Main execution"""
    print("="*80)
    print("🔍 MANUFACTURER ENRICHMENT STATUS CHECK")
    print("="*80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all checks
    has_staging_data = check_staging_table()
    
    if has_staging_data:
        check_matches()
    
    check_enrichment_progress()
    check_quality_gates()
    check_database_statistics()
    
    print("\n" + "="*80)
    print("✅ STATUS CHECK COMPLETE")
    print("="*80)
    
    if not has_staging_data:
        print("\n⚠️  No harvest data in staging table yet.")
        print("Run the harvest script first to populate staging data.")
    else:
        print("\n🎯 Next Steps:")
        print("1. Review brands that don't meet quality gates")
        print("2. Run additional harvests for missing data")
        print("3. Promote qualifying brands to production")

if __name__ == "__main__":
    main()