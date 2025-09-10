#!/usr/bin/env python3
import requests
import json

print("Testing PFX API...")

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; LupitoBot/1.0)'})

# Test just first 3 pages
for page in [1, 2, 3]:
    url = f"https://petfoodexpert.com/api/products?species=dog&page={page}"
    print(f"Page {page}: ", end="")
    
    try:
        response = session.get(url, timeout=10)
        data = response.json()
        products = data.get('data', [])
        print(f"{len(products)} products")
    except Exception as e:
        print(f"ERROR: {e}")
        break

print("API test complete!")