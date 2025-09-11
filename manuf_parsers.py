#!/usr/bin/env python3
"""
Parsers for manufacturer data extraction from HTML, JSON-LD, and PDFs
"""

import re
import json
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import PyPDF2
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class ManufacturerParser:
    """Base parser for manufacturer data"""
    
    # Allergen mapping (same as before)
    ALLERGEN_MAP = {
        'chicken': ['chicken', 'poultry', 'fowl', 'hen'],
        'beef': ['beef', 'bovine', 'cattle', 'veal'],
        'pork': ['pork', 'swine', 'bacon', 'ham'],
        'lamb': ['lamb', 'mutton', 'sheep'],
        'fish': ['fish', 'salmon', 'tuna', 'cod', 'herring', 'anchovy', 'sardine', 'mackerel'],
        'egg': ['egg', 'eggs', 'albumin', 'albumen'],
        'dairy': ['milk', 'cheese', 'yogurt', 'dairy', 'lactose', 'whey', 'casein'],
        'grain': ['wheat', 'corn', 'rice', 'barley', 'oats', 'grain', 'cereal'],
        'soy': ['soy', 'soya', 'soybean', 'tofu'],
        'gluten': ['gluten', 'wheat', 'barley', 'rye']
    }
    
    def normalize_ingredients(self, text: str) -> List[str]:
        """Normalize and tokenize ingredients text"""
        if not text:
            return []
        
        # Clean text
        text = text.lower()
        text = re.sub(r'[^\w\s,()]', ' ', text)
        
        # Split by common delimiters
        tokens = re.split(r'[,;]', text)
        
        # Clean and filter tokens
        clean_tokens = []
        for token in tokens:
            token = token.strip()
            # Remove percentages and numbers
            token = re.sub(r'\d+\.?\d*\s*%?', '', token).strip()
            if len(token) > 2:
                clean_tokens.append(token)
        
        return clean_tokens
    
    def detect_allergens(self, ingredients: List[str]) -> List[str]:
        """Detect allergen groups from ingredients"""
        allergens = set()
        ingredients_text = ' '.join(ingredients).lower()
        
        for allergen, keywords in self.ALLERGEN_MAP.items():
            for keyword in keywords:
                if keyword in ingredients_text:
                    allergens.add(allergen)
                    break
        
        return sorted(list(allergens))
    
    def parse_analytical_constituents(self, text: str) -> Dict[str, float]:
        """Parse analytical constituents (protein, fat, etc.)"""
        constituents = {}
        
        if not text:
            return constituents
        
        text = text.lower()
        
        # Common patterns
        patterns = {
            'protein': r'(?:crude\s+)?protein[:\s]+([0-9.]+)\s*%',
            'fat': r'(?:crude\s+)?(?:fat|oils)[:\s]+([0-9.]+)\s*%',
            'fiber': r'(?:crude\s+)?fib(?:re|er)[:\s]+([0-9.]+)\s*%',
            'ash': r'(?:crude\s+)?ash[:\s]+([0-9.]+)\s*%',
            'moisture': r'moisture[:\s]+([0-9.]+)\s*%',
            'carbohydrate': r'carbohydrate[:\s]+([0-9.]+)\s*%'
        }
        
        for nutrient, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    constituents[f'{nutrient}_percent'] = float(match.group(1))
                except ValueError:
                    pass
        
        return constituents
    
    def calculate_kcal(self, constituents: Dict[str, float]) -> Optional[float]:
        """Calculate kcal/100g using Atwater factors"""
        protein = constituents.get('protein_percent', 0)
        fat = constituents.get('fat_percent', 0)
        carbs = constituents.get('carbohydrate_percent', 0)
        
        # If no carbs but we have other values, estimate
        if carbs == 0 and protein > 0 and fat > 0:
            fiber = constituents.get('fiber_percent', 0)
            ash = constituents.get('ash_percent', 0)
            moisture = constituents.get('moisture_percent', 0)
            carbs = max(0, 100 - protein - fat - fiber - ash - moisture)
        
        if protein > 0 or fat > 0 or carbs > 0:
            # Atwater factors for pet food
            kcal = (protein * 3.5) + (fat * 8.5) + (carbs * 3.5)
            return round(kcal, 1)
        
        return None
    
    def detect_form(self, text: str) -> Optional[str]:
        """Detect product form (dry, wet, etc.)"""
        if not text:
            return None
        
        text = text.lower()
        
        if any(word in text for word in ['dry', 'kibble', 'biscuit', 'crunchy']):
            return 'dry'
        elif any(word in text for word in ['wet', 'can', 'canned', 'pouch', 'pate', 'chunks', 'jelly', 'gravy', 'sauce']):
            return 'wet'
        elif any(word in text for word in ['raw', 'frozen', 'fresh']):
            return 'raw'
        elif 'freeze' in text and 'dried' in text:
            return 'freeze_dried'
        
        return None
    
    def detect_life_stage(self, text: str) -> Optional[str]:
        """Detect life stage (for dogs only)"""
        if not text:
            return None
        
        text = text.lower()
        
        # Exclude cat products
        if any(word in text for word in ['cat', 'kitten', 'feline']):
            return None
        
        if any(word in text for word in ['puppy', 'junior', 'growth']):
            return 'puppy'
        elif any(word in text for word in ['senior', 'mature', '7+', '11+', 'aging']):
            return 'senior'
        elif any(word in text for word in ['adult', 'maintenance']):
            return 'adult'
        elif any(phrase in text for phrase in ['all life stages', 'all ages']):
            return 'all'
        
        return None
    
    def parse_pack_size(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse pack size and weight"""
        if not text:
            return None
        
        text = text.lower()
        
        # Pattern 1: Multipack (e.g., "24x400g")
        multipack = re.search(r'(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l|oz|lb)', text)
        if multipack:
            count = int(multipack.group(1))
            size = float(multipack.group(2))
            unit = multipack.group(3)
            
            # Convert to kg
            if unit == 'g':
                total_kg = (count * size) / 1000
            elif unit == 'kg':
                total_kg = count * size
            elif unit == 'lb':
                total_kg = (count * size) * 0.453592
            elif unit == 'oz':
                total_kg = (count * size) * 0.0283495
            else:
                total_kg = None
            
            return {
                'pack_count': count,
                'unit_size': size,
                'unit': unit,
                'total_kg': total_kg
            }
        
        # Pattern 2: Single pack (e.g., "2kg", "400g")
        single = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l|oz|lb)', text)
        if single:
            size = float(single.group(1))
            unit = single.group(2)
            
            # Convert to kg
            if unit == 'g':
                total_kg = size / 1000
            elif unit == 'kg':
                total_kg = size
            elif unit == 'lb':
                total_kg = size * 0.453592
            elif unit == 'oz':
                total_kg = size * 0.0283495
            else:
                total_kg = None
            
            return {
                'pack_count': 1,
                'unit_size': size,
                'unit': unit,
                'total_kg': total_kg
            }
        
        return None


class HTMLParser(ManufacturerParser):
    """Parser for HTML content"""
    
    def parse(self, html: str, selectors: Dict) -> Dict:
        """Parse HTML using provided selectors"""
        soup = BeautifulSoup(html, 'html.parser')
        data = {}
        
        # Extract text content
        full_text = soup.get_text()
        
        # Product name
        if 'product_name' in selectors:
            element = soup.select_one(selectors['product_name'].get('css', ''))
            if element:
                data['product_name'] = element.get_text(strip=True)
        
        # Ingredients
        ingredients_text = None
        if 'ingredients' in selectors:
            element = soup.select_one(selectors['ingredients'].get('css', ''))
            if element:
                ingredients_text = element.get_text(strip=True)
            elif 'regex' in selectors['ingredients']:
                match = re.search(selectors['ingredients']['regex'], full_text, re.IGNORECASE)
                if match:
                    ingredients_text = match.group(1)
        
        if ingredients_text:
            data['ingredients_text'] = ingredients_text
            data['ingredients_tokens'] = self.normalize_ingredients(ingredients_text)
            data['allergen_groups'] = self.detect_allergens(data['ingredients_tokens'])
        
        # Analytical constituents
        analytical_text = None
        if 'analytical_constituents' in selectors:
            element = soup.select_one(selectors['analytical_constituents'].get('css', ''))
            if element:
                analytical_text = element.get_text(strip=True)
            elif 'regex' in selectors['analytical_constituents']:
                match = re.search(selectors['analytical_constituents']['regex'], full_text, re.IGNORECASE)
                if match:
                    analytical_text = match.group(0)
        
        if analytical_text:
            constituents = self.parse_analytical_constituents(analytical_text)
            data.update(constituents)
            
            # Calculate kcal if not present
            kcal = self.calculate_kcal(constituents)
            if kcal:
                data['kcal_per_100g'] = kcal
                data['kcal_from'] = 'calculated'
        
        # Form
        data['form'] = self.detect_form(full_text)
        
        # Life stage
        data['life_stage'] = self.detect_life_stage(full_text)
        
        # Pack size
        if 'pack_size' in selectors:
            element = soup.select_one(selectors['pack_size'].get('css', ''))
            if element:
                pack_info = self.parse_pack_size(element.get_text(strip=True))
                if pack_info:
                    data['pack_size'] = pack_info
        
        # Price
        if 'price' in selectors:
            element = soup.select_one(selectors['price'].get('css', ''))
            if element:
                price_text = element.get_text(strip=True)
                # Extract numeric price
                price_match = re.search(r'([0-9.,]+)', price_text)
                if price_match:
                    try:
                        price = float(price_match.group(1).replace(',', ''))
                        data['price'] = price
                        
                        # Calculate price per kg if we have pack size
                        if 'pack_size' in data and data['pack_size'].get('total_kg'):
                            data['price_per_kg'] = round(price / data['pack_size']['total_kg'], 2)
                    except ValueError:
                        pass
        
        return data


class JSONLDParser(ManufacturerParser):
    """Parser for JSON-LD structured data"""
    
    def parse(self, jsonld: Dict) -> Dict:
        """Parse JSON-LD Product schema"""
        data = {}
        
        # Basic product info
        data['product_name'] = jsonld.get('name', '')
        data['description'] = jsonld.get('description', '')
        data['brand'] = jsonld.get('brand', {}).get('name', '') if isinstance(jsonld.get('brand'), dict) else jsonld.get('brand', '')
        
        # SKU/GTIN
        data['sku'] = jsonld.get('sku', '')
        data['gtin'] = jsonld.get('gtin13', '') or jsonld.get('gtin12', '') or jsonld.get('gtin8', '')
        
        # Images
        if 'image' in jsonld:
            images = jsonld['image']
            if isinstance(images, str):
                data['image_url'] = images
            elif isinstance(images, list) and images:
                data['image_url'] = images[0]
        
        # Price info from Offer
        if 'offers' in jsonld:
            offers = jsonld['offers']
            if isinstance(offers, dict):
                offers = [offers]
            
            if isinstance(offers, list) and offers:
                offer = offers[0]  # Take first offer
                
                if 'price' in offer:
                    try:
                        data['price'] = float(offer['price'])
                        data['price_currency'] = offer.get('priceCurrency', 'EUR')
                    except (ValueError, TypeError):
                        pass
                
                data['availability'] = offer.get('availability', '')
        
        # Nutrition info (if present in additionalProperty)
        if 'additionalProperty' in jsonld:
            for prop in jsonld['additionalProperty']:
                if isinstance(prop, dict):
                    name = prop.get('name', '').lower()
                    value = prop.get('value')
                    
                    if 'protein' in name:
                        data['protein_percent'] = self._extract_number(value)
                    elif 'fat' in name:
                        data['fat_percent'] = self._extract_number(value)
                    elif 'fiber' in name or 'fibre' in name:
                        data['fiber_percent'] = self._extract_number(value)
                    elif 'kcal' in name or 'calorie' in name:
                        data['kcal_per_100g'] = self._extract_number(value)
        
        # Weight/Size
        if 'weight' in jsonld:
            weight = jsonld['weight']
            if isinstance(weight, dict):
                value = weight.get('value')
                unit = weight.get('unitCode', '')
                if value and unit:
                    pack_info = self.parse_pack_size(f"{value}{unit}")
                    if pack_info:
                        data['pack_size'] = pack_info
        
        # Try to detect form and life stage from name/description
        text = f"{data.get('product_name', '')} {data.get('description', '')}"
        data['form'] = self.detect_form(text)
        data['life_stage'] = self.detect_life_stage(text)
        
        return data
    
    def _extract_number(self, value: Any) -> Optional[float]:
        """Extract number from various formats"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            match = re.search(r'([0-9.]+)', value)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        return None


class PDFParser(ManufacturerParser):
    """Parser for PDF documents"""
    
    def parse(self, pdf_bytes: bytes) -> Dict:
        """Parse PDF content"""
        data = {}
        
        try:
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            # Look for composition/ingredients section
            ingredients_match = re.search(
                r'(?:composition|ingredients)[:\s]+(.*?)(?:analytical|nutrition|feeding|$)',
                full_text,
                re.IGNORECASE | re.DOTALL
            )
            
            if ingredients_match:
                ingredients_text = ingredients_match.group(1)
                data['ingredients_text'] = ingredients_text
                data['ingredients_tokens'] = self.normalize_ingredients(ingredients_text)
                data['allergen_groups'] = self.detect_allergens(data['ingredients_tokens'])
            
            # Look for analytical constituents
            analytical_match = re.search(
                r'(?:analytical constituents|nutrition|analysis)[:\s]+(.*?)(?:additives|feeding|ingredients|$)',
                full_text,
                re.IGNORECASE | re.DOTALL
            )
            
            if analytical_match:
                analytical_text = analytical_match.group(1)
                constituents = self.parse_analytical_constituents(analytical_text)
                data.update(constituents)
                
                # Calculate kcal
                kcal = self.calculate_kcal(constituents)
                if kcal:
                    data['kcal_per_100g'] = kcal
                    data['kcal_from'] = 'calculated'
            
            # Detect form and life stage
            data['form'] = self.detect_form(full_text)
            data['life_stage'] = self.detect_life_stage(full_text)
            
            # Set source
            data['source'] = 'pdf'
            
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
        
        return data


class ManufacturerDataNormalizer:
    """Normalize and combine data from multiple parsers"""
    
    def normalize(self, html_data: Dict, jsonld_data: Dict = None, pdf_data: Dict = None) -> Dict:
        """Combine and normalize data from multiple sources"""
        normalized = {
            'source': 'manufacturer',
            'confidence': 0.0,
            'extracted_at': None
        }
        
        # Priority: JSON-LD > PDF > HTML
        sources = [
            (html_data or {}, 0.8),
            (pdf_data or {}, 0.9),
            (jsonld_data or {}, 0.95)
        ]
        
        for source_data, confidence in sources:
            for key, value in source_data.items():
                if value and key not in normalized:
                    normalized[key] = value
                    if key in ['ingredients_tokens', 'kcal_per_100g', 'form', 'life_stage']:
                        normalized[f'{key}_confidence'] = confidence
        
        # Calculate overall confidence
        field_count = sum(1 for k in normalized if not k.endswith('_confidence') and k not in ['source', 'confidence', 'extracted_at'])
        normalized['confidence'] = min(0.95, field_count * 0.1)
        
        # Add provenance
        normalized['provenance'] = {
            'has_html': bool(html_data),
            'has_jsonld': bool(jsonld_data),
            'has_pdf': bool(pdf_data)
        }
        
        return normalized