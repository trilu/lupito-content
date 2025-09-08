#!/usr/bin/env python3
"""
AKC Breed Scraper using Playwright - Handles JavaScript-rendered content
"""

import os
import sys
import json
import time
import re
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

class AKCPlaywrightScraper:
    def __init__(self):
        """Initialize the scraper"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials in .env file")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Statistics
        self.stats = {
            'processed': 0,
            'extracted': 0,
            'failed': 0,
            'updated': 0
        }

    async def extract_breed_data(self, page, url: str) -> Dict[str, Any]:
        """Extract breed data from AKC page using Playwright"""
        
        print(f"  🔍 Extracting from: {url}")
        
        # Navigate to the page
        await page.goto(url, wait_until='networkidle')
        
        # Wait a bit for any dynamic content
        await page.wait_for_timeout(2000)
        
        breed_data = {
            'akc_url': url,
            'breed_slug': url.rstrip('/').split('/')[-1],
            'extraction_status': 'success'
        }
        
        # Get breed name
        try:
            h1 = await page.query_selector('h1')
            if h1:
                breed_data['display_name'] = await h1.text_content()
                breed_data['display_name'] = breed_data['display_name'].strip()
        except:
            pass
        
        # Get all text content
        content = await page.content()
        visible_text = await page.evaluate('() => document.body.innerText')
        
        # Extract physical characteristics using regex patterns
        traits = {}
        
        # Height
        height_match = re.search(
            r'Height[:\s]*([0-9]+(?:\.[0-9]+)?(?:\s*[-–]\s*[0-9]+(?:\.[0-9]+)?)?)\s*inch',
            visible_text, re.IGNORECASE
        )
        if height_match:
            traits['Height'] = height_match.group(1)
            height_min, height_max = self._parse_range(height_match.group(1))
            if height_min:
                breed_data['height_cm_min'] = round(height_min * 2.54, 1)
            if height_max:
                breed_data['height_cm_max'] = round(height_max * 2.54, 1)
            print(f"    ✅ Found height: {height_match.group(1)} inches")
        
        # Weight
        weight_match = re.search(
            r'Weight[:\s]*([0-9]+(?:\.[0-9]+)?(?:\s*[-–]\s*[0-9]+(?:\.[0-9]+)?)?)\s*(?:pound|lb)',
            visible_text, re.IGNORECASE
        )
        if weight_match:
            traits['Weight'] = weight_match.group(1)
            weight_min, weight_max = self._parse_range(weight_match.group(1))
            if weight_min:
                breed_data['weight_kg_min'] = round(weight_min * 0.453592, 1)
            if weight_max:
                breed_data['weight_kg_max'] = round(weight_max * 0.453592, 1)
            print(f"    ✅ Found weight: {weight_match.group(1)} pounds")
        
        # Life Expectancy
        life_match = re.search(
            r'Life (?:Expectancy|Span)[:\s]*([0-9]+(?:\s*[-–]\s*[0-9]+)?)\s*year',
            visible_text, re.IGNORECASE
        )
        if life_match:
            traits['Life Expectancy'] = life_match.group(1)
            life_min, life_max = self._parse_range(life_match.group(1))
            if life_min:
                breed_data['lifespan_years_min'] = int(life_min)
            if life_max:
                breed_data['lifespan_years_max'] = int(life_max)
            print(f"    ✅ Found lifespan: {life_match.group(1)} years")
        
        # Try to extract from structured data or JavaScript objects
        try:
            # Execute JavaScript to check for any global breed data
            js_data = await page.evaluate('''() => {
                // Check for common variable names
                const possibleVars = ['breedData', 'breed', '__INITIAL_STATE__', 'pageData'];
                for (let varName of possibleVars) {
                    if (window[varName]) {
                        return JSON.stringify(window[varName]);
                    }
                }
                
                // Check for React props
                const reactRoot = document.querySelector('#root') || document.querySelector('[data-reactroot]');
                if (reactRoot && reactRoot._reactRootContainer) {
                    return JSON.stringify(reactRoot._reactRootContainer);
                }
                
                // Check for data attributes
                const elements = document.querySelectorAll('[data-breed], [data-characteristics]');
                const data = {};
                elements.forEach(el => {
                    for (let attr of el.attributes) {
                        if (attr.name.startsWith('data-')) {
                            data[attr.name] = attr.value;
                        }
                    }
                });
                return JSON.stringify(data);
            }''')
            
            if js_data and js_data != '{}':
                print(f"    📦 Found JavaScript data: {js_data[:100]}...")
                # Parse and extract any useful data
                try:
                    parsed = json.loads(js_data)
                    # Look for breed-specific fields
                    for key in ['height', 'weight', 'lifespan', 'size', 'energy']:
                        if key in parsed:
                            traits[key] = parsed[key]
                except:
                    pass
        except:
            pass
        
        # Extract breed characteristics (energy, shedding, etc.)
        characteristic_patterns = {
            'energy': r'Energy (?:Level)?[:\s]*(\w+)',
            'shedding': r'Shedding[:\s]*(\w+)',
            'trainability': r'Trainability[:\s]*(\w+)',
            'bark_level': r'Bark(?:ing)? (?:Level)?[:\s]*(\w+)',
            'coat_length': r'Coat (?:Length)?[:\s]*(\w+)'
        }
        
        for char_name, pattern in characteristic_patterns.items():
            match = re.search(pattern, visible_text, re.IGNORECASE)
            if match:
                value = match.group(1).lower()
                breed_data[char_name] = self._normalize_value(char_name, value)
                print(f"    ✅ Found {char_name}: {value}")
        
        # Determine size based on weight
        if 'weight_kg_max' in breed_data:
            breed_data['size'] = self._determine_size(breed_data['weight_kg_max'])
        
        # Store raw traits
        breed_data['raw_traits'] = traits
        
        # Extract comprehensive content sections
        content_sections = {}
        
        # Try to get main content sections
        sections = await page.query_selector_all('section, article, .breed-content')
        for section in sections:
            try:
                heading = await section.query_selector('h2, h3')
                if heading:
                    title = await heading.text_content()
                    content_text = await section.text_content()
                    
                    title_lower = title.lower().strip()
                    if 'history' in title_lower:
                        content_sections['history'] = content_text[:5000]
                    elif 'personality' in title_lower or 'temperament' in title_lower:
                        content_sections['personality'] = content_text[:5000]
                    elif 'health' in title_lower:
                        content_sections['health'] = content_text[:5000]
                    elif 'care' in title_lower:
                        content_sections['care'] = content_text[:5000]
                    elif 'grooming' in title_lower:
                        content_sections['grooming'] = content_text[:5000]
                    elif 'exercise' in title_lower:
                        content_sections['exercise'] = content_text[:5000]
                    elif 'training' in title_lower:
                        content_sections['training'] = content_text[:5000]
            except:
                continue
        
        # If no sections found, use the general text
        if not content_sections:
            content_sections['about'] = visible_text[:10000]
        
        breed_data['comprehensive_content'] = content_sections
        
        return breed_data

    def _parse_range(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse a range like '50-90' or '50 - 90' into min and max values"""
        numbers = re.findall(r'[0-9]+(?:\.[0-9]+)?', text)
        if len(numbers) >= 2:
            return float(numbers[0]), float(numbers[1])
        elif len(numbers) == 1:
            return float(numbers[0]), float(numbers[0])
        return None, None

    def _determine_size(self, weight_kg: float) -> str:
        """Determine size category based on weight"""
        if weight_kg < 10:
            return 'small'
        elif weight_kg < 25:
            return 'medium'
        elif weight_kg < 45:
            return 'large'
        else:
            return 'giant'

    def _normalize_value(self, field: str, value: str) -> str:
        """Normalize characteristic values"""
        value = value.lower()
        
        if field in ['energy', 'shedding', 'bark_level']:
            if value in ['low', 'minimal']:
                return 'low'
            elif value in ['moderate', 'medium', 'average']:
                return 'moderate'
            elif value in ['high', 'heavy']:
                return 'high'
            elif value in ['very high', 'extreme']:
                return 'very high'
        
        elif field == 'trainability':
            if value in ['easy', 'high']:
                return 'easy'
            elif value in ['moderate', 'medium']:
                return 'moderate'
            elif value in ['challenging', 'difficult', 'low']:
                return 'challenging'
        
        elif field == 'coat_length':
            if value in ['short', 'smooth']:
                return 'short'
            elif value in ['medium', 'moderate']:
                return 'medium'
            elif value in ['long', 'flowing']:
                return 'long'
        
        return value

    def update_breed(self, breed_data: Dict[str, Any]) -> bool:
        """Update breed in akc_breeds table"""
        try:
            breed_slug = breed_data['breed_slug']
            
            # Update the breed
            result = self.supabase.table('akc_breeds').update(breed_data).eq('breed_slug', breed_slug).execute()
            
            if result.data:
                print(f"    ✅ Updated: {breed_data.get('display_name', breed_slug)}")
                self.stats['updated'] += 1
                return True
            else:
                print(f"    ❌ Failed to update: {breed_slug}")
                return False
                
        except Exception as e:
            print(f"    ❌ Database error: {e}")
            return False

    async def scrape_breeds(self, limit: Optional[int] = None):
        """Main scraping function"""
        
        # Get breeds that need updating (those without physical data)
        result = self.supabase.table('akc_breeds').select('breed_slug, akc_url, display_name').execute()
        
        breeds_to_update = []
        for breed in result.data:
            # Check if breed needs updating (no physical data)
            check = self.supabase.table('akc_breeds').select('has_physical_data').eq('breed_slug', breed['breed_slug']).single().execute()
            if check.data and not check.data.get('has_physical_data'):
                breeds_to_update.append(breed)
        
        if limit:
            breeds_to_update = breeds_to_update[:limit]
        
        print(f"📊 Found {len(breeds_to_update)} breeds needing physical data extraction")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            for idx, breed in enumerate(breeds_to_update, 1):
                print(f"\n[{idx}/{len(breeds_to_update)}] Processing: {breed['display_name']}")
                
                try:
                    # Extract breed data
                    breed_data = await self.extract_breed_data(page, breed['akc_url'])
                    
                    if breed_data:
                        self.stats['extracted'] += 1
                        # Update in database
                        self.update_breed(breed_data)
                    else:
                        self.stats['failed'] += 1
                        
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    self.stats['failed'] += 1
                
                self.stats['processed'] += 1
                
                # Rate limiting
                if idx < len(breeds_to_update):
                    await asyncio.sleep(2)
                
                # Progress update
                if idx % 10 == 0:
                    print(f"\n📊 Progress: {idx}/{len(breeds_to_update)}")
                    print(f"  Extracted: {self.stats['extracted']}")
                    print(f"  Updated: {self.stats['updated']}")
                    print(f"  Failed: {self.stats['failed']}")
            
            await browser.close()
        
        # Final report
        print("\n" + "=" * 60)
        print("🎯 PLAYWRIGHT SCRAPER REPORT")
        print("=" * 60)
        print(f"Breeds processed: {self.stats['processed']}")
        print(f"Successfully extracted: {self.stats['extracted']}")
        print(f"Database updated: {self.stats['updated']}")
        print(f"Failed: {self.stats['failed']}")
        
        if self.stats['extracted'] > 0:
            success_rate = (self.stats['extracted'] / self.stats['processed']) * 100
            print(f"Success rate: {success_rate:.1f}%")
        print("=" * 60)


async def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AKC Breed Scraper with Playwright')
    parser.add_argument('--limit', type=int, help='Limit number of breeds to update')
    parser.add_argument('--test', action='store_true', help='Test with 5 breeds')
    
    args = parser.parse_args()
    
    scraper = AKCPlaywrightScraper()
    
    if args.test:
        await scraper.scrape_breeds(limit=5)
    else:
        await scraper.scrape_breeds(limit=args.limit)


if __name__ == "__main__":
    print("🚀 Starting AKC Playwright Scraper")
    print("=" * 60)
    asyncio.run(main())