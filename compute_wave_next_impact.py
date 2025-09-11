#!/usr/bin/env python3
"""
NEXT-1: Compute impact queue from live Supabase Preview data
Prioritize brands by: SKU count × (100 - ingredients coverage)
"""

import os
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import requests
from urllib.robotparser import RobotFileParser

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

print("="*80)
print("NEXT-1: WAVE-NEXT IMPACT QUEUE COMPUTATION")
print("="*80)
print(f"Timestamp: {datetime.now().isoformat()}")
print("Data source: foods_published_preview (live)")

def get_brand_impact_metrics():
    """Get brand metrics from foods_published_preview"""
    print("\n1. QUERYING SUPABASE PREVIEW DATA...")
    
    # Get brand-level aggregates
    response = supabase.table('foods_published_preview').select(
        'brand_slug, brand, ingredients_tokens, kcal_per_100g, form, life_stage'
    ).execute()
    
    if not response.data:
        print("❌ No data found in foods_published_preview")
        return []
    
    print(f"✅ Retrieved {len(response.data)} product records")
    
    # Aggregate by brand
    brand_metrics = {}
    for product in response.data:
        brand_slug = product['brand_slug']
        brand = product['brand']
        
        if brand_slug not in brand_metrics:
            brand_metrics[brand_slug] = {
                'brand_name': brand,
                'total_skus': 0,
                'has_ingredients': 0,
                'has_kcal': 0,
                'has_form': 0,
                'has_life_stage': 0,
                'ingredients_coverage': 0,
                'kcal_coverage': 0,
                'form_coverage': 0,
                'life_stage_coverage': 0
            }
        
        brand_metrics[brand_slug]['total_skus'] += 1
        
        # Check ingredient coverage
        if product.get('ingredients_tokens') and len(product['ingredients_tokens']) > 0:
            brand_metrics[brand_slug]['has_ingredients'] += 1
        
        # Check kcal coverage (200-600 range)
        kcal = product.get('kcal_per_100g')
        if kcal and 200 <= kcal <= 600:
            brand_metrics[brand_slug]['has_kcal'] += 1
        
        # Check form coverage
        if product.get('form'):
            brand_metrics[brand_slug]['has_form'] += 1
        
        # Check life_stage coverage
        if product.get('life_stage'):
            brand_metrics[brand_slug]['has_life_stage'] += 1
    
    # Calculate percentages and impact scores
    impact_queue = []
    for brand_slug, metrics in brand_metrics.items():
        total = metrics['total_skus']
        
        if total > 0:
            metrics['ingredients_coverage'] = round(metrics['has_ingredients'] / total * 100, 1)
            metrics['kcal_coverage'] = round(metrics['has_kcal'] / total * 100, 1)
            metrics['form_coverage'] = round(metrics['has_form'] / total * 100, 1)
            metrics['life_stage_coverage'] = round(metrics['has_life_stage'] / total * 100, 1)
            
            # Impact formula: SKU count × (100 - ingredients coverage)
            ingredients_gap = 100 - metrics['ingredients_coverage']
            impact_score = total * ingredients_gap
            
            impact_queue.append({
                'brand_slug': brand_slug,
                'brand_name': metrics['brand_name'],
                'total_skus': total,
                'ingredients_coverage': metrics['ingredients_coverage'],
                'ingredients_gap': ingredients_gap,
                'impact_score': impact_score,
                'kcal_coverage': metrics['kcal_coverage'],
                'form_coverage': metrics['form_coverage'],
                'life_stage_coverage': metrics['life_stage_coverage']
            })
    
    # Sort by impact score (descending)
    impact_queue.sort(key=lambda x: x['impact_score'], reverse=True)
    
    return impact_queue

def check_domain_accessibility(domain):
    """Check if domain is publicly accessible and get robots.txt status"""
    try:
        # Test basic connectivity
        response = requests.get(f"https://{domain}", timeout=10, allow_redirects=True)
        accessible = response.status_code < 400
        
        # Check robots.txt
        robots_url = f"https://{domain}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            robots_status = "accessible"
            # Test crawling permission for common paths
            can_crawl = rp.can_fetch('*', f"https://{domain}/products/")
            if not can_crawl:
                robots_status = "restricted"
        except:
            robots_status = "no_robots_txt"
        
        return {
            'accessible': accessible,
            'status_code': response.status_code,
            'robots_status': robots_status,
            'final_url': response.url
        }
        
    except Exception as e:
        return {
            'accessible': False,
            'status_code': None,
            'robots_status': 'error',
            'error': str(e)
        }

def get_brand_domains():
    """Get known brand domains from existing data"""
    # This would ideally come from a brands table, but we'll use common patterns
    common_domains = {
        'acana': 'acana.com',
        'orijen': 'orijen.com',
        'royal_canin': 'royalcanin.com',
        'hills': 'hillspet.com',
        'purina': 'purina.com',
        'eukanuba': 'eukanuba.com',
        'pedigree': 'pedigree.com',
        'whiskas': 'whiskas.com',
        'iams': 'iams.com',
        'science_diet': 'hillspet.com',
        'wellness': 'wellnesspetfood.com',
        'blue_buffalo': 'bluebuffalo.com',
        'taste_of_wild': 'tasteofthewildpetfood.com',
        'fromm': 'frommfamily.com',
        'canidae': 'canidae.com',
        'merrick': 'merrickpetcare.com',
        'nutro': 'nutro.com',
        'diamond': 'diamondpet.com',
        'natural_balance': 'naturalbalanceinc.com',
        'castor_pollux': 'castorpolluxpet.com'
    }
    return common_domains

def main():
    """Main execution for NEXT-1 impact analysis"""
    
    # Get impact metrics
    impact_queue = get_brand_impact_metrics()
    
    if not impact_queue:
        print("❌ No brand data available")
        return
    
    print(f"\n2. IMPACT ANALYSIS COMPLETE")
    print(f"   Analyzed {len(impact_queue)} brands from Preview data")
    
    # Get brand domains for accessibility testing
    brand_domains = get_brand_domains()
    
    print(f"\n3. TOP 20 HIGHEST IMPACT BRANDS")
    print(f"{'Rank':<4} {'Brand':<20} {'SKUs':<6} {'Ingr%':<6} {'Gap%':<6} {'Impact':<8} {'Domain Status':<15}")
    print("-" * 85)
    
    enhanced_queue = []
    for i, brand in enumerate(impact_queue[:20], 1):
        brand_slug = brand['brand_slug']
        domain = brand_domains.get(brand_slug, f"{brand_slug.replace('_', '')}.com")
        
        # Check domain accessibility (for top 10 only to save time)
        if i <= 10:
            domain_info = check_domain_accessibility(domain)
            domain_status = 'accessible' if domain_info['accessible'] else 'blocked/error'
        else:
            domain_status = 'unchecked'
        
        print(f"{i:<4} {brand['brand_name'][:19]:<20} {brand['total_skus']:<6} "
              f"{brand['ingredients_coverage']:<6.1f} {brand['ingredients_gap']:<6.1f} "
              f"{brand['impact_score']:<8.0f} {domain_status:<15}")
        
        enhanced_queue.append({
            **brand,
            'domain': domain,
            'domain_status': domain_status,
            'rank': i
        })
    
    # Filter for high-impact, accessible brands
    print(f"\n4. FILTERING FOR WAVE-NEXT CANDIDATES")
    candidates = []
    
    for brand in enhanced_queue[:10]:  # Only consider top 10
        # Criteria: high impact + accessible + significant SKU count
        if (brand['impact_score'] >= 100 and  # Significant impact potential
            brand['total_skus'] >= 5 and       # Meaningful SKU count
            brand['domain_status'] == 'accessible'):  # Technically feasible
            
            candidates.append(brand)
            print(f"✅ {brand['brand_name']}: {brand['total_skus']} SKUs, "
                  f"{brand['ingredients_coverage']}% coverage, {brand['impact_score']:.0f} impact")
    
    if len(candidates) < 3:
        print(f"⚠️  Only found {len(candidates)} accessible candidates")
        print("   Including partially accessible/high-impact brands...")
        
        # Expand criteria if needed
        for brand in enhanced_queue[:10]:
            if len(candidates) >= 3:
                break
            if (brand['impact_score'] >= 50 and 
                brand['total_skus'] >= 3 and
                brand not in candidates):
                candidates.append(brand)
                print(f"📋 {brand['brand_name']}: {brand['total_skus']} SKUs, "
                      f"{brand['ingredients_coverage']}% coverage (fallback)")
    
    # Select final Wave-Next-3
    wave_next_3 = candidates[:3]
    
    print(f"\n5. WAVE-NEXT-3 SELECTED")
    for i, brand in enumerate(wave_next_3, 1):
        print(f"{i}. **{brand['brand_name']}** ({brand['brand_slug']})")
        print(f"   - SKUs: {brand['total_skus']}")
        print(f"   - Current ingredients coverage: {brand['ingredients_coverage']}%")
        print(f"   - Impact potential: {brand['impact_score']:.0f}")
        print(f"   - Domain: {brand['domain']} ({brand['domain_status']})")
        print()
    
    # Save results for report generation
    with open('wave_next_impact_data.json', 'w') as f:
        import json
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'full_impact_queue': impact_queue,
            'wave_next_3': wave_next_3
        }, f, indent=2)
    
    print(f"✅ Impact analysis complete - data saved to wave_next_impact_data.json")
    
    return wave_next_3

if __name__ == "__main__":
    wave_next_3 = main()
    
    if wave_next_3:
        print(f"\n🎯 SUMMARY: Wave-Next-3 brands selected:")
        for brand in wave_next_3:
            print(f"   - {brand['brand_name']} ({brand['total_skus']} SKUs, {100-brand['ingredients_coverage']:.1f}% gap)")