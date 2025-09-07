#!/usr/bin/env python3
"""
Universal Breed Scraper Web Service - Flask API for ScrapingBee integration
============================================================================

Simple Flask web service that exposes the universal scraper via HTTP endpoints.
Perfect for testing the ScrapingBee integration in Cloud Run.

Endpoints:
- GET / : Health check
- POST /scrape : Scrape a single URL with smart BeautifulSoup → ScrapingBee fallback
- POST /scrape-batch : Scrape multiple URLs
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Import our scraper logic
import sys
import time
import requests
from urllib.parse import quote, urljoin
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalBreedScraper:
    def __init__(self):
        self.scrapingbee_api_key = os.getenv('SCRAPING_BEE')
        self.scrapingbee_endpoint = "https://app.scrapingbee.com/api/v1/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.total_cost_credits = 0

    def needs_javascript(self, html_content: str) -> bool:
        """Detect if page needs JavaScript rendering"""
        js_indicators = [
            'window.ReactDOM', 'ng-app', 'vue.js', 'data-reactroot',
            'window.angular', 'Loading...', 'Please enable JavaScript',
            'window.Vue', 'window.React', '__NUXT__'
        ]
        
        # Check for very small body content (likely JS-rendered)
        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.find('body')
        if body and len(body.get_text(strip=True)) < 200:
            return True
            
        # Check for JS indicators
        return any(indicator in html_content for indicator in js_indicators)

    def fetch_with_beautifulsoup(self, url: str) -> Tuple[Optional[str], bool]:
        """Fetch using BeautifulSoup (free method)"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text, True
        except Exception as e:
            logger.warning(f"BeautifulSoup failed for {url}: {e}")
            return None, False

    def fetch_with_scrapingbee(self, url: str, render_js: bool = True) -> Tuple[Optional[str], bool]:
        """Fetch using ScrapingBee with JavaScript rendering"""
        if not self.scrapingbee_api_key:
            logger.error("ScrapingBee API key not found!")
            return None, False

        params = {
            'api_key': self.scrapingbee_api_key,
            'url': url,
            'render_js': 'true' if render_js else 'false',
            'premium_proxy': 'false',  # Save costs
            'block_resources': 'true',  # Block images/css for speed
        }
        
        try:
            response = requests.get(self.scrapingbee_endpoint, params=params, timeout=60)
            if response.status_code == 200:
                # Track costs (5 credits for JS rendering)
                cost = 5 if render_js else 1
                self.total_cost_credits += cost
                logger.info(f"ScrapingBee success: {cost} credits used (total: {self.total_cost_credits})")
                return response.text, True
            else:
                logger.error(f"ScrapingBee failed: {response.status_code} - {response.text}")
                return None, False
        except Exception as e:
            logger.error(f"ScrapingBee error for {url}: {e}")
            return None, False

    def smart_fetch(self, url: str) -> Tuple[Optional[str], str]:
        """Smart fetch with automatic fallback"""
        # First try BeautifulSoup (free)
        html, success = self.fetch_with_beautifulsoup(url)
        
        if success and html:
            # Check if we need JavaScript
            if self.needs_javascript(html):
                logger.info(f"JavaScript detected for {url}, falling back to ScrapingBee")
                # Fall back to ScrapingBee
                html_sb, success_sb = self.fetch_with_scrapingbee(url)
                if success_sb and html_sb:
                    return html_sb, "scrapingbee"
                else:
                    logger.warning(f"ScrapingBee also failed for {url}, using BeautifulSoup result")
                    return html, "beautifulsoup"
            else:
                return html, "beautifulsoup"
        else:
            # BeautifulSoup failed, try ScrapingBee
            logger.info(f"BeautifulSoup failed for {url}, trying ScrapingBee")
            html_sb, success_sb = self.fetch_with_scrapingbee(url)
            if success_sb and html_sb:
                return html_sb, "scrapingbee"
            else:
                return None, "failed"

    def extract_akc_breed_data(self, html: str, url: str) -> Dict:
        """Extract breed data from AKC pages"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract breed name from URL
        breed_slug = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
        
        data = {
            'breed_slug': breed_slug,
            'display_name': breed_slug.replace('-', ' ').title(),
            'akc_url': url,
            'extraction_timestamp': datetime.now().isoformat(),
            'extraction_status': 'success',
            'has_physical_data': False,
            'has_profile_data': False
        }
        
        # Extract text content
        content_sections = ['about', 'personality', 'health', 'care', 'feeding', 'grooming', 'exercise', 'training', 'history']
        for section in content_sections:
            data[section] = ""
        
        # Try to extract main content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main_content:
            text = main_content.get_text(strip=True)
            data['training'] = text[:500]  # Store first 500 chars as training data
            data['has_profile_data'] = len(text) > 100
        
        return data

# Initialize scraper
scraper = UniversalBreedScraper()

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Universal Breed Scraper',
        'scrapingbee_configured': bool(scraper.scrapingbee_api_key),
        'total_credits_used': scraper.total_cost_credits,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/scrape', methods=['POST'])
def scrape_single():
    """Scrape a single URL"""
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL required in JSON body'}), 400
    
    url = data['url']
    logger.info(f"Scraping: {url}")
    
    try:
        # Fetch with smart fallback
        html, method = scraper.smart_fetch(url)
        
        if html:
            # Extract breed data
            breed_data = scraper.extract_akc_breed_data(html, url)
            breed_data['scraping_method'] = method
            breed_data['scrapingbee_cost'] = 5 if method == 'scrapingbee' else 0
            
            return jsonify(breed_data)
        else:
            return jsonify({
                'error': 'Failed to fetch content',
                'url': url,
                'scraping_method': method
            }), 500
            
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return jsonify({'error': str(e), 'url': url}), 500

@app.route('/scrape-batch', methods=['POST'])
def scrape_batch():
    """Scrape multiple URLs"""
    data = request.get_json()
    if not data or 'urls' not in data:
        return jsonify({'error': 'URLs array required in JSON body'}), 400
    
    urls = data['urls']
    limit = data.get('limit', len(urls))
    results = []
    
    logger.info(f"Batch scraping {min(limit, len(urls))} URLs")
    
    for i, url in enumerate(urls[:limit]):
        try:
            logger.info(f"Processing {i+1}/{limit}: {url}")
            
            # Fetch with smart fallback
            html, method = scraper.smart_fetch(url)
            
            if html:
                breed_data = scraper.extract_akc_breed_data(html, url)
                breed_data['scraping_method'] = method
                breed_data['scrapingbee_cost'] = 5 if method == 'scrapingbee' else 0
                results.append(breed_data)
            else:
                results.append({
                    'error': 'Failed to fetch',
                    'url': url,
                    'scraping_method': method
                })
            
            # Rate limiting
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            results.append({'error': str(e), 'url': url})
    
    return jsonify({
        'total_processed': len(results),
        'total_cost_credits': scraper.total_cost_credits,
        'estimated_cost_usd': scraper.total_cost_credits * 0.001,
        'results': results
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)