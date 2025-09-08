#!/usr/bin/env python3
"""
Test script to verify Selenium setup and extract AKC breed data
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json

def test_akc_extraction():
    """Test extracting data from AKC with Selenium"""
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # New headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Setup driver with automatic ChromeDriver management
    print("Setting up Chrome driver...")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Driver created successfully")
    except Exception as e:
        print(f"❌ Failed to create driver: {e}")
        print("\nTrying alternative setup...")
        
        # Try without service object
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("✅ Driver created with alternative method")
        except Exception as e2:
            print(f"❌ Alternative also failed: {e2}")
            return None
    
    try:
        # Test URL
        url = "https://www.akc.org/dog-breeds/german-shepherd-dog/"
        print(f"\n📍 Loading: {url}")
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        
        # Wait for the main content
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        time.sleep(3)  # Additional wait for dynamic content
        
        print("✅ Page loaded")
        
        # Try different methods to extract data
        breed_data = {}
        
        # Method 1: Look for breed stats/characteristics section
        print("\n🔍 Searching for breed characteristics...")
        
        # Try to find breed stats by various selectors
        selectors_to_try = [
            "div.breed-stats",
            "div.breed-characteristics",
            "div.breed-info",
            "[class*='breed-stat']",
            "[class*='characteristic']",
            "[data-breed-stat]",
            "dl",  # Definition lists are often used for characteristics
            "table.breed-table",
            ".breed-hero__stats"
        ]
        
        for selector in selectors_to_try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"  Found elements with selector: {selector}")
                for elem in elements[:3]:  # Check first 3
                    text = elem.text.strip()
                    if text:
                        print(f"    Content: {text[:100]}...")
        
        # Method 2: Search for specific text patterns
        print("\n🔍 Searching for specific patterns...")
        
        # Search for height
        height_patterns = [
            "//text()[contains(., 'Height')]/..",
            "//*[contains(text(), 'inches')]",
            "//*[contains(@class, 'height')]"
        ]
        
        for pattern in height_patterns:
            try:
                elements = driver.find_elements(By.XPATH, pattern)
                if elements:
                    print(f"  Found height-related elements: {len(elements)}")
                    for elem in elements[:2]:
                        print(f"    {elem.text[:100] if elem.text else 'No text'}")
            except:
                pass
        
        # Method 3: Get all text and search for patterns
        print("\n🔍 Extracting all text content...")
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Search for common patterns
        import re
        
        # Height pattern
        height_match = re.search(r'Height[:\s]+([0-9]+(?:\.[0-9]+)?(?:-[0-9]+(?:\.[0-9]+)?)?)\s*inch', body_text, re.IGNORECASE)
        if height_match:
            breed_data['height'] = height_match.group(1)
            print(f"  ✅ Found height: {height_match.group(1)} inches")
        
        # Weight pattern
        weight_match = re.search(r'Weight[:\s]+([0-9]+(?:\.[0-9]+)?(?:-[0-9]+(?:\.[0-9]+)?)?)\s*(?:pound|lb)', body_text, re.IGNORECASE)
        if weight_match:
            breed_data['weight'] = weight_match.group(1)
            print(f"  ✅ Found weight: {weight_match.group(1)} pounds")
        
        # Life expectancy pattern
        life_match = re.search(r'Life (?:Expectancy|Span)[:\s]+([0-9]+(?:-[0-9]+)?)\s*year', body_text, re.IGNORECASE)
        if life_match:
            breed_data['lifespan'] = life_match.group(1)
            print(f"  ✅ Found lifespan: {life_match.group(1)} years")
        
        # Method 4: Check page source for JSON-LD or structured data
        print("\n🔍 Checking for structured data...")
        scripts = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
        if scripts:
            print(f"  Found {len(scripts)} JSON-LD scripts")
            for script in scripts:
                try:
                    json_data = json.loads(script.get_attribute('innerHTML'))
                    print(f"    Type: {json_data.get('@type', 'Unknown')}")
                    if 'breed' in str(json_data).lower():
                        print(f"    Contains breed data: {json.dumps(json_data, indent=2)[:500]}...")
                except:
                    pass
        
        # Method 5: Check for React/Vue data attributes
        print("\n🔍 Checking for React/Vue data...")
        react_elements = driver.find_elements(By.XPATH, "//*[@data-react-props or @data-vue-props or @data-breed]")
        if react_elements:
            print(f"  Found {len(react_elements)} elements with data attributes")
            for elem in react_elements[:3]:
                for attr in elem.get_property('attributes'):
                    if 'data' in attr['name']:
                        print(f"    {attr['name']}: {attr['value'][:100]}...")
        
        # Method 6: Execute JavaScript to access any global breed data
        print("\n🔍 Checking JavaScript globals...")
        js_globals = driver.execute_script("""
            var breedData = {};
            // Check common variable names
            var possibleVars = ['breedData', 'breed', 'dogBreed', 'pageData', '__INITIAL_STATE__', 'window.__data'];
            for (var i = 0; i < possibleVars.length; i++) {
                if (window[possibleVars[i]]) {
                    breedData[possibleVars[i]] = window[possibleVars[i]];
                }
            }
            return JSON.stringify(breedData);
        """)
        
        if js_globals and js_globals != "{}":
            print(f"  Found JS data: {js_globals[:200]}...")
        
        print(f"\n📊 Extracted breed data: {breed_data}")
        
        return breed_data
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        driver.quit()
        print("\n✅ Driver closed")

if __name__ == "__main__":
    print("🚀 Starting AKC Selenium test")
    print("=" * 60)
    
    result = test_akc_extraction()
    
    if result:
        print("\n✅ Test completed successfully")
        print(f"Results: {json.dumps(result, indent=2)}")
    else:
        print("\n❌ Test failed - Selenium might need different setup")
        print("\nPossible fixes:")
        print("1. Install Chrome browser if not installed")
        print("2. Try: brew install --cask google-chrome")
        print("3. Or use Safari driver: brew install --cask safari-technology-preview")