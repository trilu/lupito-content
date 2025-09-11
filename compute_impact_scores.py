#!/usr/bin/env python3
"""
Compute coverage baseline and identify next 5 brands to fix by impact
Impact score = sku_count * (1 - completion_pct)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json

class ImpactAnalyzer:
    def __init__(self):
        self.harvest_dir = Path("reports/MANUF/PILOT/harvests")
        self.output_dir = Path("reports")
        self.gaps_dir = Path("reports/gaps")
        self.gaps_dir.mkdir(parents=True, exist_ok=True)
        
        # All brands we have data for
        self.all_brands = {
            'brit': 73,
            'alpha': 53,
            'briantos': 46,
            'bozita': 34,
            'belcando': 34,
            'acana': 32,
            'advance': 28,
            'almo_nature': 26,
            'animonda': 25,
            'applaws': 24,
            'arden_grange': 23,
            'bosch': 22,
            'burns': 21,
            'carnilove': 20,
            'concept_for_life': 19
        }
        
        # Brands with harvest data
        self.harvested_brands = ['brit', 'alpha', 'briantos', 'bozita', 'belcando']
        
    def load_brand_data(self, brand_slug):
        """Load harvest data for a brand if available"""
        brand_files = list(self.harvest_dir.glob(f"{brand_slug}_pilot_*.csv"))
        if brand_files:
            return pd.read_csv(brand_files[0])
        return None
    
    def calculate_coverage(self, df):
        """Calculate coverage for key fields"""
        if df is None or df.empty:
            return {
                'form_cov': 0.0,
                'life_stage_cov': 0.0,
                'ingredients_cov': 0.0,
                'kcal_cov': 0.0,
                'price_cov': 0.0
            }
        
        total = len(df)
        return {
            'form_cov': round(df['form'].notna().sum() / total * 100, 1),
            'life_stage_cov': round(df['life_stage'].notna().sum() / total * 100, 1),
            'ingredients_cov': round(df['ingredients'].notna().sum() / total * 100, 1),
            'kcal_cov': round(df['kcal_per_100g'].notna().sum() / total * 100, 1) if 'kcal_per_100g' in df else 0.0,
            'price_cov': round(df['price'].notna().sum() / total * 100, 1)
        }
    
    def identify_gaps(self, df, brand_slug):
        """Identify SKUs with missing fields"""
        if df is None or df.empty:
            return pd.DataFrame()
        
        # Check for gaps in key fields
        gaps_mask = (
            df['form'].isna() |
            df['life_stage'].isna() |
            df['ingredients'].isna() |
            (df['kcal_per_100g'].isna() if 'kcal_per_100g' in df else False) |
            df['price'].isna()
        )
        
        gaps_df = df[gaps_mask].copy()
        
        if not gaps_df.empty:
            # Add gap indicators
            gaps_df['missing_form'] = gaps_df['form'].isna()
            gaps_df['missing_life_stage'] = gaps_df['life_stage'].isna()
            gaps_df['missing_ingredients'] = gaps_df['ingredients'].isna()
            gaps_df['missing_kcal'] = gaps_df['kcal_per_100g'].isna() if 'kcal_per_100g' in gaps_df else True
            gaps_df['missing_price'] = gaps_df['price'].isna()
            
            # Count gaps per SKU
            gaps_df['gap_count'] = (
                gaps_df['missing_form'].astype(int) +
                gaps_df['missing_life_stage'].astype(int) +
                gaps_df['missing_ingredients'].astype(int) +
                gaps_df['missing_kcal'].astype(int) +
                gaps_df['missing_price'].astype(int)
            )
            
            # Select relevant columns for export
            export_cols = ['product_id', 'product_name', 'brand_slug', 
                          'missing_form', 'missing_life_stage', 'missing_ingredients',
                          'missing_kcal', 'missing_price', 'gap_count']
            
            return gaps_df[export_cols]
        
        return pd.DataFrame()
    
    def compute_impact_scores(self):
        """Compute impact scores for all brands"""
        brand_metrics = []
        
        for brand_slug, sku_count in self.all_brands.items():
            # Load data if available
            if brand_slug in self.harvested_brands:
                df = self.load_brand_data(brand_slug)
                coverage = self.calculate_coverage(df)
                
                # Calculate completion percentage
                completion_pct = round((
                    coverage['form_cov'] +
                    coverage['life_stage_cov'] +
                    coverage['ingredients_cov'] +
                    coverage['kcal_cov'] +
                    coverage['price_cov']
                ) / 5, 1)
                
                # Identify specific gaps
                gaps = []
                if coverage['form_cov'] < 95:
                    gaps.append(f"form({coverage['form_cov']}%)")
                if coverage['life_stage_cov'] < 95:
                    gaps.append(f"life_stage({coverage['life_stage_cov']}%)")
                if coverage['ingredients_cov'] < 85:
                    gaps.append(f"ingredients({coverage['ingredients_cov']}%)")
                if coverage['kcal_cov'] < 85:
                    gaps.append(f"kcal({coverage['kcal_cov']}%)")
                if coverage['price_cov'] < 70:
                    gaps.append(f"price({coverage['price_cov']}%)")
                
            else:
                # No data yet
                coverage = self.calculate_coverage(None)
                completion_pct = 0.0
                gaps = ['no_data']
            
            # Calculate impact score
            # Higher score = more SKUs with lower completion
            impact_score = round(sku_count * (100 - completion_pct) / 100, 1)
            
            brand_metrics.append({
                'brand': brand_slug,
                'sku_count': sku_count,
                'form_cov': coverage['form_cov'],
                'life_stage_cov': coverage['life_stage_cov'],
                'ingredients_cov': coverage['ingredients_cov'],
                'kcal_cov': coverage['kcal_cov'],
                'price_cov': coverage['price_cov'],
                'completion_pct': completion_pct,
                'gaps': ', '.join(gaps) if gaps else 'none',
                'impact_score': impact_score,
                'has_data': brand_slug in self.harvested_brands
            })
        
        # Sort by impact score (descending)
        brand_metrics.sort(key=lambda x: x['impact_score'], reverse=True)
        
        return brand_metrics
    
    def export_gap_csvs(self, top_brands):
        """Export gap CSVs for top 5 brands"""
        exported = []
        
        for brand_info in top_brands[:5]:
            brand_slug = brand_info['brand']
            
            if brand_info['has_data']:
                df = self.load_brand_data(brand_slug)
                gaps_df = self.identify_gaps(df, brand_slug)
                
                if not gaps_df.empty:
                    output_file = self.gaps_dir / f"{brand_slug}_gaps.csv"
                    gaps_df.to_csv(output_file, index=False)
                    exported.append({
                        'brand': brand_slug,
                        'gaps_count': len(gaps_df),
                        'file': output_file
                    })
                    print(f"  Exported {len(gaps_df)} gaps for {brand_slug}")
            else:
                print(f"  No data for {brand_slug} - needs initial harvest")
        
        return exported
    
    def generate_impact_queue_report(self, brand_metrics):
        """Generate FOODS_IMPACT_QUEUE.md report"""
        
        report = f"""# FOODS IMPACT QUEUE

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 IMPACT SCORING METHODOLOGY

**Impact Score = SKU Count × (100 - Completion %)**

Higher scores indicate brands with:
- Many products (high SKU count)
- Poor data quality (low completion %)

## 🎯 TOP 5 BRANDS TO FIX (By Impact)

| Rank | Brand | SKUs | Completion % | Gaps | Impact Score | Priority |
|------|-------|------|--------------|------|--------------|----------|
"""
        
        # Add top 5 to fix
        for i, brand in enumerate(brand_metrics[:5], 1):
            priority = "🔴 HIGH" if brand['impact_score'] > 30 else "🟡 MEDIUM"
            gaps_summary = brand['gaps'] if brand['gaps'] != 'no_data' else '**needs harvest**'
            
            report += f"| {i} | **{brand['brand']}** | {brand['sku_count']} | "
            report += f"{brand['completion_pct']}% | {gaps_summary} | "
            report += f"**{brand['impact_score']}** | {priority} |\n"
        
        report += f"""

## 📈 FULL BRAND RANKING

| Brand | SKUs | Form | Life Stage | Ingredients | Kcal | Price | Completion | Impact |
|-------|------|------|------------|-------------|------|-------|------------|--------|
"""
        
        for brand in brand_metrics:
            status = "✅" if brand['completion_pct'] >= 85 else "🔶" if brand['completion_pct'] >= 70 else "❌"
            
            report += f"| {brand['brand']} | {brand['sku_count']} | "
            report += f"{brand['form_cov']}% | {brand['life_stage_cov']}% | "
            report += f"{brand['ingredients_cov']}% | {brand['kcal_cov']}% | "
            report += f"{brand['price_cov']}% | {brand['completion_pct']}% {status} | "
            report += f"{brand['impact_score']} |\n"
        
        # Summary statistics
        harvested = [b for b in brand_metrics if b['has_data']]
        unharvested = [b for b in brand_metrics if not b['has_data']]
        
        report += f"""

## 📊 COVERAGE SUMMARY

### Harvested Brands ({len(harvested)})
- **Average Completion**: {np.mean([b['completion_pct'] for b in harvested]):.1f}%
- **Total SKUs**: {sum(b['sku_count'] for b in harvested)}
- **Average Impact**: {np.mean([b['impact_score'] for b in harvested]):.1f}

### Unharvested Brands ({len(unharvested)})
- **Total SKUs**: {sum(b['sku_count'] for b in unharvested)}
- **Total Impact**: {sum(b['impact_score'] for b in unharvested):.1f}

## 🔧 RECOMMENDED ACTIONS

### Immediate (Top 5 Priority)
"""
        
        for i, brand in enumerate(brand_metrics[:5], 1):
            if brand['has_data']:
                if 'form' in brand['gaps']:
                    report += f"{i}. **{brand['brand']}**: Fix form detection (currently {brand['form_cov']}%)\n"
                elif 'life_stage' in brand['gaps']:
                    report += f"{i}. **{brand['brand']}**: Fix life_stage detection (currently {brand['life_stage_cov']}%)\n"
                elif 'kcal' in brand['gaps']:
                    report += f"{i}. **{brand['brand']}**: Calculate missing kcal values\n"
                else:
                    report += f"{i}. **{brand['brand']}**: General field improvements needed\n"
            else:
                report += f"{i}. **{brand['brand']}**: Initial harvest required ({brand['sku_count']} SKUs)\n"
        
        report += f"""

### Gap Files Exported
Check `reports/gaps/` directory for detailed gap analysis:
"""
        
        for brand in brand_metrics[:5]:
            if brand['has_data']:
                report += f"- `{brand['brand']}_gaps.csv` - SKUs with missing fields\n"
        
        report += f"""

## 🎯 SUCCESS CRITERIA

Brands are production-ready when:
- Form coverage ≥ 95%
- Life stage coverage ≥ 95%
- Ingredients coverage ≥ 85%
- Kcal coverage ≥ 85%
- Price coverage ≥ 70%

## 📝 NEXT STEPS

1. Fix gaps for high-impact brands with existing data
2. Begin harvesting top unharvested brands
3. Apply learned patterns to improve extraction
4. Re-calculate impact scores weekly

---

**Note**: Focus on brands with impact scores > 10 for maximum efficiency
"""
        
        return report

def main():
    analyzer = ImpactAnalyzer()
    
    print("="*60)
    print("COMPUTING IMPACT SCORES")
    print("="*60)
    
    # Compute impact scores
    brand_metrics = analyzer.compute_impact_scores()
    
    print(f"\nAnalyzed {len(brand_metrics)} brands")
    
    # Export gap CSVs for top 5
    print("\nExporting gap CSVs for top 5 brands:")
    exported = analyzer.export_gap_csvs(brand_metrics)
    
    # Generate report
    report = analyzer.generate_impact_queue_report(brand_metrics)
    report_file = analyzer.output_dir / "FOODS_IMPACT_QUEUE.md"
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Report saved to: {report_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("TOP 5 BRANDS BY IMPACT")
    print("="*60)
    
    for i, brand in enumerate(brand_metrics[:5], 1):
        print(f"{i}. {brand['brand'].upper()}")
        print(f"   SKUs: {brand['sku_count']}")
        print(f"   Completion: {brand['completion_pct']}%")
        print(f"   Impact Score: {brand['impact_score']}")
        print(f"   Gaps: {brand['gaps'] if brand['gaps'] else 'None'}")
        print()
    
    print("="*60)

if __name__ == "__main__":
    main()