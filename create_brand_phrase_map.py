#!/usr/bin/env python3
"""
Create canonical brand phrase map for fixing split brands
Includes both discovered patterns and curated seed list
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import re

class BrandPhraseMapper:
    def __init__(self):
        self.output_dir = Path("data")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def create_brand_phrase_map(self):
        """Create comprehensive brand phrase map"""
        
        # Define canonical brand mappings
        brand_mappings = [
            # Royal Canin variants
            {
                'source_brand': 'Royal',
                'prefix_from_name': 'Canin',
                'canonical_brand': 'Royal Canin',
                'brand_slug': 'royal_canin',
                'brand_line': None,
                'strip_prefix_regex': r'^Canin\s+',
                'confidence': 'very_high',
                'notes': 'Common split: Royal | Canin ...'
            },
            
            # Hill's variants
            {
                'source_brand': 'Hills',
                'prefix_from_name': 'Science Plan',
                'canonical_brand': "Hill's",
                'brand_slug': 'hills',
                'brand_line': 'Science Plan',
                'strip_prefix_regex': r'^Science\s+Plan\s+',
                'confidence': 'very_high',
                'notes': "Hill's Science Plan line"
            },
            {
                'source_brand': "Hill's",
                'prefix_from_name': 'Science Plan',
                'canonical_brand': "Hill's",
                'brand_slug': 'hills',
                'brand_line': 'Science Plan',
                'strip_prefix_regex': r'^Science\s+Plan\s+',
                'confidence': 'very_high',
                'notes': "Hill's Science Plan line"
            },
            {
                'source_brand': 'Hills',
                'prefix_from_name': 'Prescription Diet',
                'canonical_brand': "Hill's",
                'brand_slug': 'hills',
                'brand_line': 'Prescription Diet',
                'strip_prefix_regex': r'^Prescription\s+Diet\s+',
                'confidence': 'very_high',
                'notes': "Hill's Prescription Diet line"
            },
            
            # Purina variants
            {
                'source_brand': 'Purina',
                'prefix_from_name': 'Pro Plan',
                'canonical_brand': 'Purina',
                'brand_slug': 'purina',
                'brand_line': 'Pro Plan',
                'strip_prefix_regex': r'^Pro\s+Plan\s+',
                'confidence': 'very_high',
                'notes': 'Purina Pro Plan line'
            },
            {
                'source_brand': 'Purina',
                'prefix_from_name': 'ONE',
                'canonical_brand': 'Purina',
                'brand_slug': 'purina',
                'brand_line': 'ONE',
                'strip_prefix_regex': r'^ONE\s+',
                'confidence': 'very_high',
                'notes': 'Purina ONE line'
            },
            {
                'source_brand': 'Purina',
                'prefix_from_name': 'Beta',
                'canonical_brand': 'Purina',
                'brand_slug': 'purina',
                'brand_line': 'Beta',
                'strip_prefix_regex': r'^Beta\s+',
                'confidence': 'high',
                'notes': 'Purina Beta line'
            },
            
            # Farmina variants
            {
                'source_brand': 'Farmina',
                'prefix_from_name': 'N&D',
                'canonical_brand': 'Farmina',
                'brand_slug': 'farmina',
                'brand_line': 'N&D',
                'strip_prefix_regex': r'^N&D\s+',
                'confidence': 'very_high',
                'notes': 'Farmina N&D line'
            },
            
            # Other multi-word brands
            {
                'source_brand': 'Taste',
                'prefix_from_name': 'of the Wild',
                'canonical_brand': 'Taste of the Wild',
                'brand_slug': 'taste_of_the_wild',
                'brand_line': None,
                'strip_prefix_regex': r'^of\s+the\s+Wild\s+',
                'confidence': 'very_high',
                'notes': 'Full brand name'
            },
            {
                'source_brand': "Nature's",
                'prefix_from_name': 'Variety Instinct',
                'canonical_brand': "Nature's Variety",
                'brand_slug': 'natures_variety',
                'brand_line': 'Instinct',
                'strip_prefix_regex': r'^Variety\s+Instinct\s+',
                'confidence': 'high',
                'notes': "Nature's Variety Instinct line"
            },
            {
                'source_brand': 'Concept',
                'prefix_from_name': 'for Life',
                'canonical_brand': 'Concept for Life',
                'brand_slug': 'concept_for_life',
                'brand_line': None,
                'strip_prefix_regex': r'^for\s+Life\s+',
                'confidence': 'high',
                'notes': 'Zooplus brand'
            },
            {
                'source_brand': 'Happy',
                'prefix_from_name': 'Dog',
                'canonical_brand': 'Happy Dog',
                'brand_slug': 'happy_dog',
                'brand_line': None,
                'strip_prefix_regex': r'^Dog\s+',
                'confidence': 'high',
                'notes': 'Full brand name'
            },
            {
                'source_brand': 'Arden',
                'prefix_from_name': 'Grange',
                'canonical_brand': 'Arden Grange',
                'brand_slug': 'arden_grange',
                'brand_line': None,
                'strip_prefix_regex': r'^Grange\s+',
                'confidence': 'very_high',
                'notes': 'Full brand name'
            },
            {
                'source_brand': 'Burns',
                'prefix_from_name': 'Pet',
                'canonical_brand': 'Burns',
                'brand_slug': 'burns',
                'brand_line': None,
                'strip_prefix_regex': r'^Pet\s+',
                'confidence': 'medium',
                'notes': 'Burns Pet Nutrition'
            },
            {
                'source_brand': 'James',
                'prefix_from_name': 'Wellbeloved',
                'canonical_brand': 'James Wellbeloved',
                'brand_slug': 'james_wellbeloved',
                'brand_line': None,
                'strip_prefix_regex': r'^Wellbeloved\s+',
                'confidence': 'very_high',
                'notes': 'Full brand name'
            },
            {
                'source_brand': "Lily's",
                'prefix_from_name': 'Kitchen',
                'canonical_brand': "Lily's Kitchen",
                'brand_slug': 'lilys_kitchen',
                'brand_line': None,
                'strip_prefix_regex': r'^Kitchen\s+',
                'confidence': 'very_high',
                'notes': 'Full brand name'
            },
            {
                'source_brand': 'Barking',
                'prefix_from_name': 'Heads',
                'canonical_brand': 'Barking Heads',
                'brand_slug': 'barking_heads',
                'brand_line': None,
                'strip_prefix_regex': r'^Heads\s+',
                'confidence': 'very_high',
                'notes': 'Full brand name'
            },
            {
                'source_brand': 'Wellness',
                'prefix_from_name': 'Core',
                'canonical_brand': 'Wellness',
                'brand_slug': 'wellness',
                'brand_line': 'Core',
                'strip_prefix_regex': r'^Core\s+',
                'confidence': 'high',
                'notes': 'Wellness Core line'
            },
            {
                'source_brand': 'Wild',
                'prefix_from_name': 'Freedom',
                'canonical_brand': 'Wild Freedom',
                'brand_slug': 'wild_freedom',
                'brand_line': None,
                'strip_prefix_regex': r'^Freedom\s+',
                'confidence': 'high',
                'notes': 'Zooplus brand'
            },
            
            # Orphaned fragments (product_name starts with these)
            {
                'source_brand': '*',  # Any brand
                'prefix_from_name': 'Canin',
                'canonical_brand': 'Royal Canin',
                'brand_slug': 'royal_canin',
                'brand_line': None,
                'strip_prefix_regex': r'^Canin\s+',
                'confidence': 'orphan',
                'notes': 'Orphaned "Canin" fragment'
            },
            {
                'source_brand': '*',
                'prefix_from_name': 'Science Plan',
                'canonical_brand': "Hill's",
                'brand_slug': 'hills',
                'brand_line': 'Science Plan',
                'strip_prefix_regex': r'^Science\s+Plan\s+',
                'confidence': 'orphan',
                'notes': 'Orphaned "Science Plan" fragment'
            },
            {
                'source_brand': '*',
                'prefix_from_name': 'Pro Plan',
                'canonical_brand': 'Purina',
                'brand_slug': 'purina',
                'brand_line': 'Pro Plan',
                'strip_prefix_regex': r'^Pro\s+Plan\s+',
                'confidence': 'orphan',
                'notes': 'Orphaned "Pro Plan" fragment'
            }
        ]
        
        # Create DataFrame
        df = pd.DataFrame(brand_mappings)
        
        # Add metadata
        df['created_at'] = datetime.now().isoformat()
        df['version'] = '1.0'
        
        # Sort by confidence and source brand
        confidence_order = {'very_high': 0, 'high': 1, 'medium': 2, 'orphan': 3}
        df['confidence_rank'] = df['confidence'].map(confidence_order)
        df = df.sort_values(['confidence_rank', 'source_brand', 'prefix_from_name'])
        df = df.drop('confidence_rank', axis=1)
        
        return df
    
    def save_brand_phrase_map(self, df):
        """Save brand phrase map to CSV"""
        output_file = self.output_dir / "brand_phrase_map.csv"
        df.to_csv(output_file, index=False)
        return output_file
    
    def generate_brand_glossary(self, df):
        """Generate brand glossary report"""
        
        # Group by canonical brand
        brand_groups = df.groupby('canonical_brand').agg({
            'brand_slug': 'first',
            'brand_line': lambda x: list(x.dropna().unique()),
            'source_brand': lambda x: list(x.unique()),
            'confidence': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
        }).reset_index()
        
        report = f"""# BRAND GLOSSARY

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Version: 1.0

## 📚 CANONICAL BRANDS

| Canonical Brand | Slug | Known Lines | Source Variants | Confidence |
|-----------------|------|-------------|-----------------|------------|
"""
        
        for _, row in brand_groups.iterrows():
            lines = ', '.join(row['brand_line']) if row['brand_line'] else '-'
            sources = ', '.join(str(s) for s in row['source_brand'][:3])
            
            report += f"| **{row['canonical_brand']}** | `{row['brand_slug']}` | "
            report += f"{lines} | {sources} | {row['confidence']} |\n"
        
        report += f"""

## 🔧 BRAND LINES

Brands with multiple product lines:

"""
        
        multi_line = brand_groups[brand_groups['brand_line'].apply(lambda x: len(x) > 0)]
        
        for _, row in multi_line.iterrows():
            report += f"""### {row['canonical_brand']}
- **Slug**: `{row['brand_slug']}`
- **Lines**: {', '.join(row['brand_line'])}
"""
        
        report += f"""

## 📝 NORMALIZATION RULES

### Source Brand Fixes
Total mappings: {len(df)}
- Very High confidence: {len(df[df['confidence'] == 'very_high'])}
- High confidence: {len(df[df['confidence'] == 'high'])}
- Medium confidence: {len(df[df['confidence'] == 'medium'])}
- Orphan fragments: {len(df[df['confidence'] == 'orphan'])}

### Strip Patterns
Common prefixes that will be removed from product_name:
- "Canin " (when brand is Royal Canin)
- "Science Plan " (when brand is Hill's)
- "Pro Plan " (when brand is Purina)
- "of the Wild " (when brand is Taste of the Wild)
- And {len(df['strip_prefix_regex'].unique())-4} more...

---

**Note**: This glossary defines the canonical brand structure for normalization.
"""
        
        return report

def main():
    mapper = BrandPhraseMapper()
    
    print("="*60)
    print("CREATING BRAND PHRASE MAP")
    print("="*60)
    
    # Create brand phrase map
    df = mapper.create_brand_phrase_map()
    
    print(f"Created {len(df)} brand mappings")
    print(f"Unique canonical brands: {df['canonical_brand'].nunique()}")
    
    # Save to CSV
    output_file = mapper.save_brand_phrase_map(df)
    print(f"\n✅ Saved brand phrase map to: {output_file}")
    
    # Generate glossary
    glossary = mapper.generate_brand_glossary(df)
    glossary_file = Path("reports") / "BRAND_GLOSSARY.md"
    
    with open(glossary_file, 'w') as f:
        f.write(glossary)
    
    print(f"✅ Generated brand glossary: {glossary_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("BRAND MAPPING SUMMARY")
    print("="*60)
    
    print("\nTop canonical brands:")
    for brand in df['canonical_brand'].value_counts().head(5).index:
        count = len(df[df['canonical_brand'] == brand])
        print(f"  {brand}: {count} mappings")
    
    print("\nConfidence distribution:")
    for conf, count in df['confidence'].value_counts().items():
        print(f"  {conf}: {count}")
    
    print("="*60)

if __name__ == "__main__":
    main()