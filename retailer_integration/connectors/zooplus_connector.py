#!/usr/bin/env python3
"""
Zooplus connector - scrapes structured data from Zooplus UK
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


class ZooplusConnector(RetailerConnector):
    """Connector for Zooplus using structured data scraping"""
    
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
        Search for products by brand name using Zooplus search
        
        Args:
            brand_name: Brand to search for
            page: Page number for pagination
            
        Returns:
            List of basic product information
        """
        self.rate_limit()
        
        # Construct search URL
        search_url = f"{self.base_url}/shop/search"
        params = {
            'q': brand_name,
            'page': page
        }
        
        try:
            response = self.session.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract products from search results
            products = []
            
            # Look for JSON-LD structured data first
            json_ld_products = self._extract_json_ld_products(soup)
            if json_ld_products:
                products.extend(json_ld_products)
            
            # Fallback to HTML parsing
            if not products:
                products = self._extract_html_products(soup)
            
            logger.info(f"Found {len(products)} products for brand '{brand_name}' on page {page}")
            return products
            
        except Exception as e:
            logger.error(f"Error searching for brand {brand_name}: {e}")
            return []
    
    def _extract_json_ld_products(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract products from JSON-LD structured data"""
        products = []
        
        # Find JSON-LD script tags
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                
                # Handle CollectionPage with ItemList
                if data.get('@type') == 'CollectionPage':
                    main_entity = data.get('mainEntity', {})
                    if main_entity.get('@type') == 'ItemList':
                        items = main_entity.get('itemListElement', [])
                        
                        for item in items:
                            product_data = item.get('item', {})
                            if product_data.get('@type') == 'Product':
                                product = self._parse_json_ld_product(product_data)
                                if product:
                                    products.append(product)
                
                # Handle direct Product array
                elif isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Product':
                            product = self._parse_json_ld_product(item)
                            if product:
                                products.append(product)
                
                # Handle single Product
                elif data.get('@type') == 'Product':
                    product = self._parse_json_ld_product(data)
                    if product:
                        products.append(product)
                        
            except json.JSONDecodeError:
                continue
        
        return products
    
    def _parse_json_ld_product(self, product_data: Dict) -> Optional[Dict]:
        """Parse a single product from JSON-LD data"""
        try:
            # Extract product URL to get ID
            product_url = product_data.get('url', '')
            product_id = self._extract_product_id_from_url(product_url)
            
            if not product_id:
                return None
            
            # Extract offers/price information
            offers = product_data.get('offers', {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            
            price = None
            currency = 'GBP'
            in_stock = False
            
            if offers:
                price = offers.get('price')
                currency = offers.get('priceCurrency', 'GBP')
                availability = offers.get('availability', '')
                in_stock = 'InStock' in availability
            
            # Extract brand
            brand_data = product_data.get('brand', {})
            brand_name = brand_data.get('name', '') if isinstance(brand_data, dict) else str(brand_data)
            
            if isinstance(brand_name, list):
                brand_name = brand_name[0] if brand_name else ''
            
            # Extract aggregated rating
            rating = None
            review_count = None
            aggregate_rating = product_data.get('aggregateRating', {})
            if aggregate_rating:
                rating = aggregate_rating.get('ratingValue')
                review_count = aggregate_rating.get('reviewCount')
            
            return {
                'id': product_id,
                'name': product_data.get('name', ''),
                'description': product_data.get('description', ''),
                'url': product_url,
                'image': product_data.get('image', ''),
                'brand': brand_name,
                'price': float(price) if price else None,
                'currency': currency,
                'in_stock': in_stock,
                'rating': float(rating) if rating else None,
                'review_count': int(review_count) if review_count else None
            }
            
        except Exception as e:
            logger.error(f"Error parsing JSON-LD product: {e}")
            return None
    
    def _extract_html_products(self, soup: BeautifulSoup) -> List[Dict]:
        """Fallback HTML parsing for products"""
        products = []
        
        # Common selectors for product cards
        product_selectors = [
            'article[data-product-id]',
            '.product-card',
            '.product-tile',
            '[data-testid*="product"]'
        ]
        
        for selector in product_selectors:
            product_elements = soup.select(selector)
            if product_elements:
                logger.info(f"Using selector: {selector} - found {len(product_elements)} products")
                
                for element in product_elements:
                    product = self._parse_html_product(element)
                    if product:
                        products.append(product)
                break
        
        return products
    
    def _parse_html_product(self, element) -> Optional[Dict]:
        """Parse product from HTML element"""
        try:
            # Extract product ID
            product_id = (
                element.get('data-product-id') or
                element.get('data-product-sku') or
                element.get('id', '').replace('product-', '')
            )
            
            if not product_id:
                # Try to extract from link
                link = element.find('a')
                if link and link.get('href'):
                    product_id = self._extract_product_id_from_url(link['href'])
            
            # Extract product name
            name_element = element.find(['h2', 'h3', 'a'], class_=re.compile(r'product.*name|title', re.I))
            name = name_element.get_text(strip=True) if name_element else ''
            
            # Extract brand
            brand_element = element.find(class_=re.compile(r'brand', re.I))
            brand = brand_element.get_text(strip=True) if brand_element else ''
            
            # Extract price
            price_element = element.find(class_=re.compile(r'price', re.I))
            price = None
            if price_element:
                price_text = price_element.get_text(strip=True)
                price_match = re.search(r'[\d.,]+', price_text.replace(',', ''))
                if price_match:
                    price = float(price_match.group())
            
            # Extract image
            img_element = element.find('img')
            image_url = ''
            if img_element:
                image_url = img_element.get('src') or img_element.get('data-src', '')
                if image_url and not image_url.startswith('http'):
                    image_url = urljoin(self.base_url, image_url)
            
            # Extract product URL
            link_element = element.find('a')
            product_url = ''
            if link_element and link_element.get('href'):
                product_url = urljoin(self.base_url, link_element['href'])
            
            if not product_id or not name:
                return None
            
            return {
                'id': product_id,
                'name': name,
                'brand': brand,
                'price': price,
                'currency': 'GBP',
                'image': image_url,
                'url': product_url,
                'in_stock': True  # Assume in stock if shown in search
            }
            
        except Exception as e:
            logger.error(f"Error parsing HTML product: {e}")
            return None
    
    def _extract_product_id_from_url(self, url: str) -> Optional[str]:
        """Extract product ID from Zooplus URL"""
        if not url:
            return None
        
        # Common Zooplus URL patterns
        patterns = [
            r'/(\d+)/?$',  # Product ID at end of URL
            r'/product[/-](\d+)',  # /product/123 or /product-123
            r'/p/(\d+)',  # /p/123
            r'product[_-]?id[=:](\d+)',  # product_id=123 or productId:123
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_product_details(self, product_id: str) -> Optional[Dict]:
        """
        Get detailed product information from product page
        
        Args:
            product_id: Product ID or URL
            
        Returns:
            Detailed product dictionary
        """
        self.rate_limit()
        
        # Construct product URL if we only have ID
        if product_id.isdigit():
            # Need to find actual product URL - this is a limitation
            # For now, we'll try common URL patterns
            possible_urls = [
                f"{self.base_url}/shop/dogs/dry_dog_food/product/{product_id}",
                f"{self.base_url}/shop/product/{product_id}",
                f"{self.base_url}/p/{product_id}"
            ]
            
            for product_url in possible_urls:
                response = self.session.head(product_url)
                if response.status_code == 200:
                    break
            else:
                logger.warning(f"Could not find URL for product ID: {product_id}")
                return None
        else:
            product_url = product_id if product_id.startswith('http') else f"{self.base_url}{product_id}"
        
        try:
            response = self.session.get(product_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract detailed product information
            product_details = self._extract_product_details(soup, product_url)
            
            if product_details:
                logger.info(f"Extracted details for product: {product_details.get('name', product_id)}")
            
            return product_details
            
        except Exception as e:
            logger.error(f"Error getting product details for {product_id}: {e}")
            return None
    
    def _extract_product_details(self, soup: BeautifulSoup, product_url: str) -> Optional[Dict]:
        """Extract detailed product information from product page"""
        try:
            product = {
                'url': product_url,
                'id': self._extract_product_id_from_url(product_url)
            }
            
            # Try JSON-LD first
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if data.get('@type') == 'Product':
                        product.update(self._parse_json_ld_product(data))
                        break
                except:
                    continue
            
            # Extract additional details not in JSON-LD
            
            # Nutrition information
            nutrition_info = self._extract_nutrition_info(soup)
            product.update(nutrition_info)
            
            # Ingredients
            ingredients = self._extract_ingredients(soup)
            if ingredients:
                product['ingredients'] = ingredients
            
            # Multiple images
            images = self._extract_all_images(soup)
            if images:
                product['images'] = images
                if not product.get('image'):
                    product['image'] = images[0]
            
            # Additional product details
            additional_details = self._extract_additional_details(soup)
            product.update(additional_details)
            
            return product
            
        except Exception as e:
            logger.error(f"Error extracting product details: {e}")
            return None
    
    def _extract_nutrition_info(self, soup: BeautifulSoup) -> Dict:
        """Extract nutrition information from product page"""
        nutrition = {}
        
        # Look for nutrition table or structured data
        nutrition_selectors = [
            '.nutrition-facts',
            '.nutritional-info', 
            '.analytical-constituents',
            'table.nutrition',
            '[data-testid*="nutrition"]'
        ]
        
        for selector in nutrition_selectors:
            element = soup.select_one(selector)
            if element:
                nutrition.update(self._parse_nutrition_element(element))
                break
        
        # Look for specific nutrition values in text
        page_text = soup.get_text().lower()
        nutrition_patterns = {
            'protein': r'protein[:\s]*([0-9.,]+)\s*%',
            'fat': r'fat[:\s]*([0-9.,]+)\s*%|crude fat[:\s]*([0-9.,]+)\s*%',
            'fiber': r'fiber[:\s]*([0-9.,]+)\s*%|fibre[:\s]*([0-9.,]+)\s*%|crude fiber[:\s]*([0-9.,]+)\s*%',
            'ash': r'ash[:\s]*([0-9.,]+)\s*%|crude ash[:\s]*([0-9.,]+)\s*%',
            'moisture': r'moisture[:\s]*([0-9.,]+)\s*%'
        }
        
        for nutrient, pattern in nutrition_patterns.items():
            if nutrient not in nutrition:
                match = re.search(pattern, page_text)
                if match:
                    # Get first non-None group
                    value = next((g for g in match.groups() if g), None)
                    if value:
                        nutrition[nutrient] = float(value.replace(',', '.'))
        
        return nutrition
    
    def _parse_nutrition_element(self, element) -> Dict:
        """Parse nutrition from HTML element"""
        nutrition = {}
        
        # Try table format first
        if element.name == 'table':
            rows = element.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    nutrient = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    # Parse value
                    value_match = re.search(r'([0-9.,]+)', value.replace(',', '.'))
                    if value_match:
                        value_float = float(value_match.group(1))
                        
                        if 'protein' in nutrient:
                            nutrition['protein'] = value_float
                        elif 'fat' in nutrient:
                            nutrition['fat'] = value_float
                        elif 'fiber' in nutrient or 'fibre' in nutrient:
                            nutrition['fiber'] = value_float
                        elif 'ash' in nutrient:
                            nutrition['ash'] = value_float
                        elif 'moisture' in nutrient:
                            nutrition['moisture'] = value_float
        
        else:
            # Parse from div/span structure
            text = element.get_text()
            nutrition_patterns = {
                'protein': r'protein[:\s]*([0-9.,]+)\s*%',
                'fat': r'fat[:\s]*([0-9.,]+)\s*%',
                'fiber': r'fiber[:\s]*([0-9.,]+)\s*%|fibre[:\s]*([0-9.,]+)\s*%',
                'ash': r'ash[:\s]*([0-9.,]+)\s*%',
                'moisture': r'moisture[:\s]*([0-9.,]+)\s*%'
            }
            
            for nutrient, pattern in nutrition_patterns.items():
                match = re.search(pattern, text.lower())
                if match:
                    value = next((g for g in match.groups() if g), None)
                    if value:
                        nutrition[nutrient] = float(value.replace(',', '.'))
        
        return nutrition
    
    def _extract_ingredients(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract ingredients list"""
        ingredients_selectors = [
            '.ingredients',
            '.composition',
            '[data-testid*="ingredient"]',
            'div:contains("Composition")',
            'div:contains("Ingredients")'
        ]
        
        for selector in ingredients_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return None
    
    def _extract_all_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract all product images"""
        images = []
        
        # Look for image gallery or product images
        img_elements = soup.find_all('img')
        
        for img in img_elements:
            src = img.get('src') or img.get('data-src')
            if src and any(keyword in src.lower() for keyword in ['product', 'media', 'bilder']):
                if not src.startswith('http'):
                    src = urljoin(self.base_url, src)
                if src not in images:
                    images.append(src)
        
        return images[:5]  # Limit to 5 images
    
    def _extract_additional_details(self, soup: BeautifulSoup) -> Dict:
        """Extract additional product details"""
        details = {}
        
        # Extract pack sizes
        pack_size_text = soup.get_text()
        size_patterns = [
            r'(\d+(?:\.\d+)?)\s*kg',
            r'(\d+(?:\.\d+)?)\s*g',
            r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*kg'
        ]
        
        pack_sizes = []
        for pattern in size_patterns:
            matches = re.findall(pattern, pack_size_text)
            for match in matches:
                if isinstance(match, tuple):
                    pack_sizes.append(' x '.join(match))
                else:
                    pack_sizes.append(match)
        
        if pack_sizes:
            details['pack_sizes'] = list(set(pack_sizes))  # Remove duplicates
        
        return details
    
    def parse_nutrition(self, product_data: Dict) -> Dict:
        """
        Parse nutrition data from product
        
        Args:
            product_data: Product dictionary
            
        Returns:
            Nutrition data in standardized format
        """
        nutrition = {}
        
        # Map from extracted nutrition data
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