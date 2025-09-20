#!/usr/bin/env python3
"""
BREED STANDARDS IMPORTER - Import structured data from official sources

Target sources:
- AKC (American Kennel Club) - Official US breed data
- The Kennel Club UK - Official UK breed data
- FCI (World Canine Organisation) - International breed data
- UKC (United Kennel Club) - Alternative US breed data

Target fields:
- Physical characteristics (height, weight, lifespan)
- Recognition status and breed groups
- Health issues and care requirements
- Temperament and working roles

Expected impact: High-quality, authoritative breed data
"""

import os
import json
import time
import random
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class BreedStandardsImporter:
    def __init__(self):
        """Initialize breed standards importer"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # ScrapingBee setup for official sites
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        if not self.scrapingbee_api_key:
            raise ValueError("Missing ScrapingBee API key (SCRAPING_BEE)")

        # Official breed registry sources
        self.breed_sources = {
            'akc': {
                'base_url': 'https://www.akc.org',
                'search_pattern': '/dog-breeds/{breed_slug}/',
                'priority': 1,
                'country': 'US'
            },
            'kennel_club': {
                'base_url': 'https://www.thekennelclub.org.uk',
                'search_pattern': '/breed-information/{breed_slug}/',
                'priority': 2,
                'country': 'UK'
            },
            'fci': {
                'base_url': 'https://www.fci.be',
                'search_pattern': '/en/breeds/{breed_slug}/',
                'priority': 3,
                'country': 'International'
            },
            'ukc': {
                'base_url': 'https://www.ukcdogs.com',
                'search_pattern': '/{breed_slug}/',
                'priority': 4,
                'country': 'US'
            }
        }

        # Data extraction patterns for official sources
        self.extraction_patterns = {
            'height_range': [
                r'height.*?(\d+).*?(?:to|-|–).*?(\d+).*?(?:inches?|cm)',
                r'(?:tall|height).*?(\d+).*?(?:to|-|–).*?(\d+)',
                r'(\d+).*?(?:to|-|–).*?(\d+).*?(?:inches?|cm).*?tall'
            ],
            'weight_range': [
                r'weight.*?(\d+).*?(?:to|-|–).*?(\d+).*?(?:pounds?|lbs?|kg)',
                r'(\d+).*?(?:to|-|–).*?(\d+).*?(?:pounds?|lbs?|kg)',
                r'weighs?.*?(\d+).*?(?:to|-|–).*?(\d+)'
            ],
            'lifespan': [
                r'life.*?expectancy.*?(\d+).*?(?:to|-|–).*?(\d+).*?years?',
                r'lifespan.*?(\d+).*?(?:to|-|–).*?(\d+).*?years?',
                r'lives?.*?(\d+).*?(?:to|-|–).*?(\d+).*?years?'
            ],
            'breed_group': [
                r'(?:group|classification).*?(?::|is|are)\s*([a-z\s]+?)(?:\.|;|\n)',
                r'(?:sporting|hound|working|terrier|toy|non-sporting|herding|miscellaneous)',
                r'breed.*?group.*?([a-z\s]+?)(?:\.|;|\n)'
            ],
            'temperament': [
                r'temperament.*?(?::|is|are)\s*([a-z\s,]+?)(?:\.|;|\n)',
                r'personality.*?(?::|is|are)\s*([a-z\s,]+?)(?:\.|;|\n)',
                r'(?:friendly|loyal|intelligent|active|calm|gentle)'
            ],
            'health_issues': [
                r'health.*?(?:concerns?|issues?|problems?).*?(?:include|are).*?([a-z\s,]+?)(?:\.|;|\n)',
                r'(?:prone|susceptible).*?to.*?([a-z\s,]+?)(?:\.|;|\n)',
                r'common.*?health.*?([a-z\s,]+?)(?:\.|;|\n)'
            ],
            'grooming_needs': [
                r'grooming.*?(?:needs?|requirements?).*?([a-z\s,]+?)(?:\.|;|\n)',
                r'coat.*?care.*?([a-z\s,]+?)(?:\.|;|\n)',
                r'brushing.*?([a-z\s,]+?)(?:\.|;|\n)'
            ]
        }

        # Priority mapping for breeds based on popularity/importance
        self.breed_priorities = {
            'high': ['labrador-retriever', 'golden-retriever', 'german-shepherd',
                    'french-bulldog', 'poodle', 'bulldog', 'beagle', 'rottweiler'],
            'medium': ['yorkshire-terrier', 'siberian-husky', 'boxer', 'dachshund'],
            'low': []  # All others
        }

    def get_breed_priority(self, breed_slug):
        """Get processing priority for breed"""
        if breed_slug in self.breed_priorities['high']:
            return 1
        elif breed_slug in self.breed_priorities['medium']:
            return 2
        else:
            return 3

    def get_breeds_needing_standards(self):
        """Get breeds that need official breed standard data"""
        print("🔍 Identifying breeds needing official breed standards...")

        response = self.supabase.table('breeds_unified_api').select('*').execute()
        breeds_data = response.data

        # Fields that can be filled from breed standards
        standard_fields = [
            'height_range', 'weight_range', 'lifespan_avg_years',
            'breed_group', 'temperament', 'health_issues',
            'grooming_needs', 'working_roles', 'recognized_by'
        ]

        target_breeds = []

        for breed in breeds_data:
            missing_fields = []
            for field in standard_fields:
                if not breed.get(field):
                    missing_fields.append(field)

            if missing_fields:
                priority = self.get_breed_priority(breed['breed_slug'])
                target_breeds.append({
                    'breed_slug': breed['breed_slug'],
                    'display_name': breed.get('display_name', breed['breed_slug']),
                    'missing_fields': missing_fields,
                    'priority': priority,
                    'gap_count': len(missing_fields),
                    'origin': breed.get('origin', ''),
                    'recognized_by': breed.get('recognized_by', '')
                })

        # Sort by priority (high priority first, then by gap count)
        target_breeds.sort(key=lambda x: (x['priority'], -x['gap_count']))

        print(f"📊 Found {len(target_breeds)} breeds needing breed standards")
        print(f"   High priority: {len([b for b in target_breeds if b['priority'] == 1])}")
        print(f"   Medium priority: {len([b for b in target_breeds if b['priority'] == 2])}")
        print(f"   Low priority: {len([b for b in target_breeds if b['priority'] == 3])}")

        return target_breeds

    def get_best_source_for_breed(self, breed_info):
        """Determine best official source for breed based on origin/recognition"""
        breed_slug = breed_info['breed_slug']
        origin = breed_info['origin'].lower()
        recognized_by = breed_info['recognized_by'].lower()

        # Priority order based on breed characteristics
        if 'akc' in recognized_by or 'american' in origin or 'united states' in origin:
            return ['akc', 'ukc', 'kennel_club', 'fci']
        elif 'kennel club' in recognized_by or 'british' in origin or 'united kingdom' in origin:
            return ['kennel_club', 'akc', 'fci', 'ukc']
        elif 'fci' in recognized_by or any(country in origin for country in
                                         ['germany', 'france', 'italy', 'spain', 'belgium']):
            return ['fci', 'kennel_club', 'akc', 'ukc']
        else:
            return ['akc', 'kennel_club', 'fci', 'ukc']

    def scrape_with_scrapingbee(self, url, breed_name=""):
        """Scrape official breed standard pages with ScrapingBee"""
        try:
            params = {
                'api_key': self.scrapingbee_api_key,
                'url': url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'country_code': 'us',
                'wait': 2000  # Wait for page to load
            }

            response = requests.get('https://app.scrapingbee.com/api/v1/',
                                  params=params, timeout=45)

            if response.status_code == 200:
                return response.text
            else:
                print(f"⚠️  ScrapingBee error {response.status_code} for {breed_name} at {url}")
                return None

        except Exception as e:
            print(f"❌ ScrapingBee failed for {breed_name}: {e}")
            return None

    def extract_breed_data(self, content, breed_name, source):
        """Extract structured breed data from official source content"""
        if not content:
            return {}

        import re
        content_lower = content.lower()
        extracted = {}

        for field, patterns in self.extraction_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, content_lower, re.IGNORECASE | re.DOTALL)
                if matches:
                    if field in ['height_range', 'weight_range']:
                        if len(matches[0]) == 2:  # Two numbers found
                            min_val, max_val = matches[0]
                            extracted[field] = f"{min_val}-{max_val}"

                            # Also extract individual min/max
                            if field == 'height_range':
                                extracted['height_min_cm'] = min_val
                                extracted['height_max_cm'] = max_val
                            elif field == 'weight_range':
                                extracted['weight_min_kg'] = min_val
                                extracted['weight_max_kg'] = max_val
                            break

                    elif field == 'lifespan':
                        if len(matches[0]) == 2:
                            min_years, max_years = matches[0]
                            extracted['lifespan_min_years'] = min_years
                            extracted['lifespan_max_years'] = max_years
                            extracted['lifespan_avg_years'] = str(round((int(min_years) + int(max_years)) / 2))
                            break

                    else:
                        # Text fields
                        result = matches[0].strip() if isinstance(matches[0], str) else str(matches[0])
                        if len(result) > 3:
                            extracted[field] = result
                            break

        # Source-specific extractions
        if source == 'akc':
            # AKC-specific breed group extraction
            group_match = re.search(r'(sporting|hound|working|terrier|toy|non-sporting|herding|miscellaneous)\s+group',
                                   content_lower)
            if group_match:
                extracted['breed_group'] = group_match.group(1).title() + ' Group'

        elif source == 'kennel_club':
            # KC-specific recognition status
            if 'kennel club' in content_lower:
                extracted['recognized_by'] = 'The Kennel Club UK'

        return extracted

    def process_breed_standards(self, breed_info):
        """Process breed to get official breed standards"""
        breed_slug = breed_info['breed_slug']
        breed_name = breed_info['display_name']
        missing_fields = breed_info['missing_fields']

        print(f"📋 Processing {breed_name} (Priority {breed_info['priority']})")

        # Get preferred sources for this breed
        source_priority = self.get_best_source_for_breed(breed_info)
        updates = {}
        fields_filled = 0

        for source in source_priority:
            if len(updates) >= 3:  # Limit to avoid over-processing
                break

            source_config = self.breed_sources[source]

            # Try different URL patterns for breed slug
            url_variations = [
                breed_slug,
                breed_slug.replace('-', '_'),
                breed_slug.replace('-', ''),
                breed_name.lower().replace(' ', '-')
            ]

            for url_variant in url_variations:
                url = source_config['base_url'] + source_config['search_pattern'].format(breed_slug=url_variant)

                print(f"   🔍 Trying {source}: {url}")
                content = self.scrape_with_scrapingbee(url, breed_name)

                if content and len(content) > 1000:  # Ensure we got substantial content
                    extracted = self.extract_breed_data(content, breed_name, source)

                    if extracted:
                        for field, value in extracted.items():
                            if field in missing_fields and field not in updates:
                                updates[field] = value
                                fields_filled += 1
                                print(f"   ✓ {source}: {field} = {value[:50]}...")

                        break  # Found good content, move to next source

                time.sleep(random.uniform(2, 4))  # Rate limiting

            if len(updates) >= len(missing_fields):
                break  # All fields filled

        # Update database
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
                print(f"   ❌ Database update failed: {e}")
                return {'breed': breed_name, 'success': False, 'error': str(e)}
        else:
            print(f"   ⚠️  No data extracted for {breed_name}")
            return {'breed': breed_name, 'fields_filled': 0, 'success': False}

    def run_standards_import(self, max_breeds=None):
        """Execute breed standards import"""
        print("\n" + "="*80)
        print("📚 BREED STANDARDS IMPORTER - STARTING")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        target_breeds = self.get_breeds_needing_standards()

        if max_breeds:
            target_breeds = target_breeds[:max_breeds]
            print(f"🎯 Limiting to first {max_breeds} highest-priority breeds")

        total_breeds = len(target_breeds)
        print(f"📊 Processing {total_breeds} breeds for official breed standards")

        # Process breeds sequentially (official sites are sensitive)
        results = []
        success_count = 0
        total_fields_filled = 0

        for i, breed_info in enumerate(target_breeds, 1):
            try:
                print(f"\n[{i:3d}/{total_breeds}] Processing {breed_info['display_name']}...")
                result = self.process_breed_standards(breed_info)
                results.append(result)

                if result['success']:
                    success_count += 1
                    total_fields_filled += result.get('fields_filled', 0)

                # Progress update every 10 breeds
                if i % 10 == 0:
                    progress = (i / total_breeds) * 100
                    print(f"\n📊 Progress: {progress:.1f}% - {total_fields_filled} fields filled")

            except Exception as e:
                print(f"❌ Error processing breed {i}: {e}")
                results.append({'breed': breed_info['display_name'], 'success': False, 'error': str(e)})

            # Cool-down between breeds for official sites
            time.sleep(random.uniform(3, 6))

        # Final summary
        success_rate = (success_count / total_breeds) * 100 if total_breeds > 0 else 0

        print("\n" + "="*80)
        print("🎉 BREED STANDARDS IMPORT COMPLETE")
        print("="*80)
        print(f"📊 FINAL STATISTICS:")
        print(f"   Breeds processed: {total_breeds}")
        print(f"   Successful updates: {success_count}")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total fields filled: {total_fields_filled}")
        print(f"   Estimated completeness gain: +{(total_fields_filled / 29733) * 100:.1f}%")
        print(f"⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'operation': 'Breed Standards Import',
            'total_breeds': total_breeds,
            'success_count': success_count,
            'success_rate': success_rate,
            'total_fields_filled': total_fields_filled,
            'estimated_gain_percent': (total_fields_filled / 29733) * 100,
            'sources_used': list(self.breed_sources.keys()),
            'detailed_results': results
        }

        with open('breed_standards_import_results.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📁 Report saved to breed_standards_import_results.json")
        return success_rate, total_fields_filled

if __name__ == "__main__":
    importer = BreedStandardsImporter()
    success_rate, fields_filled = importer.run_standards_import(max_breeds=25)  # Start with 25 breeds