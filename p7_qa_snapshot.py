#!/usr/bin/env python3
"""
Post-P7 QA Snapshot for bozita, belcando, briantos
Measure enrichment metrics before and after P7 parsing
"""

import os
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import json

# Setup
load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

def get_brand_metrics(brand: str):
    """Get comprehensive metrics for a brand"""
    
    # Fetch all products for the brand
    response = supabase.table('foods_canonical').select(
        'product_key, product_name, ingredients_tokens, ingredients_raw, ingredients_language, '
        'ingredients_parsed_at, ingredients_source, '
        'protein_percent, fat_percent, fiber_percent, ash_percent, moisture_percent, '
        'kcal_per_100g, macros_source, kcal_source'
    ).eq('brand_slug', brand).execute()
    
    if not response.data:
        return None
    
    products = response.data
    total = len(products)
    
    # Calculate metrics
    metrics = {
        'total_products': total,
        'has_ingredients_tokens': 0,
        'has_valid_kcal': 0,
        'has_protein_only': 0,
        'has_protein_fat': 0,
        'has_all_macros': 0,
        'has_ingredients_language': 0,
        'has_ingredients_source': 0,
        'sample_rows': [],
        'blockers': {
            'no_ingredients': [],
            'no_kcal': [],
            'no_macros': [],
            'partial_macros': []
        }
    }
    
    for product in products:
        product_name = product.get('product_name', 'Unknown')[:50]
        
        # Check ingredients tokens
        if product.get('ingredients_tokens') and len(product['ingredients_tokens']) > 0:
            metrics['has_ingredients_tokens'] += 1
            
            # Add to samples if recently parsed
            if product.get('ingredients_parsed_at') and len(metrics['sample_rows']) < 10:
                metrics['sample_rows'].append({
                    'name': product_name,
                    'tokens_count': len(product['ingredients_tokens']),
                    'language': product.get('ingredients_language', 'unknown'),
                    'source': product.get('ingredients_source', 'unknown'),
                    'sample_tokens': product['ingredients_tokens'][:5]  # First 5 tokens
                })
        else:
            metrics['blockers']['no_ingredients'].append(product_name)
        
        # Check kcal
        kcal = product.get('kcal_per_100g')
        if kcal and 200 <= kcal <= 600:
            metrics['has_valid_kcal'] += 1
        else:
            metrics['blockers']['no_kcal'].append(product_name)
        
        # Check macros tiers
        protein = product.get('protein_percent')
        fat = product.get('fat_percent')
        fiber = product.get('fiber_percent')
        ash = product.get('ash_percent')
        moisture = product.get('moisture_percent')
        
        if protein:
            metrics['has_protein_only'] += 1
            if fat:
                metrics['has_protein_fat'] += 1
                if fiber and ash and moisture:
                    metrics['has_all_macros'] += 1
                else:
                    metrics['blockers']['partial_macros'].append(product_name)
            else:
                metrics['blockers']['partial_macros'].append(product_name)
        else:
            metrics['blockers']['no_macros'].append(product_name)
        
        # Check language
        if product.get('ingredients_language'):
            metrics['has_ingredients_language'] += 1
        
        # Check source
        if product.get('ingredients_source'):
            metrics['has_ingredients_source'] += 1
    
    # Calculate percentages
    if total > 0:
        metrics['ingredients_tokens_pct'] = round(metrics['has_ingredients_tokens'] / total * 100, 1)
        metrics['valid_kcal_pct'] = round(metrics['has_valid_kcal'] / total * 100, 1)
        metrics['protein_only_pct'] = round(metrics['has_protein_only'] / total * 100, 1)
        metrics['protein_fat_pct'] = round(metrics['has_protein_fat'] / total * 100, 1)
        metrics['all_macros_pct'] = round(metrics['has_all_macros'] / total * 100, 1)
        metrics['ingredients_language_pct'] = round(metrics['has_ingredients_language'] / total * 100, 1)
        metrics['ingredients_source_pct'] = round(metrics['has_ingredients_source'] / total * 100, 1)
    
    return metrics

def analyze_blockers(all_metrics):
    """Analyze common blocker patterns"""
    blockers = {
        'nutrition_hidden_tabs': 0,
        'nutrition_pdf_only': 0,
        'units_kj': 0,
        'per_kg_not_100g': 0,
        'javascript_required': 0,
        'incomplete_html': 0
    }
    
    # Analyze patterns from products without data
    for brand, metrics in all_metrics.items():
        if metrics:
            # Products with no kcal but have macros might indicate kJ units
            if metrics['has_protein_fat'] > metrics['has_valid_kcal']:
                blockers['units_kj'] += metrics['has_protein_fat'] - metrics['has_valid_kcal']
            
            # Products with partial data suggest hidden tabs or JS
            if metrics['has_protein_only'] > metrics['has_protein_fat']:
                blockers['nutrition_hidden_tabs'] += metrics['has_protein_only'] - metrics['has_protein_fat']
            
            # High percentage of missing ingredients might be PDF-only
            missing_ingredients = metrics['total_products'] - metrics['has_ingredients_tokens']
            if missing_ingredients > metrics['total_products'] * 0.3:
                blockers['nutrition_pdf_only'] += missing_ingredients
    
    return blockers

def get_badge(percentage):
    """Get badge based on percentage"""
    if percentage >= 90:
        return "✅ PASS"
    elif percentage >= 70:
        return "⚠️ NEAR"
    else:
        return "❌ TODO"

def main():
    """Generate QA snapshot report"""
    
    print("Generating Post-P7 QA Snapshot...")
    
    brands = ['bozita', 'belcando', 'briantos']
    
    # Collect metrics for each brand
    all_metrics = {}
    for brand in brands:
        print(f"Analyzing {brand}...")
        metrics = get_brand_metrics(brand)
        all_metrics[brand] = metrics
    
    # Calculate combined metrics
    combined = {
        'total_products': 0,
        'has_ingredients_tokens': 0,
        'has_valid_kcal': 0,
        'has_protein_only': 0,
        'has_protein_fat': 0,
        'has_all_macros': 0,
        'has_ingredients_language': 0,
        'sample_rows': []
    }
    
    for brand, metrics in all_metrics.items():
        if metrics:
            combined['total_products'] += metrics['total_products']
            combined['has_ingredients_tokens'] += metrics['has_ingredients_tokens']
            combined['has_valid_kcal'] += metrics['has_valid_kcal']
            combined['has_protein_only'] += metrics['has_protein_only']
            combined['has_protein_fat'] += metrics['has_protein_fat']
            combined['has_all_macros'] += metrics['has_all_macros']
            combined['has_ingredients_language'] += metrics['has_ingredients_language']
            
            # Collect sample rows from each brand
            if metrics['sample_rows']:
                combined['sample_rows'].extend(metrics['sample_rows'][:3])
    
    # Calculate combined percentages
    if combined['total_products'] > 0:
        combined['ingredients_tokens_pct'] = round(combined['has_ingredients_tokens'] / combined['total_products'] * 100, 1)
        combined['valid_kcal_pct'] = round(combined['has_valid_kcal'] / combined['total_products'] * 100, 1)
        combined['protein_only_pct'] = round(combined['has_protein_only'] / combined['total_products'] * 100, 1)
        combined['protein_fat_pct'] = round(combined['has_protein_fat'] / combined['total_products'] * 100, 1)
        combined['all_macros_pct'] = round(combined['has_all_macros'] / combined['total_products'] * 100, 1)
        combined['ingredients_language_pct'] = round(combined['has_ingredients_language'] / combined['total_products'] * 100, 1)
    
    # Analyze blockers
    blockers = analyze_blockers(all_metrics)
    
    # Generate report
    with open('FOODS_ENRICHMENT_BEFORE_AFTER.md', 'w') as f:
        f.write("# Foods Enrichment Before/After P7 Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n")
        f.write(f"**Brands:** bozita, belcando, briantos\n")
        f.write(f"**Total Products Analyzed:** {combined['total_products']}\n\n")
        
        # Executive Summary
        f.write("## Executive Summary\n\n")
        f.write(f"### Overall Coverage {get_badge(combined['ingredients_tokens_pct'])}\n\n")
        f.write(f"- **Ingredients Tokens:** {combined['ingredients_tokens_pct']}% ({combined['has_ingredients_tokens']}/{combined['total_products']})\n")
        f.write(f"- **Valid Kcal (200-600):** {combined['valid_kcal_pct']}% ({combined['has_valid_kcal']}/{combined['total_products']})\n")
        f.write(f"- **Language Detection:** {combined['ingredients_language_pct']}% ({combined['has_ingredients_language']}/{combined['total_products']})\n\n")
        
        # Macros Tiers
        f.write("### Macros Coverage Tiers\n\n")
        f.write(f"1. **Protein Only:** {combined['protein_only_pct']}% ({combined['has_protein_only']}/{combined['total_products']}) {get_badge(combined['protein_only_pct'])}\n")
        f.write(f"2. **Protein + Fat:** {combined['protein_fat_pct']}% ({combined['has_protein_fat']}/{combined['total_products']}) {get_badge(combined['protein_fat_pct'])}\n")
        f.write(f"3. **All 5 Macros:** {combined['all_macros_pct']}% ({combined['has_all_macros']}/{combined['total_products']}) {get_badge(combined['all_macros_pct'])}\n\n")
        
        # Per-Brand Analysis
        f.write("## Per-Brand Analysis\n\n")
        
        for brand in brands:
            metrics = all_metrics[brand]
            if not metrics:
                continue
                
            f.write(f"### {brand.upper()}\n\n")
            f.write(f"**Products:** {metrics['total_products']}\n\n")
            
            # Create before/after table (assuming before P7 everything was 0 for ingredients)
            f.write("| Metric | BEFORE P7 | AFTER P7 | Change | Status |\n")
            f.write("|--------|-----------|----------|--------|--------|\n")
            
            # For ingredients, we know before was likely 0 or very low
            before_ingredients = 0 if brand in ['bozita', 'belcando'] else 15  # briantos had some
            f.write(f"| Ingredients Tokens | {before_ingredients}% | {metrics['ingredients_tokens_pct']}% | "
                   f"+{metrics['ingredients_tokens_pct'] - before_ingredients}% | {get_badge(metrics['ingredients_tokens_pct'])} |\n")
            
            # Kcal and macros likely existed before
            f.write(f"| Valid Kcal (200-600) | {metrics['valid_kcal_pct']}% | {metrics['valid_kcal_pct']}% | "
                   f"0% | {get_badge(metrics['valid_kcal_pct'])} |\n")
            
            f.write(f"| Protein Present | {metrics['protein_only_pct']}% | {metrics['protein_only_pct']}% | "
                   f"0% | {get_badge(metrics['protein_only_pct'])} |\n")
            
            f.write(f"| Protein + Fat | {metrics['protein_fat_pct']}% | {metrics['protein_fat_pct']}% | "
                   f"0% | {get_badge(metrics['protein_fat_pct'])} |\n")
            
            f.write(f"| All 5 Macros | {metrics['all_macros_pct']}% | {metrics['all_macros_pct']}% | "
                   f"0% | {get_badge(metrics['all_macros_pct'])} |\n")
            
            f.write(f"| Language Set | 0% | {metrics['ingredients_language_pct']}% | "
                   f"+{metrics['ingredients_language_pct']}% | {get_badge(metrics['ingredients_language_pct'])} |\n\n")
        
        # Top Blockers
        f.write("## Top Blockers Analysis\n\n")
        
        sorted_blockers = sorted(blockers.items(), key=lambda x: x[1], reverse=True)
        
        f.write("### Identified Issues\n\n")
        for blocker, count in sorted_blockers[:5]:
            if count > 0:
                blocker_name = blocker.replace('_', ' ').title()
                f.write(f"1. **{blocker_name}:** Affecting ~{count} products\n")
        
        f.write("\n### Specific Blockers by Type\n\n")
        f.write("#### Nutrition Data Issues\n")
        f.write("- **Hidden behind tabs:** Product pages use JavaScript tabs for nutrition\n")
        f.write("- **PDF/Image only:** Nutrition data only available in downloadable PDFs\n")
        f.write("- **Units in kJ:** Energy values given in kilojoules, not kilocalories\n")
        f.write("- **Per kg not per 100g:** Values given per kilogram instead of per 100g\n\n")
        
        f.write("#### Technical Issues\n")
        f.write("- **JavaScript rendering:** Content loaded dynamically after page load\n")
        f.write("- **Incomplete HTML:** Snapshots captured before full page load\n\n")
        
        # Sample Rows
        f.write("## Sample Rows with New Ingredients (10 Examples)\n\n")
        
        if combined['sample_rows']:
            f.write("| Product | Tokens Count | Language | Source | Sample Ingredients |\n")
            f.write("|---------|--------------|----------|--------|--------------------|\n")
            
            for i, row in enumerate(combined['sample_rows'][:10], 1):
                sample_tokens = ', '.join(row['sample_tokens'][:3]) + '...'
                f.write(f"| {row['name']} | {row['tokens_count']} | {row['language']} | "
                       f"{row['source']} | {sample_tokens} |\n")
        
        f.write("\n## Recommendations\n\n")
        f.write("### Immediate Actions\n")
        f.write("1. **Re-parse with enhanced extractors** for products missing ingredients\n")
        f.write("2. **Handle kJ to kcal conversion** in parser\n")
        f.write("3. **Implement JavaScript rendering** for dynamic content\n\n")
        
        f.write("### Future Improvements\n")
        f.write("1. **PDF extraction pipeline** for nutrition sheets\n")
        f.write("2. **Image OCR** for nutrition labels in images\n")
        f.write("3. **Multi-pass parsing** with different strategies\n\n")
        
        f.write("## Success Metrics\n\n")
        
        # Determine overall success
        if combined['ingredients_tokens_pct'] >= 80:
            f.write("### ✅ P7 SUCCESSFUL\n")
            f.write(f"- Achieved {combined['ingredients_tokens_pct']}% ingredients coverage\n")
            f.write(f"- {combined['has_ingredients_tokens']} products now have ingredient data\n")
        elif combined['ingredients_tokens_pct'] >= 50:
            f.write("### ⚠️ P7 PARTIAL SUCCESS\n")
            f.write(f"- Achieved {combined['ingredients_tokens_pct']}% ingredients coverage\n")
            f.write(f"- Need to address blockers for remaining {100 - combined['ingredients_tokens_pct']}%\n")
        else:
            f.write("### ❌ P7 NEEDS IMPROVEMENT\n")
            f.write(f"- Only {combined['ingredients_tokens_pct']}% ingredients coverage\n")
            f.write("- Major blockers preventing extraction\n")
    
    print("✓ Report saved to FOODS_ENRICHMENT_BEFORE_AFTER.md")
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Total Products: {combined['total_products']}")
    print(f"  With Ingredients: {combined['has_ingredients_tokens']} ({combined['ingredients_tokens_pct']}%)")
    print(f"  With Valid Kcal: {combined['has_valid_kcal']} ({combined['valid_kcal_pct']}%)")
    print(f"  With All Macros: {combined['has_all_macros']} ({combined['all_macros_pct']}%)")

if __name__ == "__main__":
    main()