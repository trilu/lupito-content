#!/usr/bin/env python3
"""
Parse Belcando and Bozita snapshots from GCS
"""

import os
import re
from pathlib import Path
from parse_gcs_snapshots import GCSSnapshotParser
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Parse recently harvested Belcando and Bozita snapshots"""
    
    print("="*80)
    print("PARSING BELCANDO AND BOZITA SNAPSHOTS")
    print("="*80)
    
    # Initialize parser
    parser = GCSSnapshotParser()
    
    # Parse Belcando
    print("\nProcessing belcando...")
    belcando_stats = parser.parse_brand_snapshots('belcando')
    print(f"  Processed {belcando_stats['total_products']} products")
    print(f"  Extracted ingredients: {belcando_stats['ingredients_extracted']}")
    print(f"  Extracted macros: {belcando_stats['macros_extracted']}")
    print(f"  Extracted kcal: {belcando_stats['kcal_extracted']}")
    
    # Parse Bozita
    print("\nProcessing bozita...")
    bozita_stats = parser.parse_brand_snapshots('bozita')
    print(f"  Processed {bozita_stats['total_products']} products")
    print(f"  Extracted ingredients: {bozita_stats['ingredients_extracted']}")
    print(f"  Extracted macros: {bozita_stats['macros_extracted']}")
    print(f"  Extracted kcal: {bozita_stats['kcal_extracted']}")
    
    # Generate report
    print("\n" + "="*80)
    print("PARSING COMPLETE")
    print("="*80)
    
    total_ingredients = belcando_stats['ingredients_extracted'] + bozita_stats['ingredients_extracted']
    total_macros = belcando_stats['macros_extracted'] + bozita_stats['macros_extracted']
    total_kcal = belcando_stats['kcal_extracted'] + bozita_stats['kcal_extracted']
    
    print(f"\nTotal extractions:")
    print(f"  - Ingredients: {total_ingredients}")
    print(f"  - Macros: {total_macros}")
    print(f"  - Kcal: {total_kcal}")
    
    # Create summary report
    report = f"""
# Belcando & Bozita Parsing Report

## Summary
- **Brands Parsed**: belcando, bozita
- **Total Products**: {belcando_stats['total_products'] + bozita_stats['total_products']}
- **Total Ingredients Extracted**: {total_ingredients}
- **Total Macros Extracted**: {total_macros}
- **Total Kcal Extracted**: {total_kcal}

## Belcando
- Products: {belcando_stats['total_products']}
- Ingredients: {belcando_stats['ingredients_extracted']}
- Macros: {belcando_stats['macros_extracted']}
- Kcal: {belcando_stats['kcal_extracted']}

## Bozita
- Products: {bozita_stats['total_products']}
- Ingredients: {bozita_stats['ingredients_extracted']}
- Macros: {bozita_stats['macros_extracted']}
- Kcal: {bozita_stats['kcal_extracted']}
"""
    
    with open('BELCANDO_BOZITA_PARSE_REPORT.md', 'w') as f:
        f.write(report)
    
    print("\n✓ Report saved to BELCANDO_BOZITA_PARSE_REPORT.md")

if __name__ == "__main__":
    main()