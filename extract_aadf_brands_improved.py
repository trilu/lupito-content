#!/usr/bin/env python3
"""
Improved AADF brand extraction - Better pattern matching
"""

import re
import pandas as pd
from typing import Tuple

def extract_brand_product_improved(url: str, description: str) -> Tuple[str, str]:
    """Extract brand and product from AADF URL with improved logic"""
    brand = ""
    product = ""
    
    if pd.notna(url) and 'allaboutdogfood.co.uk' in url and '/dog-food-reviews/' in url:
        # Extract the product slug from URL
        parts = url.split('/')
        if len(parts) >= 6:
            product_slug = parts[-1]  # e.g., "forthglade-complete-meal-with-brown-rice-adult"
            
            # Known multi-word brands
            multi_word_brands = {
                'royal-canin': 'Royal Canin',
                'barking-heads': 'Barking Heads',
                'lily-s-kitchen': "Lily's Kitchen",
                'lilys-kitchen': "Lily's Kitchen",
                'natures-menu': "Nature's Menu",
                'natures-deli': "Nature's Deli",
                'james-wellbeloved': 'James Wellbeloved',
                'country-pursuit': 'Country Pursuit',
                'alpha-spirit': 'Alpha Spirit',
                'millies-wolfheart': "Millies Wolfheart",
                'wolf-of-wilderness': 'Wolf of Wilderness',
                'farmina-natural': 'Farmina Natural',
                'arden-grange': 'Arden Grange',
                'pro-plan': 'Pro Plan',
                'concept-for': 'Concept For',
                'pooch-mutt': 'Pooch & Mutt',
                'country-dog': 'Country Dog',
                'hills-science': "Hill's Science",
                'wainwrights-dry': 'Wainwrights',
                'southend-dog': 'Southend Dog',
                'noochy-poochy': 'Noochy Poochy',
                'calibra-expert': 'Calibra Expert'
            }
            
            # Check for multi-word brands first
            for pattern, brand_name in multi_word_brands.items():
                if product_slug.startswith(pattern):
                    brand = brand_name
                    # Remove brand part from product
                    product = product_slug[len(pattern):].strip('-')
                    product = product.replace('-', ' ')
                    break
            
            # If no multi-word brand found, try single word
            if not brand:
                words = product_slug.split('-')
                if words:
                    # Special cases
                    if words[0].lower() == 'csj':
                        brand = 'CSJ'
                        product = ' '.join(words[1:])
                    elif words[0].lower() in ['fish4dogs', 'scrumbles', 'forthglade', 'ava', 'eukanuba', 
                                              'nutribalance', 'nutro', 'icepaw', 'essential', 'feelwells',
                                              'salters', 'husse', 'calibra', 'paleo', 'burns', 'purina',
                                              'acana', 'orijen', 'wellness', 'canagan', 'harringtons']:
                        brand = words[0].title()
                        product = ' '.join(words[1:])
                    else:
                        # Default: first word is brand
                        brand = words[0].title()
                        product = ' '.join(words[1:])
    
    # Fallback to description if no brand from URL
    if not brand and pd.notna(description):
        # Clean description
        desc_clean = re.sub(r'^\d+[k]?\s+\d+.*?days?\s+', '', str(description), flags=re.IGNORECASE)
        desc_clean = desc_clean.strip(' "')
        
        # Try to extract from description
        words = desc_clean.split()
        if words:
            # Look for known brand indicators in description
            if words[0].lower() in ['made', 'here', 'at', 'our']:
                # Skip introductory words
                pass
            else:
                brand = words[0].title()
                product = ' '.join(words[1:5]) if len(words) > 1 else ""  # Take first few words as product
    
    return brand.strip(), product.strip()

# Test the improved extraction
if __name__ == "__main__":
    import pandas as pd
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Load AADF data
    df = pd.read_csv('data/aadf/aadf-dataset.csv')
    
    # Test extraction on sample
    results = []
    for idx, row in df.head(50).iterrows():
        url = row.get('data-page-selector-href', '')
        desc = row.get('manufacturer_description-0', '')
        brand, product = extract_brand_product_improved(url, desc)
        results.append({
            'url': url.split('/')[-1] if pd.notna(url) else 'N/A',
            'brand': brand,
            'product': product[:40] if product else 'N/A'
        })
    
    # Display results
    results_df = pd.DataFrame(results)
    print("\n=== Sample Brand/Product Extraction ===\n")
    print(results_df.to_string(index=False))
    
    # Show brand distribution
    print("\n=== Brand Distribution (Top 20) ===\n")
    all_brands = []
    for idx, row in df.iterrows():
        url = row.get('data-page-selector-href', '')
        desc = row.get('manufacturer_description-0', '')
        brand, _ = extract_brand_product_improved(url, desc)
        all_brands.append(brand)
    
    brand_counts = pd.Series(all_brands).value_counts().head(20)
    for brand, count in brand_counts.items():
        print(f"{brand:30} {count:4} products")