#!/usr/bin/env python3
"""
Fix remaining 5 stringified array issues in foods_published tables
"""

import pandas as pd
import json
import ast
from datetime import datetime
import shutil
from pathlib import Path

class RemainingIssuesFixer:
    def __init__(self):
        self.base_dir = Path('/Users/sergiubiris/Desktop/lupito-content')
        self.data_dir = self.base_dir / 'data'
        self.backup_dir = self.base_dir / 'backups' / f'remaining_fixes_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.array_columns = ['ingredients_tokens', 'available_countries', 'sources']
        self.fixes_applied = []
    
    def backup_file(self, file_path):
        """Create backup of file before modification"""
        if file_path.exists():
            backup_path = self.backup_dir / file_path.name
            shutil.copy2(file_path, backup_path)
            print(f"✓ Backed up {file_path.name}")
            return backup_path
        return None
    
    def is_stringified_array(self, val):
        """Check if value is a stringified array"""
        if pd.isna(val) or val == '' or val == '[]':
            return False
        
        if isinstance(val, str):
            # Check for JSON array pattern
            if val.startswith('[') and val.endswith(']'):
                return True
            # Check for Python list string representation
            if val.startswith("['") or val.startswith('["'):
                return True
        
        return False
    
    def fix_stringified_value(self, val):
        """Convert stringified array to proper format"""
        if pd.isna(val) or val == '' or val == '[]':
            return val
        
        try:
            # Try parsing as JSON
            if isinstance(val, str) and val.startswith('['):
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return str(parsed)
        except:
            pass
        
        try:
            # Try parsing with ast.literal_eval
            if isinstance(val, str):
                parsed = ast.literal_eval(val)
                if isinstance(parsed, list):
                    return str(parsed)
        except:
            pass
        
        return val
    
    def find_stringified_arrays(self, df, table_name):
        """Find all stringified arrays in dataframe"""
        issues = []
        
        for col in self.array_columns:
            if col in df.columns:
                for idx, val in df[col].items():
                    if self.is_stringified_array(val):
                        issues.append({
                            'table': table_name,
                            'column': col,
                            'row_index': idx,
                            'value': str(val)[:100]  # Sample for reporting
                        })
        
        return issues
    
    def fix_table(self, file_path):
        """Fix stringified arrays in a single table"""
        if not file_path.exists():
            print(f"⚠️ File not found: {file_path}")
            return 0
        
        print(f"\n📋 Processing {file_path.name}...")
        
        # Backup first
        self.backup_file(file_path)
        
        # Load data
        df = pd.read_csv(file_path)
        original_issues = self.find_stringified_arrays(df, file_path.name)
        
        if not original_issues:
            print(f"  ✓ No stringified arrays found")
            return 0
        
        print(f"  Found {len(original_issues)} stringified arrays")
        
        # Apply fixes
        fixes_count = 0
        for col in self.array_columns:
            if col in df.columns:
                for idx in df.index:
                    val = df.at[idx, col]
                    if self.is_stringified_array(val):
                        fixed_val = self.fix_stringified_value(val)
                        if fixed_val != val:
                            df.at[idx, col] = fixed_val
                            fixes_count += 1
                            self.fixes_applied.append({
                                'table': file_path.name,
                                'column': col,
                                'row': idx,
                                'before': str(val)[:50],
                                'after': str(fixed_val)[:50]
                            })
        
        # Save fixed data
        if fixes_count > 0:
            df.to_csv(file_path, index=False)
            print(f"  ✓ Applied {fixes_count} fixes")
        
        # Verify fixes
        df_after = pd.read_csv(file_path)
        remaining_issues = self.find_stringified_arrays(df_after, file_path.name)
        
        if remaining_issues:
            print(f"  ⚠️ {len(remaining_issues)} issues remain")
            for issue in remaining_issues[:3]:  # Show first 3
                print(f"    - {issue['column']}: row {issue['row_index']}")
        else:
            print(f"  ✓ All issues resolved")
        
        return fixes_count
    
    def generate_report(self):
        """Generate detailed report of fixes"""
        report_path = self.base_dir / 'reports' / 'REMAINING_FIXES.md'
        
        with open(report_path, 'w') as f:
            f.write("# REMAINING ISSUES FIX REPORT\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- Total fixes applied: {len(self.fixes_applied)}\n")
            f.write(f"- Tables processed: 2\n")
            f.write(f"- Backup location: {self.backup_dir}\n\n")
            
            if self.fixes_applied:
                f.write("## Fixes Applied\n\n")
                f.write("| Table | Column | Row | Before | After |\n")
                f.write("|-------|--------|-----|--------|-------|\n")
                
                for fix in self.fixes_applied[:10]:  # Show first 10
                    f.write(f"| {fix['table']} | {fix['column']} | {fix['row']} | {fix['before']} | {fix['after']} |\n")
                
                if len(self.fixes_applied) > 10:
                    f.write(f"\n... and {len(self.fixes_applied) - 10} more fixes\n")
            
            f.write("\n## Rollback Instructions\n\n")
            f.write("To rollback these changes:\n")
            f.write("```bash\n")
            f.write(f"cp {self.backup_dir}/*.csv data/\n")
            f.write("```\n")
        
        print(f"\n✓ Report saved to {report_path}")
    
    def run(self):
        """Execute remaining fixes"""
        print("🔧 Fixing Remaining Stringified Array Issues")
        print("=" * 50)
        
        # Target files with remaining issues
        target_files = [
            self.base_dir / 'reports' / 'MANUF' / 'PRODUCTION' / 'foods_published_prod.csv',
            self.base_dir / 'reports' / 'MANUF' / 'foods_published_v2.csv'
        ]
        
        total_fixes = 0
        for file_path in target_files:
            fixes = self.fix_table(file_path)
            total_fixes += fixes
        
        print(f"\n✅ Total fixes applied: {total_fixes}")
        
        # Generate report
        self.generate_report()
        
        # Final validation
        print("\n🔍 Final Validation:")
        remaining_total = 0
        for file_path in target_files:
            if file_path.exists():
                df = pd.read_csv(file_path)
                issues = self.find_stringified_arrays(df, file_path.name)
                if issues:
                    print(f"  ⚠️ {file_path.name}: {len(issues)} issues remain")
                    remaining_total += len(issues)
                else:
                    print(f"  ✓ {file_path.name}: Clean")
        
        if remaining_total == 0:
            print("\n🎉 SUCCESS: All stringified array issues resolved!")
        else:
            print(f"\n⚠️ WARNING: {remaining_total} issues could not be automatically fixed")
            print("Manual intervention may be required for edge cases")
        
        return remaining_total == 0

if __name__ == "__main__":
    fixer = RemainingIssuesFixer()
    success = fixer.run()
    exit(0 if success else 1)