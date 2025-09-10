#!/usr/bin/env python3
"""
Re-scrape all breeds with proper rate limiting and progress tracking
"""

import os
import sys
import time
import random
from datetime import datetime, timedelta
import json
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jobs.wikipedia_breed_scraper_fixed import WikipediaBreedScraper
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

class RateLimitedScraper(WikipediaBreedScraper):
    """Enhanced scraper with rate limiting and progress tracking"""
    
    def __init__(self, min_delay=3, max_delay=7):
        """Initialize with configurable delays"""
        super().__init__()
        self.min_delay = min_delay  # Minimum seconds between requests
        self.max_delay = max_delay  # Maximum seconds between requests
        self.last_request_time = None
        self.progress_file = 'scraping_progress.json'
        self.completed_breeds = self.load_progress()
        
    def load_progress(self) -> set:
        """Load previously completed breeds"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                return set(data.get('completed', []))
        return set()
    
    def save_progress(self):
        """Save progress to file"""
        with open(self.progress_file, 'w') as f:
            json.dump({
                'completed': list(self.completed_breeds),
                'last_updated': datetime.now().isoformat(),
                'stats': self.stats
            }, f, indent=2)
    
    def wait_if_needed(self):
        """Implement rate limiting with random delay"""
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            # Random delay between min and max
            required_delay = random.uniform(self.min_delay, self.max_delay)
            if elapsed < required_delay:
                sleep_time = required_delay - elapsed
                print(f"  Rate limiting: waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def scrape_breed(self, breed_name: str, url: str) -> Dict[str, Any]:
        """Scrape with rate limiting"""
        self.wait_if_needed()
        return super().scrape_breed(breed_name, url)
    
    def process_breeds_batch(self, breeds_data: List[tuple], batch_name: str = "batch"):
        """Process breeds with progress tracking and recovery"""
        total_breeds = len(breeds_data)
        print(f"\n{'='*80}")
        print(f"PROCESSING {batch_name.upper()}")
        print(f"Total breeds to process: {total_breeds}")
        print(f"Already completed: {len(self.completed_breeds)}")
        print(f"Remaining: {total_breeds - len([b for b in breeds_data if b[0] in self.completed_breeds])}")
        print(f"Rate limiting: {self.min_delay}-{self.max_delay} seconds between requests")
        print(f"{'='*80}\n")
        
        start_time = datetime.now()
        
        for i, (breed_name, url) in enumerate(breeds_data):
            # Skip if already completed
            if breed_name in self.completed_breeds:
                print(f"[{i+1}/{total_breeds}] Skipping {breed_name} (already completed)")
                continue
            
            self.stats['total'] += 1
            
            # Progress indicator
            elapsed = datetime.now() - start_time
            if self.stats['total'] > 0:
                avg_time = elapsed.total_seconds() / self.stats['total']
                remaining = (total_breeds - i - 1) * avg_time
                eta = datetime.now() + timedelta(seconds=remaining)
                print(f"\n[{i+1}/{total_breeds}] Processing: {breed_name}")
                print(f"  Progress: {((i+1)/total_breeds)*100:.1f}%")
                print(f"  ETA: {eta.strftime('%H:%M:%S')}")
            
            # Scrape breed
            try:
                breed_data = self.scrape_breed(breed_name, url)
                
                if breed_data:
                    # Save to database
                    if self.save_to_database(breed_data):
                        self.stats['success'] += 1
                        self.completed_breeds.add(breed_name)
                        print(f"  ✅ Success: Saved {breed_name}")
                    else:
                        self.stats['failed'] += 1
                        print(f"  ❌ Failed: Could not save {breed_name}")
                else:
                    self.stats['failed'] += 1
                    print(f"  ❌ Failed: Could not scrape {breed_name}")
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user. Saving progress...")
                self.save_progress()
                self._print_stats()
                print(f"\nProgress saved. Run again to resume from breed #{i+1}")
                sys.exit(0)
            except Exception as e:
                print(f"  ❌ Error: {e}")
                self.stats['failed'] += 1
                self.stats['errors'].append(f"{breed_name}: {str(e)}")
            
            # Save progress every 10 breeds
            if (i + 1) % 10 == 0:
                self.save_progress()
                self._print_stats()
        
        # Final save
        self.save_progress()
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n{'='*80}")
        print(f"BATCH COMPLETE: {batch_name}")
        print(f"Duration: {duration}")
        print(f"Average time per breed: {duration.total_seconds()/max(self.stats['total'], 1):.1f}s")
        self._print_stats()

def get_all_breed_urls():
    """Get all breed URLs from both files"""
    all_breeds = []
    
    # Get existing breeds that need re-scraping
    if os.path.exists('wikipedia_urls.txt'):
        with open('wikipedia_urls.txt', 'r') as f:
            for line in f:
                if '|' in line:
                    breed_name, url = line.strip().split('|', 1)
                    all_breeds.append((breed_name, url))
        print(f"Loaded {len(all_breeds)} breeds from wikipedia_urls.txt")
    
    # Get missing breeds
    if os.path.exists('missing_breeds_wikipedia_urls.txt'):
        missing_count = 0
        with open('missing_breeds_wikipedia_urls.txt', 'r') as f:
            for line in f:
                if '|' in line:
                    breed_name, url = line.strip().split('|', 1)
                    all_breeds.append((breed_name, url))
                    missing_count += 1
        print(f"Loaded {missing_count} missing breeds from missing_breeds_wikipedia_urls.txt")
    
    return all_breeds

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Re-scrape all breeds with rate limiting')
    parser.add_argument('--min-delay', type=int, default=3, help='Minimum delay between requests (seconds)')
    parser.add_argument('--max-delay', type=int, default=7, help='Maximum delay between requests (seconds)')
    parser.add_argument('--resume', action='store_true', help='Resume from previous progress')
    parser.add_argument('--reset', action='store_true', help='Reset progress and start fresh')
    parser.add_argument('--test', action='store_true', help='Test mode - only process 5 breeds')
    
    args = parser.parse_args()
    
    # Initialize scraper with rate limiting
    scraper = RateLimitedScraper(min_delay=args.min_delay, max_delay=args.max_delay)
    
    # Reset progress if requested
    if args.reset:
        print("Resetting progress...")
        scraper.completed_breeds = set()
        scraper.save_progress()
    
    # Get all breed URLs
    all_breeds = get_all_breed_urls()
    
    if args.test:
        all_breeds = all_breeds[:5]
        print("TEST MODE - Processing only 5 breeds")
    
    print(f"\n{'='*80}")
    print("WIKIPEDIA BREED RE-SCRAPING CAMPAIGN")
    print(f"{'='*80}")
    print(f"Total breeds to process: {len(all_breeds)}")
    print(f"Rate limiting: {args.min_delay}-{args.max_delay} seconds between requests")
    
    # Estimate time
    avg_delay = (args.min_delay + args.max_delay) / 2
    avg_process_time = 2  # Estimated processing time per breed
    total_time = len(all_breeds) * (avg_delay + avg_process_time)
    print(f"Estimated total time: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)")
    
    if not args.resume and scraper.completed_breeds:
        print(f"\n⚠️  Found {len(scraper.completed_breeds)} previously completed breeds.")
        print("Use --resume to continue from where you left off, or --reset to start fresh.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
    
    # Process all breeds
    print("\nStarting scraping... (Press Ctrl+C to pause and save progress)")
    scraper.process_breeds_batch(all_breeds, "All Breeds")
    
    # Generate final report
    scraper._generate_report()
    
    print("\n✅ RE-SCRAPING COMPLETE!")
    print(f"Check the report file for details.")
    print(f"Progress saved in: {scraper.progress_file}")

if __name__ == "__main__":
    main()