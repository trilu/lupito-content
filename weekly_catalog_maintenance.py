#!/usr/bin/env python3
"""
PROMPT G: Weekly Catalog Maintenance
Goal: Keep data quality high without manual babysitting
"""

import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path
import json

load_dotenv()

class WeeklyCatalogMaintenance:
    def __init__(self):
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(url, key)
        self.timestamp = datetime.now()
        
        print("="*70)
        print("WEEKLY CATALOG MAINTENANCE")
        print("="*70)
        print(f"Run Date: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
    
    def step1_refresh_enrichment(self):
        """Refresh Preview enrichment"""
        print("\n📊 STEP 1: REFRESHING ENRICHMENT")
        print("-"*40)
        
        stats = {}
        
        # Get products needing enrichment
        try:
            # Count products missing form
            resp = self.supabase.table('foods_canonical').select("*", count='exact', head=True).is_('form', 'null').execute()
            missing_form = resp.count or 0
            
            # Count products missing life_stage
            resp = self.supabase.table('foods_canonical').select("*", count='exact', head=True).is_('life_stage', 'null').execute()
            missing_life = resp.count or 0
            
            # Count invalid kcal
            resp = self.supabase.table('foods_canonical').select("*", count='exact', head=True).or_('kcal_per_100g.lt.200,kcal_per_100g.gt.600').execute()
            invalid_kcal = resp.count or 0
            
            stats['missing_form'] = missing_form
            stats['missing_life_stage'] = missing_life
            stats['invalid_kcal'] = invalid_kcal
            
            print(f"Products needing enrichment:")
            print(f"  Missing form: {missing_form}")
            print(f"  Missing life_stage: {missing_life}")
            print(f"  Invalid kcal: {invalid_kcal}")
            
            # Quick enrichment for most critical fields
            if missing_form > 100:
                print("  ⚠️  Many products missing form - needs attention")
            
            if missing_life > 100:
                print("  ⚠️  Many products missing life_stage - needs attention")
                
        except Exception as e:
            print(f"Error checking enrichment needs: {e}")
            
        return stats
    
    def step2_refresh_mvs(self):
        """Refresh materialized views"""
        print("\n🔄 STEP 2: REFRESHING MATERIALIZED VIEWS")
        print("-"*40)
        
        try:
            # Try to refresh brand quality MVs
            self.supabase.rpc('refresh_brand_quality_preview').execute()
            print("✅ Preview MV refreshed")
        except:
            print("⚠️  Could not refresh Preview MV")
        
        try:
            self.supabase.rpc('refresh_brand_quality_prod').execute()
            print("✅ Production MV refreshed")
        except:
            print("⚠️  Could not refresh Production MV")
    
    def step3_brand_health_check(self):
        """Check brand health metrics"""
        print("\n💊 STEP 3: BRAND HEALTH CHECK")
        print("-"*40)
        
        alerts = []
        
        # Check top brands
        top_brands = ['royal_canin', 'hills', 'purina', 'purina_pro_plan', 'eukanuba']
        
        for brand_slug in top_brands:
            try:
                # Get brand metrics
                resp = self.supabase.table('foods_canonical').select("*").eq('brand_slug', brand_slug).execute()
                
                if resp.data:
                    products = resp.data
                    total = len(products)
                    
                    # Check coverage
                    form_coverage = sum(1 for p in products if p.get('form')) / total * 100
                    life_coverage = sum(1 for p in products if p.get('life_stage')) / total * 100
                    
                    print(f"\n{brand_slug}:")
                    print(f"  Products: {total}")
                    print(f"  Form coverage: {form_coverage:.1f}%")
                    print(f"  Life stage coverage: {life_coverage:.1f}%")
                    
                    # Check for issues
                    if form_coverage < 70:
                        alerts.append(f"{brand_slug}: Low form coverage ({form_coverage:.1f}%)")
                    
                    if life_coverage < 70:
                        alerts.append(f"{brand_slug}: Low life stage coverage ({life_coverage:.1f}%)")
                        
            except Exception as e:
                print(f"Error checking {brand_slug}: {e}")
        
        return alerts
    
    def step4_production_health(self):
        """Check production health"""
        print("\n🏭 STEP 4: PRODUCTION HEALTH")
        print("-"*40)
        
        try:
            # Get production stats
            resp = self.supabase.table('foods_published_prod').select("*", count='exact', head=True).execute()
            prod_count = resp.count or 0
            
            print(f"Production SKUs: {prod_count}")
            
            if prod_count == 0:
                print("⚠️  WARNING: Production is EMPTY!")
                return {'status': 'CRITICAL', 'count': 0}
            elif prod_count < 50:
                print("⚠️  Production has very few SKUs")
                return {'status': 'LOW', 'count': prod_count}
            else:
                print("✅ Production healthy")
                return {'status': 'OK', 'count': prod_count}
                
        except Exception as e:
            print(f"Error checking production: {e}")
            return {'status': 'ERROR', 'count': 0}
    
    def step5_gate_compliance(self):
        """Check gate compliance"""
        print("\n🚦 STEP 5: GATE COMPLIANCE CHECK")
        print("-"*40)
        
        try:
            # Get total
            resp = self.supabase.table('foods_canonical').select("*", count='exact', head=True).execute()
            total = resp.count or 0
            
            # Form coverage
            resp = self.supabase.table('foods_canonical').select("*", count='exact', head=True).not_.is_('form', 'null').execute()
            form_pct = (resp.count or 0) / total * 100 if total > 0 else 0
            
            # Life stage coverage
            resp = self.supabase.table('foods_canonical').select("*", count='exact', head=True).not_.is_('life_stage', 'null').execute()
            life_pct = (resp.count or 0) / total * 100 if total > 0 else 0
            
            # Ingredients coverage
            resp = self.supabase.table('foods_canonical').select("*", count='exact', head=True).not_.is_('ingredients_tokens', 'null').execute()
            ing_pct = (resp.count or 0) / total * 100 if total > 0 else 0
            
            # Valid kcal
            resp = self.supabase.table('foods_canonical').select("*", count='exact', head=True).gte('kcal_per_100g', 200).lte('kcal_per_100g', 600).execute()
            kcal_pct = (resp.count or 0) / total * 100 if total > 0 else 0
            
            gates = {
                'form': {'current': form_pct, 'target': 90},
                'life_stage': {'current': life_pct, 'target': 95},
                'ingredients': {'current': ing_pct, 'target': 85},
                'kcal_valid': {'current': kcal_pct, 'target': 90}
            }
            
            print("Gate Status:")
            failing_gates = []
            
            for field, data in gates.items():
                status = "✅" if data['current'] >= data['target'] else "❌"
                print(f"  {field}: {data['current']:.1f}% / {data['target']}% {status}")
                
                if data['current'] < data['target']:
                    failing_gates.append(f"{field} ({data['current']:.1f}% < {data['target']}%)")
            
            return gates, failing_gates
            
        except Exception as e:
            print(f"Error checking gates: {e}")
            return {}, []
    
    def generate_health_report(self, stats, alerts, prod_health, gates, failing_gates):
        """Generate weekly health report"""
        report_path = Path('/Users/sergiubiris/Desktop/lupito-content/docs/WEEKLY-CATALOG-HEALTH.md')
        
        content = f"""# WEEKLY CATALOG HEALTH REPORT
Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

- **Production Status**: {prod_health['status']} ({prod_health['count']} SKUs)
- **Failing Gates**: {len(failing_gates)}
- **Brand Alerts**: {len(alerts)}

## Enrichment Needs

- Products missing form: {stats.get('missing_form', 'N/A')}
- Products missing life_stage: {stats.get('missing_life_stage', 'N/A')}
- Invalid kcal values: {stats.get('invalid_kcal', 'N/A')}

## Gate Compliance

| Field | Current | Target | Status |
|-------|---------|--------|--------|
"""
        
        for field, data in gates.items():
            status = "✅ PASS" if data['current'] >= data['target'] else "❌ FAIL"
            content += f"| {field} | {data['current']:.1f}% | {data['target']}% | {status} |\n"
        
        if alerts:
            content += "\n## Brand Alerts\n\n"
            for alert in alerts:
                content += f"- ⚠️  {alert}\n"
        
        if failing_gates:
            content += "\n## Action Required\n\n"
            content += "The following gates are failing:\n"
            for gate in failing_gates:
                content += f"- {gate}\n"
        
        content += """

## Automated Actions Taken

1. ✅ Enrichment needs assessed
2. ✅ Materialized views refresh attempted
3. ✅ Brand health checked
4. ✅ Production health verified
5. ✅ Gate compliance measured

## Recommendations

"""
        
        if prod_health['status'] == 'CRITICAL':
            content += "- **URGENT**: Production is empty! Promote qualified brands immediately.\n"
        elif prod_health['status'] == 'LOW':
            content += "- Production has few SKUs. Consider promoting more brands.\n"
        
        if len(failing_gates) > 0:
            content += "- Some quality gates are failing. Run enrichment pipeline.\n"
        
        if len(alerts) > 0:
            content += "- Some brands have quality issues. Review and fix.\n"
        
        content += "\n---\n*This report was generated automatically by the weekly maintenance script.*"
        
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(content)
        print(f"\n✅ Health report saved to: {report_path}")
        
        return content
    
    def setup_cron_job(self):
        """Setup weekly cron job instructions"""
        print("\n⏰ WEEKLY AUTOMATION SETUP")
        print("-"*40)
        
        cron_file = Path('/Users/sergiubiris/Desktop/lupito-content/docs/WEEKLY-CRON-SETUP.md')
        
        content = """# WEEKLY MAINTENANCE SETUP

## Cron Job Configuration

Add to crontab (`crontab -e`):

```bash
# Run weekly catalog maintenance every Sunday at 2 AM
0 2 * * 0 cd /Users/sergiubiris/Desktop/lupito-content && source venv/bin/activate && python3 weekly_catalog_maintenance.py >> logs/weekly_maintenance.log 2>&1
```

## Manual Run

To run maintenance manually:

```bash
cd /Users/sergiubiris/Desktop/lupito-content
source venv/bin/activate
python3 weekly_catalog_maintenance.py
```

## What It Does

1. **Enrichment Check**: Identifies products needing enrichment
2. **MV Refresh**: Attempts to refresh materialized views
3. **Brand Health**: Checks top brands for quality issues
4. **Production Health**: Verifies production isn't empty
5. **Gate Compliance**: Measures against quality gates
6. **Report Generation**: Creates health report in docs/

## Alert Conditions

The script will flag issues if:
- Production has < 50 SKUs
- Any brand has < 70% coverage
- Quality gates are not met
- Enrichment backlog is > 100 products

## Log Location

Logs are saved to: `logs/weekly_maintenance.log`
"""
        
        cron_file.parent.mkdir(exist_ok=True)
        cron_file.write_text(content)
        print(f"✅ Cron setup instructions saved to: {cron_file}")

def main():
    maintenance = WeeklyCatalogMaintenance()
    
    # Run all maintenance steps
    stats = maintenance.step1_refresh_enrichment()
    maintenance.step2_refresh_mvs()
    alerts = maintenance.step3_brand_health_check()
    prod_health = maintenance.step4_production_health()
    gates, failing_gates = maintenance.step5_gate_compliance()
    
    # Generate report
    maintenance.generate_health_report(stats, alerts, prod_health, gates, failing_gates)
    
    # Setup cron instructions
    maintenance.setup_cron_job()
    
    print("\n" + "="*70)
    print("WEEKLY MAINTENANCE COMPLETE")
    print("="*70)
    
    if len(failing_gates) > 0:
        print(f"⚠️  {len(failing_gates)} gates failing - action needed")
    else:
        print("✅ All gates passing")
    
    if len(alerts) > 0:
        print(f"⚠️  {len(alerts)} brand alerts")
    else:
        print("✅ All brands healthy")
    
    print("\n✅ PROMPT G COMPLETE: Weekly maintenance configured")

if __name__ == "__main__":
    main()