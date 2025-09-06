#!/usr/bin/env python3
"""
Test nutrition parser with real HTML fixtures
"""
import sys
import os
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

from etl.nutrition_parser import NutritionParser, parse_nutrition_from_html


def test_parser_with_fixtures():
    """Test parser with downloaded HTML pages"""
    parser = NutritionParser()
    fixtures_dir = Path(__file__).parent / 'fixtures'
    
    results = {}
    
    # Test each fixture
    for fixture_file in fixtures_dir.glob('*.html'):
        print(f"\nTesting {fixture_file.name}...")
        
        with open(fixture_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        result = parser.parse_html(html)
        results[fixture_file.name] = result
        
        print(f"  Protein: {result.get('protein_percent')}%")
        print(f"  Fat: {result.get('fat_percent')}%")
        print(f"  Fiber: {result.get('fiber_percent')}%")
        print(f"  Ash: {result.get('ash_percent')}%")
        print(f"  Moisture: {result.get('moisture_percent')}%")
        print(f"  Kcal/100g: {result.get('kcal_per_100g')} ({result.get('kcal_basis', 'N/A')})")
    
    # Assertions
    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)
    
    success_count = 0
    for filename, data in results.items():
        has_macros = bool(data.get('protein_percent') or data.get('fat_percent'))
        has_energy = bool(data.get('kcal_per_100g'))
        
        if has_macros:
            success_count += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        print(f"{filename}: {status}")
        print(f"  - Has macros: {has_macros}")
        print(f"  - Has energy: {has_energy}")
    
    print(f"\nSuccess rate: {success_count}/{len(results)} files parsed successfully")
    
    return results


def test_specific_patterns():
    """Test specific nutrition text patterns"""
    parser = NutritionParser()
    
    test_cases = [
        # Test case 1: Standard format
        {
            'html': """
            <div>
                <h3>Analytical Constituents</h3>
                <p>Protein 25%, Fat 15%, Fiber 3%, Ash 7%, Moisture 10%</p>
                <p>Energy: 375 kcal/100g</p>
            </div>
            """,
            'expected': {
                'protein_percent': 25.0,
                'fat_percent': 15.0,
                'fiber_percent': 3.0,
                'ash_percent': 7.0,
                'moisture_percent': 10.0,
                'kcal_per_100g': 375.0
            }
        },
        # Test case 2: Table format
        {
            'html': """
            <table>
                <tr><td>Crude Protein</td><td>28%</td></tr>
                <tr><td>Crude Fat</td><td>18%</td></tr>
                <tr><td>Crude Fiber</td><td>2.5%</td></tr>
                <tr><td>Metabolizable Energy</td><td>1570 kJ/100g</td></tr>
            </table>
            """,
            'expected': {
                'protein_percent': 28.0,
                'fat_percent': 18.0,
                'fiber_percent': 2.5,
                'kcal_per_100g': 375.2  # 1570 / 4.184
            }
        },
        # Test case 3: Comma decimals
        {
            'html': """
            <div class="nutrition">
                Protein: 25,5%
                Oil & Fat: 14,5%
                Ash: 7,2%
            </div>
            """,
            'expected': {
                'protein_percent': 25.5,
                'fat_percent': 14.5,
                'ash_percent': 7.2
            }
        }
    ]
    
    print("\n" + "="*60)
    print("PATTERN TESTS")
    print("="*60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest case {i}:")
        result = parser.parse_html(test['html'])
        
        passed = True
        for key, expected_value in test['expected'].items():
            actual_value = result.get(key)
            if actual_value is None:
                print(f"  ❌ {key}: Expected {expected_value}, got None")
                passed = False
            elif abs(actual_value - expected_value) > 0.5:
                print(f"  ❌ {key}: Expected {expected_value}, got {actual_value}")
                passed = False
            else:
                print(f"  ✅ {key}: {actual_value}")
        
        if result.get('kcal_per_100g') and 'kcal_per_100g' not in test['expected']:
            print(f"  ℹ️  Estimated kcal: {result['kcal_per_100g']}")
        
        print(f"  Overall: {'PASS' if passed else 'FAIL'}")


if __name__ == '__main__':
    print("Testing Nutrition Parser")
    print("="*60)
    
    # Test with real fixtures
    fixture_results = test_parser_with_fixtures()
    
    # Test specific patterns
    test_specific_patterns()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)