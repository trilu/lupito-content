#!/usr/bin/env python3
"""
DOM analyzer for B1: Find ingredient selectors in brand HTML
"""

from bs4 import BeautifulSoup
import re
from pathlib import Path

def analyze_bozita_dom(html_content):
    """Analyze Bozita DOM for ingredient selectors"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for Swedish ingredient keywords
    swedish_keywords = ['sammansättning', 'ingredienser', 'analytiska', 'beståndsdelar', 'energi']
    
    selectors_found = []
    
    # Search for text containing keywords
    for keyword in swedish_keywords:
        elements = soup.find_all(string=re.compile(keyword, re.I))
        for elem in elements:
            if elem.parent:
                parent = elem.parent
                selector = f"{parent.name}"
                if parent.get('class'):
                    selector += f".{'.'.join(parent.get('class'))}"
                if parent.get('id'):
                    selector += f"#{parent.get('id')}"
                
                # Get context
                context = parent.get_text()[:200].replace('\n', ' ').strip()
                selectors_found.append({
                    'keyword': keyword,
                    'selector': selector,
                    'context': context
                })
    
    return selectors_found

def analyze_belcando_dom(html_content):
    """Analyze Belcando DOM for ingredient selectors"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for German ingredient keywords
    german_keywords = ['zusammensetzung', 'inhaltsstoffe', 'analytische', 'bestandteile', 'energie']
    
    selectors_found = []
    
    # Search for text containing keywords
    for keyword in german_keywords:
        elements = soup.find_all(string=re.compile(keyword, re.I))
        for elem in elements:
            if elem.parent:
                parent = elem.parent
                selector = f"{parent.name}"
                if parent.get('class'):
                    selector += f".{'.'.join(parent.get('class'))}"
                if parent.get('id'):
                    selector += f"#{parent.get('id')}"
                
                # Get context
                context = parent.get_text()[:200].replace('\n', ' ').strip()
                selectors_found.append({
                    'keyword': keyword,
                    'selector': selector,
                    'context': context
                })
    
    return selectors_found

def analyze_briantos_dom(html_content):
    """Analyze Briantos DOM for ingredient selectors"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for English/German ingredient keywords
    keywords = ['composition', 'ingredients', 'analytical', 'constituents', 'energy', 
                'zusammensetzung', 'inhaltsstoffe']
    
    selectors_found = []
    
    # Search for text containing keywords
    for keyword in keywords:
        elements = soup.find_all(string=re.compile(keyword, re.I))
        for elem in elements:
            if elem.parent:
                parent = elem.parent
                selector = f"{parent.name}"
                if parent.get('class'):
                    selector += f".{'.'.join(parent.get('class'))}"
                if parent.get('id'):
                    selector += f"#{parent.get('id')}"
                
                # Get context
                context = parent.get_text()[:200].replace('\n', ' ').strip()
                selectors_found.append({
                    'keyword': keyword,
                    'selector': selector,
                    'context': context
                })
    
    return selectors_found

def main():
    """Analyze DOM samples"""
    
    print("="*80)
    print("B1: DOM ANALYSIS FOR INGREDIENT SELECTORS")
    print("="*80)
    
    samples = [
        ('bozita', 'dom_analysis/bozita_sample1.html', analyze_bozita_dom),
        ('belcando', 'dom_analysis/belcando_sample1.html', analyze_belcando_dom),
        ('briantos', 'dom_analysis/briantos_sample1.html', analyze_briantos_dom)
    ]
    
    all_results = {}
    
    for brand, filename, analyzer in samples:
        print(f"\nAnalyzing {brand}...")
        
        filepath = Path(filename)
        if not filepath.exists():
            print(f"  ❌ File not found: {filename}")
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        selectors = analyzer(html_content)
        all_results[brand] = selectors
        
        print(f"  Found {len(selectors)} potential selectors:")
        for selector in selectors[:5]:  # Show first 5
            print(f"    - {selector['keyword']}: {selector['selector']}")
            print(f"      Context: {selector['context'][:100]}...")
    
    # Generate selector map
    print("\n" + "="*80)
    print("RECOMMENDED SELECTOR MAPS")
    print("="*80)
    
    for brand, selectors in all_results.items():
        print(f"\n### {brand.upper()} SELECTORS:")
        
        # Group by keyword
        by_keyword = {}
        for sel in selectors:
            keyword = sel['keyword'].lower()
            if keyword not in by_keyword:
                by_keyword[keyword] = []
            by_keyword[keyword].append(sel)
        
        for keyword, sels in by_keyword.items():
            print(f"  {keyword}:")
            for sel in sels[:3]:  # Top 3 per keyword
                print(f"    - {sel['selector']}")
    
    return all_results

if __name__ == "__main__":
    main()