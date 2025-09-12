#!/usr/bin/env python3
"""
Orchestrator Dashboard - Real-time monitoring of scraping progress
Shows coverage progress, active sessions, and performance metrics
"""

import os
import time
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

class OrchestratorDashboard:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def get_coverage_stats(self):
        """Get current database coverage"""
        try:
            # Total products
            total_result = self.supabase.table('foods_canonical').select('product_key', count='exact').execute()
            total_products = total_result.count
            
            # Products with ingredients
            ingredients_result = self.supabase.table('foods_canonical').select(
                'product_key', count='exact'
            ).not_.is_('ingredients_raw', 'null').execute()
            ingredients_count = ingredients_result.count
            
            # Missing ingredients from Zooplus
            missing_result = self.supabase.table('foods_canonical').select(
                'product_key', count='exact'
            ).ilike('product_url', '%zooplus%')\
            .is_('ingredients_raw', 'null').execute()
            missing_count = missing_result.count
            
            return {
                'total_products': total_products,
                'ingredients_count': ingredients_count,
                'ingredients_percentage': (ingredients_count / total_products * 100) if total_products > 0 else 0,
                'missing_ingredients': missing_count,
                'target_95': int(total_products * 0.95),
                'needed_for_95': int(total_products * 0.95) - ingredients_count
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return None
    
    def get_active_sessions(self):
        """Get active GCS sessions from today"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            result = subprocess.run([
                'gsutil', 'ls', f'gs://{GCS_BUCKET}/scraped/zooplus/{today}*/'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                folders = result.stdout.strip().split('\n')
                
                sessions = []
                for folder in folders:
                    if folder:
                        folder_name = folder.split('/')[-2]
                        
                        # Count files
                        count_result = subprocess.run([
                            'gsutil', 'ls', folder + '*.json'
                        ], capture_output=True, text=True)
                        
                        if count_result.returncode == 0:
                            file_count = len(count_result.stdout.strip().split('\n'))
                        else:
                            file_count = 0
                        
                        # Extract session info
                        parts = folder_name.split('_')
                        session_type = "unknown"
                        if len(parts) >= 3:
                            session_type = parts[-1]
                        
                        sessions.append({
                            'name': folder_name,
                            'type': session_type,
                            'files': file_count,
                            'gcs_path': folder
                        })
                
                return sessions
            else:
                return []
        except Exception as e:
            print(f"Error getting sessions: {e}")
            return []
    
    def get_running_processes(self):
        """Get running orchestrator processes"""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            
            orchestrator_processes = []
            scraper_processes = []
            
            for line in result.stdout.split('\n'):
                if 'orchestrator' in line and 'grep' not in line:
                    orchestrator_processes.append(line)
                elif 'orchestrated_scraper.py' in line and 'grep' not in line:
                    scraper_processes.append(line)
            
            return {
                'orchestrators': len(orchestrator_processes),
                'scrapers': len(scraper_processes),
                'orchestrator_details': orchestrator_processes,
                'scraper_details': scraper_processes
            }
        except Exception as e:
            print(f"Error getting processes: {e}")
            return {'orchestrators': 0, 'scrapers': 0}
    
    def display_dashboard(self):
        """Display the dashboard"""
        # Clear screen
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🎛️  SCRAPER ORCHESTRATOR DASHBOARD")
        print("=" * 70)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Coverage stats
        coverage = self.get_coverage_stats()
        if coverage:
            progress_bar = self.create_progress_bar(coverage['ingredients_percentage'], 95.0)
            
            print("📊 DATABASE COVERAGE PROGRESS")
            print("-" * 40)
            print(f"   Current: {coverage['ingredients_count']:,} products ({coverage['ingredients_percentage']:.1f}%)")
            print(f"   Target:  {coverage['target_95']:,} products (95.0%)")
            print(f"   Gap:     {coverage['needed_for_95']:,} products needed")
            print(f"   Available: {coverage['missing_ingredients']:,} Zooplus products")
            print()
            print(f"   Progress: {progress_bar}")
            print()
        
        # Active processes
        processes = self.get_running_processes()
        print("🚀 ACTIVE PROCESSES")
        print("-" * 40)
        print(f"   Orchestrators: {processes['orchestrators']}")
        print(f"   Scrapers: {processes['scrapers']}")
        print()
        
        # Active sessions
        sessions = self.get_active_sessions()
        if sessions:
            print("☁️  ACTIVE GCS SESSIONS")
            print("-" * 40)
            total_files = 0
            
            # Group by session type
            session_types = {}
            for session in sessions:
                session_type = session['type']
                if session_type not in session_types:
                    session_types[session_type] = []
                session_types[session_type].append(session)
                total_files += session['files']
            
            for session_type, type_sessions in session_types.items():
                type_total = sum(s['files'] for s in type_sessions)
                flag = self.get_country_flag(session_type)
                print(f"   {flag} {session_type.upper()}: {len(type_sessions)} sessions, {type_total} files")
            
            print(f"   📄 Total files scraped today: {total_files}")
            print()
        
        # Performance estimate
        if coverage and total_files > 0:
            print("📈 PERFORMANCE METRICS")
            print("-" * 40)
            
            # Estimate time to 95%
            if coverage['needed_for_95'] > 0:
                # Rough estimate based on current file count (assuming files ~ products with data)
                estimated_hours = coverage['needed_for_95'] / max(10, total_files)  # Conservative estimate
                print(f"   Estimated time to 95%: ~{estimated_hours:.1f} hours")
                print(f"   (Based on current activity level)")
            else:
                print("   🎉 95% COVERAGE ACHIEVED!")
            print()
        
        print("💡 Commands:")
        print("   • Start orchestrator: python scripts/scraper_orchestrator.py")
        print("   • Monitor continuously: watch -n 30 python scripts/orchestrator_dashboard.py")
        print("   • Stop all: pkill -f orchestrator")
    
    def create_progress_bar(self, current: float, target: float, width: int = 40) -> str:
        """Create a visual progress bar"""
        progress = min(current / target, 1.0)
        filled = int(progress * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {current:.1f}%"
    
    def get_country_flag(self, country_code: str) -> str:
        """Get flag emoji for country code"""
        flags = {
            'us': '🇺🇸',
            'gb': '🇬🇧',
            'de': '🇩🇪',
            'ca': '🇨🇦',
            'fr': '🇫🇷',
            'au': '🇦🇺',
            'it': '🇮🇹',
            'es': '🇪🇸'
        }
        return flags.get(country_code.lower(), '🏳️')

def main():
    dashboard = OrchestratorDashboard()
    dashboard.display_dashboard()

if __name__ == "__main__":
    main()