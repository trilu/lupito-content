#!/usr/bin/env python3
"""
Multi-Orchestrator Dashboard - Monitor all orchestrator instances and scrapers
Real-time tracking of multiple orchestrator instances and their sessions
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

class MultiOrchestratorDashboard:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.start_time = datetime.now()
    
    def get_database_coverage(self) -> Dict:
        """Get current database coverage statistics"""
        try:
            # Total products
            total_result = self.supabase.table('foods_canonical').select('product_key', count='exact').execute()
            total_products = total_result.count
            
            # Products with ingredients
            ingredients_result = self.supabase.table('foods_canonical').select(
                'product_key', count='exact'
            ).not_.is_('ingredients_raw', 'null').execute()
            ingredients_count = ingredients_result.count
            
            # Products with complete nutrition
            nutrition_result = self.supabase.table('foods_canonical').select(
                'product_key', count='exact'
            ).not_.is_('protein_percent', 'null')\
            .not_.is_('fat_percent', 'null')\
            .not_.is_('fiber_percent', 'null')\
            .not_.is_('ash_percent', 'null')\
            .not_.is_('moisture_percent', 'null').execute()
            nutrition_count = nutrition_result.count
            
            # Products missing ingredients from Zooplus
            missing_ingredients = self.supabase.table('foods_canonical').select(
                'product_key', count='exact'
            ).ilike('product_url', '%zooplus%')\
            .is_('ingredients_raw', 'null').execute()
            missing_count = missing_ingredients.count
            
            return {
                'total_products': total_products,
                'ingredients_count': ingredients_count,
                'ingredients_percentage': (ingredients_count / total_products * 100) if total_products > 0 else 0,
                'nutrition_count': nutrition_count,
                'nutrition_percentage': (nutrition_count / total_products * 100) if total_products > 0 else 0,
                'missing_ingredients': missing_count,
                'target_95_percent': int(total_products * 0.95),
                'ingredients_needed': int(total_products * 0.95) - ingredients_count
            }
        except Exception as e:
            print(f"Error getting coverage: {e}")
            return {}
    
    def get_active_processes(self) -> Dict:
        """Get information about active orchestrator and scraper processes"""
        try:
            # Get orchestrator processes
            orchestrator_result = subprocess.run([
                'ps', 'aux'
            ], capture_output=True, text=True)
            
            orchestrator_processes = []
            scraper_processes = []
            
            if orchestrator_result.returncode == 0:
                lines = orchestrator_result.stdout.strip().split('\n')
                for line in lines:
                    if 'scraper_orchestrator.py' in line and 'grep' not in line:
                        parts = line.split()
                        if len(parts) >= 11:
                            pid = parts[1]
                            # Try to extract instance info from command line
                            if '--instance' in line:
                                try:
                                    instance_idx = line.index('--instance') + len('--instance') + 1
                                    instance_part = line[instance_idx:].split()[0]
                                    instance_id = instance_part
                                except:
                                    instance_id = "unknown"
                            else:
                                instance_id = "1"  # Default instance
                            
                            orchestrator_processes.append({
                                'pid': pid,
                                'instance': instance_id,
                                'command': ' '.join(parts[10:])
                            })
                    
                    elif 'orchestrated_scraper.py' in line and 'grep' not in line:
                        parts = line.split()
                        if len(parts) >= 11:
                            pid = parts[1]
                            # Extract session info from command line args
                            try:
                                cmd_parts = line.split('orchestrated_scraper.py')[1].strip().split()
                                session_name = cmd_parts[0] if cmd_parts else "unknown"
                                country_code = cmd_parts[1] if len(cmd_parts) > 1 else "unknown"
                                offset = cmd_parts[5] if len(cmd_parts) > 5 else "unknown"
                            except:
                                session_name = "unknown"
                                country_code = "unknown"
                                offset = "unknown"
                            
                            scraper_processes.append({
                                'pid': pid,
                                'session': session_name,
                                'country': country_code,
                                'offset': offset
                            })
            
            return {
                'orchestrators': orchestrator_processes,
                'scrapers': scraper_processes
            }
        except Exception as e:
            print(f"Error getting processes: {e}")
            return {'orchestrators': [], 'scrapers': []}
    
    def get_gcs_activity(self) -> Dict:
        """Get GCS scraping activity for today"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            
            # Get today's folders
            result = subprocess.run([
                'gsutil', 'ls', f'gs://{GCS_BUCKET}/scraped/zooplus/'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                return {'total_files_today': 0, 'total_files_all_time': 0, 'sessions': []}
            
            folders = result.stdout.strip().split('\n')
            today_folders = [f for f in folders if today in f]
            
            # Count files in today's folders
            total_files_today = 0
            session_info = []
            
            for folder in today_folders[-10:]:  # Last 10 sessions
                try:
                    folder_name = folder.strip('/').split('/')[-1]
                    files_result = subprocess.run([
                        'gsutil', 'ls', f'{folder}*.json'
                    ], capture_output=True, text=True)
                    
                    if files_result.returncode == 0:
                        file_count = len(files_result.stdout.strip().split('\n'))
                        total_files_today += file_count
                        
                        # Parse session info
                        parts = folder_name.split('_')
                        if len(parts) >= 3:
                            timestamp = parts[1]
                            session = parts[2]
                            time_formatted = f"{timestamp[:2]}:{timestamp[2:4]}:{timestamp[4:6]}"
                            
                            session_info.append({
                                'time': time_formatted,
                                'session': session,
                                'files': file_count,
                                'folder': folder_name
                            })
                except:
                    continue
            
            # Count all-time files
            all_files_result = subprocess.run([
                'gsutil', 'ls', f'gs://{GCS_BUCKET}/scraped/zooplus/*/*.json'
            ], capture_output=True, text=True)
            
            total_files_all_time = 0
            if all_files_result.returncode == 0:
                total_files_all_time = len(all_files_result.stdout.strip().split('\n'))
            
            return {
                'total_files_today': total_files_today,
                'total_files_all_time': total_files_all_time,
                'sessions': sorted(session_info, key=lambda x: x['time'], reverse=True)[:10]
            }
            
        except Exception as e:
            print(f"Error getting GCS activity: {e}")
            return {'total_files_today': 0, 'total_files_all_time': 0, 'sessions': []}
    
    def display_dashboard(self):
        """Display the complete dashboard"""
        # Clear screen and move cursor to top
        print("\033[2J\033[H", end="")
        
        print("=" * 80)
        print(f"🎛️  MULTI-ORCHESTRATOR DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Database coverage
        coverage = self.get_database_coverage()
        if coverage:
            print("\n📊 DATABASE COVERAGE PROGRESS")
            print(f"   Current: {coverage['ingredients_count']:,} products ({coverage['ingredients_percentage']:.1f}%)")
            print(f"   Target:  {coverage['target_95_percent']:,} products (95.0%)")
            print(f"   Gap:     {coverage['ingredients_needed']:,} products needed")
            print(f"   Available: {coverage['missing_ingredients']:,} Zooplus products")
            
            # Progress bar
            progress = coverage['ingredients_percentage'] / 95.0 * 100
            filled = int(progress / 2.5)
            empty = 40 - filled
            print(f"\n   Progress: [{'█' * filled}{'░' * empty}] {coverage['ingredients_percentage']:.1f}%")
        
        # Active processes
        processes = self.get_active_processes()
        print(f"\n🚀 ACTIVE PROCESSES")
        print(f"   Orchestrators: {len(processes['orchestrators'])}")
        print(f"   Scrapers: {len(processes['scrapers'])}")
        
        if processes['orchestrators']:
            print(f"\n🎛️  ORCHESTRATOR INSTANCES:")
            for orch in processes['orchestrators']:
                print(f"   Instance #{orch['instance']}: PID {orch['pid']}")
        
        if processes['scrapers']:
            print(f"\n🌍 ACTIVE SCRAPER SESSIONS:")
            # Group by country
            by_country = {}
            for scraper in processes['scrapers']:
                country = scraper['country'].upper()
                if country not in by_country:
                    by_country[country] = []
                by_country[country].append(scraper)
            
            # Country code to flag mapping
            flags = {
                'US': '🇺🇸', 'GB': '🇬🇧', 'DE': '🇩🇪', 'CA': '🇨🇦', 'FR': '🇫🇷',
                'IT': '🇮🇹', 'ES': '🇪🇸', 'NL': '🇳🇱', 'AU': '🇦🇺', 'NO': '🇳🇴'
            }
            
            for country, scrapers in by_country.items():
                flag = flags.get(country, '🌐')
                sessions = [s['session'] for s in scrapers]
                print(f"   {flag} {country}: {len(scrapers)} sessions ({', '.join(sessions)})")
        
        # GCS activity
        gcs_info = self.get_gcs_activity()
        print(f"\n☁️  SCRAPING PROGRESS")
        print(f"   📄 Total files scraped today: {gcs_info['total_files_today']}")
        print(f"   📄 Total files scraped all time: {gcs_info['total_files_all_time']}")
        
        if gcs_info['total_files_all_time'] > 0:
            completion_pct = min(100.0, gcs_info['total_files_all_time'] / 6000 * 100)
            print(f"   🎯 Estimated completion: {completion_pct:.1f}% (of ~6,000 target)")
        
        if gcs_info['sessions']:
            print(f"\n📂 RECENT SESSIONS (Last 10):")
            for session in gcs_info['sessions'][:10]:
                print(f"      {session['time']} {session['session']}: {session['files']} files")
        
        # Performance estimates
        if gcs_info['total_files_today'] > 0:
            runtime_hours = (datetime.now() - self.start_time.replace(hour=0, minute=0, second=0)).total_seconds() / 3600
            if runtime_hours > 0:
                files_per_hour = gcs_info['total_files_today'] / runtime_hours
                print(f"\n📈 PERFORMANCE")
                print(f"   Rate today: {files_per_hour:.0f} files/hour")
                
                remaining = max(0, 6000 - gcs_info['total_files_all_time'])
                if files_per_hour > 0:
                    hours_remaining = remaining / files_per_hour
                    print(f"   Est. time to completion: {hours_remaining:.1f} hours")
        
        print(f"\n🕐 Dashboard updated: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)

def main():
    dashboard = MultiOrchestratorDashboard()
    
    try:
        # Check if running in continuous mode
        if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
            print("Starting continuous monitoring (Ctrl+C to stop)")
            while True:
                dashboard.display_dashboard()
                time.sleep(30)  # Update every 30 seconds
        else:
            # Single run
            dashboard.display_dashboard()
            
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard monitoring stopped")
    except Exception as e:
        print(f"❌ Dashboard error: {e}")

if __name__ == "__main__":
    main()