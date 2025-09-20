#!/usr/bin/env python3
"""
ULTIMATE WEB ASSAULT (FREE VERSION) - Target ALL 500+ breeds with critical gaps
No ScrapingBee required - uses smart HTTP techniques and multiple sources
Objective: Push completeness from 40.9% to 50%+ without paid services
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
from urllib.parse import quote

# Load environment variables
load_dotenv()

class UltimateWebAssaultFree:
    def __init__(self, batch_size: int = 100):
        """Initialize the free assault system"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ultimate_assault_free.log'),
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
        self.batch_size = batch_size

        # User agents pool
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]

        # Expanded sources - more free sources!
        self.sources = {
            'akc': {
                'url_template': 'https://www.akc.org/dog-breeds/{breed_slug}/',
                'priority': 1,
                'success_rate': 0.60
            },
            'dogtime': {
                'url_template': 'https://dogtime.com/dog-breeds/{breed_slug}',
                'priority': 2,
                'success_rate': 0.40
            },
            'vetstreet': {
                'url_template': 'http://www.vetstreet.com/dogs/{breed_slug}',
                'priority': 3,
                'success_rate': 0.35
            },
            'dogbreedinfo': {
                'url_template': 'https://www.dogbreedinfo.com/{breed_slug}.htm',
                'priority': 4,
                'success_rate': 0.30
            },
            'yourpurebredpuppy': {
                'url_template': 'https://www.yourpurebredpuppy.com/reviews/dogbreeds/{breed_slug}s.html',
                'priority': 5,
                'success_rate': 0.25
            }
        }

        # Target fields
        self.critical_fields = ['grooming_frequency', 'good_with_children', 'good_with_pets']

        # Tracking
        self.stats = {
            'breeds_processed': 0,
            'breeds_updated': 0,
            'fields_filled': 0,
            'requests_made': 0,
            'source_hits': {},
            'start_time': datetime.now()
        }

        # Thread lock for stats
        self.stats_lock = threading.Lock()

    def get_all_breeds_with_gaps(self) -> List[Dict[str, Any]]:
        """Get ALL breeds missing critical fields"""
        try:
            response = self.supabase.table('breeds_unified_api').select(
                'breed_slug,display_name,grooming_frequency,good_with_children,good_with_pets,popularity_score'
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
                        'priority': breed.get('popularity_score', 0)
                    })

            # Sort by priority (popularity)
            breeds.sort(key=lambda x: x['priority'], reverse=True)

            self.logger.info(f"🎯 TARGET: {len(breeds)} breeds with critical gaps")
            self.logger.info(f"📊 Total fields to fill: {sum(len(b['missing_fields']) for b in breeds)}")

            return breeds

        except Exception as e:
            self.logger.error(f"Error loading breeds: {e}")
            return []

    def fetch_with_retries(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Fetch URL with smart retry logic and rotating user agents"""
        for attempt in range(max_retries):
            try:
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }

                # Add delay to avoid rate limiting
                if attempt > 0:
                    time.sleep(random.uniform(1, 3))

                response = requests.get(
                    url,
                    headers=headers,
                    timeout=10,
                    allow_redirects=True
                )

                if response.status_code == 200:
                    with self.stats_lock:
                        self.stats['requests_made'] += 1
                    return response.text
                elif response.status_code == 404:
                    return None  # No point retrying 404s

            except requests.exceptions.Timeout:
                self.logger.debug(f"Timeout for {url} (attempt {attempt + 1})")
            except Exception as e:
                self.logger.debug(f"Error fetching {url}: {e}")

            # Exponential backoff
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

        return None

    def extract_fields_enhanced(self, content: str, breed_slug: str, source: str) -> Dict[str, Any]:
        """Enhanced extraction with more patterns"""
        extracted = {}

        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()

            # Remove extra whitespace
            text = ' '.join(text.split())

            # Enhanced grooming frequency extraction
            if 'grooming' in text or 'groom' in text or 'brush' in text:
                # Daily patterns
                if any(term in text for term in [
                    'daily grooming', 'everyday grooming', 'daily brushing',
                    'brush daily', 'groomed daily', 'high maintenance',
                    'requires daily', 'needs daily grooming'
                ]):
                    extracted['grooming_frequency'] = 'daily'
                # Weekly patterns
                elif any(term in text for term in [
                    'weekly grooming', 'once a week', 'regular grooming',
                    'weekly brushing', 'brush weekly', 'once per week',
                    'moderate grooming', 'moderate maintenance'
                ]):
                    extracted['grooming_frequency'] = 'weekly'
                # Monthly patterns
                elif any(term in text for term in [
                    'monthly', 'occasional grooming', 'low maintenance',
                    'minimal grooming', 'easy to groom', 'little grooming',
                    'low grooming needs', 'easy grooming'
                ]):
                    extracted['grooming_frequency'] = 'monthly'
                # Rarely patterns
                elif any(term in text for term in [
                    'minimal grooming', 'rarely', 'very low maintenance',
                    'almost no grooming', 'very little grooming'
                ]):
                    extracted['grooming_frequency'] = 'rarely'

            # Enhanced good with children extraction
            if 'child' in text or 'kids' in text or 'family' in text or 'toddler' in text:
                # Positive patterns
                if any(term in text for term in [
                    'excellent with children', 'great with kids', 'perfect family',
                    'loves children', 'gentle with children', 'patient with kids',
                    'good with children', 'family dog', 'family-friendly',
                    'wonderful with kids', 'great family pet', 'child-friendly',
                    'good family dog', 'excellent family', 'loves kids',
                    'tolerant of children', 'patient with children'
                ]):
                    extracted['good_with_children'] = True
                # Negative patterns
                elif any(term in text for term in [
                    'not recommended for children', 'not good with kids',
                    'better without children', 'may snap', 'not child-friendly',
                    'not suitable for children', 'avoid children',
                    'not for families with young', 'not ideal for children',
                    'better suited for adult', 'not tolerant of children'
                ]):
                    extracted['good_with_children'] = False

            # Enhanced good with pets extraction
            if 'pet' in text or 'dog' in text or 'cat' in text or 'animal' in text:
                # Positive patterns
                if any(term in text for term in [
                    'gets along well with', 'friendly with other',
                    'good with other pets', 'sociable with',
                    'lives peacefully with', 'tolerates other pets',
                    'good with cats', 'friendly to other dogs',
                    'can live with other', 'social with other pets',
                    'plays well with others'
                ]):
                    extracted['good_with_pets'] = True
                # Negative patterns
                elif any(term in text for term in [
                    'aggressive toward', 'not good with other',
                    'should be only pet', 'prey drive', 'chase',
                    'may be aggressive', 'doesn\'t tolerate other',
                    'not friendly with', 'territorial',
                    'better as only pet', 'high prey drive'
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

            # Try different URL formats for the breed slug
            slug_variants = [
                breed_slug,
                breed_slug.replace('-', ''),
                breed_slug.replace('-', '_'),
                breed_slug.title().replace('-', '')
            ]

            for slug_variant in slug_variants:
                url = source_config['url_template'].format(breed_slug=slug_variant)

                content = self.fetch_with_retries(url, max_retries=2)

                if content:
                    extracted = self.extract_fields_enhanced(content, breed_slug, source_name)

                    # Only keep fields we're missing
                    for field in missing_fields:
                        if field in extracted and field not in collected_data:
                            collected_data[field] = extracted[field]
                            with self.stats_lock:
                                self.stats['source_hits'][source_name] = self.stats['source_hits'].get(source_name, 0) + 1

                    if extracted:
                        break  # Found data with this variant, move to next source

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

    def process_batch_parallel(self, breeds: List[Dict[str, Any]], max_workers: int = 3):
        """Process breeds in parallel batches - limited workers for free version"""
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
                            success_rate = (self.stats['breeds_updated']/self.stats['breeds_processed']*100) if self.stats['breeds_processed'] > 0 else 0
                            self.logger.info(f"""
📊 PROGRESS: {self.stats['breeds_processed']}/{len(breeds)}
✅ Updated: {self.stats['breeds_updated']}
📝 Fields filled: {self.stats['fields_filled']}
🌐 Requests made: {self.stats['requests_made']}
⚡ Success rate: {success_rate:.1f}%
                            """)

                except Exception as e:
                    self.logger.error(f"Failed to process {breed['breed_slug']}: {e}")

    def launch_ultimate_assault(self):
        """Launch the free assault on all breeds with gaps"""
        self.logger.info("""
        ================================================
        🚀 ULTIMATE WEB ASSAULT (FREE VERSION) 🚀
        ================================================
        Target: ALL breeds with critical field gaps
        Strategy: Smart HTTP requests with multiple sources
        No paid services required!
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

            self.process_batch_parallel(batch, max_workers=3)  # Conservative for free version

            # Brief pause between batches to be respectful
            if i + self.batch_size < len(all_breeds):
                time.sleep(10)

        # Final report
        duration = (datetime.now() - self.stats['start_time']).total_seconds() / 60
        success_rate = (self.stats['breeds_updated']/self.stats['breeds_processed']*100) if self.stats['breeds_processed'] > 0 else 0

        self.logger.info(f"""
        ================================================
        🏁 FREE ASSAULT COMPLETE 🏁
        ================================================
        Duration: {duration:.1f} minutes
        Breeds processed: {self.stats['breeds_processed']}
        Breeds updated: {self.stats['breeds_updated']}
        Fields filled: {self.stats['fields_filled']}
        Success rate: {success_rate:.1f}%
        Requests made: {self.stats['requests_made']}

        Source performance:
        {json.dumps(self.stats['source_hits'], indent=2)}

        Expected completeness gain: +{self.stats['fields_filled']/1749*100:.1f}%
        ================================================
        """)

if __name__ == "__main__":
    import sys

    batch_size = 50  # Smaller default for free version
    if len(sys.argv) > 1:
        try:
            batch_size = int(sys.argv[1])
        except:
            pass

    assault = UltimateWebAssaultFree(batch_size=batch_size)
    assault.launch_ultimate_assault()