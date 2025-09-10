#!/usr/bin/env python3
"""
Utility script to manage brand allowlist
Provides CLI interface for common allowlist operations
"""

import argparse
from datetime import datetime
from pathlib import Path
import json

class AllowlistManager:
    def __init__(self):
        self.changelog_path = Path("docs/ALLOWLIST_CHANGELOG.md")
        self.status_path = Path("reports/ALLOWLIST_STATUS.md")
        
        # Current allowlist state (would come from DB in production)
        self.allowlist = {
            'ACTIVE': ['briantos', 'bozita'],
            'PENDING': ['brit', 'alpha', 'belcando'],
            'PAUSED': [],
            'REMOVED': []
        }
    
    def add_brand(self, brand_slug, status, changed_by, reason, coverage):
        """Add a brand to the allowlist"""
        print(f"Adding {brand_slug} with status {status}")
        
        # Add to appropriate list
        if brand_slug not in self.get_all_brands():
            self.allowlist[status].append(brand_slug)
            
            # Log the change
            self.log_change('ADD', brand_slug, status, changed_by, reason, coverage)
            print(f"✅ Added {brand_slug} to {status} list")
        else:
            print(f"⚠️ {brand_slug} already in allowlist")
    
    def promote_brand(self, brand_slug, changed_by, reason):
        """Promote a PENDING brand to ACTIVE"""
        if brand_slug in self.allowlist['PENDING']:
            self.allowlist['PENDING'].remove(brand_slug)
            self.allowlist['ACTIVE'].append(brand_slug)
            
            self.log_change('PROMOTE', brand_slug, 'ACTIVE', changed_by, reason, {})
            print(f"✅ Promoted {brand_slug} to ACTIVE")
        else:
            print(f"⚠️ {brand_slug} not in PENDING list")
    
    def pause_brand(self, brand_slug, changed_by, reason):
        """Pause an ACTIVE brand"""
        if brand_slug in self.allowlist['ACTIVE']:
            self.allowlist['ACTIVE'].remove(brand_slug)
            self.allowlist['PAUSED'].append(brand_slug)
            
            self.log_change('PAUSE', brand_slug, 'PAUSED', changed_by, reason, {})
            print(f"⏸️ Paused {brand_slug}")
        else:
            print(f"⚠️ {brand_slug} not in ACTIVE list")
    
    def remove_brand(self, brand_slug, changed_by, reason):
        """Remove a brand from allowlist"""
        for status in ['ACTIVE', 'PENDING', 'PAUSED']:
            if brand_slug in self.allowlist[status]:
                self.allowlist[status].remove(brand_slug)
                self.allowlist['REMOVED'].append(brand_slug)
                
                self.log_change('REMOVE', brand_slug, 'REMOVED', changed_by, reason, {})
                print(f"❌ Removed {brand_slug}")
                return
        
        print(f"⚠️ {brand_slug} not found in allowlist")
    
    def get_all_brands(self):
        """Get all brands across all statuses"""
        all_brands = []
        for status_list in self.allowlist.values():
            all_brands.extend(status_list)
        return all_brands
    
    def log_change(self, action, brand_slug, status, changed_by, reason, coverage):
        """Log change to changelog"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        
        entry = f"""
## {timestamp}
**Action**: {action}  
**Brand**: {brand_slug}  
**Status**: {status}  
**Changed By**: {changed_by}  
**Reason**: {reason}  
"""
        
        if coverage:
            entry += f"**Coverage**: Form {coverage.get('form', 'N/A')}%, Life Stage {coverage.get('life_stage', 'N/A')}%, Ingredients {coverage.get('ingredients', 'N/A')}%  \n"
        
        # Append to changelog
        if self.changelog_path.exists():
            content = self.changelog_path.read_text()
            # Insert after the header but before existing entries
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                new_content = parts[0] + '---\n' + entry + '\n---\n' + parts[2]
            else:
                new_content = content + '\n' + entry
            
            self.changelog_path.write_text(new_content)
            print(f"📝 Logged change to {self.changelog_path}")
    
    def show_status(self):
        """Display current allowlist status"""
        print("\n" + "="*60)
        print("CURRENT ALLOWLIST STATUS")
        print("="*60)
        
        for status, brands in self.allowlist.items():
            if brands:
                print(f"\n{status} ({len(brands)} brands):")
                for brand in sorted(brands):
                    print(f"  - {brand}")
        
        print("\n" + "="*60)
        print(f"Total brands: {len(self.get_all_brands())}")
        print("="*60)
    
    def generate_sql(self):
        """Generate SQL statements for current allowlist"""
        print("\n-- SQL to sync allowlist table")
        print("-- " + "="*50)
        
        for status, brands in self.allowlist.items():
            if status == 'REMOVED':
                continue
                
            for brand in brands:
                print(f"""
INSERT INTO brand_allowlist (brand_slug, status, added_by, reason)
VALUES ('{brand}', '{status}', 'System', 'Synced from script')
ON CONFLICT (brand_slug) 
DO UPDATE SET status = '{status}', updated_at = CURRENT_TIMESTAMP;""")
        
        print("\n-- Verify with: SELECT brand_slug, status FROM brand_allowlist ORDER BY status, brand_slug;")

def main():
    parser = argparse.ArgumentParser(description='Manage brand allowlist')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add brand to allowlist')
    add_parser.add_argument('brand', help='Brand slug')
    add_parser.add_argument('--status', default='PENDING', choices=['ACTIVE', 'PENDING'])
    add_parser.add_argument('--by', default='CLI User', help='Changed by')
    add_parser.add_argument('--reason', default='Added via CLI', help='Reason')
    
    # Promote command
    promote_parser = subparsers.add_parser('promote', help='Promote brand to ACTIVE')
    promote_parser.add_argument('brand', help='Brand slug')
    promote_parser.add_argument('--by', default='CLI User', help='Changed by')
    promote_parser.add_argument('--reason', default='Promoted via CLI', help='Reason')
    
    # Pause command
    pause_parser = subparsers.add_parser('pause', help='Pause brand')
    pause_parser.add_argument('brand', help='Brand slug')
    pause_parser.add_argument('--by', default='CLI User', help='Changed by')
    pause_parser.add_argument('--reason', default='Paused via CLI', help='Reason')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove brand')
    remove_parser.add_argument('brand', help='Brand slug')
    remove_parser.add_argument('--by', default='CLI User', help='Changed by')
    remove_parser.add_argument('--reason', default='Removed via CLI', help='Reason')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current status')
    
    # SQL command
    sql_parser = subparsers.add_parser('sql', help='Generate SQL statements')
    
    args = parser.parse_args()
    
    manager = AllowlistManager()
    
    if args.command == 'add':
        manager.add_brand(args.brand, args.status, args.by, args.reason, {})
    elif args.command == 'promote':
        manager.promote_brand(args.brand, args.by, args.reason)
    elif args.command == 'pause':
        manager.pause_brand(args.brand, args.by, args.reason)
    elif args.command == 'remove':
        manager.remove_brand(args.brand, args.by, args.reason)
    elif args.command == 'status':
        manager.show_status()
    elif args.command == 'sql':
        manager.generate_sql()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()