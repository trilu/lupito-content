#!/usr/bin/env python3
"""
Discovery & Evidence for split-brand cases
Scan catalog for multi-word brands broken across brand and product_name fields
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
from collections import Counter, defaultdict

class BrandSplitDiscovery:
    def __init__(self):
        self.harvest_dir = Path("reports/MANUF/PILOT/harvests")
        self.output_dir = Path("reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Known multi-word brands that are commonly split
        self.known_multi_word = [
            'Royal Canin',
            "Hill's Science Plan",
            "Hill's Prescription Diet",
            'Purina Pro Plan', 
            'Purina ONE',
            'Farmina N&D',
            'Taste of the Wild',
            "Nature's Variety Instinct",
            'Concept for Life',
            'Happy Dog',
            'Arden Grange',
            'Burns Pet',
            'James Wellbeloved',
            'Lily\'s Kitchen',
            'Harringtons',
            'Barking Heads',
            'AATU',
            'Canagan',
            'Eden',
            'Orijen',
            'Acana Heritage',
            'Wellness Core',
            'Wild Freedom',
            'MAC\'s',
            'Rocco & Roxie'
        ]
        
        # Common brand prefixes that might be split
        self.common_prefixes = {
            'Royal': 'Canin',
            'Hills': ['Science Plan', 'Prescription Diet', 'Science Diet'],
            "Hill's": ['Science Plan', 'Prescription Diet', 'Science Diet'],
            'Purina': ['Pro Plan', 'ONE', 'Beta', 'Dentalife', 'Adventuros'],
            'Farmina': ['N&D', 'Vet Life'],
            'Taste': ['of the Wild'],
            "Nature's": ['Variety', 'Variety Instinct'],
            'Concept': ['for Life'],
            'Happy': ['Dog', 'Cat'],
            'Arden': ['Grange'],
            'Burns': ['Pet', 'Pet Nutrition'],
            'James': ['Wellbeloved'],
            "Lily's": ['Kitchen'],
            'Barking': ['Heads'],
            'Wellness': ['Core', 'Simple'],
            'Wild': ['Freedom'],
            'Rocco': ['& Roxie']
        }
        
    def load_all_data(self):
        """Load all available harvest data"""
        all_data = []
        
        for csv_file in self.harvest_dir.glob("*_pilot_*.csv"):
            df = pd.read_csv(csv_file)
            all_data.append(df)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
    
    def detect_split_candidates(self, df):
        """Detect potential split-brand cases"""
        candidates = defaultdict(list)
        
        for _, row in df.iterrows():
            brand = str(row.get('brand', '')).strip()
            brand_slug = str(row.get('brand_slug', '')).strip()
            product_name = str(row.get('product_name', '')).strip()
            
            if not brand or not product_name:
                continue
            
            # Case 1: Short brand (≤6 chars) with capitalized product name start
            if len(brand) <= 6:
                # Extract first 1-3 words from product_name
                name_words = product_name.split()[:3]
                
                for i in range(1, min(4, len(name_words) + 1)):
                    prefix = ' '.join(name_words[:i])
                    
                    # Check if this could form a known multi-word brand
                    potential_brand = f"{brand} {prefix}"
                    
                    # Check against known patterns
                    if brand in self.common_prefixes:
                        expected = self.common_prefixes[brand]
                        if isinstance(expected, str):
                            if prefix.lower().startswith(expected.lower()):
                                candidates[potential_brand].append({
                                    'product_id': row.get('product_id'),
                                    'current_brand': brand,
                                    'product_name': product_name,
                                    'prefix_found': prefix,
                                    'confidence': 'high'
                                })
                        elif isinstance(expected, list):
                            for exp in expected:
                                if prefix.lower().startswith(exp.lower()):
                                    candidates[potential_brand].append({
                                        'product_id': row.get('product_id'),
                                        'current_brand': brand,
                                        'product_name': product_name,
                                        'prefix_found': prefix,
                                        'confidence': 'high'
                                    })
            
            # Case 2: Check for known multi-word brands
            for known_brand in self.known_multi_word:
                # Check if brand is first part and product_name starts with second part
                parts = known_brand.split(' ', 1)
                if len(parts) == 2:
                    if (brand.lower() == parts[0].lower() and 
                        product_name.lower().startswith(parts[1].lower())):
                        candidates[known_brand].append({
                            'product_id': row.get('product_id'),
                            'current_brand': brand,
                            'product_name': product_name,
                            'prefix_found': parts[1],
                            'confidence': 'very_high'
                        })
            
            # Case 3: Look for orphaned fragments (e.g., product_name starts with "Canin")
            orphan_fragments = ['Canin', 'Plan', 'Diet', 'Core', 'Life', 'Grange', 
                               'Kitchen', 'Heads', 'Freedom', 'Heritage']
            
            for fragment in orphan_fragments:
                if product_name.startswith(fragment + ' '):
                    # This is likely an orphaned fragment
                    candidates[f"<orphan:{fragment}>"].append({
                        'product_id': row.get('product_id'),
                        'current_brand': brand,
                        'product_name': product_name,
                        'prefix_found': fragment,
                        'confidence': 'orphan'
                    })
        
        return candidates
    
    def analyze_frequency_patterns(self, candidates):
        """Analyze frequency and consistency of candidate pairs"""
        analysis = []
        
        for candidate_brand, instances in candidates.items():
            if len(instances) < 2:  # Skip single occurrences
                continue
            
            # Group by current brand
            brand_groups = defaultdict(list)
            for inst in instances:
                brand_groups[inst['current_brand']].append(inst)
            
            # Calculate consistency score
            max_group_size = max(len(group) for group in brand_groups.values())
            consistency = max_group_size / len(instances)
            
            # Get sample products
            samples = instances[:5]  # First 5 examples
            
            analysis.append({
                'candidate_brand': candidate_brand,
                'total_instances': len(instances),
                'unique_brands': len(brand_groups),
                'consistency_score': round(consistency, 2),
                'confidence': instances[0]['confidence'],
                'impact_score': len(instances) * consistency,
                'samples': samples
            })
        
        # Sort by impact score
        analysis.sort(key=lambda x: x['impact_score'], reverse=True)
        
        return analysis
    
    def detect_false_positives(self, analysis):
        """Identify potential false positives"""
        false_positives = []
        
        for item in analysis:
            candidate = item['candidate_brand']
            
            # Check for word similarity issues
            if 'Canin' in candidate:
                # Check if products contain "Canine" instead
                canine_count = sum(1 for s in item['samples'] 
                                 if 'Canine' in s['product_name'])
                if canine_count > 0:
                    false_positives.append({
                        'candidate': candidate,
                        'reason': f'Contains "Canine" not "Canin" in {canine_count} samples',
                        'severity': 'high'
                    })
            
            # Check for generic words
            generic_words = ['Life', 'Plan', 'Diet', 'Food', 'Pet']
            for word in generic_words:
                if candidate.endswith(word) and item['consistency_score'] < 0.8:
                    false_positives.append({
                        'candidate': candidate,
                        'reason': f'Generic word "{word}" with low consistency',
                        'severity': 'medium'
                    })
        
        return false_positives
    
    def generate_report(self, analysis, false_positives, df):
        """Generate BRAND_SPLIT_CANDIDATES.md report"""
        
        report = f"""# BRAND SPLIT CANDIDATES

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Products Analyzed: {len(df)}

## 🔍 DISCOVERY SUMMARY

Found **{len(analysis)}** potential split-brand cases affecting **{sum(a['total_instances'] for a in analysis)}** products.

## 🎯 TOP CANDIDATE PAIRS

| Candidate Brand | Instances | Consistency | Confidence | Impact | Action |
|-----------------|-----------|-------------|------------|--------|--------|
"""
        
        # Top 10 candidates
        for item in analysis[:10]:
            action = "✅ Fix" if item['confidence'] in ['very_high', 'high'] else "🔍 Review"
            
            report += f"| **{item['candidate_brand']}** | {item['total_instances']} | "
            report += f"{item['consistency_score']:.2f} | {item['confidence']} | "
            report += f"{item['impact_score']:.1f} | {action} |\n"
        
        # Detailed examples for top candidates
        report += """

## 📋 DETAILED EXAMPLES

"""
        
        for item in analysis[:5]:
            report += f"""### {item['candidate_brand']}
- **Instances**: {item['total_instances']}
- **Confidence**: {item['confidence']}
- **Samples**:
"""
            
            for sample in item['samples'][:3]:
                report += f"""  - Product: `{sample['product_id']}`
    - Current: brand="{sample['current_brand']}", name="{sample['product_name'][:50]}..."
    - Found prefix: "{sample['prefix_found']}"
"""
            report += "\n"
        
        # Orphaned fragments
        orphans = [a for a in analysis if a['candidate_brand'].startswith('<orphan:')]
        
        if orphans:
            report += """## ⚠️ ORPHANED FRAGMENTS

These product names start with brand fragments that should be fixed:

| Fragment | Count | Example Products |
|----------|-------|------------------|
"""
            
            for orphan in orphans:
                fragment = orphan['candidate_brand'].replace('<orphan:', '').replace('>', '')
                examples = ', '.join([s['product_id'] for s in orphan['samples'][:3]])
                report += f"| {fragment} | {orphan['total_instances']} | {examples} |\n"
        
        # False positives
        if false_positives:
            report += """

## 🚫 SUSPECTED FALSE POSITIVES

| Candidate | Reason | Severity |
|-----------|--------|----------|
"""
            
            for fp in false_positives:
                report += f"| {fp['candidate']} | {fp['reason']} | {fp['severity']} |\n"
        
        # Statistics
        report += f"""

## 📊 STATISTICS

### Brand Distribution
- Short brands (≤6 chars): {len(df[df['brand'].str.len() <= 6])}
- Potential splits detected: {len(analysis)}
- High confidence fixes: {len([a for a in analysis if a['confidence'] in ['very_high', 'high']])}
- Products affected: {sum(a['total_instances'] for a in analysis)}

### Common Split Patterns
"""
        
        # Group by pattern type
        pattern_counts = Counter()
        for item in analysis:
            if 'Royal' in item['candidate_brand']:
                pattern_counts['Royal Canin'] += item['total_instances']
            elif 'Hill' in item['candidate_brand']:
                pattern_counts["Hill's variants"] += item['total_instances']
            elif 'Purina' in item['candidate_brand']:
                pattern_counts['Purina lines'] += item['total_instances']
            else:
                pattern_counts['Other'] += item['total_instances']
        
        for pattern, count in pattern_counts.most_common():
            report += f"- {pattern}: {count} products\n"
        
        report += """

## 🔧 RECOMMENDED FIXES

### High Priority (Confidence: very_high/high)
"""
        
        high_priority = [a for a in analysis if a['confidence'] in ['very_high', 'high']][:5]
        for item in high_priority:
            report += f"""
1. **{item['candidate_brand']}**
   - Affects: {item['total_instances']} products
   - Action: Merge brand parts and clean product_name
"""
        
        report += """

### Guards Needed
- Word boundary checks for "Canin" vs "Canine"
- Preserve legitimate product lines (e.g., "Pro Plan", "Science Plan")
- Avoid over-stripping generic words

## 📝 NEXT STEPS

1. Review high-confidence candidates
2. Create brand_phrase_map with canonical names
3. Run normalization with dry-run mode
4. Apply fixes after QA validation

---

**Note**: This is a dry-run discovery. No data has been modified yet.
"""
        
        return report

def main():
    discovery = BrandSplitDiscovery()
    
    print("="*60)
    print("DISCOVERING BRAND SPLITS")
    print("="*60)
    
    # Load data
    df = discovery.load_all_data()
    
    if df.empty:
        print("No data found to analyze")
        return
    
    print(f"Loaded {len(df)} products for analysis")
    
    # Detect split candidates
    print("\nScanning for split-brand cases...")
    candidates = discovery.detect_split_candidates(df)
    
    print(f"Found {len(candidates)} candidate patterns")
    
    # Analyze frequency and consistency
    analysis = discovery.analyze_frequency_patterns(candidates)
    
    # Detect false positives
    false_positives = discovery.detect_false_positives(analysis)
    
    # Generate report
    report = discovery.generate_report(analysis, false_positives, df)
    
    report_file = discovery.output_dir / "BRAND_SPLIT_CANDIDATES.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Report saved to: {report_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("TOP SPLIT-BRAND CANDIDATES")
    print("="*60)
    
    for item in analysis[:5]:
        print(f"\n{item['candidate_brand']}")
        print(f"  Instances: {item['total_instances']}")
        print(f"  Confidence: {item['confidence']}")
        print(f"  Impact: {item['impact_score']:.1f}")
    
    print("\n" + "="*60)
    print(f"Total candidates: {len(analysis)}")
    print(f"Products affected: {sum(a['total_instances'] for a in analysis)}")
    print("="*60)

if __name__ == "__main__":
    main()