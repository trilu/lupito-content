#!/usr/bin/env python3
"""
BREED CONTENT SCRAPER ORCHESTRATOR
Robust ScrapingBee-based scraper for breed content using orchestrator pattern
Targets high-value breed information sites with JavaScript and bot protection
"""

import os
import json
import re
import time
import random
import requests
import threading
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

class BreedContentScraper:
    def __init__(self, session_name: str, country_code: str = 'us'):
        """Initialize a scraper session"""
        self.session_name = session_name
        self.country_code = country_code

        # ScrapingBee setup
        self.scrapingbee_key = os.getenv('SCRAPINGBEE_API_KEY')
        if not self.scrapingbee_key:
            self.scrapingbee_key = os.getenv('SCRAPING_BEE')  # Alternative env var

        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Statistics
        self.stats = {
            'breeds_processed': 0,
            'fields_scraped': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

        # High-value breed information sources
        self.breed_sources = {
            'akc': 'https://www.akc.org/dog-breeds/{breed}/',
            'dogtime': 'https://dogtime.com/dog-breeds/{breed}',
            'petfinder': 'https://www.petfinder.com/dog-breeds/{breed}/',
            'hillspet': 'https://www.hillspet.com/dog-care/dog-breeds/{breed}',
            'purina': 'https://www.purina.com/dogs/dog-breeds/{breed}',
            'rover': 'https://www.rover.com/blog/dog-breeds/{breed}/',
            'dailypaws': 'https://www.dailypaws.com/dogs-puppies/dog-breeds/{breed}',
            'thesprucepets': 'https://www.thesprucepets.com/{breed}-dog-breed-profile-'
        }

        print(f"🎯 Session {session_name} initialized with country_code={country_code}")

    def scrape_with_scrapingbee(self, url: str, wait_time: int = 5000) -> Optional[str]:
        """Scrape a URL using ScrapingBee with robust settings"""
        params = {
            'api_key': self.scrapingbee_key,
            'url': url,
            'render_js': 'true',
            'wait': str(wait_time),
            'premium_proxy': 'true',
            'country_code': self.country_code,
            'block_ads': 'true',
            'block_resources': 'false',
            'javascript_snippet': """
                // Wait for dynamic content
                await new Promise(resolve => setTimeout(resolve, 2000));

                // Scroll to trigger lazy loading
                window.scrollTo(0, document.body.scrollHeight / 2);
                await new Promise(resolve => setTimeout(resolve, 1000));
                window.scrollTo(0, document.body.scrollHeight);
            """
        }

        try:
            response = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=60
            )

            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                print(f"   ⚠️ Rate limited, waiting 30s...")
                time.sleep(30)
                return None
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:100]}")
                return None

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return None

    def extract_breed_content(self, html: str, breed_name: str) -> Dict:
        """Extract breed content from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        content = {}
        page_text = soup.get_text()

        # Height extraction
        height_patterns = [
            r'height[:\s]*([\d]+)[-–to\s]+([\d]+)\s*(?:inches|in)',
            r'([\d]+)[-–to\s]+([\d]+)\s*(?:inches|in)[^.]*(?:tall|height)',
            r'height[:\s]*([\d]+)[-–to\s]+([\d]+)\s*cm',
        ]

        for pattern in height_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                min_val = int(match.group(1))
                max_val = int(match.group(2))

                # Convert inches to cm if needed
                if 'in' in pattern:
                    min_val = round(min_val * 2.54)
                    max_val = round(max_val * 2.54)

                content['height_min_cm'] = min_val
                content['height_max_cm'] = max_val
                break

        # Weight extraction
        weight_patterns = [
            r'weight[:\s]*([\d]+)[-–to\s]+([\d]+)\s*(?:pounds|lbs|lb)',
            r'([\d]+)[-–to\s]+([\d]+)\s*(?:pounds|lbs|lb)[^.]*weight',
            r'weight[:\s]*([\d]+)[-–to\s]+([\d]+)\s*kg',
        ]

        for pattern in weight_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                min_val = float(match.group(1))
                max_val = float(match.group(2))

                # Convert pounds to kg if needed
                if 'lb' in pattern or 'pound' in pattern:
                    min_val = round(min_val * 0.453592, 1)
                    max_val = round(max_val * 0.453592, 1)

                content['weight_min_kg'] = min_val
                content['weight_max_kg'] = max_val
                break

        # Lifespan extraction
        lifespan_patterns = [
            r'(?:life\s*span|life\s*expectancy|lives?)[:\s]*([\d]+)[-–to\s]+([\d]+)\s*years?',
            r'([\d]+)[-–to\s]+([\d]+)\s*years?[^.]*(?:life|live)',
        ]

        for pattern in lifespan_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                content['lifespan_min_years'] = int(match.group(1))
                content['lifespan_max_years'] = int(match.group(2))
                content['lifespan_avg_years'] = round((content['lifespan_min_years'] + content['lifespan_max_years']) / 2, 1)
                break

        # Temperament/Personality extraction
        temperament_section = None
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if 'temperament' in heading.text.lower() or 'personality' in heading.text.lower():
                # Get next paragraph or div
                next_elem = heading.find_next_sibling(['p', 'div'])
                if next_elem:
                    temperament_section = next_elem.get_text()[:500]
                    break

        if temperament_section:
            content['temperament'] = temperament_section.strip()
            content['personality_traits'] = temperament_section[:300].strip()

        # Exercise needs extraction
        exercise_patterns = [
            r'exercise[:\s]+([^.]{20,300})',
            r'(?:needs?|requires?)[^.]{0,20}exercise[:\s]+([^.]{20,300})',
            r'activity[:\s]+([^.]{20,300})',
        ]

        for pattern in exercise_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                content['exercise_needs_detail'] = match.group(1).strip()
                break

        # Training tips extraction
        training_section = None
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if 'training' in heading.text.lower():
                next_elem = heading.find_next_sibling(['p', 'div', 'ul'])
                if next_elem:
                    training_section = next_elem.get_text()[:400]
                    break

        if training_section:
            content['training_tips'] = training_section.strip()

        # Grooming needs extraction
        grooming_patterns = [
            r'grooming[:\s]+([^.]{20,300})',
            r'(?:coat|fur)[^.]{0,30}(?:needs?|requires?)[:\s]+([^.]{20,300})',
        ]

        for pattern in grooming_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                content['grooming_needs'] = match.group(1).strip()
                break

        # Fun facts extraction
        fun_facts = []
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if 'fun fact' in heading.text.lower() or 'did you know' in heading.text.lower():
                next_elem = heading.find_next_sibling(['p', 'ul', 'ol'])
                if next_elem:
                    fun_facts.append(next_elem.get_text()[:300])

        if fun_facts:
            content['fun_facts'] = ' '.join(fun_facts)[:500]

        # Energy level extraction
        energy_patterns = [
            r'energy[:\s]+(?:level[:\s]+)?(low|moderate|high|very high)',
            r'(?:high|medium|low|moderate)\s+energy',
        ]

        for pattern in energy_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                energy_text = match.group(1) if match.group(1) else match.group(0)
                if 'high' in energy_text.lower():
                    content['energy_level_numeric'] = 4 if 'very' in energy_text.lower() else 3
                elif 'moderate' in energy_text.lower() or 'medium' in energy_text.lower():
                    content['energy_level_numeric'] = 3
                elif 'low' in energy_text.lower():
                    content['energy_level_numeric'] = 2
                break

        return content

    def scrape_breed_from_source(self, breed: Dict, source_name: str, url_template: str) -> Dict:
        """Scrape breed information from a specific source"""
        breed_name = breed.get('display_name', breed['breed_slug'])
        breed_slug = breed['breed_slug'].replace('_', '-')

        # Generate URL
        url = url_template.format(breed=breed_slug)

        print(f"      🔍 Trying {source_name}: {url}")

        # Scrape with ScrapingBee
        html = self.scrape_with_scrapingbee(url)

        if not html:
            return {}

        # Extract content
        extracted = self.extract_breed_content(html, breed_name)

        if extracted:
            print(f"      ✅ Extracted {len(extracted)} fields from {source_name}")

        return extracted

    def process_breed(self, breed: Dict) -> int:
        """Process a single breed across multiple sources"""
        breed_slug = breed['breed_slug']
        breed_name = breed.get('display_name', breed_slug)

        print(f"\n   🐕 Processing {breed_name}")

        # Find missing fields
        target_fields = [
            'height_min_cm', 'height_max_cm', 'weight_min_kg', 'weight_max_kg',
            'lifespan_min_years', 'lifespan_max_years', 'lifespan_avg_years',
            'temperament', 'personality_traits', 'exercise_needs_detail',
            'training_tips', 'grooming_needs', 'fun_facts', 'energy_level_numeric'
        ]

        missing_fields = []
        for field in target_fields:
            if not breed.get(field) or (isinstance(breed.get(field), str) and not breed.get(field).strip()):
                missing_fields.append(field)

        if not missing_fields:
            print(f"      ✅ All target fields already filled")
            return 0

        print(f"      📋 Missing: {', '.join(missing_fields[:5])}{'...' if len(missing_fields) > 5 else ''}")

        # Aggregate data from multiple sources
        aggregated_data = {}
        sources_tried = 0
        max_sources = 3  # Try up to 3 sources per breed

        for source_name, url_template in self.breed_sources.items():
            if sources_tried >= max_sources:
                break

            if len([f for f in missing_fields if f not in aggregated_data]) == 0:
                break  # All fields found

            # Rate limiting between sources
            if sources_tried > 0:
                time.sleep(random.uniform(3, 5))

            extracted = self.scrape_breed_from_source(breed, source_name, url_template)
            sources_tried += 1

            # Merge extracted data
            for field, value in extracted.items():
                if field in missing_fields and field not in aggregated_data:
                    aggregated_data[field] = value

        # Update database
        if aggregated_data:
            try:
                self.supabase.table('breeds_comprehensive_content').update(aggregated_data).eq('breed_slug', breed_slug).execute()
                print(f"      ✅ Updated {len(aggregated_data)} fields")
                return len(aggregated_data)
            except Exception as e:
                print(f"      ❌ Database error: {e}")
                return 0
        else:
            print(f"      ❌ No data extracted from any source")
            return 0

    def run_session(self, max_breeds: int = 50):
        """Run a scraping session"""
        print(f"\n🚀 SESSION {self.session_name} STARTING")
        print("="*60)

        # Get breeds with missing data
        response = self.supabase.table('breeds_comprehensive_content').select('*').execute()
        breeds = response.data

        # Filter to breeds with missing fields
        target_breeds = []
        for breed in breeds:
            if not breed.get('height_min_cm') or not breed.get('weight_min_kg') or \
               not breed.get('lifespan_min_years') or not breed.get('personality_traits'):
                target_breeds.append(breed)

        # Shuffle for variety across sessions
        random.shuffle(target_breeds)
        target_breeds = target_breeds[:max_breeds]

        print(f"📊 Found {len(target_breeds)} breeds needing data")

        total_fields = 0
        successful_breeds = 0
        consecutive_failures = 0

        for i, breed in enumerate(target_breeds, 1):
            print(f"\n[{i}/{len(target_breeds)}] Session {self.session_name}")

            fields_updated = self.process_breed(breed)

            if fields_updated > 0:
                total_fields += fields_updated
                successful_breeds += 1
                consecutive_failures = 0
                self.stats['fields_scraped'] += fields_updated
            else:
                consecutive_failures += 1

            self.stats['breeds_processed'] += 1

            # Health check - stop if not producing results
            if consecutive_failures >= 5:
                print(f"\n⚠️ Session {self.session_name}: 5 consecutive failures, stopping")
                break

            # Progress update
            if i % 5 == 0:
                success_rate = (successful_breeds / i) * 100
                print(f"\n📈 Session {self.session_name} Progress: {success_rate:.1f}% success, {total_fields} fields")

                if success_rate < 20 and i >= 10:
                    print(f"⚠️ Session {self.session_name}: Low success rate, stopping")
                    break

            # Rate limiting
            time.sleep(random.uniform(5, 10))

        # Session summary
        runtime = (datetime.now() - self.stats['start_time']).total_seconds() / 60
        print(f"\n{'='*60}")
        print(f"✅ SESSION {self.session_name} COMPLETE")
        print(f"   Runtime: {runtime:.1f} minutes")
        print(f"   Breeds processed: {self.stats['breeds_processed']}")
        print(f"   Successful breeds: {successful_breeds}")
        print(f"   Fields scraped: {self.stats['fields_scraped']}")
        print(f"   Success rate: {(successful_breeds/self.stats['breeds_processed']*100):.1f}%")

        return self.stats['fields_scraped']

class BreedContentOrchestrator:
    def __init__(self):
        """Initialize the orchestrator"""
        self.sessions = []
        self.max_concurrent = 3  # Run 3 parallel sessions
        self.total_fields_scraped = 0
        self.start_time = datetime.now()

        # Session configurations with different country codes
        self.session_configs = [
            {'name': 'US-Session', 'country_code': 'us'},
            {'name': 'UK-Session', 'country_code': 'gb'},
            {'name': 'CA-Session', 'country_code': 'ca'},
        ]

        print("🎯 BREED CONTENT SCRAPER ORCHESTRATOR")
        print("="*60)
        print(f"Max concurrent sessions: {self.max_concurrent}")
        print(f"Target: Fill missing breed physical and behavioral data")
        print("="*60)

    def run_parallel_sessions(self, max_breeds_per_session: int = 50):
        """Run multiple scraping sessions in parallel"""
        print("\n🚀 LAUNCHING PARALLEL SESSIONS")

        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # Submit all sessions
            futures = []
            for config in self.session_configs:
                scraper = BreedContentScraper(
                    session_name=config['name'],
                    country_code=config['country_code']
                )
                future = executor.submit(scraper.run_session, max_breeds_per_session)
                futures.append((future, config['name']))

                # Stagger session starts
                time.sleep(2)

            # Collect results
            for future, session_name in futures:
                try:
                    fields_scraped = future.result(timeout=3600)  # 1 hour timeout
                    self.total_fields_scraped += fields_scraped
                    print(f"✅ {session_name} completed: {fields_scraped} fields")
                except Exception as e:
                    print(f"❌ {session_name} failed: {e}")

        # Final summary
        runtime = (datetime.now() - self.start_time).total_seconds() / 60
        estimated_gain = (self.total_fields_scraped / 29733) * 100

        print("\n" + "="*60)
        print("🎉 ORCHESTRATOR COMPLETE")
        print("="*60)
        print(f"⏰ Total runtime: {runtime:.1f} minutes")
        print(f"📊 Total fields scraped: {self.total_fields_scraped}")
        print(f"📈 Estimated completeness gain: +{estimated_gain:.2f}%")

        # Save results
        results = {
            'timestamp': datetime.now().isoformat(),
            'runtime_minutes': runtime,
            'total_fields_scraped': self.total_fields_scraped,
            'estimated_gain_percent': estimated_gain,
            'sessions': self.session_configs
        }

        with open('breed_content_orchestrator_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        print(f"📁 Results saved to breed_content_orchestrator_results.json")

        return self.total_fields_scraped

if __name__ == "__main__":
    orchestrator = BreedContentOrchestrator()
    orchestrator.run_parallel_sessions(max_breeds_per_session=30)