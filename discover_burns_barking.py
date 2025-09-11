#!/usr/bin/env python3
"""
Discover all products for Burns and Barking brands
"""

import os
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
import re

def discover_burns_products():
    """Discover all Burns products"""
    print("\n" + "="*60)
    print("DISCOVERING BURNS PRODUCTS")
    print("="*60)
    
    base_url = "https://burnspet.co.uk"
    products = set()
    
    # Burns has product categories
    categories = [
        "/collections/dry-dog-food",
        "/collections/wet-dog-food",
        "/collections/treats-chews",
        "/pages/all-products"
    ]
    
    for category_url in categories:
        try:
            url = base_url + category_url
            print(f"\nChecking: {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find product links
                product_links = soup.find_all('a', href=re.compile(r'/products/'))
                
                for link in product_links:
                    href = link.get('href', '')
                    if href and '/products/' in href:
                        if href.startswith('/'):
                            product_url = base_url + href
                        else:
                            product_url = href
                        
                        # Clean URL
                        product_url = product_url.split('?')[0]
                        products.add(product_url)
                
                print(f"  Found {len(products)} products so far")
                time.sleep(1)
                
        except Exception as e:
            print(f"  Error: {e}")
    
    # Save URLs
    if products:
        with open('burns_all_product_urls.txt', 'w') as f:
            for url in sorted(products):
                f.write(url + '\n')
        print(f"\n✓ Found {len(products)} total Burns products")
        print(f"✓ Saved to burns_all_product_urls.txt")
    
    return list(products)

def discover_barking_products():
    """Discover all Barking Heads products"""
    print("\n" + "="*60)
    print("DISCOVERING BARKING HEADS PRODUCTS")
    print("="*60)
    
    base_url = "https://barkingheads.co.uk"
    products = set()
    
    # Barking has product categories
    categories = [
        "/collections/dry-dog-food",
        "/collections/wet-dog-food",
        "/collections/treats",
        "/collections/all-dog-food"
    ]
    
    for category_url in categories:
        try:
            url = base_url + category_url
            print(f"\nChecking: {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find product links - Shopify patterns
                selectors = [
                    'a[href*="/products/"]',
                    '.product-item a',
                    '.product-card a',
                    '.grid-product__link'
                ]
                
                for selector in selectors:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href', '')
                        if href and '/products/' in href:
                            if href.startswith('/'):
                                product_url = base_url + href
                            else:
                                product_url = href
                            
                            # Clean URL
                            product_url = product_url.split('?')[0]
                            products.add(product_url)
                
                print(f"  Found {len(products)} products so far")
                time.sleep(1)
                
        except Exception as e:
            print(f"  Error: {e}")
    
    # Save URLs
    if products:
        with open('barking_all_product_urls.txt', 'w') as f:
            for url in sorted(products):
                f.write(url + '\n')
        print(f"\n✓ Found {len(products)} total Barking Heads products")
        print(f"✓ Saved to barking_all_product_urls.txt")
    
    return list(products)

def main():
    """Main function"""
    print("="*80)
    print("DISCOVERING ALL BURNS & BARKING PRODUCTS")
    print("="*80)
    
    burns_products = discover_burns_products()
    barking_products = discover_barking_products()
    
    print("\n" + "="*80)
    print("DISCOVERY COMPLETE")
    print("="*80)
    print(f"✓ Burns: {len(burns_products)} products")
    print(f"✓ Barking: {len(barking_products)} products")
    
    return burns_products, barking_products

if __name__ == "__main__":
    main()