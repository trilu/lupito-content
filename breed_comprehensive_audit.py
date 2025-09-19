#!/usr/bin/env python3
"""
Comprehensive Breed Data Audit Script
Analyzes all breed tables and generates detailed quality report
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from collections import Counter, defaultdict
from dotenv import load_dotenv
from supabase import create_client
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BreedComprehensiveAudit:
    def __init__(self):
        load_dotenv()
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.report = []
        self.stats = defaultdict(dict)

    def log_section(self, title, content=""):
        """Add section to report"""
        separator = "=" * 60
        self.report.append(f"\n{separator}")
        self.report.append(title)
        self.report.append(separator)
        if content:
            self.report.append(content)
        logger.info(f"Section: {title}")

    def analyze_breeds_published(self):
        """Analyze the main breeds_published view"""
        self.log_section("BREEDS_PUBLISHED ANALYSIS")

        # Fetch all data
        response = self.supabase.table('breeds_published').select('*').execute()
        df = pd.DataFrame(response.data)

        total_breeds = len(df)
        self.stats['breeds_published']['total'] = total_breeds

        # Field coverage analysis
        coverage = {}
        for col in df.columns:
            non_null = df[col].notna().sum()
            coverage[col] = {
                'count': non_null,
                'percentage': (non_null / total_breeds) * 100
            }

        self.stats['breeds_published']['coverage'] = coverage

        # Size distribution
        size_dist = df['size_category'].value_counts().to_dict()
        self.stats['breeds_published']['size_distribution'] = size_dist

        # Energy distribution (instead of activity_baseline)
        if 'energy' in df.columns:
            energy_dist = df['energy'].value_counts().to_dict()
            self.stats['breeds_published']['energy_distribution'] = energy_dist
        else:
            energy_dist = {}

        # Weight statistics (using actual column names)
        weight_stats = {
            'min_weight_range': df['adult_weight_min_kg'].min() if 'adult_weight_min_kg' in df.columns else None,
            'max_weight_range': df['adult_weight_max_kg'].max() if 'adult_weight_max_kg' in df.columns else None,
            'avg_weight': df['adult_weight_avg_kg'].mean() if 'adult_weight_avg_kg' in df.columns else None,
            'missing_weight': df['adult_weight_min_kg'].isna().sum() if 'adult_weight_min_kg' in df.columns else 0
        }
        self.stats['breeds_published']['weight_stats'] = weight_stats

        # Age boundaries statistics
        age_stats = {
            'growth_end_avg': df['growth_end_months'].mean(),
            'senior_start_avg': df['senior_start_months'].mean(),
            'growth_end_min': df['growth_end_months'].min(),
            'growth_end_max': df['growth_end_months'].max(),
            'senior_start_min': df['senior_start_months'].min(),
            'senior_start_max': df['senior_start_months'].max()
        }
        self.stats['breeds_published']['age_stats'] = age_stats

        # Energy values distribution (if exists)
        if 'energy' in df.columns:
            energy_unique = df['energy'].value_counts()
            self.stats['breeds_published']['energy_values'] = energy_unique.to_dict()
        else:
            self.stats['breeds_published']['energy_values'] = {}

        # Report summary
        report_text = f"""
Total Breeds: {total_breeds}

Field Coverage:
"""
        for field, data in sorted(coverage.items(), key=lambda x: x[1]['percentage'], reverse=True)[:10]:
            report_text += f"  {field}: {data['percentage']:.1f}% ({data['count']}/{total_breeds})\n"

        report_text += f"""
Size Distribution:
  XS: {size_dist.get('xs', 0)} breeds
  S:  {size_dist.get('s', 0)} breeds
  M:  {size_dist.get('m', 0)} breeds
  L:  {size_dist.get('l', 0)} breeds
  XL: {size_dist.get('xl', 0)} breeds

Energy Distribution:
  Low:       {energy_dist.get('low', 0)} breeds
  Moderate:  {energy_dist.get('moderate', 0)} breeds
  High:      {energy_dist.get('high', 0)} breeds
  Very High: {energy_dist.get('very_high', 0)} breeds

Weight Coverage: {coverage.get('adult_weight_min_kg', {}).get('percentage', 0):.1f}%
Missing Weight: {weight_stats['missing_weight']} breeds
"""
        self.report.append(report_text)
        return df

    def analyze_breeds_details(self):
        """Analyze breeds_details table for Wikipedia data"""
        self.log_section("BREEDS_DETAILS ANALYSIS (Wikipedia)")

        response = self.supabase.table('breeds_details').select('*').execute()
        df = pd.DataFrame(response.data)

        total = len(df)
        self.stats['breeds_details']['total'] = total

        # Check raw_html storage (if column exists)
        if 'raw_html' in df.columns:
            has_html = df['raw_html'].notna().sum()
            html_lengths = df['raw_html'].dropna().str.len()
        else:
            has_html = 0
            html_lengths = pd.Series([])

        # Check extracted fields
        extracted_fields = [
            'weight_range', 'height_range', 'life_span',
            'energy_level', 'temperament', 'health_issues'
        ]

        field_coverage = {}
        for field in extracted_fields:
            if field in df.columns:
                count = df[field].notna().sum()
                field_coverage[field] = {
                    'count': count,
                    'percentage': (count / total) * 100
                }

        self.stats['breeds_details']['field_coverage'] = field_coverage

        html_pct = (has_html/total)*100 if total > 0 else 0
        avg_len = html_lengths.mean() if len(html_lengths) > 0 else 0
        max_len = html_lengths.max() if len(html_lengths) > 0 else 0

        report_text = f"""
Total Breeds: {total}
Has Raw HTML: {has_html} ({html_pct:.1f}%)
Avg HTML Length: {avg_len:.0f} chars
Max HTML Length: {max_len:.0f} chars

Field Coverage:
"""
        for field, data in field_coverage.items():
            report_text += f"  {field}: {data['percentage']:.1f}% ({data['count']}/{total})\n"

        self.report.append(report_text)
        return df

    def identify_missing_data(self, published_df, details_df):
        """Identify breeds with missing critical data"""
        self.log_section("MISSING DATA ANALYSIS")

        # Breeds without weight data
        no_weight = published_df[published_df['adult_weight_min_kg'].isna()] if 'adult_weight_min_kg' in published_df.columns else published_df.iloc[:0]

        # Breeds with default energy (moderate) - using energy column
        default_energy = published_df[published_df['energy'] == 'moderate'] if 'energy' in published_df.columns else published_df

        # Breeds with no energy data
        no_energy = published_df[published_df['energy'].isna()] if 'energy' in published_df.columns else published_df.iloc[:0]

        # Breeds not in details table (no Wikipedia data)
        published_slugs = set(published_df['breed_slug'])
        details_slugs = set(details_df['breed_slug']) if 'breed_slug' in details_df.columns else set()
        no_wikipedia = published_slugs - details_slugs

        self.stats['missing_data'] = {
            'no_weight': len(no_weight),
            'default_energy': len(default_energy),
            'no_energy': len(no_energy),
            'no_wikipedia': len(no_wikipedia)
        }

        report_text = f"""
Critical Missing Data:
  Breeds without weight: {len(no_weight)} ({(len(no_weight)/len(published_df))*100:.1f}%)
  Breeds with default energy (moderate): {len(default_energy)} ({(len(default_energy)/len(published_df))*100:.1f}%)
  Breeds with no energy data: {len(no_energy)} ({(len(no_energy)/len(published_df))*100:.1f}%)
  Breeds without Wikipedia data: {len(no_wikipedia)}

Top 10 Breeds Missing Weight:
"""
        for idx, row in no_weight.head(10).iterrows():
            breed_name = row.get('display_name', row.get('breed_name', 'Unknown'))
            report_text += f"  - {breed_name} ({row['breed_slug']})\n"

        self.report.append(report_text)

        # Save lists for further action
        return {
            'no_weight': no_weight[['breed_slug', 'display_name']].to_dict('records') if len(no_weight) > 0 else [],
            'default_energy': default_energy[['breed_slug', 'display_name']].to_dict('records')[:20] if len(default_energy) > 0 else [],
            'no_wikipedia': list(no_wikipedia)
        }

    def check_data_quality(self, df):
        """Check for data quality issues"""
        self.log_section("DATA QUALITY CHECKS")

        issues = []

        # Check weight consistency with size
        size_weight_map = {
            'xs': (0, 7),
            's': (5, 15),
            'm': (10, 30),
            'l': (25, 50),
            'xl': (40, 100)
        }

        inconsistent = []
        for idx, row in df.iterrows():
            if pd.notna(row.get('adult_weight_min_kg')) and pd.notna(row.get('size_category')):
                size = row['size_category']
                weight_min = row['adult_weight_min_kg']
                weight_max = row.get('adult_weight_max_kg', weight_min)

                if size in size_weight_map:
                    expected_min, expected_max = size_weight_map[size]
                    if weight_max < expected_min * 0.7 or weight_min > expected_max * 1.3:
                        inconsistent.append({
                            'breed': row.get('display_name', row.get('breed_name', 'Unknown')),
                            'size': size,
                            'weight': f"{weight_min}-{weight_max}kg",
                            'expected': f"{expected_min}-{expected_max}kg"
                        })

        # Check for outliers in age boundaries
        growth_outliers = df[
            (df['growth_end_months'] < 6) |
            (df['growth_end_months'] > 24)
        ]

        senior_outliers = df[
            (df['senior_start_months'] < 60) |
            (df['senior_start_months'] > 144)
        ]

        self.stats['quality_issues'] = {
            'size_weight_inconsistent': len(inconsistent),
            'growth_outliers': len(growth_outliers),
            'senior_outliers': len(senior_outliers)
        }

        report_text = f"""
Quality Issues Found:
  Size/Weight Inconsistencies: {len(inconsistent)}
  Growth End Outliers (<6 or >24 months): {len(growth_outliers)}
  Senior Start Outliers (<60 or >144 months): {len(senior_outliers)}

Size/Weight Inconsistencies (first 5):
"""
        for item in inconsistent[:5]:
            report_text += f"  - {item['breed']}: Size={item['size']}, Weight={item['weight']}, Expected={item['expected']}\n"

        self.report.append(report_text)
        return inconsistent

    def analyze_dogs_linkage(self):
        """Check how well dogs table links to breeds"""
        self.log_section("DOGS TABLE LINKAGE")

        dogs_response = self.supabase.table('dogs').select('*').execute()
        dogs_df = pd.DataFrame(dogs_response.data)

        total_dogs = len(dogs_df)
        has_breed = dogs_df['breed'].notna().sum() if 'breed' in dogs_df.columns else 0

        if 'breed' in dogs_df.columns:
            breed_counts = dogs_df['breed'].value_counts()
            top_breeds = breed_counts.head(10)
        else:
            top_breeds = pd.Series()

        self.stats['dogs_linkage'] = {
            'total_dogs': total_dogs,
            'has_breed': has_breed,
            'percentage': (has_breed / total_dogs * 100) if total_dogs > 0 else 0
        }

        report_text = f"""
Total Dogs: {total_dogs}
Dogs with Breed: {has_breed} ({(has_breed/total_dogs)*100:.1f}%)

Top 10 Breeds in Dogs Table:
"""
        for breed, count in top_breeds.items():
            report_text += f"  - {breed}: {count} dogs\n"

        self.report.append(report_text)

    def generate_recommendations(self):
        """Generate actionable recommendations"""
        self.log_section("RECOMMENDATIONS")

        recommendations = f"""
Priority 1 - Critical Data Fixes:
  1. Add weight data for {self.stats['missing_data']['no_weight']} breeds missing weights
  2. Review and update energy levels for {self.stats['missing_data']['default_energy']} breeds with defaults
  3. Add energy data for {self.stats['missing_data']['no_energy']} breeds without any energy info

Priority 2 - Wikipedia Enhancement:
  1. Re-scrape all {self.stats['breeds_published']['total']} breeds from Wikipedia
  2. Store complete HTML in GCS (current limit: 50k chars)
  3. Extract missing fields: health issues, exercise needs, dietary requirements
  4. Add {self.stats['missing_data']['no_wikipedia']} breeds without Wikipedia data

Priority 3 - Quality Improvements:
  1. Fix {self.stats['quality_issues']['size_weight_inconsistent']} size/weight inconsistencies
  2. Review {self.stats['quality_issues']['growth_outliers']} growth boundary outliers
  3. Review {self.stats['quality_issues']['senior_outliers']} senior age outliers
  4. Implement breeds_overrides table for manual corrections

Priority 4 - Enrichment:
  1. Add breed-specific health conditions
  2. Add nutrition requirements
  3. Add exercise requirements
  4. Add temperament scores

Estimated Data Quality Score: {self._calculate_quality_score()}/100
"""
        self.report.append(recommendations)

    def _calculate_quality_score(self):
        """Calculate overall quality score"""
        scores = []

        # Weight coverage (30 points)
        weight_coverage = self.stats['breeds_published']['coverage'].get('adult_weight_min_kg', {}).get('percentage', 0)
        scores.append(weight_coverage * 0.3)

        # Energy diversity (20 points) - penalize if >90% are moderate
        default_pct = (self.stats['missing_data'].get('default_energy', 0) / self.stats['breeds_published']['total']) * 100
        energy_score = max(0, 20 - (default_pct - 50) * 0.4)
        scores.append(energy_score)

        # Size distribution (10 points) - good if all sizes represented
        size_dist = self.stats['breeds_published']['size_distribution']
        has_all_sizes = all(size in size_dist for size in ['xs', 's', 'm', 'l', 'xl'])
        scores.append(10 if has_all_sizes else 5)

        # Wikipedia coverage (20 points)
        wiki_coverage = ((self.stats['breeds_details']['total'] - self.stats['missing_data']['no_wikipedia'])
                        / self.stats['breeds_published']['total']) * 20
        scores.append(wiki_coverage)

        # Dogs linkage (20 points)
        dogs_linkage = self.stats['dogs_linkage']['percentage'] * 0.2
        scores.append(dogs_linkage)

        return round(sum(scores))

    def save_report(self):
        """Save the complete report"""
        # Save markdown report
        report_content = "\n".join(self.report)
        report_path = f"breeds_audit_report_{self.timestamp}.md"

        with open(report_path, 'w') as f:
            f.write(f"# Breed Data Comprehensive Audit Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(report_content)

        # Save JSON statistics
        stats_path = f"breeds_audit_stats_{self.timestamp}.json"
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2, default=str)

        logger.info(f"Report saved to {report_path}")
        logger.info(f"Statistics saved to {stats_path}")

        return report_path, stats_path

    def run(self):
        """Execute the complete audit"""
        logger.info("Starting Comprehensive Breed Audit...")

        try:
            # Analyze main tables
            published_df = self.analyze_breeds_published()
            details_df = self.analyze_breeds_details()

            # Identify missing data
            missing_data = self.identify_missing_data(published_df, details_df)

            # Check data quality
            quality_issues = self.check_data_quality(published_df)

            # Analyze dogs linkage
            self.analyze_dogs_linkage()

            # Generate recommendations
            self.generate_recommendations()

            # Save reports
            report_path, stats_path = self.save_report()

            # Save actionable lists
            with open(f'breeds_action_items_{self.timestamp}.json', 'w') as f:
                json.dump({
                    'missing_weight': missing_data['no_weight'],
                    'default_energy': missing_data.get('default_energy', [])[:20],  # First 20
                    'no_wikipedia': missing_data['no_wikipedia'],
                    'quality_issues': quality_issues[:10]  # First 10
                }, f, indent=2)

            print("\n" + "="*60)
            print("AUDIT COMPLETE")
            print("="*60)
            print(f"Quality Score: {self._calculate_quality_score()}/100")
            print(f"Report: {report_path}")
            print(f"Stats: {stats_path}")
            print(f"Action Items: breeds_action_items_{self.timestamp}.json")

            return self.stats

        except Exception as e:
            logger.error(f"Audit failed: {e}")
            raise

if __name__ == "__main__":
    auditor = BreedComprehensiveAudit()
    auditor.run()