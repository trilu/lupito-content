#!/usr/bin/env python3
"""
AKC Breeds Supabase Population Script
=====================================

Integrates Universal ScrapingBee scraper with Supabase to populate akc_breeds table.
Uses smart BeautifulSoup → ScrapingBee fallback for cost-effective scraping.

Usage:
    python3 jobs/populate_akc_supabase.py                    # Process all breeds
    python3 jobs/populate_akc_supabase.py --limit 10         # Test with 10 breeds
    python3 jobs/populate_akc_supabase.py --force-update     # Update existing breeds
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Install with: pip install supabase python-dotenv requests beautifulsoup4")
    sys.exit(1)

# Import our universal scraper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from universal_breed_scraper import UniversalBreedScraper

load_dotenv()

class AKCSupabasePopulator:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required in .env")
            
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.scraper = UniversalBreedScraper()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize stats
        self.stats = {
            'total_urls': 0,
            'processed': 0,
            'successful': 0,
            'skipped': 0,
            'failed': 0,
            'total_cost_credits': 0,
            'beautifulsoup_count': 0,
            'scrapingbee_count': 0
        }

    def get_akc_breed_urls(self) -> List[str]:
        """Load AKC breed URLs from file"""
        urls_file = os.path.join(os.path.dirname(__file__), '..', 'akc_breed_urls.txt')
        
        if not os.path.exists(urls_file):
            self.logger.error(f"AKC breed URLs file not found: {urls_file}")
            # Create sample URLs for testing if file doesn't exist
            self.logger.info("Creating sample URLs for testing...")
            sample_urls = [
                "https://www.akc.org/dog-breeds/golden-retriever/",
                "https://www.akc.org/dog-breeds/german-shepherd-dog/",
                "https://www.akc.org/dog-breeds/labrador-retriever/",
                "https://www.akc.org/dog-breeds/bulldog/",
                "https://www.akc.org/dog-breeds/poodle/"
            ]
            return sample_urls
            
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
        self.logger.info(f"Loaded {len(urls)} AKC breed URLs from {urls_file}")
        return urls

    def breed_exists(self, breed_slug: str) -> bool:
        """Check if breed already exists in Supabase"""
        try:
            response = self.supabase.table('akc_breeds').select('id').eq('breed_slug', breed_slug).execute()
            return len(response.data) > 0
        except Exception as e:
            self.logger.error(f"Error checking breed existence for {breed_slug}: {e}")
            return False

    def insert_breed_data(self, breed_data: Dict[str, Any]) -> bool:
        """Insert or update breed data in Supabase"""
        try:
            # Prepare data for existing Supabase schema
            supabase_data = {
                'breed_slug': breed_data['breed_slug'],
                'display_name': breed_data['display_name'],
                'akc_url': breed_data['akc_url'],
                'extraction_status': breed_data['extraction_status'],
                'has_physical_data': breed_data.get('has_physical_data', False),
                'has_content': breed_data.get('has_profile_data', False),
                'comprehensive_content': breed_data.get('training', ''),  # Store scraped content here
                'extraction_notes': f"Scraped via {breed_data['scraping_method']} (cost: {breed_data.get('scrapingbee_cost', 0)} credits)",
                'updated_at': datetime.now().isoformat()
            }
            
            # Use upsert to handle duplicates
            response = self.supabase.table('akc_breeds').upsert(supabase_data, on_conflict='breed_slug').execute()
            
            if response.data:
                method_emoji = "🆓" if breed_data['scraping_method'] == 'beautifulsoup' else "💰"
                cost_info = f" (${breed_data.get('scrapingbee_cost', 0) * 0.001:.3f})" if breed_data.get('scrapingbee_cost', 0) > 0 else ""
                
                self.logger.info(f"✅ {method_emoji} Saved {breed_data['breed_slug']} via {breed_data['scraping_method']}{cost_info}")
                return True
            else:
                self.logger.error(f"❌ Failed to save {breed_data['breed_slug']}: No data returned")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error saving {breed_data['breed_slug']}: {e}")
            return False

    def populate_breeds(self, limit: Optional[int] = None, skip_existing: bool = True) -> Dict[str, int]:
        """Populate AKC breeds in Supabase using Universal Scraper"""
        urls = self.get_akc_breed_urls()
        
        if limit:
            urls = urls[:limit]
            
        self.stats['total_urls'] = len(urls)
        
        self.logger.info(f"🚀 Starting AKC breeds population")
        self.logger.info(f"📊 Total URLs: {len(urls)}")
        self.logger.info(f"⚙️  Skip existing: {skip_existing}")
        self.logger.info(f"🔧 ScrapingBee configured: {bool(self.scraper.scrapingbee_api_key)}")
        print("-" * 80)
        
        for i, url in enumerate(urls, 1):
            try:
                # Extract breed slug from URL
                breed_slug = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
                
                self.logger.info(f"[{i}/{len(urls)}] Processing: {breed_slug}")
                
                # Skip if exists and skip_existing is True
                if skip_existing and self.breed_exists(breed_slug):
                    self.logger.info(f"⏭️  Skipping {breed_slug} (already exists)")
                    self.stats['skipped'] += 1
                    continue
                
                # Scrape using Universal Scraper
                html, method = self.scraper.smart_fetch(url)
                
                if not html:
                    self.logger.error(f"❌ Failed to fetch content for {breed_slug}")
                    self.stats['failed'] += 1
                    continue
                
                # Extract breed data
                breed_data = self.scraper.extract_akc_breed_data(html, url)
                breed_data['scraping_method'] = method
                breed_data['scrapingbee_cost'] = 5 if method == 'scrapingbee' else 0
                
                # Update method stats
                if method == 'beautifulsoup':
                    self.stats['beautifulsoup_count'] += 1
                elif method == 'scrapingbee':
                    self.stats['scrapingbee_count'] += 1
                
                # Track costs
                self.stats['total_cost_credits'] += breed_data['scrapingbee_cost']
                
                # Save to Supabase
                if self.insert_breed_data(breed_data):
                    self.stats['successful'] += 1
                else:
                    self.stats['failed'] += 1
                    
                self.stats['processed'] += 1
                
                # Show progress every 10 breeds
                if i % 10 == 0:
                    self.print_progress()
                
                # Rate limiting (be respectful to AKC and ScrapingBee)
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"❌ Error processing {url}: {e}")
                self.stats['failed'] += 1
                
        # Update total cost from scraper
        self.stats['total_cost_credits'] = self.scraper.total_cost_credits
        
        return self.stats

    def print_progress(self):
        """Print current progress"""
        processed = self.stats['processed']
        total = self.stats['total_urls']
        success_rate = (self.stats['successful'] / max(processed, 1)) * 100
        
        print(f"📈 Progress: {processed}/{total} ({processed/total*100:.1f}%) | "
              f"✅ Success: {self.stats['successful']} ({success_rate:.1f}%) | "
              f"💰 Cost: {self.stats['total_cost_credits']} credits")

    def print_summary(self):
        """Print comprehensive population summary"""
        stats = self.stats
        
        print("\n" + "="*80)
        print("🎯 AKC BREEDS SUPABASE POPULATION SUMMARY")
        print("="*80)
        
        # Basic Stats
        print(f"📊 Total URLs: {stats['total_urls']}")
        print(f"📈 Processed: {stats['processed']}")
        print(f"✅ Successful: {stats['successful']}")
        print(f"⏭️  Skipped: {stats['skipped']}")
        print(f"❌ Failed: {stats['failed']}")
        
        # Success Rate
        if stats['processed'] > 0:
            success_rate = (stats['successful'] / stats['processed']) * 100
            print(f"🎯 Success Rate: {success_rate:.1f}%")
        
        # Method Breakdown
        print(f"\n🔧 SCRAPING METHOD BREAKDOWN:")
        print(f"🆓 BeautifulSoup: {stats['beautifulsoup_count']} breeds (FREE)")
        print(f"💰 ScrapingBee: {stats['scrapingbee_count']} breeds (${stats['scrapingbee_count'] * 0.005:.3f})")
        
        # Cost Analysis
        total_cost_usd = stats['total_cost_credits'] * 0.001
        print(f"\n💰 COST ANALYSIS:")
        print(f"Credits Used: {stats['total_cost_credits']}")
        print(f"Estimated Cost: ${total_cost_usd:.3f}")
        
        if stats['total_urls'] > stats['processed']:
            remaining = stats['total_urls'] - stats['processed']
            estimated_remaining_cost = remaining * 0.005  # Assume worst case (all ScrapingBee)
            print(f"Remaining Breeds: {remaining}")
            print(f"Max Additional Cost: ${estimated_remaining_cost:.3f}")
        
        # Recommendations
        print(f"\n🚀 RECOMMENDATIONS:")
        if stats['beautifulsoup_count'] > stats['scrapingbee_count']:
            print("✅ Excellent! Most breeds scraped with free BeautifulSoup method")
        if stats['failed'] > 0:
            print(f"⚠️  {stats['failed']} breeds failed - consider retrying with --force-update")
        if total_cost_usd > 1.0:
            print("💸 High ScrapingBee usage - consider optimizing JavaScript detection")
        
        print("="*80)

    def get_database_stats(self):
        """Get current database statistics"""
        try:
            # Total breeds
            total_response = self.supabase.table('akc_breeds').select('id', count='exact').execute()
            total_breeds = total_response.count if total_response.count else 0
            
            # Successful breeds
            success_response = self.supabase.table('akc_breeds').select('id', count='exact').eq('extraction_status', 'success').execute()
            successful_breeds = success_response.count if success_response.count else 0
            
            # Method breakdown from extraction_notes
            method_response = self.supabase.table('akc_breeds').select('extraction_notes').execute()
            methods = {}
            for breed in method_response.data:
                note = breed.get('extraction_notes', '')
                if 'beautifulsoup' in note.lower():
                    methods['beautifulsoup'] = methods.get('beautifulsoup', 0) + 1
                elif 'scrapingbee' in note.lower():
                    methods['scrapingbee'] = methods.get('scrapingbee', 0) + 1
                else:
                    methods['unknown'] = methods.get('unknown', 0) + 1
            
            return {
                'total_breeds': total_breeds,
                'successful_breeds': successful_breeds,
                'methods': methods
            }
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return None

    def print_database_status(self):
        """Print current database status"""
        db_stats = self.get_database_stats()
        if not db_stats:
            return
            
        print("\n" + "="*80)
        print("📊 CURRENT DATABASE STATUS")
        print("="*80)
        print(f"Total Breeds: {db_stats['total_breeds']}")
        print(f"Successful: {db_stats['successful_breeds']}")
        
        if db_stats['methods']:
            print("\nMethod Breakdown:")
            for method, count in db_stats['methods'].items():
                emoji = "🆓" if method == 'beautifulsoup' else "💰" if method == 'scrapingbee' else "❓"
                print(f"  {emoji} {method}: {count}")
        
        print("="*80)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Populate AKC breeds in Supabase using Universal ScrapingBee scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 jobs/populate_akc_supabase.py                    # Process all breeds
  python3 jobs/populate_akc_supabase.py --limit 10         # Test with 10 breeds  
  python3 jobs/populate_akc_supabase.py --force-update     # Update existing breeds
  python3 jobs/populate_akc_supabase.py --status           # Check database status
        """
    )
    
    parser.add_argument('--limit', type=int, 
                       help='Limit number of breeds to process')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                       help='Skip breeds that already exist in database (default: True)')
    parser.add_argument('--force-update', action='store_true', default=False,
                       help='Update existing breeds (opposite of --skip-existing)')
    parser.add_argument('--status', action='store_true',
                       help='Show current database status and exit')
    
    args = parser.parse_args()
    
    try:
        populator = AKCSupabasePopulator()
        
        # Show database status if requested
        if args.status:
            populator.print_database_status()
            return
        
        # Show initial database status
        populator.print_database_status()
        
        skip_existing = not args.force_update if args.force_update else args.skip_existing
        
        print(f"\n🚀 Starting breed population...")
        start_time = time.time()
        
        stats = populator.populate_breeds(
            limit=args.limit,
            skip_existing=skip_existing
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        populator.print_summary()
        
        print(f"\n⏱️  Total Time: {duration:.1f} seconds")
        if stats['processed'] > 0:
            print(f"⚡ Average Time per Breed: {duration/stats['processed']:.1f} seconds")
        
        # Show final database status
        populator.print_database_status()
        
    except KeyboardInterrupt:
        print("\n\n❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()