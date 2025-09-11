#!/usr/bin/env python3
"""
Generate comprehensive QA report for food enrichment data
Analyzes before/after metrics per brand for P7 objectives
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from collections import defaultdict
import json

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'lupito'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres')
    )

def analyze_brand_metrics(conn):
    """Analyze enrichment metrics per brand"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get overall statistics first
        query = """
        WITH brand_stats AS (
            SELECT 
                b.name as brand_name,
                b.website_url,
                b.allowlist_status,
                COUNT(DISTINCT f.id) as total_products,
                
                -- Ingredients metrics
                COUNT(DISTINCT CASE WHEN f.ingredients_tokens IS NOT NULL 
                    AND f.ingredients_tokens != '[]' 
                    AND f.ingredients_tokens != '' THEN f.id END) as has_ingredients,
                
                -- Kcal metrics
                COUNT(DISTINCT CASE WHEN f.kcal_per_100g IS NOT NULL 
                    AND f.kcal_per_100g BETWEEN 200 AND 600 THEN f.id END) as has_valid_kcal,
                
                -- Macros metrics
                COUNT(DISTINCT CASE WHEN f.protein_percent IS NOT NULL 
                    AND f.fat_percent IS NOT NULL THEN f.id END) as has_basic_macros,
                COUNT(DISTINCT CASE WHEN f.protein_percent IS NOT NULL THEN f.id END) as has_protein,
                COUNT(DISTINCT CASE WHEN f.fat_percent IS NOT NULL THEN f.id END) as has_fat,
                COUNT(DISTINCT CASE WHEN f.fiber_percent IS NOT NULL THEN f.id END) as has_fiber,
                COUNT(DISTINCT CASE WHEN f.moisture_percent IS NOT NULL THEN f.id END) as has_moisture,
                
                -- Language metrics
                COUNT(DISTINCT CASE WHEN f.ingredients_language IS NOT NULL 
                    AND f.ingredients_language != '' THEN f.id END) as has_language,
                
                -- Enrichment sources
                COUNT(DISTINCT CASE WHEN f.enrichment_source = 'scraper' THEN f.id END) as from_scraper,
                COUNT(DISTINCT CASE WHEN f.enrichment_source = 'gcs_parser' THEN f.id END) as from_gcs,
                COUNT(DISTINCT CASE WHEN f.enrichment_source = 'manual' THEN f.id END) as from_manual,
                COUNT(DISTINCT CASE WHEN f.enrichment_source IS NULL THEN f.id END) as no_enrichment,
                
                -- Recent updates
                COUNT(DISTINCT CASE WHEN f.updated_at >= CURRENT_DATE - INTERVAL '7 days' THEN f.id END) as updated_last_week,
                COUNT(DISTINCT CASE WHEN f.updated_at >= CURRENT_DATE - INTERVAL '1 day' THEN f.id END) as updated_today
                
            FROM brands b
            LEFT JOIN foods f ON f.brand_id = b.id
            WHERE b.name IS NOT NULL
            GROUP BY b.name, b.website_url, b.allowlist_status
            ORDER BY b.name
        )
        SELECT *,
            ROUND(100.0 * has_ingredients / NULLIF(total_products, 0), 1) as ingredients_pct,
            ROUND(100.0 * has_valid_kcal / NULLIF(total_products, 0), 1) as kcal_pct,
            ROUND(100.0 * has_basic_macros / NULLIF(total_products, 0), 1) as macros_pct,
            ROUND(100.0 * has_language / NULLIF(total_products, 0), 1) as language_pct
        FROM brand_stats
        WHERE total_products > 0
        ORDER BY total_products DESC
        """
        
        cur.execute(query)
        return cur.fetchall()

def identify_parsing_blockers(conn):
    """Identify common parsing issues and blockers"""
    blockers = []
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Check for products with URLs but no enrichment
        cur.execute("""
            SELECT 
                b.name as brand_name,
                COUNT(*) as count
            FROM foods f
            JOIN brands b ON f.brand_id = b.id
            WHERE f.url IS NOT NULL 
            AND f.url != ''
            AND (f.ingredients_tokens IS NULL OR f.ingredients_tokens = '' OR f.ingredients_tokens = '[]')
            AND (f.protein_percent IS NULL)
            GROUP BY b.name
            HAVING COUNT(*) > 5
            ORDER BY count DESC
            LIMIT 10
        """)
        
        url_no_data = cur.fetchall()
        if url_no_data:
            blockers.append({
                'type': 'URL exists but no data extracted',
                'brands': url_no_data
            })
        
        # Check for recent harvest attempts with no data
        cur.execute("""
            SELECT 
                b.name as brand_name,
                COUNT(*) as failed_attempts,
                MAX(hs.created_at) as last_attempt
            FROM harvest_snapshots hs
            JOIN brands b ON b.name = hs.brand_name
            WHERE hs.snapshot_url IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM foods f 
                WHERE f.brand_id = b.id 
                AND (f.enrichment_source = 'gcs_parser' OR f.enrichment_source = 'scraper')
                AND f.updated_at > hs.created_at - INTERVAL '1 day'
            )
            GROUP BY b.name
            HAVING COUNT(*) > 5
            ORDER BY failed_attempts DESC
            LIMIT 10
        """)
        
        harvest_no_parse = cur.fetchall()
        if harvest_no_parse:
            blockers.append({
                'type': 'Harvested but not parsed',
                'brands': harvest_no_parse
            })
        
        # Check for JavaScript-rendered content indicators
        cur.execute("""
            SELECT 
                b.name as brand_name,
                COUNT(*) as js_products
            FROM foods f
            JOIN brands b ON f.brand_id = b.id
            WHERE f.url LIKE '%ajax%' 
               OR f.url LIKE '%api%'
               OR f.url LIKE '%json%'
               OR b.website_url LIKE '%shopify%'
               OR b.website_url LIKE '%woocommerce%'
            GROUP BY b.name
            HAVING COUNT(*) > 5
            ORDER BY js_products DESC
            LIMIT 10
        """)
        
        js_rendered = cur.fetchall()
        if js_rendered:
            blockers.append({
                'type': 'JavaScript-rendered content',
                'brands': js_rendered
            })
        
        return blockers

def get_before_after_comparison(conn):
    """Get before/after metrics for recently enriched brands"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get brands with recent enrichment activity
        cur.execute("""
            WITH recent_enrichment AS (
                SELECT DISTINCT brand_id
                FROM foods
                WHERE updated_at >= CURRENT_DATE - INTERVAL '7 days'
                AND enrichment_source IS NOT NULL
            ),
            before_metrics AS (
                -- Snapshot from 7 days ago (approximate "before")
                SELECT 
                    f.brand_id,
                    COUNT(*) as total_before,
                    COUNT(CASE WHEN f.ingredients_tokens IS NOT NULL 
                        AND f.ingredients_tokens != '[]' THEN 1 END) as ingredients_before,
                    COUNT(CASE WHEN f.kcal_per_100g BETWEEN 200 AND 600 THEN 1 END) as kcal_before,
                    COUNT(CASE WHEN f.protein_percent IS NOT NULL 
                        AND f.fat_percent IS NOT NULL THEN 1 END) as macros_before
                FROM foods f
                WHERE f.brand_id IN (SELECT brand_id FROM recent_enrichment)
                AND f.created_at < CURRENT_DATE - INTERVAL '7 days'
                GROUP BY f.brand_id
            ),
            after_metrics AS (
                -- Current state
                SELECT 
                    f.brand_id,
                    COUNT(*) as total_after,
                    COUNT(CASE WHEN f.ingredients_tokens IS NOT NULL 
                        AND f.ingredients_tokens != '[]' THEN 1 END) as ingredients_after,
                    COUNT(CASE WHEN f.kcal_per_100g BETWEEN 200 AND 600 THEN 1 END) as kcal_after,
                    COUNT(CASE WHEN f.protein_percent IS NOT NULL 
                        AND f.fat_percent IS NOT NULL THEN 1 END) as macros_after
                FROM foods f
                WHERE f.brand_id IN (SELECT brand_id FROM recent_enrichment)
                GROUP BY f.brand_id
            )
            SELECT 
                b.name as brand_name,
                COALESCE(bm.total_before, 0) as products_before,
                am.total_after as products_after,
                ROUND(100.0 * COALESCE(bm.ingredients_before, 0) / NULLIF(bm.total_before, 0), 1) as ingredients_pct_before,
                ROUND(100.0 * am.ingredients_after / NULLIF(am.total_after, 0), 1) as ingredients_pct_after,
                ROUND(100.0 * COALESCE(bm.kcal_before, 0) / NULLIF(bm.total_before, 0), 1) as kcal_pct_before,
                ROUND(100.0 * am.kcal_after / NULLIF(am.total_after, 0), 1) as kcal_pct_after,
                ROUND(100.0 * COALESCE(bm.macros_before, 0) / NULLIF(bm.total_before, 0), 1) as macros_pct_before,
                ROUND(100.0 * am.macros_after / NULLIF(am.total_after, 0), 1) as macros_pct_after
            FROM after_metrics am
            LEFT JOIN before_metrics bm ON am.brand_id = bm.brand_id
            JOIN brands b ON b.id = am.brand_id
            ORDER BY am.total_after DESC
        """)
        
        return cur.fetchall()

def classify_brand_status(metrics):
    """Classify brand as PASS/NEAR/TODO based on metrics"""
    ingredients_pct = metrics.get('ingredients_pct', 0) or 0
    macros_pct = metrics.get('macros_pct', 0) or 0
    kcal_pct = metrics.get('kcal_pct', 0) or 0
    
    # PASS criteria: ingredients ≥85% OR macros ≥70%
    if ingredients_pct >= 85 or macros_pct >= 70:
        return 'PASS'
    # NEAR criteria: ingredients ≥60% OR macros ≥50%
    elif ingredients_pct >= 60 or macros_pct >= 50:
        return 'NEAR'
    else:
        return 'TODO'

def generate_report():
    """Generate the comprehensive QA report"""
    conn = get_db_connection()
    
    try:
        # Get current metrics
        brand_metrics = analyze_brand_metrics(conn)
        
        # Get parsing blockers
        blockers = identify_parsing_blockers(conn)
        
        # Get before/after comparison
        before_after = get_before_after_comparison(conn)
        
        # Generate report
        report = []
        report.append("# FOODS ENRICHMENT BEFORE/AFTER REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary")
        report.append("")
        
        total_brands = len(brand_metrics)
        total_products = sum(b['total_products'] for b in brand_metrics)
        avg_ingredients = sum(b['ingredients_pct'] or 0 for b in brand_metrics) / len(brand_metrics)
        avg_macros = sum(b['macros_pct'] or 0 for b in brand_metrics) / len(brand_metrics)
        
        report.append(f"- **Total Brands Analyzed:** {total_brands}")
        report.append(f"- **Total Products:** {total_products:,}")
        report.append(f"- **Average Ingredients Coverage:** {avg_ingredients:.1f}%")
        report.append(f"- **Average Macros Coverage:** {avg_macros:.1f}%")
        report.append("")
        
        # Per-Brand Metrics
        report.append("## Per-Brand Enrichment Metrics")
        report.append("")
        
        # Group by status
        brands_by_status = defaultdict(list)
        for brand in brand_metrics:
            status = classify_brand_status(brand)
            brands_by_status[status].append(brand)
        
        # PASS Brands
        report.append("### 🟢 PASS Brands (Ready for Production)")
        report.append("*Criteria: ingredients ≥85% OR macros ≥70%*")
        report.append("")
        
        if brands_by_status['PASS']:
            report.append("| Brand | Products | Ingredients | Kcal | Macros | Language | Status | Recommendation |")
            report.append("|-------|----------|-------------|------|---------|----------|---------|----------------|")
            
            for brand in sorted(brands_by_status['PASS'], key=lambda x: x['total_products'], reverse=True):
                status_emoji = "✅" if brand['allowlist_status'] == 'ACTIVE' else "⏳"
                recommendation = "Keep ACTIVE" if brand['allowlist_status'] == 'ACTIVE' else "**→ ACTIVATE**"
                
                report.append(f"| {brand['brand_name']} | {brand['total_products']} | "
                            f"{brand['ingredients_pct']:.1f}% | {brand['kcal_pct']:.1f}% | "
                            f"{brand['macros_pct']:.1f}% | {brand['language_pct']:.1f}% | "
                            f"{status_emoji} {brand['allowlist_status']} | {recommendation} |")
        else:
            report.append("*No brands currently meet PASS criteria*")
        report.append("")
        
        # NEAR Brands
        report.append("### 🟡 NEAR Brands (Close to Ready)")
        report.append("*Criteria: ingredients ≥60% OR macros ≥50%*")
        report.append("")
        
        if brands_by_status['NEAR']:
            report.append("| Brand | Products | Ingredients | Kcal | Macros | Missing |")
            report.append("|-------|----------|-------------|------|---------|---------|")
            
            for brand in sorted(brands_by_status['NEAR'], key=lambda x: x['total_products'], reverse=True):
                missing = []
                if brand['ingredients_pct'] < 85:
                    missing.append(f"Ingredients ({brand['ingredients_pct']:.0f}%→85%)")
                if brand['macros_pct'] < 70:
                    missing.append(f"Macros ({brand['macros_pct']:.0f}%→70%)")
                
                report.append(f"| {brand['brand_name']} | {brand['total_products']} | "
                            f"{brand['ingredients_pct']:.1f}% | {brand['kcal_pct']:.1f}% | "
                            f"{brand['macros_pct']:.1f}% | {', '.join(missing)} |")
        else:
            report.append("*No brands in NEAR status*")
        report.append("")
        
        # TODO Brands
        report.append("### 🔴 TODO Brands (Need Work)")
        report.append("*Criteria: ingredients <60% AND macros <50%*")
        report.append("")
        
        if brands_by_status['TODO']:
            report.append("| Brand | Products | Ingredients | Macros | Enrichment Source |")
            report.append("|-------|----------|-------------|---------|-------------------|")
            
            for brand in sorted(brands_by_status['TODO'], key=lambda x: x['total_products'], reverse=True)[:15]:
                sources = []
                if brand['from_scraper'] > 0:
                    sources.append(f"Scraper({brand['from_scraper']})")
                if brand['from_gcs'] > 0:
                    sources.append(f"GCS({brand['from_gcs']})")
                if brand['no_enrichment'] > 0:
                    sources.append(f"None({brand['no_enrichment']})")
                
                report.append(f"| {brand['brand_name']} | {brand['total_products']} | "
                            f"{brand['ingredients_pct']:.1f}% | {brand['macros_pct']:.1f}% | "
                            f"{', '.join(sources) if sources else 'No enrichment'} |")
        else:
            report.append("*No brands in TODO status*")
        report.append("")
        
        # Before/After Comparison
        if before_after:
            report.append("## Before/After Comparison (Last 7 Days)")
            report.append("")
            report.append("| Brand | Products | Ingredients Δ | Kcal Δ | Macros Δ |")
            report.append("|-------|----------|---------------|---------|----------|")
            
            for comp in before_after[:10]:
                ing_delta = (comp['ingredients_pct_after'] or 0) - (comp['ingredients_pct_before'] or 0)
                kcal_delta = (comp['kcal_pct_after'] or 0) - (comp['kcal_pct_before'] or 0)
                macros_delta = (comp['macros_pct_after'] or 0) - (comp['macros_pct_before'] or 0)
                
                ing_arrow = "↑" if ing_delta > 0 else "↓" if ing_delta < 0 else "→"
                kcal_arrow = "↑" if kcal_delta > 0 else "↓" if kcal_delta < 0 else "→"
                macros_arrow = "↑" if macros_delta > 0 else "↓" if macros_delta < 0 else "→"
                
                report.append(f"| {comp['brand_name']} | "
                            f"{comp['products_before']}→{comp['products_after']} | "
                            f"{ing_arrow} {abs(ing_delta):.1f}% | "
                            f"{kcal_arrow} {abs(kcal_delta):.1f}% | "
                            f"{macros_arrow} {abs(macros_delta):.1f}% |")
            report.append("")
        
        # Parsing Blockers
        report.append("## Top Parsing Blockers")
        report.append("")
        
        for blocker in blockers:
            report.append(f"### {blocker['type']}")
            report.append("")
            
            if blocker['brands']:
                for brand in blocker['brands'][:5]:
                    if blocker['type'] == 'Harvested but not parsed':
                        report.append(f"- **{brand['brand_name']}**: {brand['failed_attempts']} snapshots "
                                    f"(last: {brand['last_attempt'].strftime('%Y-%m-%d')})")
                    else:
                        report.append(f"- **{brand['brand_name']}**: {brand.get('count', brand.get('js_products', 0))} products")
            report.append("")
        
        # Common Issues
        report.append("## Common Issues Identified")
        report.append("")
        report.append("1. **JavaScript-Rendered Nutrition Tables**: Many sites load nutrition data via AJAX")
        report.append("2. **PDF-Only Nutrition**: Some brands only provide nutrition in PDF downloads")
        report.append("3. **Image-Based Tables**: Nutrition data embedded in product images")
        report.append("4. **CloudFlare Protection**: Several sites block automated access")
        report.append("5. **Incomplete Harvesting**: Some brands have URLs but no snapshot data")
        report.append("")
        
        # Recommendations
        report.append("## Recommendations for Activation")
        report.append("")
        report.append("### Immediate Activation (PASS Status)")
        
        activate_brands = [b for b in brands_by_status['PASS'] 
                          if b['allowlist_status'] != 'ACTIVE']
        
        if activate_brands:
            report.append("The following brands meet quality thresholds and should be activated:")
            report.append("")
            for brand in activate_brands:
                report.append(f"- **{brand['brand_name']}**: "
                            f"{brand['ingredients_pct']:.0f}% ingredients, "
                            f"{brand['macros_pct']:.0f}% macros → **PENDING → ACTIVE**")
        else:
            report.append("*All PASS brands are already ACTIVE*")
        report.append("")
        
        report.append("### Priority Improvements (NEAR Status)")
        report.append("")
        if brands_by_status['NEAR']:
            report.append("Focus enrichment efforts on these brands to reach PASS status:")
            report.append("")
            for brand in brands_by_status['NEAR'][:5]:
                gap = min(85 - (brand['ingredients_pct'] or 0), 
                         70 - (brand['macros_pct'] or 0))
                report.append(f"- **{brand['brand_name']}**: ~{abs(gap):.0f}% improvement needed")
        report.append("")
        
        # Summary Statistics
        report.append("## Summary Statistics")
        report.append("")
        report.append(f"- **PASS Brands**: {len(brands_by_status['PASS'])} "
                     f"({100*len(brands_by_status['PASS'])/total_brands:.1f}%)")
        report.append(f"- **NEAR Brands**: {len(brands_by_status['NEAR'])} "
                     f"({100*len(brands_by_status['NEAR'])/total_brands:.1f}%)")
        report.append(f"- **TODO Brands**: {len(brands_by_status['TODO'])} "
                     f"({100*len(brands_by_status['TODO'])/total_brands:.1f}%)")
        report.append("")
        report.append("---")
        report.append("*Report generated for P7: Consolidated QA & Gates*")
        
        # Write report
        report_content = "\n".join(report)
        
        with open('docs/FOODS_ENRICHMENT_BEFORE_AFTER.md', 'w') as f:
            f.write(report_content)
        
        print("✅ Report generated: docs/FOODS_ENRICHMENT_BEFORE_AFTER.md")
        
        # Print summary
        print(f"\nSummary:")
        print(f"- PASS brands: {len(brands_by_status['PASS'])}")
        print(f"- NEAR brands: {len(brands_by_status['NEAR'])}")
        print(f"- TODO brands: {len(brands_by_status['TODO'])}")
        
        if activate_brands:
            print(f"\n🎯 {len(activate_brands)} brands ready for activation!")
            for brand in activate_brands:
                print(f"  - {brand['brand_name']}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    generate_report()