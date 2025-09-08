#!/usr/bin/env python3
"""
Improved Zooplus connector - properly extracts products, names, and nutrition
"""
import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote_plus
import logging
import time

from .base_connector import RetailerConnector

logger = logging.getLogger(__name__)


class ZooplusConnectorV2(RetailerConnector):
    """Improved Zooplus connector with better extraction"""
    
    def __init__(self, config_path: str = None):
        super().__init__('zooplus', config_path)
        
        self.base_url = 'https://www.zooplus.co.uk'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
    def search_brand(self, brand_name: str, page: int = 1) -> List[Dict]:
        """
        Search for products by brand on category/search pages
        Extracts from JSON-LD on category pages which has product info
        """
        self.rate_limit()
        
        # Try brand-specific category URL first
        brand_slug = brand_name.lower().replace(' ', '_').replace("'", '')
        category_urls = [
            f"{self.base_url}/shop/dogs/dry_dog_food/{brand_slug}_dog_food",
            f"{self.base_url}/shop/dogs/dry_dog_food/{brand_slug}",
            f"{self.base_url}/shop/search?q={quote_plus(brand_name)}"
        ]
        
        products = []
        
        for url in category_urls:
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code != 200:
                    continue
                    
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract from JSON-LD structured data on category pages
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        
                        # Look for CollectionPage with products
                        if data.get('@type') == 'CollectionPage':
                            main_entity = data.get('mainEntity', {})
                            if main_entity.get('@type') == 'ItemList':
                                items = main_entity.get('itemListElement', [])
                                
                                for list_item in items:
                                    product_data = list_item.get('item', {})
                                    if product_data.get('@type') == 'Product':
                                        # Check if it's the right brand
                                        brand_info = product_data.get('brand', {})
                                        product_brand = brand_info.get('name', '') if isinstance(brand_info, dict) else str(brand_info)
                                        
                                        if isinstance(product_brand, list):
                                            product_brand = product_brand[0] if product_brand else ''
                                        
                                        # Check brand match
                                        if brand_name.lower() in product_brand.lower():
                                            product = self._parse_category_product(product_data)
                                            if product:
                                                products.append(product)
                                                
                    except json.JSONDecodeError:
                        continue
                
                if products:
                    logger.info(f"Found {len(products)} products for '{brand_name}' from {url}")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                continue
        
        # If no products from category pages, extract product URLs and fetch individually
        if not products:
            products = self._extract_product_urls_and_fetch(brand_name)
        
        return products[:20]  # Limit to 20 for testing
    
    def _parse_category_product(self, product_data: Dict) -> Optional[Dict]:
        """Parse product from category page JSON-LD"""
        try:
            # Extract product URL
            offers = product_data.get('offers', {})
            product_url = offers.get('url', '') if isinstance(offers, dict) else ''
            
            if not product_url:
                return None
            
            # Extract product ID from URL
            product_id = self._extract_product_id_from_url(product_url)
            
            # Extract price
            price = offers.get('price') if isinstance(offers, dict) else None
            
            # Extract brand
            brand_data = product_data.get('brand', {})
            brand_name = brand_data.get('name', '') if isinstance(brand_data, dict) else str(brand_data)
            if isinstance(brand_name, list):
                brand_name = brand_name[0] if brand_name else ''
            
            return {
                'id': product_id,
                'name': product_data.get('name', ''),
                'description': product_data.get('description', ''),
                'url': product_url,
                'image': product_data.get('image', ''),
                'brand': brand_name,
                'price': float(price) if price else None,
                'currency': offers.get('priceCurrency', 'GBP') if isinstance(offers, dict) else 'GBP',
                'in_stock': 'InStock' in offers.get('availability', '') if isinstance(offers, dict) else False
            }
            
        except Exception as e:
            logger.error(f"Error parsing category product: {e}")
            return None
    
    def _extract_product_urls_and_fetch(self, brand_name: str) -> List[Dict]:
        """Fallback: Extract product URLs from HTML and fetch details"""
        products = []
        
        url = f"{self.base_url}/shop/search?q={quote_plus(brand_name)}"
        
        try:
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find product links
            product_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Match product URLs with numeric IDs
                if re.search(r'/\d+/?$', href):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in product_links:
                        product_links.append(full_url)
            
            logger.info(f"Found {len(product_links)} product URLs to fetch")
            
            # Fetch details for each product
            for product_url in product_links[:5]:  # Limit for testing
                self.rate_limit()
                product_details = self.get_product_details(product_url)
                if product_details:
                    products.append(product_details)
                    
        except Exception as e:
            logger.error(f"Error extracting product URLs: {e}")
        
        return products
    
    def _extract_product_id_from_url(self, url: str) -> Optional[str]:
        """Extract product ID from URL"""
        if not url:
            return None
        
        # Extract numeric ID from end of URL
        match = re.search(r'/(\d+)/?(?:\?.*)?$', url)
        if match:
            return match.group(1)
        
        return None
    
    def get_product_details(self, product_url: str) -> Optional[Dict]:
        """
        Get detailed product information including nutrition
        """
        self.rate_limit()
        
        if not product_url.startswith('http'):
            product_url = urljoin(self.base_url, product_url)
        
        try:
            response = self.session.get(product_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            product = {
                'url': product_url,
                'id': self._extract_product_id_from_url(product_url)
            }
            
            # Extract product name from h1 or title
            name_elem = soup.find('h1')
            if name_elem:
                product['name'] = name_elem.get_text(strip=True)
            else:
                title = soup.find('title')
                if title:
                    # Clean up title - remove site suffix
                    product['name'] = title.get_text(strip=True).split('|')[0].strip()
            
            # Try JSON-LD for basic info
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if data.get('@type') == 'Product':
                        # Update with JSON-LD data
                        product['brand'] = self._extract_brand_from_json_ld(data)
                        
                        offers = data.get('offers', {})
                        if isinstance(offers, dict):
                            product['price'] = offers.get('price')
                            product['currency'] = offers.get('priceCurrency', 'GBP')
                            product['in_stock'] = 'InStock' in offers.get('availability', '')
                        
                        product['image'] = data.get('image', '')
                        
                        # Use JSON-LD name if better than what we found
                        json_name = data.get('name', '')
                        if json_name and len(json_name) > len(product.get('name', '')):
                            product['name'] = json_name
                            
                except json.JSONDecodeError:
                    continue
            
            # Extract nutrition - this is critical!
            nutrition = self._extract_nutrition_from_page(soup)
            product.update(nutrition)
            
            # Extract ingredients
            ingredients = self._extract_ingredients_from_page(soup)
            if ingredients:
                product['ingredients'] = ingredients
            
            # Extract all images
            images = []
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src', '')
                if src and any(keyword in src.lower() for keyword in ['product', 'media', 'bilder']):
                    if not src.startswith('http'):
                        src = urljoin(self.base_url, src)
                    if src not in images:
                        images.append(src)
            
            if images:
                product['images'] = images[:5]
                if not product.get('image'):
                    product['image'] = images[0]
            
            # Extract pack sizes
            pack_sizes = self._extract_pack_sizes(soup)
            if pack_sizes:
                product['pack_sizes'] = pack_sizes
            
            logger.info(f"Extracted product: {product.get('name', 'Unknown')} with {len([k for k in ['protein', 'fat', 'fiber'] if k in product])} nutrition values")
            
            return product
            
        except Exception as e:
            logger.error(f"Error getting product details for {product_url}: {e}")
            return None
    
    def _extract_brand_from_json_ld(self, data: Dict) -> str:
        """Extract brand from JSON-LD data"""
        brand_data = data.get('brand', {})
        if isinstance(brand_data, dict):
            brand = brand_data.get('name', '')
        else:
            brand = str(brand_data)
        
        if isinstance(brand, list):
            brand = brand[0] if brand else ''
            
        return brand
    
    def _extract_nutrition_from_page(self, soup: BeautifulSoup) -> Dict:
        """
        Extract nutrition data with improved patterns
        """
        nutrition = {}
        
        # Get all text from page
        page_text = soup.get_text()
        
        # Look for analytical constituents section
        # This section usually contains all nutrition info together
        analytical_patterns = [
            r'Analytical [Cc]onstituents[:\s]*([^€£$]{50,500})',
            r'Guaranteed [Aa]nalysis[:\s]*([^€£$]{50,500})',
            r'[Nn]utritional [Aa]nalysis[:\s]*([^€£$]{50,500})',
            r'[Cc]omposition [Aa]nalysis[:\s]*([^€£$]{50,500})'
        ]
        
        nutrition_text = ""
        for pattern in analytical_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
            if match:
                nutrition_text = match.group(1)
                break
        
        # If no section found, search whole page
        if not nutrition_text:
            nutrition_text = page_text
        
        # Extract individual nutrients with multiple pattern variations
        nutrient_patterns = {
            'protein': [
                r'[Cc]rude [Pp]rotein[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Pp]rotein[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Pp]rotein[^\d]*([0-9]+(?:[.,][0-9]+)?)\s*%'
            ],
            'fat': [
                r'[Cc]rude [Ff]at[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Ff]at [Cc]ontent[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Ff]ats?[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Oo]ils and [Ff]ats[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
            ],
            'fiber': [
                r'[Cc]rude [Ff]ibre[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Cc]rude [Ff]iber[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Ff]ibre[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Ff]iber[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
            ],
            'ash': [
                r'[Cc]rude [Aa]sh[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Aa]sh[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Ii]norganic [Mm]atter[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
            ],
            'moisture': [
                r'[Mm]oisture[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Ww]ater[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%',
                r'[Mm]oisture [Cc]ontent[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%'
            ]
        }
        
        for nutrient, patterns in nutrient_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, nutrition_text)
                if match:
                    value = match.group(1).replace(',', '.')
                    try:
                        nutrition[nutrient] = float(value)
                        break
                    except ValueError:
                        continue
        
        # Also check tables for nutrition data
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    # Match nutrients
                    if 'protein' in label and 'protein' not in nutrition:
                        match = re.search(r'([0-9]+(?:[.,][0-9]+)?)', value)
                        if match:
                            nutrition['protein'] = float(match.group(1).replace(',', '.'))
                    elif 'fat' in label and 'fat' not in nutrition:
                        match = re.search(r'([0-9]+(?:[.,][0-9]+)?)', value)
                        if match:
                            nutrition['fat'] = float(match.group(1).replace(',', '.'))
                    elif ('fibre' in label or 'fiber' in label) and 'fiber' not in nutrition:
                        match = re.search(r'([0-9]+(?:[.,][0-9]+)?)', value)
                        if match:
                            nutrition['fiber'] = float(match.group(1).replace(',', '.'))
        
        return nutrition
    
    def _extract_ingredients_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract ingredients with improved patterns"""
        page_text = soup.get_text()
        
        # Look for ingredients section
        ingredients_patterns = [
            r'[Cc]omposition[:\s]*([^€£$]{50,1000})(?:[Aa]nalytical|[Aa]dditives|[Nn]utritional)',
            r'[Ii]ngredients[:\s]*([^€£$]{50,1000})(?:[Aa]nalytical|[Aa]dditives|[Nn]utritional)',
            r'[Rr]ecipe[:\s]*([^€£$]{50,1000})(?:[Aa]nalytical|[Aa]dditives|[Nn]utritional)'
        ]
        
        for pattern in ingredients_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
            if match:
                ingredients = match.group(1).strip()
                # Clean up
                ingredients = re.sub(r'\s+', ' ', ingredients)
                ingredients = ingredients.replace('\n', ' ')
                return ingredients[:1000]  # Limit length
        
        return None
    
    def _extract_pack_sizes(self, soup: BeautifulSoup) -> List[str]:
        """Extract available pack sizes"""
        pack_sizes = []
        page_text = soup.get_text()
        
        # Common size patterns
        size_patterns = [
            r'(\d+(?:\.\d+)?)\s*kg\b',
            r'(\d+)\s*g\b',
            r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*kg',
            r'(\d+)\s*x\s*(\d+)\s*g'
        ]
        
        for pattern in size_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    size = ' x '.join(match)
                else:
                    size = match
                    
                # Add unit if needed
                if re.match(r'^\d+$', size):
                    continue  # Skip plain numbers
                    
                if size not in pack_sizes:
                    pack_sizes.append(size)
        
        # Sort and deduplicate
        pack_sizes = list(set(pack_sizes))
        
        # Filter out unrealistic sizes
        filtered_sizes = []
        for size in pack_sizes:
            # Extract numeric value
            num_match = re.match(r'(\d+(?:\.\d+)?)', size)
            if num_match:
                value = float(num_match.group(1))
                # Dog food typically between 0.1kg and 20kg per pack
                if 'kg' in size and 0.1 <= value <= 20:
                    filtered_sizes.append(size)
                elif 'g' in size and 50 <= value <= 5000:
                    filtered_sizes.append(size)
        
        return filtered_sizes[:5]  # Limit to 5 sizes
    
    def parse_nutrition(self, product_data: Dict) -> Dict:
        """
        Convert nutrition data to database format
        """
        nutrition = {}
        
        # Map nutrition fields
        nutrition_mapping = {
            'protein': 'protein_percent',
            'fat': 'fat_percent',
            'fiber': 'fiber_percent',
            'ash': 'ash_percent',
            'moisture': 'moisture_percent'
        }
        
        for source_key, target_key in nutrition_mapping.items():
            if source_key in product_data:
                nutrition[target_key] = product_data[source_key]
        
        return nutrition