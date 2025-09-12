#!/usr/bin/env python3
"""
Monitor all parallel scraping sessions
Shows real-time status of each session
"""

import subprocess
import time
from datetime import datetime

def check_gcs_activity():
    """Check recent GCS activity for all sessions"""
    try:
        # Get all folders for today
        today = datetime.now().strftime('%Y%m%d')
        result = subprocess.run([
            'gsutil', 'ls', f'gs://lupito-content-raw-eu/scraped/zooplus/{today}*/'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            folders = result.stdout.strip().split('\n')
            print(f"📁 Active GCS Sessions ({len(folders)}):")
            
            for folder in folders:
                folder_name = folder.split('/')[-2]
                
                # Count files in each folder
                count_result = subprocess.run([
                    'gsutil', 'ls', folder + '*.json', '|', 'wc', '-l'
                ], shell=True, capture_output=True, text=True)
                
                try:
                    file_count = int(count_result.stdout.strip())
                except:
                    file_count = '?'
                
                session_type = "Unknown"
                if '_us' in folder_name:
                    session_type = "🇺🇸 US"
                elif '_gb' in folder_name:
                    session_type = "🇬🇧 UK"
                elif '_de' in folder_name:
                    session_type = "🇩🇪 DE"
                elif '_ca' in folder_name:
                    session_type = "🇨🇦 CA"
                
                print(f"  {session_type} {folder_name}: {file_count} files")
        else:
            print("📁 No active sessions found")
            
    except Exception as e:
        print(f"Error checking GCS: {e}")

def check_running_processes():
    """Check running parallel scraper processes"""
    try:
        result = subprocess.run([
            'ps', 'aux'
        ], capture_output=True, text=True)
        
        parallel_processes = []
        for line in result.stdout.split('\n'):
            if 'parallel_scraper.py' in line and 'grep' not in line:
                parallel_processes.append(line)
        
        print(f"\n🚀 Running Parallel Scrapers ({len(parallel_processes)}):")
        for process in parallel_processes:
            parts = process.split()
            if len(parts) > 10:
                session = parts[-1]  # Last argument is session name
                cpu = parts[2]
                memory = parts[3]
                print(f"  Session '{session}': CPU {cpu}%, Memory {memory}%")
                
    except Exception as e:
        print(f"Error checking processes: {e}")

def main():
    """Monitor parallel sessions"""
    print("🔍 PARALLEL SCRAPING MONITOR")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    check_running_processes()
    check_gcs_activity()
    
    print("\n💡 Tip: Run this script periodically to monitor progress")
    print("   python scripts/monitor_parallel_sessions.py")

if __name__ == "__main__":
    main()