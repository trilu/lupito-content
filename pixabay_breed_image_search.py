#!/usr/bin/env python3
"""
PIXABAY BREED IMAGE SEARCH
Search for high-quality breed images on Pixabay
"""

import os
import json
import requests
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote, urlencode
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PixabayImageSearcher:
    def __init__(self):
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)

        # Get Pixabay API key from environment
        self.pixabay_api_key = os.getenv('PIXABAY_API_KEY')
        if not self.pixabay_api_key:
            logger.error("❌ PIXABAY_API_KEY not found in environment variables")
            logger.info("💡 Please get a free API key from https://pixabay.com/api/docs/")
            raise ValueError("Pixabay API key is required")

        self.search_stats = {
            'breeds_searched': 0,
            'images_found': 0,
            'api_calls_made': 0,
            'successful_breeds': []
        }

        # Pixabay API endpoint
        self.pixabay_api = "https://pixabay.com/api/"

        # Headers for requests
        self.headers = {
            'User-Agent': 'BreedImageBot/1.0 (breed-image-search; contact@example.com) python-requests/2.31.0'
        }

    def search_breed_images(self, breed_name: str, limit: int = 5) -> List[Dict]:
        """Search Pixabay for breed images"""
        try:
            # Multiple search terms for better results
            search_terms = [
                f"{breed_name} dog",
                breed_name,
                f"{breed_name} puppy",
                f"{breed_name} breed",
                f"{breed_name.split()[0]} dog" if len(breed_name.split()) > 1 else None
            ]

            # Remove None values
            search_terms = [term for term in search_terms if term]

            all_results = []

            for search_term in search_terms:
                logger.info(f"   Searching: '{search_term}'")

                # Pixabay API parameters
                params = {
                    'key': self.pixabay_api_key,
                    'q': search_term,
                    'image_type': 'photo',
                    'orientation': 'all',
                    'category': 'animals',
                    'min_width': 640,
                    'min_height': 480,
                    'per_page': limit,
                    'safesearch': 'true',
                    'order': 'popular'
                }

                response = requests.get(self.pixabay_api, params=params, headers=self.headers, timeout=15)
                self.search_stats['api_calls_made'] += 1

                if response.status_code == 200:
                    data = response.json()
                    hits = data.get('hits', [])
                    logger.info(f"      Found {len(hits)} results")

                    for hit in hits:
                        # Process image data
                        image_info = self.process_pixabay_image(hit)
                        if image_info:
                            image_info['search_term'] = search_term
                            all_results.append(image_info)
                            logger.info(f"      ✅ Valid image: {image_info['id']}")
                else:
                    logger.error(f"      ❌ API error: {response.status_code} - {response.text}")

                # Rate limiting - be respectful to Pixabay
                time.sleep(0.3)

                # Stop if we found enough images
                if len(all_results) >= limit:
                    break

            # Remove duplicates by ID and sort by quality
            unique_results = {}
            for result in all_results:
                image_id = result['id']
                if image_id not in unique_results:
                    unique_results[image_id] = result

            # Sort by downloads and views (popularity indicators)
            sorted_results = sorted(
                unique_results.values(),
                key=lambda x: (x.get('downloads', 0) + x.get('views', 0) / 100),
                reverse=True
            )

            return sorted_results[:limit]

        except Exception as e:
            logger.error(f"   ❌ Error searching for {breed_name}: {e}")
            return []

    def process_pixabay_image(self, hit: Dict) -> Optional[Dict]:
        """Process a Pixabay API hit into standardized image info"""
        try:
            # Extract image information
            return {
                'id': hit.get('id', ''),
                'page_url': hit.get('pageURL', ''),
                'web_url': hit.get('webformatURL', ''),
                'large_url': hit.get('largeImageURL', ''),
                'full_hd_url': hit.get('fullHDURL', ''),
                'width': hit.get('imageWidth', 0),
                'height': hit.get('imageHeight', 0),
                'web_width': hit.get('webformatWidth', 0),
                'web_height': hit.get('webformatHeight', 0),
                'size': hit.get('imageSize', 0),
                'views': hit.get('views', 0),
                'downloads': hit.get('downloads', 0),
                'likes': hit.get('likes', 0),
                'tags': hit.get('tags', ''),
                'user': hit.get('user', ''),
                'license_info': {
                    'license': 'Pixabay License',
                    'commercial_use': True,
                    'attribution_required': False,
                    'compatible': True,
                    'license_url': 'https://pixabay.com/service/license/'
                }
            }

        except Exception as e:
            logger.error(f"   ⚠️ Error processing image data: {e}")
            return None

    def search_breeds_batch(self, breed_slugs: List[str]) -> Dict:
        """Search for images for a batch of breeds"""
        logger.info(f"🔍 SEARCHING PIXABAY FOR {len(breed_slugs)} BREEDS")
        logger.info("=" * 60)

        results = {}

        for i, breed_slug in enumerate(breed_slugs, 1):
            # Convert slug to searchable name
            breed_name = breed_slug.replace('-', ' ').title()

            # Special cases for better search results
            search_name = self.optimize_breed_name_for_search(breed_name)

            logger.info(f"[{i}/{len(breed_slugs)}] {breed_slug}")
            logger.info(f"   Display: {breed_name}")
            if search_name != breed_name:
                logger.info(f"   Search: {search_name}")

            # Search for images
            images = self.search_breed_images(search_name)

            if images:
                logger.info(f"   ✅ Found {len(images)} image(s)")
                results[breed_slug] = {
                    'breed_name': breed_name,
                    'search_name': search_name,
                    'images': images,
                    'best_image': images[0] if images else None
                }
                self.search_stats['images_found'] += len(images)
                self.search_stats['successful_breeds'].append(breed_slug)
            else:
                logger.info(f"   ❌ No suitable images found")
                results[breed_slug] = {
                    'breed_name': breed_name,
                    'search_name': search_name,
                    'images': [],
                    'best_image': None
                }

            self.search_stats['breeds_searched'] += 1

            # Progress update every 5 breeds
            if i % 5 == 0:
                self.print_progress_stats()

            # Rate limiting
            time.sleep(1)

        return results

    def optimize_breed_name_for_search(self, breed_name: str) -> str:
        """Optimize breed names for better search results on Pixabay"""
        # Handle special cases and known variations
        optimizations = {
            'Anatolian Shepherd Dog': 'Anatolian Shepherd',
            'German Short Haired Pointer': 'German Shorthaired Pointer',
            'German Wire Haired Pointer': 'German Wirehaired Pointer',
            'Cardigan Welsh Corgis': 'Cardigan Welsh Corgi',
            'Grand Anglo Fran Ais Tricolore': 'Grand Anglo-Français Tricolore',
            'Glen Of Imaal Terrier': 'Glen of Imaal Terrier',
            'Black Tan Coonhound': 'Black and Tan Coonhound',
            'Briquet De Provence': 'Briquet Griffon Vendéen',
            'Portuguese Podengo Pequeno': 'Portuguese Podengo',
            'Petit Basset Griffon Vendeen': 'Petit Basset Griffon Vendéen',
            'West Siberian Laika': 'West Siberian Husky',
            'Russo European Laika': 'Russian European Laika'
        }

        return optimizations.get(breed_name, breed_name)

    def print_progress_stats(self):
        """Print current search progress"""
        logger.info(f"   📊 Progress: {self.search_stats['breeds_searched']} breeds searched, "
                   f"{self.search_stats['images_found']} images found, "
                   f"{len(self.search_stats['successful_breeds'])} with images")

    def generate_search_report(self, results: Dict):
        """Generate comprehensive search report"""
        logger.info("\n" + "=" * 60)
        logger.info("🎉 PIXABAY SEARCH COMPLETE")
        logger.info("=" * 60)

        success_count = len(self.search_stats['successful_breeds'])
        total_searched = self.search_stats['breeds_searched']

        logger.info(f"📊 SEARCH STATISTICS:")
        logger.info(f"   - Breeds searched: {total_searched}")
        logger.info(f"   - Breeds with images found: {success_count}")
        logger.info(f"   - Total images found: {self.search_stats['images_found']}")
        logger.info(f"   - API calls made: {self.search_stats['api_calls_made']}")
        success_rate = (success_count/total_searched*100) if total_searched > 0 else 0
        logger.info(f"   - Success rate: {success_rate:.1f}%")

        logger.info(f"\n✅ BREEDS WITH IMAGES FOUND:")
        for breed_slug in self.search_stats['successful_breeds']:
            breed_info = results[breed_slug]
            best_image = breed_info['best_image']
            if best_image:
                size_mb = best_image.get('size', 0) / (1024*1024) if best_image.get('size') else 0
                license_status = "✅" if best_image['license_info']['compatible'] else "⚠️"
                logger.info(f"   {license_status} {breed_slug} -> {breed_info['breed_name']}")
                logger.info(f"      Image: {best_image['width']}x{best_image['height']}, {size_mb:.1f}MB")
                logger.info(f"      Stats: {best_image['views']} views, {best_image['downloads']} downloads")

        # Save detailed results
        report_filename = f'pixabay_search_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'search_type': 'pixabay_breed_images',
                'statistics': self.search_stats,
                'results': results
            }, f, indent=2)

        logger.info(f"\n📋 Detailed results saved: {report_filename}")

        if success_count > 0:
            logger.info(f"\n🌟 SEARCH SUCCESSFUL!")
            logger.info(f"🚀 Found images for {success_count} breeds on Pixabay!")
        else:
            logger.info(f"\n⚠️ No images found for the searched breeds")

if __name__ == '__main__':
    searcher = PixabayImageSearcher()

    # Get breeds without images from database (excluding those already found on Wikimedia)
    result = searcher.supabase.table('breeds_comprehensive_content')\
        .select('breed_slug')\
        .is_('image_url', 'null')\
        .order('breed_slug')\
        .execute()  # Get ALL remaining breeds

    if result.data:
        breed_slugs = [breed['breed_slug'] for breed in result.data]
        search_results = searcher.search_breeds_batch(breed_slugs)
        searcher.generate_search_report(search_results)
    else:
        logger.info("No breeds without images found in database")