#!/usr/bin/env python3
"""
Test relaxed extraction (Pattern 8) on 5 specific Zooplus URLs
"""

import os
import sys
import json
import time
import random
from datetime import datetime
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

# 5 test URLs from the remaining 237 products
TEST_URLS = [
    "https://www.zooplus.com/shop/dogs/canned_dog_food/rinti/rinti_cans/128729",
    "https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/hundenassfuttermitdreifachenproteinenregionen/1952494",
    "https://www.zooplus.com/shop/dogs/canned_dog_food/rinti/specialist_diet/1582654",
    "https://www.zooplus.com/shop/dogs/canned_dog_food/wow/1947711",
    "https://www.zooplus.com/shop/dogs/dry_dog_food/simpsons_premium/sensitive/538330"
]

def scrape_product(url: str) -> Dict:
    """Scrape with proven parameters"""
    
    # Clean URL
    if '?activeVariant=' in url:
        url = url.split('?activeVariant=')[0]
    
    # Use proven stealth parameters
    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': url,
        'render_js': 'true',
        'premium_proxy': 'true',
        'stealth_proxy': 'true',
        'country_code': 'gb',
        'wait': '3000',
        'return_page_source': 'true'
    }
    
    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=120
        )
        
        if response.status_code == 200:
            return parse_response(response.text, url)
        else:
            error_msg = f'HTTP {response.status_code}'
            if response.text:
                error_msg += f': {response.text[:100]}'
            return {'url': url, 'error': error_msg}
            
    except Exception as e:
        return {'url': url, 'error': str(e)[:200]}

def parse_response(html: str, url: str) -> Dict:
    """Parse HTML response with Pattern 8"""
    
    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text(separator='\n', strip=True)
    
    result = {
        'url': url,
        'scraped_at': datetime.now().isoformat()
    }
    
    # Product name
    h1 = soup.find('h1')
    if h1:
        result['product_name'] = h1.text.strip()
    
    # Test Pattern 8: Relaxed capture from "Go to analytical constituents"
    import re
    
    # First try Pattern 8
    pattern_8 = r'Go to analytical constituents\s*\n(.*?)(?:Analytical constituents|$)'
    match = re.search(pattern_8, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    
    if match:
        captured_content = match.group(1).strip()
        result['pattern_8_captured'] = captured_content[:500]  # First 500 chars for review
        result['pattern_8_full'] = captured_content  # Full content
        
        # Try to extract ingredients from captured content
        ingredients_match = re.search(r'Ingredients:?\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*?)(?:\n\nAdditives|\nAdditives|$)', 
                                     captured_content, re.IGNORECASE | re.MULTILINE)
        if ingredients_match:
            result['ingredients_extracted'] = ingredients_match.group(1).strip()
    else:
        result['pattern_8_captured'] = None
    
    # Also test existing patterns for comparison
    existing_patterns = [
        r'Ingredients\s*/\s*composition\s*\n([^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+(?:\([^)]+\))?)*?)(?:\n\nAdditives|\nAdditives|\nAnalytical|\n\n)',
        r'Ingredients:\s*\n(?:[^\n]*?(?:wet food|complete|diet)[^\n]*\n)?(\d+%[^\n]+(?:[,.]?\s*[^\n]+)*?)(?:\n\nAdditives|\nAdditives)',
        r'Ingredients:\s*\n([A-Z][^\n]+(?:\([^)]+\))?[,.]?\s*)(?:\n\nAdditives per kg:|\nAdditives|\n\n)',
        r'Ingredients\s*\n((?:Meat|Duck|Chicken)[^\n]+(?:\([^)]+\))?(?:[,.]?\s*[^\n]+)*)(?:\n\nAdditives|\nAdditives)',
    ]
    
    for i, pattern in enumerate(existing_patterns, 1):
        match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            result[f'existing_pattern_{i}'] = match.group(1).strip()[:100]
            break
    
    # Extract nutrition for reference
    nutrition = {}
    patterns = [
        (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein_percent'),
        (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat_percent'),
        (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fiber_percent'),
        (r'(?:Crude\s+)?Ash[:\s]+(\d+(?:\.\d+)?)\s*%', 'ash_percent'),
        (r'Moisture[:\s]+(\d+(?:\.\d+)?)\s*%', 'moisture_percent')
    ]
    
    for pattern, key in patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            nutrition[key] = float(match.group(1))
    
    if nutrition:
        result['nutrition'] = nutrition
    
    return result

def main():
    """Run test of Pattern 8 on 5 specific URLs"""
    print("=" * 60)
    print("TESTING PATTERN 8 (RELAXED EXTRACTION) ON 5 URLS")
    print("=" * 60)
    
    # Track results
    stats = {
        'total': 0,
        'pattern_8_success': 0,
        'ingredients_extracted': 0,
        'existing_patterns_success': 0,
        'with_nutrition': 0,
        'errors': 0
    }
    
    results = []
    
    # Test each URL
    for i, url in enumerate(TEST_URLS, 1):
        print(f"\n[{i}/5] Testing URL {i}")
        print(f"URL: {url}")
        
        # Delay between requests
        if i > 1:
            delay = random.uniform(15, 25)
            print(f"Waiting {delay:.1f}s...")
            time.sleep(delay)
        
        stats['total'] += 1
        
        # Scrape
        result = scrape_product(url)
        results.append(result)
        
        # Show results
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            stats['errors'] += 1
        else:
            print(f"Product: {result.get('product_name', 'Unknown')[:50]}")
            
            if result.get('pattern_8_captured'):
                print(f"✅ Pattern 8 captured content ({len(result['pattern_8_full'])} chars)")
                print(f"   Preview: {result['pattern_8_captured'][:100]}...")
                stats['pattern_8_success'] += 1
                
                if result.get('ingredients_extracted'):
                    print(f"✅ Ingredients extracted: {result['ingredients_extracted'][:100]}...")
                    stats['ingredients_extracted'] += 1
            else:
                print(f"⚠️ Pattern 8 did not match")
            
            # Check existing patterns
            for j in range(1, 5):
                if result.get(f'existing_pattern_{j}'):
                    print(f"📝 Existing pattern {j} matched: {result[f'existing_pattern_{j}'][:50]}...")
                    stats['existing_patterns_success'] += 1
                    break
            
            if 'nutrition' in result:
                print(f"📊 Nutrition found: {result['nutrition']}")
                stats['with_nutrition'] += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("PATTERN 8 TEST RESULTS")
    print("=" * 60)
    print(f"Total tested: {stats['total']}")
    print(f"Pattern 8 captured: {stats['pattern_8_success']} ({stats['pattern_8_success']/stats['total']*100:.0f}%)")
    print(f"Ingredients extracted: {stats['ingredients_extracted']} ({stats['ingredients_extracted']/stats['total']*100:.0f}%)")
    print(f"Existing patterns matched: {stats['existing_patterns_success']} ({stats['existing_patterns_success']/stats['total']*100:.0f}%)")
    print(f"With nutrition: {stats['with_nutrition']} ({stats['with_nutrition']/stats['total']*100:.0f}%)")
    print(f"Errors: {stats['errors']}")
    
    # Save detailed results for review
    output_file = f"test_pattern_8_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")
    
    # Decision
    if stats['pattern_8_success'] >= 4:  # 80% success
        print("\n🎉 SUCCESS: Pattern 8 works well! Ready for full batch.")
    else:
        print("\n⚠️ Pattern 8 needs adjustment. Review the captured content.")

if __name__ == "__main__":
    main()