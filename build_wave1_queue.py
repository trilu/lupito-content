#!/usr/bin/env python3
"""
Build Wave 1 Brand Queue for Manufacturer Enrichment
Prioritizes brands by impact potential
"""

import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import yaml

load_dotenv()

# Initialize Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

print("="*80)
print("BUILDING WAVE 1 BRAND QUEUE")
print("="*80)

# Get brand quality data
response = supabase.table('foods_brand_quality_preview_mv').select('*').execute()
brands_df = pd.DataFrame(response.data)

# Load brand sites data
brand_sites_path = Path("data/brand_sites.yaml")
if brand_sites_path.exists():
    with open(brand_sites_path, 'r') as f:
        brand_sites_data = yaml.unsafe_load(f)
        brand_sites = brand_sites_data.get('brands', {})
else:
    brand_sites = {}

# Calculate impact score
# Impact = SKU count * (100 - completion_pct) * website_factor
brands_df['has_website'] = brands_df['brand_slug'].apply(lambda x: x in brand_sites and brand_sites[x].get('has_website', False))
brands_df['website_url'] = brands_df['brand_slug'].apply(lambda x: brand_sites[x].get('website_url', '') if x in brand_sites else '')
brands_df['country'] = brands_df['brand_slug'].apply(lambda x: brand_sites[x].get('country', '') if x in brand_sites else '')
brands_df['robots_status'] = brands_df['brand_slug'].apply(lambda x: brand_sites[x].get('robots_status', '') if x in brand_sites else '')

# Calculate impact score
brands_df['completion_gap'] = 100 - brands_df['completion_pct']
brands_df['impact_score'] = brands_df['sku_count'] * brands_df['completion_gap'] / 100

# Apply website factor (boost brands with websites)
brands_df.loc[brands_df['has_website'], 'impact_score'] *= 1.5

# Filter for brands with websites and significant gaps
wave1_candidates = brands_df[
    (brands_df['has_website']) & 
    (brands_df['sku_count'] >= 10) &
    (brands_df['completion_pct'] < 90)
].copy()

# Sort by impact score
wave1_candidates = wave1_candidates.sort_values('impact_score', ascending=False)

# Select top 10 for Wave 1
wave1_queue = wave1_candidates.head(10).copy()

# Detect suspected platform
def detect_platform(brand_slug):
    """Detect likely e-commerce platform"""
    if brand_slug not in brand_sites:
        return 'Unknown'
    
    url = brand_sites[brand_slug].get('website_url', '')
    notes = brand_sites[brand_slug].get('notes', '')
    
    if 'shopify' in url.lower() or 'myshopify' in url:
        return 'Shopify'
    elif 'wordpress' in notes.lower() or 'wp-' in url:
        return 'WordPress/WooCommerce'
    elif '.de' in url or '.it' in url or '.es' in url:
        return 'Custom (EU)'
    else:
        return 'Custom'

wave1_queue['platform'] = wave1_queue['brand_slug'].apply(detect_platform)

# Add strategy notes
def generate_strategy(row):
    """Generate strategy note for brand"""
    notes = []
    
    # Language/region specific
    if row['country'] in ['DE', 'AT', 'CH']:
        notes.append("German site - may need translation")
    elif row['country'] in ['IT']:
        notes.append("Italian site - may need translation")
    elif row['country'] in ['ES']:
        notes.append("Spanish site - may need translation")
    
    # Completion gaps
    if row['ingredients_coverage_pct'] < 50:
        notes.append("Focus on ingredients extraction")
    if row['kcal_valid_pct'] < 50:
        notes.append("Look for nutrition tables/PDFs")
    if row['form_coverage_pct'] < 80:
        notes.append("Identify product forms")
    
    # Platform specific
    if row['platform'] == 'Shopify':
        notes.append("Check for JSON-LD product data")
    
    return "; ".join(notes[:2]) if notes else "Standard harvest approach"

wave1_queue['strategy'] = wave1_queue.apply(generate_strategy, axis=1)

# Generate report
report_path = Path("reports/WAVE_1_QUEUE.md")
report_path.parent.mkdir(exist_ok=True)

with open(report_path, 'w') as f:
    f.write("# Wave 1 Brand Queue for Manufacturer Enrichment\n\n")
    f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"**Total Candidates:** {len(wave1_candidates)}\n")
    f.write(f"**Selected for Wave 1:** 10\n\n")
    
    f.write("## Selection Criteria\n\n")
    f.write("- Must have manufacturer website\n")
    f.write("- Minimum 10 SKUs\n")
    f.write("- Completion < 90%\n")
    f.write("- Prioritized by Impact Score = SKU Count × (100 - Completion%) × Website Factor\n\n")
    
    f.write("## Wave 1 Queue\n\n")
    f.write("| Rank | Brand | SKUs | Completion | Website | Country | Platform | Strategy |\n")
    f.write("|------|-------|------|------------|---------|---------|----------|----------|\n")
    
    for idx, row in wave1_queue.iterrows():
        rank = wave1_queue.index.get_loc(idx) + 1
        f.write(f"| {rank} | {row['brand_slug']} | {row['sku_count']} | ")
        f.write(f"{row['completion_pct']:.1f}% | ")
        f.write(f"[Link]({row['website_url']}) | ")
        f.write(f"{row['country']} | {row['platform']} | ")
        f.write(f"{row['strategy']} |\n")
    
    f.write("\n## Detailed Metrics\n\n")
    f.write("| Brand | Form % | Life Stage % | Ingredients % | Kcal % | Price % | Impact Score |\n")
    f.write("|-------|--------|--------------|---------------|---------|---------|-------------|\n")
    
    for idx, row in wave1_queue.iterrows():
        f.write(f"| {row['brand_slug']} | ")
        f.write(f"{row['form_coverage_pct']:.0f}% | ")
        f.write(f"{row['life_stage_coverage_pct']:.0f}% | ")
        f.write(f"{row['ingredients_coverage_pct']:.0f}% | ")
        f.write(f"{row['kcal_valid_pct']:.0f}% | ")
        f.write(f"{row['price_coverage_pct']:.0f}% | ")
        f.write(f"{row['impact_score']:.0f} |\n")
    
    f.write("\n## Language Requirements\n\n")
    
    # Group by language needs
    german_brands = wave1_queue[wave1_queue['country'].isin(['DE', 'AT', 'CH'])]
    italian_brands = wave1_queue[wave1_queue['country'] == 'IT']
    spanish_brands = wave1_queue[wave1_queue['country'] == 'ES']
    english_brands = wave1_queue[~wave1_queue['country'].isin(['DE', 'AT', 'CH', 'IT', 'ES'])]
    
    if len(german_brands) > 0:
        f.write(f"**German Sites ({len(german_brands)}):** {', '.join(german_brands['brand_slug'].tolist())}\n")
    if len(italian_brands) > 0:
        f.write(f"**Italian Sites ({len(italian_brands)}):** {', '.join(italian_brands['brand_slug'].tolist())}\n")
    if len(spanish_brands) > 0:
        f.write(f"**Spanish Sites ({len(spanish_brands)}):** {', '.join(spanish_brands['brand_slug'].tolist())}\n")
    if len(english_brands) > 0:
        f.write(f"**English Sites ({len(english_brands)}):** {', '.join(english_brands['brand_slug'].tolist())}\n")
    
    f.write("\n## PDF Detection\n\n")
    f.write("Based on platform analysis, these brands likely have PDF datasheets:\n\n")
    
    # Brands likely to have PDFs
    pdf_likely = wave1_queue[wave1_queue['platform'].isin(['Custom', 'Custom (EU)'])]
    for idx, row in pdf_likely.iterrows():
        f.write(f"- **{row['brand_slug']}**: Check for product datasheets, nutrition PDFs\n")
    
    f.write("\n## Execution Strategy\n\n")
    f.write("1. **Batch 1 (English sites):** Start with English-language sites for quick wins\n")
    f.write("2. **Batch 2 (German sites):** Use translation API or ScrapingBee for German content\n")
    f.write("3. **Batch 3 (Other EU):** Italian/Spanish sites with appropriate translation\n")
    f.write("4. **PDF Priority:** Focus on brands with low nutrition coverage but likely PDFs\n\n")
    
    f.write("## Next Steps\n\n")
    f.write("1. Create harvest profiles for each brand (profiles/brands/{brand_slug}.yaml)\n")
    f.write("2. Test robots.txt compliance for each site\n")
    f.write("3. Identify specific product listing pages/sitemaps\n")
    f.write("4. Configure ScrapingBee for sites that block standard crawlers\n")
    f.write("5. Set up translation pipeline for non-English sites\n")

print(f"\n✅ Wave 1 Queue generated: {report_path}")
print(f"\nTop 10 brands selected:")
for idx, row in wave1_queue.iterrows():
    print(f"  {wave1_queue.index.get_loc(idx) + 1}. {row['brand_slug']} - {row['sku_count']} SKUs, {row['completion_pct']:.1f}% complete, Impact: {row['impact_score']:.0f}")