#!/usr/bin/env python3
"""
Zooplus CSV Import Image Scraper
Scrapes product images from Zooplus for products imported via CSV that don't have images
"""
import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage
from bs4 import BeautifulSoup
import logging
import random
from urllib.parse import urljoin, urlparse

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")
GCS_PUBLIC_URL = "https://storage.googleapis.com/lupito-content-raw-eu"

# Set up GCS authentication
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZooplusCSVScraper:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/jpeg, image/png, image/webp, image/*',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.zooplus.com/'
        })
        self.failed_downloads = []
        self.successful_downloads = []

    def get_products_to_scrape(self):
        """Get Zooplus CSV import products without images"""
        logger.info("Fetching Zooplus CSV products to scrape...")

        all_products = []
        batch_size = 1000
        offset = 0

        while True:
            result = self.supabase.table('foods_canonical').select(
                'product_key, brand, product_name, product_url'
            ).eq(
                'source', 'zooplus_csv_import'
            ).is_(
                'image_url', 'null'
            ).range(offset, offset + batch_size - 1).execute()

            all_products.extend(result.data)

            if len(result.data) < batch_size:
                break
            offset += batch_size

        logger.info(f"Found {len(all_products)} Zooplus CSV products to scrape")
        return all_products

    def scrape_zooplus_page(self, url):
        """Scrape image from Zooplus product page"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Zooplus-specific image selectors
            image_selectors = [
                'img.ProductImage__image',  # Main product image
                'div.ProductImage img',      # Product image container
                'div.product-image img',     # Alternative product image
                'img[data-testid="product-image"]',  # Test ID selector
                'picture.ProductImage__picture img',  # Picture element
                'div.swiper-slide img',      # Carousel images
                'img.product-detail-image',  # Detail page image
                'meta[property="og:image"]', # Open Graph fallback
            ]

            for selector in image_selectors:
                if selector.startswith('meta'):
                    # Handle meta tag differently
                    element = soup.find('meta', property='og:image')
                    if element and element.get('content'):
                        image_url = element['content']
                        if self.is_valid_product_image(image_url):
                            return image_url
                else:
                    img_elements = soup.select(selector)
                    for img in img_elements:
                        src = img.get('src') or img.get('data-src') or img.get('data-original')
                        if src:
                            # Skip placeholder or icon images
                            if any(skip in src.lower() for skip in ['placeholder', 'icon', 'logo', 'loading']):
                                continue

                            # Build absolute URL
                            image_url = urljoin(url, src)

                            # Check if it's a reasonable product image
                            if self.is_valid_product_image(image_url):
                                # Try to get high-res version
                                if 's_' in image_url or '_s.' in image_url:
                                    # Replace small image indicator with large
                                    high_res = image_url.replace('s_', 'l_').replace('_s.', '_l.')
                                    return high_res
                                return image_url

            # Try to find JSON-LD structured data
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                try:
                    import json
                    data = json.loads(json_ld.string)
                    if isinstance(data, dict) and 'image' in data:
                        image_url = data['image']
                        if isinstance(image_url, list) and image_url:
                            image_url = image_url[0]
                        if self.is_valid_product_image(image_url):
                            return image_url
                except:
                    pass

            logger.warning(f"No suitable image found on {url}")
            return None

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None

    def is_valid_product_image(self, url):
        """Check if URL is likely a valid product image"""
        if not url:
            return False

        # Check for common image extensions
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        parsed = urlparse(url.lower())
        path = parsed.path

        # Check extension
        has_valid_ext = any(path.endswith(ext) for ext in valid_extensions)

        # Also check for CDN patterns common on Zooplus
        is_cdn_image = 'cdn' in parsed.netloc or 'images' in parsed.netloc

        return has_valid_ext or is_cdn_image

    def download_and_upload_image(self, image_url, product_key):
        """Download image and upload to GCS"""
        try:
            # Use same download approach as the successful downloader
            response = self.session.get(image_url, timeout=30, stream=True)
            response.raise_for_status()

            # Validate it's an image
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type:
                logger.warning(f"Non-image content type: {content_type}")
                return None

            # Read content in chunks
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk

            # Convert product key to GCS format
            gcs_key = product_key.replace('|', '_')
            blob_path = f"product-images/zooplus/{gcs_key}.jpg"

            # Upload to GCS
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(content, content_type='image/jpeg')

            gcs_url = f"{GCS_PUBLIC_URL}/{blob_path}"
            logger.info(f"✅ Uploaded {gcs_key} to GCS")

            return gcs_url

        except Exception as e:
            logger.error(f"Failed to download/upload image for {product_key}: {e}")
            return None

    def update_database(self, product_key, gcs_url):
        """Update database with GCS URL"""
        try:
            result = self.supabase.table('foods_canonical').update({
                'image_url': gcs_url,
                'updated_at': datetime.now().isoformat()
            }).eq('product_key', product_key).execute()

            if result.data:
                logger.info(f"✅ Updated database for {product_key}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to update database for {product_key}: {e}")
            return False

    def get_delay(self):
        """Get appropriate delay based on time of day"""
        hour = datetime.now().hour
        if 2 <= hour < 8:  # Night hours
            return random.uniform(3, 4)
        else:  # Day hours
            return random.uniform(6, 8)

    def run(self, limit=None):
        """Main scraping process"""
        logger.info("="*60)
        logger.info("ZOOPLUS CSV IMPORT SCRAPER")
        logger.info("="*60)

        products = self.get_products_to_scrape()

        if limit:
            products = products[:limit]
            logger.info(f"Limited to {limit} products for testing")

        total = len(products)
        scraped = 0
        updated = 0

        for i, product in enumerate(products, 1):
            logger.info(f"\nProcessing {i}/{total}: {product['product_key']}")
            logger.info(f"URL: {product['product_url'][:80]}...")

            # Scrape product page
            image_url = self.scrape_zooplus_page(product['product_url'])

            if image_url:
                logger.info(f"Found image: {image_url[:80]}...")

                # Download and upload to GCS
                gcs_url = self.download_and_upload_image(image_url, product['product_key'])

                if gcs_url:
                    scraped += 1

                    # Update database
                    if self.update_database(product['product_key'], gcs_url):
                        updated += 1
                        self.successful_downloads.append({
                            'product_key': product['product_key'],
                            'product_url': product['product_url'],
                            'image_url': image_url,
                            'gcs_url': gcs_url
                        })
                else:
                    self.failed_downloads.append({
                        'product_key': product['product_key'],
                        'product_url': product['product_url'],
                        'reason': 'Failed to upload to GCS'
                    })
            else:
                self.failed_downloads.append({
                    'product_key': product['product_key'],
                    'product_url': product['product_url'],
                    'reason': 'No image found on product page'
                })

            # Progress report every 10 products
            if i % 10 == 0:
                logger.info(f"\nProgress: {i}/{total} processed, {scraped} scraped, {updated} updated")

            # Rate limiting
            if i < total:
                delay = self.get_delay()
                time.sleep(delay)

        # Final report
        logger.info("="*60)
        logger.info("SCRAPING COMPLETE")
        logger.info("="*60)
        logger.info(f"Total products processed: {total}")
        logger.info(f"Images scraped: {scraped}")
        logger.info(f"Database updated: {updated}")
        logger.info(f"Failed: {len(self.failed_downloads)}")

        # Save logs
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if self.successful_downloads:
            success_file = f'/tmp/zooplus_csv_success_{timestamp}.json'
            with open(success_file, 'w') as f:
                json.dump(self.successful_downloads, f, indent=2)
            logger.info(f"Success log saved to {success_file}")

        if self.failed_downloads:
            failed_file = f'/tmp/zooplus_csv_failed_{timestamp}.json'
            with open(failed_file, 'w') as f:
                json.dump(self.failed_downloads, f, indent=2)
            logger.info(f"Failed log saved to {failed_file}")

        return scraped, updated

if __name__ == "__main__":
    scraper = ZooplusCSVScraper()

    # Test with a small batch first
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        logger.info("Running in test mode (5 products)...")
        scraper.run(limit=5)
    else:
        # Full run
        response = input("Ready to scrape 840 Zooplus CSV products? This will take ~2-3 hours. (y/n): ")
        if response.lower() == 'y':
            scraper.run()
        else:
            logger.info("Scraping cancelled. Use --test flag to test with 5 products.")