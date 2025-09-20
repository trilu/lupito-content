#!/usr/bin/env python3
"""
Scraping Progress Monitor
Real-time monitoring of all active scraping processes and completeness metrics.
"""

import os
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, List
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ScrapingProgressMonitor:
    def __init__(self):
        """Initialize the progress monitor"""
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if self.supabase_url and self.supabase_key:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        else:
            self.supabase = None

        # Log files to monitor
        self.log_files = [
            'web_search_phase1.log',
            'purina_hills_scraping.log',
            'orvis_scraping.log',
            'wikipedia_extraction.log',
            'scrapingbee_enhanced.log',
            'popular_breeds_scrapingbee.log'
        ]

    def check_background_processes(self) -> Dict[str, Any]:
        """Check status of background Python processes"""
        try:
            # Get all Python processes
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.split('\n')

            python_processes = []
            for line in lines:
                if 'python3' in line and any(script in line for script in [
                    'intelligent_web_search_scraper.py',
                    'scrape_purina_hills_targeted.py',
                    'scrape_orvis_breeds.py',
                    'reprocess_wikipedia_gcs'
                ]):
                    # Extract process info
                    parts = line.split()
                    if len(parts) >= 11:
                        pid = parts[1]
                        cpu = parts[2]
                        mem = parts[3]
                        time_running = parts[9]
                        command = ' '.join(parts[10:])

                        # Identify script type
                        script_type = "Unknown"
                        if 'intelligent_web_search' in command:
                            script_type = "Web Search (Authority Sources)"
                        elif 'purina_hills' in command:
                            script_type = "Purina/Hills Targeted"
                        elif 'orvis' in command:
                            script_type = "Orvis Encyclopedia"
                        elif 'wikipedia' in command:
                            script_type = "Wikipedia Reprocessing"

                        python_processes.append({
                            'pid': pid,
                            'type': script_type,
                            'cpu_percent': cpu,
                            'memory_percent': mem,
                            'runtime': time_running,
                            'command': command[:80] + "..." if len(command) > 80 else command
                        })

            return {
                'total_processes': len(python_processes),
                'processes': python_processes
            }

        except Exception as e:
            return {'error': f"Error checking processes: {e}"}

    def get_log_status(self) -> Dict[str, Any]:
        """Get status from log files"""
        log_status = {}

        for log_file in self.log_files:
            if os.path.exists(log_file):
                try:
                    # Get file size and last modified
                    stat = os.stat(log_file)
                    size_mb = stat.st_size / (1024 * 1024)
                    last_modified = datetime.fromtimestamp(stat.st_mtime)

                    # Read last few lines to get progress
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        last_lines = lines[-10:] if len(lines) >= 10 else lines

                    # Extract progress info
                    progress_info = self.extract_progress_from_log(last_lines, log_file)

                    log_status[log_file] = {
                        'exists': True,
                        'size_mb': round(size_mb, 2),
                        'last_modified': last_modified.strftime('%H:%M:%S'),
                        'progress': progress_info
                    }

                except Exception as e:
                    log_status[log_file] = {
                        'exists': True,
                        'error': str(e)
                    }
            else:
                log_status[log_file] = {'exists': False}

        return log_status

    def extract_progress_from_log(self, lines: List[str], log_file: str) -> Dict[str, Any]:
        """Extract progress information from log lines"""
        progress = {'status': 'Unknown', 'details': {}}

        for line in reversed(lines):
            line = line.strip()

            # Look for completion messages
            if 'COMPLETE' in line.upper():
                progress['status'] = 'Completed'
                break

            # Look for progress indicators
            elif '[' in line and '/' in line and ']' in line:
                # Pattern: [X/Y] Processing...
                try:
                    start = line.find('[') + 1
                    end = line.find(']')
                    if start < end:
                        progress_str = line[start:end]
                        if '/' in progress_str:
                            current, total = progress_str.split('/')
                            progress['status'] = 'Running'
                            progress['details'] = {
                                'current': int(current),
                                'total': int(total),
                                'percentage': round((int(current) / int(total)) * 100, 1)
                            }
                            break
                except:
                    pass

            # Look for update messages
            elif '✓ Updated' in line:
                progress['status'] = 'Running'
                progress['details']['last_action'] = 'Updated breed data'

            # Look for error patterns
            elif 'ERROR' in line.upper():
                progress['status'] = 'Error'
                progress['details']['last_error'] = line[-100:]

        return progress

    def get_database_completeness(self) -> Dict[str, Any]:
        """Get current database completeness metrics"""
        if not self.supabase:
            return {'error': 'Database connection not available'}

        try:
            # Get current completeness
            response = self.supabase.table('breeds_unified_api').select(
                'breed_slug, exercise_needs_detail, training_tips, grooming_needs, '
                'temperament, personality_traits, health_issues, good_with_children, '
                'good_with_pets, grooming_frequency, exercise_level'
            ).execute()

            if not response.data:
                return {'error': 'No data returned from database'}

            total_breeds = len(response.data)
            target_fields = [
                'exercise_needs_detail', 'training_tips', 'grooming_needs',
                'temperament', 'personality_traits', 'health_issues',
                'good_with_children', 'good_with_pets', 'grooming_frequency', 'exercise_level'
            ]

            # Calculate completeness
            field_stats = {}
            total_completeness = 0

            for field in target_fields:
                populated_count = 0
                for breed in response.data:
                    value = breed.get(field)
                    if value is not None and value != '' and value != []:
                        populated_count += 1

                completeness = (populated_count / total_breeds) * 100
                field_stats[field] = {
                    'populated': populated_count,
                    'total': total_breeds,
                    'percentage': round(completeness, 1)
                }
                total_completeness += completeness

            overall_completeness = total_completeness / len(target_fields)

            return {
                'total_breeds': total_breeds,
                'overall_completeness': round(overall_completeness, 1),
                'field_stats': field_stats,
                'target_95_percent': 95.0,
                'remaining_to_target': round(95.0 - overall_completeness, 1)
            }

        except Exception as e:
            return {'error': f"Database error: {e}"}

    def display_status(self):
        """Display comprehensive status"""
        print("=" * 70)
        print(f"🐕 BREED SCRAPING PROGRESS MONITOR - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70)

        # Background processes
        print("\n📊 ACTIVE SCRAPING PROCESSES:")
        processes = self.check_background_processes()
        if 'error' in processes:
            print(f"❌ {processes['error']}")
        elif processes['total_processes'] == 0:
            print("✅ No active scraping processes")
        else:
            print(f"🔄 {processes['total_processes']} processes running:")
            for proc in processes['processes']:
                print(f"   • {proc['type']}")
                print(f"     PID: {proc['pid']} | CPU: {proc['cpu_percent']}% | Memory: {proc['memory_percent']}% | Runtime: {proc['runtime']}")

        # Log file status
        print("\n📄 LOG FILE STATUS:")
        log_status = self.get_log_status()
        for log_file, status in log_status.items():
            if status['exists']:
                if 'error' in status:
                    print(f"   ❌ {log_file}: Error - {status['error']}")
                else:
                    progress = status['progress']
                    status_emoji = {
                        'Completed': '✅',
                        'Running': '🔄',
                        'Error': '❌',
                        'Unknown': '❓'
                    }.get(progress['status'], '❓')

                    print(f"   {status_emoji} {log_file}: {progress['status']}")
                    print(f"      Size: {status['size_mb']}MB | Last: {status['last_modified']}")

                    if 'details' in progress and progress['details']:
                        details = progress['details']
                        if 'current' in details and 'total' in details:
                            print(f"      Progress: {details['current']}/{details['total']} ({details['percentage']}%)")
                        if 'last_action' in details:
                            print(f"      Last: {details['last_action']}")
            else:
                print(f"   ❌ {log_file}: File not found")

        # Database completeness
        print("\n💾 DATABASE COMPLETENESS:")
        db_stats = self.get_database_completeness()
        if 'error' in db_stats:
            print(f"❌ {db_stats['error']}")
        else:
            print(f"📈 Overall Completeness: {db_stats['overall_completeness']}%")
            print(f"🎯 Target: {db_stats['target_95_percent']}% (Remaining: {db_stats['remaining_to_target']}%)")
            print(f"📊 Total Breeds: {db_stats['total_breeds']}")

            # Show top gaps
            print("\n🎯 TOP COMPLETION GAPS:")
            field_stats = db_stats['field_stats']
            sorted_fields = sorted(field_stats.items(), key=lambda x: x[1]['percentage'])

            for field, stats in sorted_fields[:5]:
                gap = 100 - stats['percentage']
                gap_emoji = "🔴" if gap > 70 else "🟡" if gap > 40 else "🟢"
                print(f"   {gap_emoji} {field}: {stats['percentage']}% ({stats['populated']}/{stats['total']})")

        print("\n" + "=" * 70)
        print("💡 Run this script anytime to check progress: python3 monitor_scraping_progress.py")
        print("=" * 70)

if __name__ == "__main__":
    monitor = ScrapingProgressMonitor()
    monitor.display_status()