#!/usr/bin/env python3
"""
ULTIMATE SCRAPINGBEE ASSAULT - Target ALL 500+ breeds with critical gaps
Objective: Push completeness from 40.9% to 55%+
Strategy: Mass parallel ScrapingBee attack on all breeds missing critical fields
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Load environment variables
load_dotenv()

class UltimateScrapingBeeAssault:
    def __init__(self, batch_size: int = 100):
        """Initialize the ultimate assault system"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ultimate_assault.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials in environment")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # ScrapingBee setup (using same env var as Zooplus/AADF projects)
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        if not self.scrapingbee_api_key:
            raise ValueError("Missing ScrapingBee API key (SCRAPING_BEE)")

        self.batch_size = batch_size

        # Priority sources (proven performers)
        self.sources = {
            'dogtime': {
                'url_template': 'https://dogtime.com/dog-breeds/{breed_slug}',
                'priority': 1,
                'success_rate': 0.40
            },
            'hillspet': {
                'url_template': 'https://www.hillspet.com/dog-care/dog-breeds/{breed_slug}',
                'priority': 2,
                'success_rate': 0.35
            },
            'rover': {
                'url_template': 'https://www.rover.com/blog/dog-breeds/{breed_slug}',
                'priority': 3,
                'success_rate': 0.25
            },
            'akc': {
                'url_template': 'https://www.akc.org/dog-breeds/{breed_slug}/',
                'priority': 4,
                'success_rate': 0.20
            }
        }

        # Target fields
        self.critical_fields = ['grooming_frequency', 'good_with_children', 'good_with_pets']

        # Tracking
        self.stats = {
            'breeds_processed': 0,
            'breeds_updated': 0,
            'fields_filled': 0,
            'scrapingbee_credits': 0,
            'source_hits': {},
            'start_time': datetime.now()
        }

        # Thread lock for stats
        self.stats_lock = threading.Lock()

    def get_all_breeds_with_gaps(self) -> List[Dict[str, Any]]:
        """Get ALL breeds missing critical fields"""
        try:
            response = self.supabase.table('breeds_unified_api').select(
                'breed_slug,display_name,grooming_frequency,good_with_children,good_with_pets'
            ).execute()

            breeds = []
            for breed in response.data:
                missing_fields = []
                for field in self.critical_fields:
                    if not breed.get(field):
                        missing_fields.append(field)

                if missing_fields:
                    breeds.append({
                        'breed_slug': breed['breed_slug'],
                        'display_name': breed.get('display_name', breed['breed_slug']),
                        'missing_fields': missing_fields,
                        'priority': 100 - len(missing_fields) * 10  # Prioritize breeds with fewer gaps
                    })

            # Sort by priority - process breeds with fewer missing fields first (easier wins)
            breeds.sort(key=lambda x: x['priority'], reverse=True)

            self.logger.info(f"🎯 ULTIMATE TARGET: {len(breeds)} breeds with critical gaps")
            self.logger.info(f"📊 Total missing fields to fill: {sum(len(b['missing_fields']) for b in breeds)}")

            return breeds

        except Exception as e:
            self.logger.error(f"Error loading breeds: {e}")
            return []

    def scrape_with_scrapingbee(self, url: str, max_retries: int = 2) -> Optional[str]:
        """Fetch URL using ScrapingBee with optimized settings"""
        for attempt in range(max_retries):
            try:
                params = {
                    'api_key': self.scrapingbee_api_key,
                    'url': url,
                    'render_js': 'true',
                    'premium_proxy': 'true',
                    'stealth_proxy': 'true',
                    'country_code': 'us',
                    'wait': '2000',  # Reduced wait for speed
                    'block_ads': 'true',
                    'return_page_source': 'true'
                }

                response = requests.get(
                    'https://app.scrapingbee.com/api/v1/',
                    params=params,
                    timeout=30  # Reduced timeout for speed
                )

                if response.status_code == 200:
                    with self.stats_lock:
                        self.stats['scrapingbee_credits'] += 1
                    return response.text

            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.debug(f"ScrapingBee failed for {url}: {e}")

            time.sleep(1)

        return None

    def extract_fields_from_content(self, content: str, breed_slug: str, source: str) -> Dict[str, Any]:
        """Extract critical fields from page content"""
        extracted = {}

        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()

            # Grooming frequency extraction
            if 'grooming' in text:
                if any(term in text for term in ['daily grooming', 'everyday grooming', 'high maintenance']):
                    extracted['grooming_frequency'] = 'daily'
                elif any(term in text for term in ['weekly grooming', 'once a week', 'regular grooming']):
                    extracted['grooming_frequency'] = 'weekly'
                elif any(term in text for term in ['monthly', 'occasional grooming', 'low maintenance']):
                    extracted['grooming_frequency'] = 'monthly'
                elif any(term in text for term in ['minimal grooming', 'rarely', 'low grooming']):
                    extracted['grooming_frequency'] = 'rarely'

            # Good with children extraction
            if 'child' in text or 'kids' in text or 'family' in text:
                if any(term in text for term in [
                    'excellent with children', 'great with kids', 'perfect family',
                    'loves children', 'gentle with children', 'patient with kids'
                ]):
                    extracted['good_with_children'] = True
                elif any(term in text for term in [
                    'not recommended for children', 'not good with kids',
                    'better without children', 'may snap', 'not child-friendly'
                ]):
                    extracted['good_with_children'] = False
                elif any(term in text for term in ['good with children', 'family dog', 'family-friendly']):
                    extracted['good_with_children'] = True

            # Good with pets extraction
            if 'pet' in text or 'dog' in text or 'cat' in text or 'animal' in text:
                if any(term in text for term in [
                    'gets along well with', 'friendly with other',
                    'good with other pets', 'sociable with'
                ]):
                    extracted['good_with_pets'] = True
                elif any(term in text for term in [
                    'aggressive toward', 'not good with other',
                    'should be only pet', 'prey drive', 'chase'
                ]):
                    extracted['good_with_pets'] = False

        except Exception as e:
            self.logger.debug(f"Extraction error for {breed_slug}: {e}")

        return extracted

    def process_breed(self, breed: Dict[str, Any]) -> bool:
        """Process a single breed through all sources"""
        breed_slug = breed['breed_slug']
        missing_fields = breed['missing_fields']

        self.logger.info(f"🔍 Processing {breed['display_name']} - Missing: {missing_fields}")

        collected_data = {}

        # Try each source
        for source_name, source_config in sorted(self.sources.items(), key=lambda x: x[1]['priority']):
            if len(collected_data) >= len(missing_fields):
                break  # We have all needed fields

            url = source_config['url_template'].format(breed_slug=breed_slug)

            # Try direct request first (faster, no credits)
            try:
                response = requests.get(url, timeout=3, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code == 200:
                    content = response.text
                else:
                    # Fall back to ScrapingBee
                    content = self.scrape_with_scrapingbee(url)
            except:
                # Fall back to ScrapingBee
                content = self.scrape_with_scrapingbee(url)

            if content:
                extracted = self.extract_fields_from_content(content, breed_slug, source_name)

                # Only keep fields we're missing
                for field in missing_fields:
                    if field in extracted and field not in collected_data:
                        collected_data[field] = extracted[field]
                        with self.stats_lock:
                            self.stats['source_hits'][source_name] = self.stats['source_hits'].get(source_name, 0) + 1

        # Update database if we found anything
        if collected_data:
            try:
                # Get existing data
                existing = self.supabase.table('breeds_comprehensive_content').select(
                    'id,' + ','.join(self.critical_fields)
                ).eq('breed_slug', breed_slug).execute()

                if existing.data:
                    # Update with new data
                    self.supabase.table('breeds_comprehensive_content').update(
                        collected_data
                    ).eq('breed_slug', breed_slug).execute()

                    self.logger.info(f"✅ Updated {breed_slug}: {list(collected_data.keys())}")

                    with self.stats_lock:
                        self.stats['breeds_updated'] += 1
                        self.stats['fields_filled'] += len(collected_data)

                    return True

            except Exception as e:
                self.logger.error(f"Database update failed for {breed_slug}: {e}")

        return False

    def process_batch_parallel(self, breeds: List[Dict[str, Any]], max_workers: int = 5):
        """Process breeds in parallel batches"""
        self.logger.info(f"🚀 Processing batch of {len(breeds)} breeds with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.process_breed, breed): breed for breed in breeds}

            for future in as_completed(futures):
                breed = futures[future]
                try:
                    success = future.result()
                    with self.stats_lock:
                        self.stats['breeds_processed'] += 1

                        # Progress report every 10 breeds
                        if self.stats['breeds_processed'] % 10 == 0:
                            self.logger.info(f"""
📊 PROGRESS: {self.stats['breeds_processed']}/{len(breeds)}
✅ Updated: {self.stats['breeds_updated']}
📝 Fields filled: {self.stats['fields_filled']}
💰 Credits used: {self.stats['scrapingbee_credits']}
⚡ Success rate: {self.stats['breeds_updated']/self.stats['breeds_processed']*100:.1f}%
                            """)

                except Exception as e:
                    self.logger.error(f"Failed to process {breed['breed_slug']}: {e}")

    def launch_ultimate_assault(self):
        """Launch the ultimate assault on all breeds with gaps"""
        self.logger.info("""
        ================================================
        🚀 ULTIMATE SCRAPINGBEE ASSAULT INITIATED 🚀
        ================================================
        Target: ALL breeds with critical field gaps
        Strategy: Mass parallel scraping with proven sources
        Objective: Push to 55%+ completeness
        ================================================
        """)

        # Get all breeds with gaps
        all_breeds = self.get_all_breeds_with_gaps()

        if not all_breeds:
            self.logger.error("No breeds to process!")
            return

        # Process in batches to manage resources
        for i in range(0, len(all_breeds), self.batch_size):
            batch = all_breeds[i:i+self.batch_size]

            self.logger.info(f"""
            ========================================
            BATCH {i//self.batch_size + 1}/{(len(all_breeds)-1)//self.batch_size + 1}
            Processing breeds {i+1} to {min(i+self.batch_size, len(all_breeds))}
            ========================================
            """)

            self.process_batch_parallel(batch, max_workers=10)  # More workers for speed

            # Brief pause between batches
            if i + self.batch_size < len(all_breeds):
                time.sleep(5)

        # Final report
        duration = (datetime.now() - self.stats['start_time']).total_seconds() / 60

        self.logger.info(f"""
        ================================================
        🏁 ULTIMATE ASSAULT COMPLETE 🏁
        ================================================
        Duration: {duration:.1f} minutes
        Breeds processed: {self.stats['breeds_processed']}
        Breeds updated: {self.stats['breeds_updated']}
        Fields filled: {self.stats['fields_filled']}
        Success rate: {self.stats['breeds_updated']/self.stats['breeds_processed']*100:.1f}%
        ScrapingBee credits used: {self.stats['scrapingbee_credits']}

        Source performance:
        {json.dumps(self.stats['source_hits'], indent=2)}

        Expected completeness gain: +{self.stats['fields_filled']/1749*100:.1f}%
        ================================================
        """)

if __name__ == "__main__":
    import sys

    batch_size = 100  # Default batch size
    if len(sys.argv) > 1:
        try:
            batch_size = int(sys.argv[1])
        except:
            pass

    assault = UltimateScrapingBeeAssault(batch_size=batch_size)
    assault.launch_ultimate_assault()