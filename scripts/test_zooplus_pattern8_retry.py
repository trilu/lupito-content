#!/usr/bin/env python3
"""
Test Pattern 8 on 5 specific PENDING Zooplus products
Using the robust orchestrator infrastructure
"""

import os
import json
import time
import re
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv
from scrapingbee import ScrapingBeeClient
from bs4 import BeautifulSoup

load_dotenv()

# Initialize ScrapingBee client
client = ScrapingBeeClient(api_key=os.getenv('SCRAPINGBEE_API_KEY'))

# Test 5 PENDING products from our retry list
TEST_PRODUCTS = [
    {
        "product_key": "terra-canis|terra_canis_essential_8_6_x_780g|wet",
        "product_name": "Terra Canis Essential 8+ 6 x 780g",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/terracanis_menu/1948338?activeVariant=1948338.1"
    },
    {
        "product_key": "almo-nature-holistic|almo_nature_holistic_small_adult_dog_beef_rice|dry",
        "product_name": "Almo Nature Holistic Small Adult Dog – Beef & Rice",
        "url": "https://www.zooplus.com/shop/dogs/dry_dog_food/almo_nature_holistic/small/536525?activeVariant=536525.1"
    },
    {
        "product_key": "purizon-wet-dog-food|purizon_adult_6_x_300g|wet",
        "product_name": "Purizon Adult 6 x 300g",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/purizon_wet_dog_food/adult/1549511?activeVariant=1549511.5"
    },
    {
        "product_key": "wow|wow_senior_duck_400g|wet",
        "product_name": "WOW Senior duck 400g",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/wow/1947711?activeVariant=1947711.0"
    },
    {
        "product_key": "dogs-n-tiger|saver_pack_dogsn_tiger_junior_12_x_400g|wet",
        "product_name": "Saver Pack Dogs N Tiger Junior 12 x 400g",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/dogs_n_tiger/puppy/1966735?activeVariant=1966735.0"
    }
]

def test_pattern_8(url: str) -> Dict:
    """Test Pattern 8 extraction on a single URL"""

    result = {
        'url': url,
        'success': False,
        'pattern_8_matched': False,
        'ingredients_found': False,
        'nutrition_found': False,
        'image_found': False,
        'error': None
    }

    try:
        # Clean URL
        if '?activeVariant=' in url:
            base_url = url.split('?activeVariant=')[0]
        else:
            base_url = url

        print(f"  Scraping: {base_url[:80]}...")

        # Use proven parameters from orchestrator
        response = client.get(
            base_url,
            params={
                'render_js': 'true',
                'premium_proxy': 'true',
                'stealth_proxy': 'true',
                'country_code': 'gb',
                'wait': '3000',
                'return_page_source': 'true'
            }
        )

        if response.status_code != 200:
            result['error'] = f"HTTP {response.status_code}"
            return result

        html = response.content
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text('\n', strip=True)

        # Test Pattern 8 specifically
        pattern_8 = r'Go to analytical constituents\s*\n(.*?)(?:Analytical constituents|$)'
        match = re.search(pattern_8, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)

        if match:
            result['pattern_8_matched'] = True
            captured = match.group(1).strip()

            # Try to extract ingredients from captured content
            inner_pattern = r'Ingredients[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives)|$)'
            inner_match = re.search(inner_pattern, captured, re.IGNORECASE | re.MULTILINE)

            if inner_match:
                ingredients = inner_match.group(1).strip()
                if any(word in ingredients.lower() for word in ['meat', 'chicken', 'beef', 'fish', 'rice', 'protein']):
                    result['ingredients_found'] = True
                    result['ingredients_preview'] = ingredients[:200]

        # Also test other patterns for comparison
        other_patterns = [
            r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives)|$)',
            r'Ingredients:\s*\n((?:Duck|Chicken|Meat|Lamb|Beef|Turkey|Salmon|Fish)[^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*)(?:\n\nAdditives|\nAdditives)',
        ]

        for pattern in other_patterns:
            if not result['ingredients_found']:
                match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    ingredients = match.group(1).strip()
                    if any(word in ingredients.lower() for word in ['meat', 'chicken', 'beef', 'fish', 'rice', 'protein']):
                        result['ingredients_found'] = True
                        result['ingredients_preview'] = ingredients[:200]
                        result['other_pattern_matched'] = True
                        break

        # Check nutrition
        nutrition_patterns = [
            (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein'),
            (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat'),
        ]

        nutrition_found = {}
        for pattern, key in nutrition_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                nutrition_found[key] = float(match.group(1))

        if nutrition_found:
            result['nutrition_found'] = True
            result['nutrition'] = nutrition_found

        # Check image
        img = soup.find('img', {'class': re.compile('product.*image', re.I)})
        if not img:
            img = soup.select_one('.product-image img, .image-wrapper img')

        if img and img.get('src'):
            result['image_found'] = True
            result['image_url'] = img['src'][:100]

        result['success'] = True

    except Exception as e:
        result['error'] = str(e)[:200]

    return result

def main():
    """Test Pattern 8 on 5 pending Zooplus products"""

    print("=" * 60)
    print("TESTING PATTERN 8 ON PENDING ZOOPLUS PRODUCTS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print()

    results = []
    stats = {
        'total': 0,
        'success': 0,
        'pattern_8_matched': 0,
        'ingredients_found': 0,
        'nutrition_found': 0,
        'image_found': 0
    }

    for i, product in enumerate(TEST_PRODUCTS, 1):
        print(f"\n[{i}/5] Testing: {product['product_name']}")

        result = test_pattern_8(product['url'])
        results.append({**product, **result})

        stats['total'] += 1
        if result['success']:
            stats['success'] += 1
        if result['pattern_8_matched']:
            stats['pattern_8_matched'] += 1
        if result['ingredients_found']:
            stats['ingredients_found'] += 1
        if result['nutrition_found']:
            stats['nutrition_found'] += 1
        if result['image_found']:
            stats['image_found'] += 1

        # Print immediate result
        print(f"  Result:")
        print(f"    Pattern 8: {'✅' if result['pattern_8_matched'] else '❌'}")
        print(f"    Ingredients: {'✅' if result['ingredients_found'] else '❌'}")
        print(f"    Nutrition: {'✅' if result['nutrition_found'] else '❌'}")
        print(f"    Image: {'✅' if result['image_found'] else '❌'}")

        if result.get('error'):
            print(f"    Error: {result['error']}")

        # Delay between requests
        if i < 5:
            print(f"  Waiting 10 seconds...")
            time.sleep(10)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total tested: {stats['total']}")
    print(f"Successful scrapes: {stats['success']}/{stats['total']} ({stats['success']/stats['total']*100:.0f}%)")
    print(f"Pattern 8 matched: {stats['pattern_8_matched']}/{stats['total']} ({stats['pattern_8_matched']/stats['total']*100:.0f}%)")
    print(f"Ingredients found: {stats['ingredients_found']}/{stats['total']} ({stats['ingredients_found']/stats['total']*100:.0f}%)")
    print(f"Nutrition found: {stats['nutrition_found']}/{stats['total']} ({stats['nutrition_found']/stats['total']*100:.0f}%)")
    print(f"Images found: {stats['image_found']}/{stats['total']} ({stats['image_found']/stats['total']*100:.0f}%)")

    # Save results
    output_file = f"pattern8_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'stats': stats,
            'results': results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")

    # Decision
    if stats['ingredients_found'] >= 3:  # 60% success
        print("\n✅ READY: Pattern 8 and other patterns work! Ready for full batch.")
    else:
        print("\n⚠️ NEEDS ADJUSTMENT: Review results and adjust patterns.")

if __name__ == '__main__':
    main()