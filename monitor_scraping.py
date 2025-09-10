#!/usr/bin/env python3
"""
Monitor the scraping progress
"""

import json
import time
from datetime import datetime

def monitor_progress():
    """Monitor and display scraping progress"""
    
    while True:
        try:
            # Load progress file
            with open('scraping_progress.json', 'r') as f:
                data = json.load(f)
            
            stats = data.get('stats', {})
            completed = len(data.get('completed', []))
            total = stats.get('total', 0)
            success = stats.get('success', 0)
            failed = stats.get('failed', 0)
            
            # Calculate success rate
            success_rate = (success / total * 100) if total > 0 else 0
            
            # Clear screen and show stats
            print("\033[2J\033[H")  # Clear screen
            print("="*60)
            print("WIKIPEDIA SCRAPING MONITOR")
            print("="*60)
            print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"\nProgress:")
            print(f"  Total Processed: {total}")
            print(f"  Successful: {success}")
            print(f"  Failed: {failed}")
            print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  Unique Breeds Completed: {completed}")
            
            # Show recent errors if any
            errors = stats.get('errors', [])
            if errors:
                print(f"\nRecent Errors (last 5):")
                for error in errors[-5:]:
                    print(f"  - {error[:100]}")
            
            # Show last updated
            last_updated = data.get('last_updated', 'Unknown')
            print(f"\nLast Progress Save: {last_updated}")
            
            print("\nPress Ctrl+C to exit monitor...")
            
            # Wait 10 seconds before refreshing
            time.sleep(10)
            
        except FileNotFoundError:
            print("Progress file not found. Waiting for scraper to start...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")
            break
        except Exception as e:
            print(f"Error reading progress: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_progress()