#!/usr/bin/env python3
"""
Scraper Orchestrator - Manages 5 concurrent scrapers for maximum coverage
Automatically restarts completed scrapers with new batches
Continuously monitors progress toward 95% goal
"""

import os
import sys
import json
import time
import random
import subprocess
import threading
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

@dataclass
class ScraperSession:
    name: str
    country_code: str
    min_delay: int
    max_delay: int
    batch_size: int
    process: Optional[subprocess.Popen] = None
    start_time: Optional[datetime] = None
    files_scraped: int = 0
    status: str = "idle"  # idle, running, completed, failed
    gcs_folder: str = ""
    restart_count: int = 0

class ScraperOrchestrator:
    def __init__(self, instance_id: int = 1, offset_start: int = 0):
        self.instance_id = instance_id
        self.offset_start = offset_start
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.max_concurrent = 5
        self.max_restarts = 10  # Maximum restarts per session
        self.monitor_interval = 30  # Check every 30 seconds
        
        # Expanded session configurations with more countries and optimized delays
        all_configs = [
            {"name": "us", "country_code": "us", "min_delay": 12, "max_delay": 20, "batch_size": 12},
            {"name": "gb", "country_code": "gb", "min_delay": 15, "max_delay": 24, "batch_size": 12},
            {"name": "de", "country_code": "de", "min_delay": 18, "max_delay": 28, "batch_size": 12},
            {"name": "ca", "country_code": "ca", "min_delay": 20, "max_delay": 30, "batch_size": 12},
            {"name": "fr", "country_code": "fr", "min_delay": 14, "max_delay": 22, "batch_size": 12},
            {"name": "it", "country_code": "it", "min_delay": 16, "max_delay": 26, "batch_size": 12},
            {"name": "es", "country_code": "es", "min_delay": 17, "max_delay": 27, "batch_size": 12},
            {"name": "nl", "country_code": "nl", "min_delay": 19, "max_delay": 29, "batch_size": 12},
            {"name": "au", "country_code": "au", "min_delay": 21, "max_delay": 31, "batch_size": 12},
            {"name": "no", "country_code": "no", "min_delay": 13, "max_delay": 23, "batch_size": 12},
        ]
        
        # Select 5 configs for this instance to avoid overlap
        start_idx = (instance_id - 1) * 5 % len(all_configs)
        self.session_configs = []
        for i in range(5):
            config = all_configs[(start_idx + i) % len(all_configs)].copy()
            config["name"] = f"{config['name']}{instance_id}"
            self.session_configs.append(config)
        
        self.sessions: List[ScraperSession] = []
        self.total_scraped = 0
        self.start_time = datetime.now()
        self.running = True
        
        # Statistics
        self.stats = {
            'total_sessions_started': 0,
            'total_files_scraped': 0,
            'total_errors': 0,
            'coverage_start': 0,
            'coverage_target': 0
        }
        
        print(f"🎛️  SCRAPER ORCHESTRATOR #{self.instance_id} INITIALIZED")
        print(f"Instance ID: {self.instance_id}")
        print(f"Offset start: {self.offset_start}")
        print(f"Max concurrent scrapers: {self.max_concurrent}")
        print(f"Monitor interval: {self.monitor_interval}s")
        print(f"Session configs: {[c['name'] for c in self.session_configs]}")
        print("=" * 60)
    
    def get_current_coverage(self) -> Dict:
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
            
            # Products with complete nutrition (all 5 nutrients)
            nutrition_result = self.supabase.table('foods_canonical').select(
                'product_key', count='exact'
            ).not_.is_('protein_percent', 'null')\
            .not_.is_('fat_percent', 'null')\
            .not_.is_('fiber_percent', 'null')\
            .not_.is_('ash_percent', 'null')\
            .not_.is_('moisture_percent', 'null').execute()
            nutrition_count = nutrition_result.count
            
            # Products missing ingredients (our target)
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
    
    def create_scraper_session(self, config: Dict, batch_offset: int) -> ScraperSession:
        """Create a new scraper session"""
        session = ScraperSession(
            name=config['name'],
            country_code=config['country_code'],
            min_delay=config['min_delay'],
            max_delay=config['max_delay'],
            batch_size=config['batch_size']
        )
        
        # Create dynamic scraper script for this session
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session.gcs_folder = f"scraped/zooplus/{timestamp}_{session.name}"
        
        return session
    
    def start_scraper_session(self, session: ScraperSession, offset: int) -> bool:
        """Start a scraper session as subprocess"""
        try:
            # Create command to run parallel scraper with custom config
            cmd = [
                'python', 'scripts/orchestrated_scraper.py',
                session.name,
                session.country_code,
                str(session.min_delay),
                str(session.max_delay),
                str(session.batch_size),
                str(offset)
            ]
            
            # Start subprocess
            session.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd()
            )
            
            session.start_time = datetime.now()
            session.status = "running"
            self.stats['total_sessions_started'] += 1
            
            print(f"🚀 Started session '{session.name}' (PID: {session.process.pid}, offset: {offset})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start session '{session.name}': {e}")
            session.status = "failed"
            return False
    
    def check_session_status(self, session: ScraperSession) -> bool:
        """Check if session is still running and update stats"""
        if not session.process:
            return False
        
        # Check if process is still running
        poll_result = session.process.poll()
        
        if poll_result is None:
            # Still running - update file count from GCS
            try:
                result = subprocess.run([
                    'gsutil', 'ls', f'gs://{GCS_BUCKET}/{session.gcs_folder}/*.json'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    session.files_scraped = len(result.stdout.strip().split('\n'))
                else:
                    session.files_scraped = 0
            except:
                pass
            
            return True
        else:
            # Process completed
            if poll_result == 0:
                session.status = "completed"
                print(f"✅ Session '{session.name}' completed successfully")
            else:
                session.status = "failed"
                print(f"❌ Session '{session.name}' failed with exit code {poll_result}")
            
            return False
    
    def restart_session(self, session: ScraperSession, offset: int) -> bool:
        """Restart a completed/failed session"""
        if session.restart_count >= self.max_restarts:
            print(f"⚠️ Session '{session.name}' hit restart limit ({self.max_restarts})")
            return False
        
        session.restart_count += 1
        session.files_scraped = 0
        session.status = "idle"
        session.process = None
        
        print(f"🔄 Restarting session '{session.name}' (restart #{session.restart_count})")
        return self.start_scraper_session(session, offset)
    
    def monitor_and_manage_sessions(self):
        """Main monitoring loop"""
        batch_offset = self.offset_start
        
        while self.running:
            try:
                # Get current coverage
                coverage = self.get_current_coverage()
                
                if coverage:
                    print(f"\n📊 COVERAGE UPDATE #{self.instance_id} - {datetime.now().strftime('%H:%M:%S')}")
                    print(f"   Ingredients: {coverage['ingredients_count']:,} ({coverage['ingredients_percentage']:.1f}%)")
                    print(f"   Missing: {coverage['missing_ingredients']:,} products")
                    print(f"   Need for 95%: {coverage['ingredients_needed']:,} products")
                    
                    # Check if we've reached 95% goal
                    if coverage['ingredients_percentage'] >= 95.0:
                        print("🎉 95% COVERAGE ACHIEVED! Stopping orchestrator.")
                        self.running = False
                        break
                
                # Check and manage sessions
                active_sessions = 0
                for session in self.sessions:
                    if self.check_session_status(session):
                        active_sessions += 1
                
                # Start new sessions if we have capacity
                while active_sessions < self.max_concurrent and len(self.sessions) < len(self.session_configs):
                    config_idx = len(self.sessions)
                    config = self.session_configs[config_idx]
                    
                    new_session = self.create_scraper_session(config, batch_offset)
                    if self.start_scraper_session(new_session, batch_offset):
                        self.sessions.append(new_session)
                        active_sessions += 1
                        batch_offset += config['batch_size']  # Non-overlapping batches
                
                # Restart completed sessions
                for session in self.sessions:
                    if session.status in ["completed", "failed"]:
                        if self.restart_session(session, batch_offset):
                            active_sessions += 1
                            batch_offset += session.batch_size
                
                # Update total stats
                self.stats['total_files_scraped'] = sum(s.files_scraped for s in self.sessions)
                
                # Print session status
                print(f"\n🎛️  INSTANCE #{self.instance_id} SESSIONS ({active_sessions}/{self.max_concurrent}):")
                for session in self.sessions:
                    runtime = ""
                    if session.start_time:
                        runtime = str(datetime.now() - session.start_time).split('.')[0]
                    
                    print(f"   {session.name}: {session.status} | {session.files_scraped} files | {runtime}")
                
                print(f"\n📈 INSTANCE #{self.instance_id} TOTALS: {self.stats['total_files_scraped']} files scraped")
                
                # Wait before next check
                time.sleep(self.monitor_interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Orchestrator interrupted by user")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                time.sleep(self.monitor_interval)
    
    def cleanup(self):
        """Cleanup all running sessions"""
        print("\n🧹 Cleaning up sessions...")
        for session in self.sessions:
            if session.process and session.process.poll() is None:
                print(f"   Terminating {session.name} (PID: {session.process.pid})")
                session.process.terminate()
                time.sleep(2)
                if session.process.poll() is None:
                    session.process.kill()
    
    def run(self):
        """Start the orchestrator"""
        try:
            # Show initial coverage
            coverage = self.get_current_coverage()
            if coverage:
                self.stats['coverage_start'] = coverage['ingredients_percentage']
                print(f"🎯 STARTING ORCHESTRATION")
                print(f"   Current coverage: {coverage['ingredients_percentage']:.1f}%")
                print(f"   Target: 95.0%")
                print(f"   Products needed: {coverage['ingredients_needed']:,}")
                print(f"   Products available: {coverage['missing_ingredients']:,}")
            
            # Start monitoring
            self.monitor_and_manage_sessions()
            
        finally:
            self.cleanup()
            
            # Final stats
            elapsed = datetime.now() - self.start_time
            print(f"\n🏁 ORCHESTRATOR #{self.instance_id} SESSION COMPLETE")
            print(f"   Duration: {elapsed}")
            print(f"   Sessions started: {self.stats['total_sessions_started']}")
            print(f"   Files scraped: {self.stats['total_files_scraped']}")
            
            if self.stats['total_files_scraped'] > 0:
                rate = self.stats['total_files_scraped'] / (elapsed.total_seconds() / 3600)
                print(f"   Average rate: {rate:.0f} files/hour")

def main():
    parser = argparse.ArgumentParser(description='Zooplus Scraper Orchestrator - Multi-instance Support')
    parser.add_argument('--instance', type=int, default=1, help='Instance ID (1-4)')
    parser.add_argument('--offset-start', type=int, default=0, help='Starting offset for this instance')
    
    args = parser.parse_args()
    
    # Validate instance ID
    if args.instance < 1 or args.instance > 4:
        print("❌ Instance ID must be between 1 and 4")
        sys.exit(1)
    
    # Auto-calculate offset if not provided
    if args.offset_start == 0:
        args.offset_start = (args.instance - 1) * 300  # 300 products per instance
    
    print(f"🚀 Starting Orchestrator Instance #{args.instance} with offset {args.offset_start}")
    
    orchestrator = ScraperOrchestrator(args.instance, args.offset_start)
    orchestrator.run()

if __name__ == "__main__":
    main()