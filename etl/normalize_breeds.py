#!/usr/bin/env python3
"""
Breed Data Normalization Functions
Handles mapping Dogo characteristics to controlled vocabularies
"""
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union
import hashlib

# Load breed aliases mapping
def load_breed_aliases() -> Dict[str, List[str]]:
    """Load breed aliases from YAML file"""
    aliases_file = Path(__file__).parent.parent / 'breed_aliases.yaml'
    
    if not aliases_file.exists():
        return {}
    
    with open(aliases_file, 'r') as f:
        return yaml.safe_load(f) or {}

# Controlled vocabulary mappings
SIZE_MAPPING = {
    # Dogo text patterns -> controlled enum
    'toy': 'tiny',
    'very small': 'tiny', 
    'extra small': 'tiny',
    'under 10': 'tiny',
    'under 10 lbs': 'tiny',
    '5-10': 'tiny',
    
    'small': 'small',
    '10-25': 'small',
    '10-25 lbs': 'small', 
    '11-25': 'small',
    'under 25': 'small',
    
    'medium': 'medium',
    '25-60': 'medium',
    '25-60 lbs': 'medium',
    '26-60': 'medium',
    'medium-sized': 'medium',
    
    'large': 'large', 
    '60-90': 'large',
    '60-90 lbs': 'large',
    '61-90': 'large',
    'over 60': 'large',
    
    'extra large': 'giant',
    'very large': 'giant', 
    'giant': 'giant',
    'over 90': 'giant',
    '90+': 'giant',
    'over 90 lbs': 'giant'
}

ENERGY_MAPPING = {
    'low energy': 'low',
    'calm': 'low',
    'relaxed': 'low',
    'laid-back': 'low',
    'couch potato': 'low',
    
    'moderate energy': 'moderate',
    'moderate': 'moderate',
    'medium energy': 'moderate',
    'balanced': 'moderate',
    
    'high energy': 'high',
    'energetic': 'high', 
    'active': 'high',
    'vigorous': 'high',
    
    'very high energy': 'very_high',
    'extremely active': 'very_high',
    'tireless': 'very_high',
    'hyperactive': 'very_high'
}

COAT_LENGTH_MAPPING = {
    'short': 'short',
    'short-haired': 'short',
    'smooth': 'short',
    
    'medium': 'medium',
    'medium-length': 'medium',
    'moderate': 'medium',
    
    'long': 'long',
    'long-haired': 'long',
    'fluffy': 'long',
    'feathery': 'long'
}

SHEDDING_MAPPING = {
    'non-shedding': 'minimal',
    'minimal': 'minimal',
    'very little': 'minimal',
    
    'low': 'low',
    'light': 'low',
    'occasional': 'low',
    
    'moderate': 'moderate',
    'medium': 'moderate', 
    'regular': 'moderate',
    
    'high': 'high',
    'heavy': 'high',
    'considerable': 'high',
    
    'very high': 'very_high',
    'excessive': 'very_high',
    'constant': 'very_high'
}

TRAINABILITY_MAPPING = {
    'difficult': 'challenging',
    'challenging': 'challenging',
    'stubborn': 'challenging',
    'independent': 'challenging',
    
    'moderate': 'moderate',
    'average': 'moderate',
    'fair': 'moderate',
    
    'easy': 'easy',
    'good': 'easy',
    'responsive': 'easy',
    'eager to please': 'easy',
    
    'very easy': 'very_easy',
    'excellent': 'very_easy',
    'highly trainable': 'very_easy',
    'brilliant': 'very_easy'
}

BARK_LEVEL_MAPPING = {
    'quiet': 'quiet',
    'rarely barks': 'quiet',
    'silent': 'quiet',
    
    'occasional': 'occasional',
    'seldom': 'occasional',
    'when necessary': 'occasional',
    
    'moderate': 'moderate',
    'average': 'moderate',
    'normal': 'moderate',
    
    'frequent': 'frequent',
    'regular': 'frequent',
    'alert': 'frequent',
    
    'very vocal': 'very_vocal',
    'excessive': 'very_vocal',
    'talkative': 'very_vocal',
    'constantly': 'very_vocal'
}

def normalize_characteristic(text: str, mapping: Dict[str, str]) -> Optional[str]:
    """Normalize a characteristic text using provided mapping"""
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    # Direct match first
    if text_lower in mapping:
        return mapping[text_lower]
    
    # Partial match
    for pattern, value in mapping.items():
        if pattern in text_lower:
            return value
    
    return None

def extract_lifespan(text: str) -> tuple[Optional[int], Optional[int]]:
    """Extract lifespan range from text like '10-12 years' or '12-14'"""
    if not text:
        return None, None
    
    # Look for patterns like "10-12", "10 to 12", "10-14 years"
    patterns = [
        r'(\d+)\s*[-–to]\s*(\d+)\s*(?:years?)?',
        r'(\d+)\s*years?'  # Single value
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            if len(match.groups()) == 2:
                return int(match.group(1)), int(match.group(2))
            else:
                # Single value, assume +/- 1 year range
                val = int(match.group(1))
                return val - 1, val + 1
    
    return None, None

def extract_weight_range(text: str) -> tuple[Optional[float], Optional[float]]:
    """Extract weight range from text like '25-60 lbs' or '30-50 kg'"""
    if not text:
        return None, None
    
    # Convert lbs to kg if needed
    text_lower = text.lower()
    is_lbs = 'lb' in text_lower or 'pound' in text_lower
    
    patterns = [
        r'(\d+(?:\.\d+)?)\s*[-–to]\s*(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*(?:kg|lb|pound)?'  # Single value
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            if len(match.groups()) == 2:
                min_val, max_val = float(match.group(1)), float(match.group(2))
            else:
                # Single value, assume +/- 10% range
                val = float(match.group(1))
                min_val, max_val = val * 0.9, val * 1.1
            
            # Convert lbs to kg
            if is_lbs:
                min_val *= 0.453592
                max_val *= 0.453592
            
            return min_val, max_val
    
    return None, None

def extract_height_range(text: str) -> tuple[Optional[int], Optional[int]]:
    """Extract height range from text like '22-26 inches' or '56-66 cm'"""
    if not text:
        return None, None
    
    text_lower = text.lower()
    is_inches = 'inch' in text_lower or '"' in text_lower
    
    patterns = [
        r'(\d+)\s*[-–to]\s*(\d+)',
        r'(\d+)\s*(?:cm|inch|")?'  # Single value
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            if len(match.groups()) == 2:
                min_val, max_val = int(match.group(1)), int(match.group(2))
            else:
                # Single value, assume +/- 2 units range
                val = int(match.group(1))
                min_val, max_val = val - 2, val + 2
            
            # Convert inches to cm
            if is_inches:
                min_val = int(min_val * 2.54)
                max_val = int(max_val * 2.54)
            
            return min_val, max_val
    
    return None, None

def normalize_friendliness(text: str) -> Optional[int]:
    """Convert friendliness description to 0-5 scale"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Map descriptions to 0-5 scale
    if any(word in text_lower for word in ['aggressive', 'hostile', 'unfriendly']):
        return 1
    elif any(word in text_lower for word in ['cautious', 'reserved', 'wary']):
        return 2  
    elif any(word in text_lower for word in ['neutral', 'average', 'moderate']):
        return 3
    elif any(word in text_lower for word in ['friendly', 'good', 'sociable']):
        return 4
    elif any(word in text_lower for word in ['very friendly', 'excellent', 'loving', 'outgoing']):
        return 5
    
    return 3  # Default to neutral

def resolve_breed_slug(breed_name: str) -> tuple[str, str, List[str]]:
    """
    Resolve breed name to canonical slug, display name, and aliases
    
    Returns:
        tuple: (breed_slug, display_name, aliases_list)
    """
    aliases_map = load_breed_aliases()
    breed_name_clean = breed_name.strip()
    
    # Check if breed name matches any alias
    for slug, aliases in aliases_map.items():
        if breed_name_clean in aliases:
            return slug, aliases[0], aliases  # First alias is display name
    
    # If no match, create slug from name
    slug = re.sub(r'[^a-z0-9]+', '-', breed_name_clean.lower()).strip('-')
    return slug, breed_name_clean, [breed_name_clean]

def generate_breed_fingerprint(breed_data: Dict) -> str:
    """Generate fingerprint for breed data deduplication"""
    # Use key characteristics for fingerprint
    key_data = {
        'name': breed_data.get('breed_name', ''),
        'size': breed_data.get('size', ''),
        'energy': breed_data.get('energy', ''),
        'origin': breed_data.get('origin', '')
    }
    
    fingerprint_str = str(sorted(key_data.items()))
    return hashlib.md5(fingerprint_str.encode()).hexdigest()

def parse_breed_sections(html_content: str) -> Dict[str, List[str]]:
    """
    Parse breed narrative into 5 required sections
    
    Returns:
        dict: {"overview": [...], "temperament": [...], "training": [...], "grooming": [...], "health": [...]}
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Initialize sections
    sections = {
        "overview": [],
        "temperament": [], 
        "training": [],
        "grooming": [],
        "health": []
    }
    
    # Common section header patterns
    section_patterns = {
        "overview": ["overview", "about", "introduction", "breed info", "general"],
        "temperament": ["temperament", "personality", "character", "behavior", "nature"],
        "training": ["training", "trainability", "intelligence", "obedience"],
        "grooming": ["grooming", "care", "maintenance", "coat care"],
        "health": ["health", "medical", "conditions", "issues", "problems"]
    }
    
    # Find all paragraph-like elements
    content_elements = soup.find_all(['p', 'div', 'section'], string=True)
    
    # Try to categorize content by proximity to section headers
    current_section = "overview"  # Default section
    
    for elem in content_elements:
        text = elem.get_text().strip()
        if not text or len(text) < 20:  # Skip short snippets
            continue
        
        # Check if this looks like a section header
        text_lower = text.lower()
        header_found = False
        
        for section, patterns in section_patterns.items():
            if any(pattern in text_lower for pattern in patterns) and len(text) < 100:
                current_section = section
                header_found = True
                break
        
        # If not a header, add to current section
        if not header_found:
            sections[current_section].append(text)
    
    # If we have very little content, try a simpler approach
    if sum(len(sec) for sec in sections.values()) < 3:
        all_text = soup.get_text()
        paragraphs = [p.strip() for p in all_text.split('\n') if len(p.strip()) > 20]
        
        # Distribute paragraphs across sections
        if paragraphs:
            sections["overview"] = paragraphs[:2] if len(paragraphs) >= 2 else paragraphs
            sections["temperament"] = paragraphs[2:4] if len(paragraphs) >= 4 else []
            sections["training"] = paragraphs[4:6] if len(paragraphs) >= 6 else []
            sections["grooming"] = paragraphs[6:8] if len(paragraphs) >= 8 else []
            sections["health"] = paragraphs[8:] if len(paragraphs) >= 10 else []
    
    return sections