#!/usr/bin/env python3
"""
Test AKC scraping with Safari driver (built into macOS)
"""

import time
import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_with_safari():
    """Test extracting AKC data with Safari"""
    
    print("🚀 Testing with Safari driver")
    print("Note: You may need to enable 'Allow Remote Automation' in Safari's Develop menu")
    print("=" * 60)
    
    try:
        # Safari driver doesn't need additional setup on macOS
        driver = webdriver.Safari()
        print("✅ Safari driver created successfully")
        
        # Test URL
        url = "https://www.akc.org/dog-breeds/german-shepherd-dog/"
        print(f"\n📍 Loading: {url}")
        driver.get(url)
        
        # Wait a bit for page to load
        time.sleep(5)
        
        print("✅ Page loaded")
        
        # Get page source
        page_source = driver.page_source
        
        # Try to extract data from page source
        breed_data = {}
        
        # Search in the raw HTML
        print("\n🔍 Searching page source for data...")
        
        # Look for height
        height_patterns = [
            r'Height[:\s]*([0-9]+(?:\.[0-9]+)?(?:\s*-\s*[0-9]+(?:\.[0-9]+)?)?)\s*inch',
            r'"height"[:\s]*"([^"]+)"',
            r'data-height="([^"]+)"'
        ]
        
        for pattern in height_patterns:
            match = re.search(pattern, page_source, re.IGNORECASE)
            if match:
                breed_data['height'] = match.group(1)
                print(f"  ✅ Found height: {match.group(1)}")
                break
        
        # Look for weight
        weight_patterns = [
            r'Weight[:\s]*([0-9]+(?:\.[0-9]+)?(?:\s*-\s*[0-9]+(?:\.[0-9]+)?)?)\s*(?:pound|lb)',
            r'"weight"[:\s]*"([^"]+)"',
            r'data-weight="([^"]+)"'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, page_source, re.IGNORECASE)
            if match:
                breed_data['weight'] = match.group(1)
                print(f"  ✅ Found weight: {match.group(1)}")
                break
        
        # Look for life expectancy
        life_patterns = [
            r'Life (?:Expectancy|Span)[:\s]*([0-9]+(?:\s*-\s*[0-9]+)?)\s*year',
            r'"lifespan"[:\s]*"([^"]+)"',
            r'data-lifespan="([^"]+)"'
        ]
        
        for pattern in life_patterns:
            match = re.search(pattern, page_source, re.IGNORECASE)
            if match:
                breed_data['lifespan'] = match.group(1)
                print(f"  ✅ Found lifespan: {match.group(1)}")
                break
        
        # Get visible text
        body = driver.find_element(By.TAG_NAME, "body")
        visible_text = body.text
        
        print(f"\n📄 Page has {len(visible_text)} characters of visible text")
        
        # Search visible text for patterns
        if 'height' not in breed_data:
            match = re.search(r'Height[:\s]+([0-9]+(?:\.[0-9]+)?(?:\s*-\s*[0-9]+(?:\.[0-9]+)?)?)\s*inch', visible_text, re.IGNORECASE)
            if match:
                breed_data['height'] = match.group(1)
                print(f"  ✅ Found height in text: {match.group(1)}")
        
        if 'weight' not in breed_data:
            match = re.search(r'Weight[:\s]+([0-9]+(?:\.[0-9]+)?(?:\s*-\s*[0-9]+(?:\.[0-9]+)?)?)\s*(?:pound|lb)', visible_text, re.IGNORECASE)
            if match:
                breed_data['weight'] = match.group(1)
                print(f"  ✅ Found weight in text: {match.group(1)}")
        
        # Try to find any structured data
        scripts = driver.find_elements(By.TAG_NAME, "script")
        print(f"\n🔍 Checking {len(scripts)} script tags...")
        
        for script in scripts:
            content = script.get_attribute('innerHTML')
            if content and ('breed' in content.lower() or 'height' in content.lower()):
                # Check if it's JSON
                if '{' in content and '}' in content:
                    print(f"  Found potential breed data in script")
                    # Try to extract JSON
                    json_match = re.search(r'\{[^{}]*"(?:height|weight|breed)[^{}]*\}', content)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                            print(f"    Parsed JSON: {json.dumps(data, indent=2)[:200]}...")
                        except:
                            pass
        
        print(f"\n📊 Final extracted data: {breed_data}")
        
        driver.quit()
        return breed_data
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    result = test_with_safari()
    
    if result:
        print("\n✅ Successfully extracted some data")
    else:
        print("\n❓ No data extracted - the site may be fully JavaScript rendered")