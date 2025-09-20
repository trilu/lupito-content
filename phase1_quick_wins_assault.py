#!/usr/bin/env python3
"""
PHASE 1 QUICK WINS ASSAULT - Target 70.9% → 80% Completeness

Targets fields with 50-90% completion for maximum ROI:
- coat (50.6% → 95%): 259 breeds missing
- grooming_needs (53.5% → 95%): 245 breeds missing
- colors (54.5% → 95%): 236 breeds missing
- lifespan data (59.2% → 95%): 209 breeds missing each
- training_tips (61.2% → 95%): 197 breeds missing

Expected impact: +2,839 fields, ~9% completeness gain
"""

import os
import json
import time
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class Phase1QuickWinsAssault:
    def __init__(self):
        """Initialize Phase 1 assault system"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # ScrapingBee setup (using same env var as previous projects)
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        if not self.scrapingbee_api_key:
            raise ValueError("Missing ScrapingBee API key (SCRAPING_BEE)")

        # Phase 1 target fields (50-90% completion)
        self.target_fields = {
            'coat': {'priority': 1, 'missing_target': 259},
            'grooming_needs': {'priority': 1, 'missing_target': 245},
            'colors': {'priority': 1, 'missing_target': 236},
            'lifespan_min_years': {'priority': 2, 'missing_target': 209},
            'lifespan_max_years': {'priority': 2, 'missing_target': 209},
            'lifespan_avg_years': {'priority': 2, 'missing_target': 209},
            'training_tips': {'priority': 3, 'missing_target': 197}
        }

        # Search patterns for each field
        self.search_patterns = {
            'coat': [
                "{breed} coat type texture",
                "{breed} hair coat description",
                "{breed} breed standard coat"
            ],
            'grooming_needs': [
                "{breed} grooming requirements care",
                "{breed} brushing maintenance needs",
                "{breed} grooming schedule frequency"
            ],
            'colors': [
                "{breed} colors coat varieties",
                "{breed} breed standard colors",
                "{breed} acceptable coat colors"
            ],
            'lifespan_min_years': [
                "{breed} lifespan life expectancy years",
                "{breed} average lifespan longevity",
                "{breed} breed information life span"
            ],
            'lifespan_max_years': [
                "{breed} lifespan life expectancy years",
                "{breed} maximum lifespan longevity",
                "{breed} breed information life span"
            ],
            'training_tips': [
                "{breed} training tips methods",
                "{breed} how to train guide",
                "{breed} training advice techniques"
            ]
        }

        # Enhanced extraction patterns
        self.extraction_patterns = {
            'coat': [
                r'coat.*?(?:is|has|features?).*?([a-z\s,]+?)(?:\.|;|,|\n)',
                r'(?:hair|fur|coat).*?(?:type|texture).*?([a-z\s,]+?)(?:\.|;|,|\n)',
                r'(?:double|single|smooth|rough|wiry|soft|dense|thick).*?coat'
            ],
            'grooming_needs': [
                r'grooming.*?(?:needs?|requires?).*?([a-z\s,]+?)(?:\.|;|,|\n)',
                r'(?:brush|brushing).*?(?:daily|weekly|monthly|regularly|occasionally)',
                r'(?:low|high|moderate|minimal).*?(?:maintenance|grooming)'
            ],
            'colors': [
                r'colors?.*?(?:include|are|:).*?([a-z\s,&-]+?)(?:\.|;|\n)',
                r'(?:acceptable|standard|recognized).*?colors?.*?([a-z\s,&-]+?)(?:\.|;|\n)',
                r'(?:black|white|brown|red|golden|silver|gray|blue|cream|sable).*?(?:and|,|&)'
            ],
            'lifespan_min_years': [
                r'(?:lifespan|life expectancy).*?(\d+).*?(?:to|-).*?\d+.*?years?',
                r'live.*?(\d+).*?(?:to|-).*?\d+.*?years?',
                r'(?:typically|average|usually).*?live.*?(\d+).*?years?'
            ],
            'lifespan_max_years': [
                r'(?:lifespan|life expectancy).*?\d+.*?(?:to|-).*?(\d+).*?years?',
                r'live.*?\d+.*?(?:to|-).*?(\d+).*?years?',
                r'up.*?to.*?(\d+).*?years?'
            ],
            'training_tips': [
                r'training.*?(?:tips?|advice|methods?).*?([a-z\s,]+?)(?:\.|;|\n)',
                r'(?:train|teach).*?(?:by|using|with).*?([a-z\s,]+?)(?:\.|;|\n)',
                r'(?:positive|consistent|patient).*?(?:training|approach)'
            ]
        }

    def get_breeds_with_phase1_gaps(self):
        """Get breeds missing Phase 1 target fields"""
        print("🔍 Identifying breeds with Phase 1 gaps...")

        response = self.supabase.table('breeds_unified_api').select('*').execute()
        breeds_data = response.data

        priority_breeds = []

        for breed in breeds_data:
            missing_fields = []
            priority_score = 0

            for field, config in self.target_fields.items():
                if not breed.get(field):
                    missing_fields.append(field)
                    priority_score += (4 - config['priority'])  # Higher priority = higher score

            if missing_fields:
                priority_breeds.append({
                    'breed_slug': breed['breed_slug'],
                    'display_name': breed.get('display_name', breed['breed_slug']),
                    'missing_fields': missing_fields,
                    'priority_score': priority_score,
                    'gap_count': len(missing_fields)
                })

        # Sort by priority score (most important gaps first)
        priority_breeds.sort(key=lambda x: (-x['priority_score'], -x['gap_count']))

        print(f"📊 Found {len(priority_breeds)} breeds with Phase 1 gaps")
        print(f"   Total missing fields: {sum(b['gap_count'] for b in priority_breeds)}")
        print(f"   Average gaps per breed: {sum(b['gap_count'] for b in priority_breeds) / len(priority_breeds):.1f}")

        return priority_breeds

    def scrape_with_scrapingbee(self, url, breed_name=""):
        """Enhanced ScrapingBee scraping with retries"""
        try:
            params = {
                'api_key': self.scrapingbee_api_key,
                'url': url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'country_code': 'us'
            }

            response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, timeout=30)

            if response.status_code == 200:
                return response.text
            else:
                print(f"⚠️  ScrapingBee error {response.status_code} for {breed_name}")
                return None

        except Exception as e:
            print(f"❌ ScrapingBee failed for {breed_name}: {e}")
            return None

    def smart_search_urls(self, breed_name, field):
        """Generate smart search URLs for specific field"""
        patterns = self.search_patterns.get(field, [f"{breed_name} {field}"])
        urls = []

        for pattern in patterns:
            query = pattern.format(breed=breed_name)
            encoded_query = quote_plus(query)

            # Target high-quality breed information sources
            search_urls = [
                f"https://www.google.com/search?q={encoded_query}+site:akc.org",
                f"https://www.google.com/search?q={encoded_query}+site:thekennelclub.org.uk",
                f"https://www.google.com/search?q={encoded_query}+site:fci.be",
                f"https://www.google.com/search?q={encoded_query}+breed+standard",
                f"https://www.google.com/search?q={encoded_query}+breed+information"
            ]
            urls.extend(search_urls)

        return urls[:3]  # Limit to 3 URLs per field to avoid overload

    def extract_field_data(self, content, field, breed_name):
        """Enhanced field extraction with multiple patterns"""
        if not content:
            return None

        import re
        content_lower = content.lower()
        patterns = self.extraction_patterns.get(field, [])

        for pattern in patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE | re.DOTALL)
            if matches:
                result = matches[0].strip()
                if len(result) > 5:  # Minimum length check
                    return result

        # Fallback: Simple keyword extraction
        if field == 'coat':
            keywords = ['smooth', 'rough', 'long', 'short', 'double', 'single', 'wiry', 'soft', 'dense']
            for keyword in keywords:
                if keyword in content_lower:
                    return f"{keyword} coat"

        elif field == 'colors':
            color_keywords = ['black', 'white', 'brown', 'red', 'golden', 'silver', 'cream', 'sable', 'brindle']
            found_colors = [color for color in color_keywords if color in content_lower]
            if found_colors:
                return ', '.join(found_colors)

        elif field.startswith('lifespan'):
            numbers = re.findall(r'(\d+).*?years?', content_lower)
            if numbers:
                years = [int(n) for n in numbers if 8 <= int(n) <= 20]  # Realistic dog lifespan
                if years:
                    if field == 'lifespan_min_years':
                        return str(min(years))
                    elif field == 'lifespan_max_years':
                        return str(max(years))
                    elif field == 'lifespan_avg_years':
                        return str(round(sum(years) / len(years)))

        return None

    def process_breed(self, breed_info):
        """Process single breed for Phase 1 fields"""
        breed_slug = breed_info['breed_slug']
        breed_name = breed_info['display_name']
        missing_fields = breed_info['missing_fields']

        print(f"🎯 Processing {breed_name} ({len(missing_fields)} gaps)")

        updates = {}
        fields_filled = 0

        for field in missing_fields:
            try:
                # Generate search URLs for this field
                search_urls = self.smart_search_urls(breed_name, field)

                for url in search_urls:
                    content = self.scrape_with_scrapingbee(url, breed_name)
                    if content:
                        extracted_data = self.extract_field_data(content, field, breed_name)
                        if extracted_data:
                            updates[field] = extracted_data
                            fields_filled += 1
                            print(f"   ✓ Found {field}: {extracted_data[:50]}...")
                            break

                    # Rate limiting
                    time.sleep(random.uniform(1, 3))

                if field not in updates:
                    print(f"   ⚠️  No data found for {field}")

            except Exception as e:
                print(f"   ❌ Error processing {field}: {e}")

        # Update database if we found anything
        if updates:
            try:
                self.supabase.table('breeds_unified_api').update(updates).eq('breed_slug', breed_slug).execute()
                print(f"   💾 Updated {len(updates)} fields for {breed_name}")
                return {
                    'breed': breed_name,
                    'fields_filled': fields_filled,
                    'updated_fields': list(updates.keys()),
                    'success': True
                }
            except Exception as e:
                print(f"   ❌ Database update failed for {breed_name}: {e}")
                return {'breed': breed_name, 'success': False, 'error': str(e)}
        else:
            return {'breed': breed_name, 'fields_filled': 0, 'success': False}

    def run_phase1_assault(self, max_breeds=None):
        """Execute Phase 1 assault with progress tracking"""
        print("\n" + "="*80)
        print("🚀 PHASE 1 QUICK WINS ASSAULT - STARTING")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # Get breeds with gaps
        target_breeds = self.get_breeds_with_phase1_gaps()

        if max_breeds:
            target_breeds = target_breeds[:max_breeds]
            print(f"🎯 Limiting to first {max_breeds} highest-priority breeds")

        total_breeds = len(target_breeds)
        print(f"📊 Processing {total_breeds} breeds with Phase 1 gaps")

        # Process breeds with threading
        results = []
        success_count = 0
        total_fields_filled = 0

        batch_size = 10
        for i in range(0, total_breeds, batch_size):
            batch = target_breeds[i:i+batch_size]
            print(f"\n🔄 BATCH {i//batch_size + 1}: Processing {len(batch)} breeds...")

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.process_breed, breed) for breed in batch]

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)

                        if result['success']:
                            success_count += 1
                            total_fields_filled += result.get('fields_filled', 0)

                        print(f"   📈 Progress: {len(results)}/{total_breeds} breeds processed")

                    except Exception as e:
                        print(f"   ❌ Batch error: {e}")

            # Progress update
            current_completion = (len(results) / total_breeds) * 100
            print(f"   📊 Batch complete: {current_completion:.1f}% overall progress")

            # Cool-down between batches
            if i + batch_size < total_breeds:
                print("   ⏳ Cooling down...")
                time.sleep(10)

        # Final summary
        success_rate = (success_count / total_breeds) * 100 if total_breeds > 0 else 0

        print("\n" + "="*80)
        print("🎉 PHASE 1 ASSAULT COMPLETE")
        print("="*80)
        print(f"📊 FINAL STATISTICS:")
        print(f"   Breeds processed: {total_breeds}")
        print(f"   Successful updates: {success_count}")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total fields filled: {total_fields_filled}")
        print(f"   Estimated completeness gain: +{(total_fields_filled / 29733) * 100:.1f}%")
        print(f"⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Save detailed results
        report = {
            'timestamp': datetime.now().isoformat(),
            'phase': 'Phase 1 - Quick Wins',
            'total_breeds': total_breeds,
            'success_count': success_count,
            'success_rate': success_rate,
            'total_fields_filled': total_fields_filled,
            'estimated_gain_percent': (total_fields_filled / 29733) * 100,
            'target_fields': list(self.target_fields.keys()),
            'detailed_results': results
        }

        with open('phase1_assault_results.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📁 Detailed report saved to phase1_assault_results.json")
        return success_rate, total_fields_filled

if __name__ == "__main__":
    assault = Phase1QuickWinsAssault()
    success_rate, fields_filled = assault.run_phase1_assault(max_breeds=50)  # Start with 50 breeds