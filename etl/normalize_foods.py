"""
ETL helpers for normalizing food product data
"""
import re
import hashlib
from typing import List, Dict, Any, Optional, Union
from decimal import Decimal


def parse_energy(value: str, unit: str = None) -> Optional[float]:
    """
    Parse energy values and convert to kcal per 100g
    Handles: kcal/100g, kcal/kg, kJ conversions
    """
    if not value:
        return None
    
    value = str(value).lower().strip()
    if unit:
        unit = unit.lower().strip()
    
    # Remove common text
    value = re.sub(r'[^\d\.,\s]*(per|\/)\s*', ' ', value)
    
    # Extract number
    number_match = re.search(r'(\d+(?:[.,]\d+)?)', value)
    if not number_match:
        return None
    
    number = float(number_match.group(1).replace(',', '.'))
    
    # Check unit and convert
    if (unit and 'kj' in unit) or ('kj' in value):
        # Convert kJ to kcal (1 kJ = 0.239006 kcal, or kcal = kJ / 4.184)
        number = number / 4.184
    
    # Check if per kg (need to divide by 10)
    if (unit and 'kg' in unit and '100' not in unit) or ('kg' in value and '100' not in value):
        number = number / 10
    
    return round(number, 2)


def parse_kcal(value: str) -> Optional[float]:
    """
    Backward compatibility wrapper for parse_energy
    """
    return parse_energy(value)


def parse_percent(value: str) -> Optional[float]:
    """
    Parse percentage values to float
    Examples: "25%", "25.5 %", "25,5"
    """
    if not value:
        return None
    
    value = str(value).strip()
    
    # Remove % sign and extract number
    number_match = re.search(r'(\d+(?:[.,]\d+)?)', value)
    if not number_match:
        return None
    
    number = float(number_match.group(1).replace(',', '.'))
    
    # Ensure reasonable range (0-100)
    if 0 <= number <= 100:
        return round(number, 2)
    
    return None


def parse_pack_size(size_str: str) -> Optional[Dict[str, Any]]:
    """
    Parse pack size string to structured format
    Examples: "2kg", "400g", "12 x 400g"
    Returns: {"amount": 2000, "unit": "g", "display": "2kg"}
    """
    if not size_str:
        return None
    
    size_str = str(size_str).lower().strip()
    
    # Handle multi-pack (e.g., "12 x 400g")
    multipack_match = re.search(r'(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*(kg|g)', size_str)
    if multipack_match:
        count = int(multipack_match.group(1))
        amount = float(multipack_match.group(2).replace(',', '.'))
        unit = multipack_match.group(3)
        
        # Convert to grams
        total_g = amount * count
        if unit == 'kg':
            total_g = total_g * 1000
            
        return {
            "amount": total_g,
            "unit": "g",
            "display": size_str,
            "multipack": True
        }
    
    # Handle single pack
    single_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|g)', size_str)
    if single_match:
        amount = float(single_match.group(1).replace(',', '.'))
        unit = single_match.group(2)
        
        # Convert to grams
        if unit == 'kg':
            amount = amount * 1000
            
        return {
            "amount": amount,
            "unit": "g",
            "display": size_str,
            "multipack": False
        }
    
    return None


def tokenize_ingredients(ingredients_str: str) -> List[str]:
    """
    Convert ingredients string to normalized tokens
    """
    if not ingredients_str:
        return []
    
    # Split by comma or semicolon
    parts = re.split(r'[,;]', ingredients_str.lower())
    
    tokens = []
    for part in parts:
        # Remove parenthetical content (e.g., "chicken (25%)")
        part = re.sub(r'\([^)]*\)', '', part)
        
        # Remove percentages
        part = re.sub(r'\d+(?:[.,]\d+)?%?', '', part)
        
        # Clean and trim
        part = part.strip()
        
        # Skip empty or very short tokens
        if len(part) > 2:
            tokens.append(part)
    
    return tokens


def check_contains_chicken(ingredients_tokens: List[str]) -> bool:
    """
    Check if ingredients contain chicken or chicken-derived products
    """
    chicken_keywords = {
        'chicken', 'chicken meal', 'chicken fat', 'chicken liver',
        'chicken heart', 'chicken protein', 'dehydrated chicken',
        'chicken broth', 'chicken digest', 'hydrolyzed chicken'
    }
    
    # Check exact matches
    for token in ingredients_tokens:
        if token in chicken_keywords:
            return True
        
        # Check if token starts with "chicken"
        if token.startswith('chicken'):
            return True
    
    return False


def parse_price(price_str: str, currency: str = None) -> Optional[Dict[str, Any]]:
    """
    Parse price string and currency
    Returns: {"amount": 25.99, "currency": "EUR"}
    """
    if not price_str:
        return None
    
    price_str = str(price_str).strip()
    
    # Extract number
    number_match = re.search(r'(\d+(?:[.,]\d+)?)', price_str)
    if not number_match:
        return None
    
    amount = float(number_match.group(1).replace(',', '.'))
    
    # Try to extract currency from string if not provided
    if not currency:
        currency_symbols = {
            '€': 'EUR', 
            '$': 'USD', 
            '£': 'GBP',
            'eur': 'EUR',
            'usd': 'USD',
            'gbp': 'GBP'
        }
        
        for symbol, code in currency_symbols.items():
            if symbol in price_str.lower():
                currency = code
                break
    
    # Default to EUR if still not found
    if not currency:
        currency = 'EUR'
    
    return {
        "amount": round(amount, 2),
        "currency": currency
    }


def estimate_kcal_from_analytical(protein: float, fat: float, fiber: float = 0, 
                                  ash: float = 0, moisture: float = 0) -> Optional[float]:
    """
    Estimate kcal/100g from analytical constituents using Atwater factors
    carb_est = 100 - (protein + fat + fiber + ash + moisture) but >= 0
    kcal/100g ≈ 4*protein + 9*fat + 4*carb_est
    Note: This is an estimate, actual metabolizable energy may differ
    """
    if protein is None or fat is None:
        return None
    
    # Use 0 for missing optional values
    fiber = fiber or 0
    ash = ash or 0
    moisture = moisture or 0
    
    # Estimate carbohydrates (NFE - Nitrogen Free Extract)
    carb_est = 100 - (protein + fat + fiber + ash + moisture)
    carb_est = max(0, carb_est)  # Ensure non-negative
    
    # Calculate using modified Atwater factors for pet food
    # Protein: 4 kcal/g, Fat: 9 kcal/g, Carbs: 4 kcal/g
    kcal_per_100g = (4 * protein) + (9 * fat) + (4 * carb_est)
    
    return round(kcal_per_100g, 1)


def contains(tokens: List[str], keywords: List[str]) -> bool:
    """
    Check if any token contains any of the keywords
    """
    if not tokens or not keywords:
        return False
    
    keywords_lower = [k.lower() for k in keywords]
    
    for token in tokens:
        token_lower = token.lower()
        for keyword in keywords_lower:
            if keyword in token_lower:
                return True
    
    return False


def derive_form(name: str, category: str = None) -> Optional[str]:
    """
    Derive food form from product name and category
    Returns: 'dry', 'wet', 'raw', 'vet', or None
    """
    text = f"{name or ''} {category or ''}".lower()
    
    if any(word in text for word in ['dry', 'kibble', 'biscuit', 'crispy', 'crunchy']):
        return 'dry'
    elif any(word in text for word in ['wet', 'can', 'canned', 'pouch', 'tray', 'pate', 'gravy', 'jelly']):
        return 'wet'
    elif any(word in text for word in ['raw', 'freeze-dried', 'frozen', 'fresh', 'barf']):
        return 'raw'
    elif any(word in text for word in ['vet', 'veterinary', 'prescription', 'therapeutic', 'clinical']):
        return 'vet'
    
    return None


def derive_life_stage(name: str, tags: List[str] = None) -> Optional[str]:
    """
    Derive life stage from product name and tags
    Returns: 'puppy', 'adult', 'senior', 'all', or None
    """
    text = name.lower() if name else ''
    if tags:
        text += ' ' + ' '.join(tags).lower()
    
    if any(word in text for word in ['puppy', 'junior', 'young', 'growth', 'starter']):
        return 'puppy'
    elif any(word in text for word in ['senior', 'mature', 'aged', 'older', '7+', '8+', '9+']):
        return 'senior'
    elif any(word in text for word in ['all life', 'all stage', 'any age', 'all age']):
        return 'all'
    elif any(word in text for word in ['adult', 'maintenance']):
        return 'adult'
    
    # Default to adult if unclear
    return 'adult' if text else None


def normalize_currency(price: float, currency: str, rates: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Normalize price to EUR using provided or default rates
    Returns dict with EUR amount, original currency, and conversion date
    """
    if not rates:
        # Default rates (should be updated from config)
        rates = {
            'EUR': 1.0,
            'USD': 0.92,
            'GBP': 1.16,
            'SEK': 0.087,
            'DKK': 0.134,
            'NOK': 0.085
        }
    
    currency = currency.upper() if currency else 'EUR'
    rate = rates.get(currency, 1.0)
    
    return {
        'price_eur': round(price * rate, 2),
        'original_currency': currency,
        'original_price': price,
        'conversion_rate': rate,
        'converted_at': '2024-01-01'  # Should be from config
    }


def convert_to_eur(amount: float, currency: str, rates: Dict[str, float] = None) -> float:
    """
    Simple currency conversion to EUR
    Backward compatibility wrapper
    """
    result = normalize_currency(amount, currency, rates)
    return result['price_eur']


def generate_fingerprint(brand: str, name: str, ingredients: str) -> str:
    """
    Generate a unique fingerprint for detecting product changes
    """
    components = [
        (brand or '').lower().strip(),
        (name or '').lower().strip(),
        (ingredients or '').lower().strip()
    ]
    
    combined = '|'.join(components)
    return hashlib.md5(combined.encode()).hexdigest()


def normalize_form(form_str: str) -> Optional[str]:
    """
    Normalize food form to standard values: dry, wet, raw, vet
    """
    if not form_str:
        return None
    
    form_str = form_str.lower().strip()
    
    form_map = {
        'dry': ['dry', 'kibble', 'biscuit', 'crispy'],
        'wet': ['wet', 'can', 'canned', 'pouch', 'tray', 'pate'],
        'raw': ['raw', 'freeze-dried', 'frozen', 'fresh'],
        'vet': ['vet', 'veterinary', 'prescription', 'therapeutic']
    }
    
    for standard, variants in form_map.items():
        for variant in variants:
            if variant in form_str:
                return standard
    
    return None


def normalize_life_stage(stage_str: str) -> Optional[str]:
    """
    Normalize life stage to standard values: puppy, adult, senior, all
    """
    if not stage_str:
        return None
    
    stage_str = stage_str.lower().strip()
    
    stage_map = {
        'puppy': ['puppy', 'junior', 'young', 'growth'],
        'adult': ['adult', 'mature', 'maintenance'],
        'senior': ['senior', 'mature adult', 'aged', 'older'],
        'all': ['all', 'any', 'life stages', 'all life']
    }
    
    for standard, variants in stage_map.items():
        for variant in variants:
            if variant in stage_str:
                return standard
    
    # Default to adult if unclear
    return 'adult'


def extract_gtin(text: str) -> Optional[str]:
    """
    Extract GTIN/EAN code from text
    """
    if not text:
        return None
    
    # Look for 8, 12, 13, or 14 digit codes
    gtin_match = re.search(r'\b(\d{8}|\d{12}|\d{13}|\d{14})\b', text)
    if gtin_match:
        return gtin_match.group(1)
    
    return None


def clean_text(text: str) -> str:
    """
    Clean and normalize text
    """
    if not text:
        return ''
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\-.,;:()%/]', '', text)
    
    return text.strip()