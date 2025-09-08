#!/usr/bin/env python3
"""
AKC Comprehensive Breed Data Extractor
=======================================
Extracts ALL relevant breed data from AKC pages including:
- Physical characteristics (height, weight, lifespan)
- Temperament traits (all 8 scored traits)
- Breed information (group, popularity, colors)
- Content sections (about, history, health, care, grooming, training)
- Breed standards and club information
"""

import json
import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class AKCComprehensiveExtractor:
    """Extract all breed data from AKC pages"""
    
    def extract_all_data(self, html: str, url: str) -> Dict[str, Any]:
        """Main extraction method - gets everything"""
        soup = BeautifulSoup(html, 'html.parser')
        breed_slug = url.rstrip('/').split('/')[-1]
        
        # Initialize result with all fields
        result = {
            'breed_slug': breed_slug,
            'url': url,
            'extraction_method': None,
            
            # Basic info
            'display_name': None,
            'breed_group': None,
            'popularity_ranking': None,
            'colors': [],
            'markings': [],
            
            # Physical measurements
            'height_male_min': None,
            'height_male_max': None,
            'height_female_min': None,
            'height_female_max': None,
            'weight_male_min': None,
            'weight_male_max': None,
            'weight_female_min': None,
            'weight_female_max': None,
            'lifespan_min': None,
            'lifespan_max': None,
            
            # Temperament traits (1-5 scores)
            'affection_family': None,
            'good_with_children': None,
            'good_with_dogs': None,
            'shedding': None,
            'grooming_needs': None,
            'drooling': None,
            'coat_type': None,
            'coat_length': None,
            'good_with_strangers': None,
            'playfulness': None,
            'protectiveness': None,
            'adaptability': None,
            'trainability': None,
            'energy': None,
            'barking': None,
            'mental_stimulation': None,
            
            # Content sections
            'about': None,
            'history': None,
            'personality': None,
            'health': None,
            'care': None,
            'feeding': None,
            'grooming': None,
            'training': None,
            'exercise': None,
            
            # Additional info
            'breed_standard': None,
            'national_club': None,
            'rescue_groups': None,
            'puppies_info': None
        }
        
        # Try multiple extraction methods
        # 1. Extract from JSON data-js-props
        json_data = self._extract_from_json(soup)
        if json_data:
            result.update(json_data)
            result['extraction_method'] = 'json'
        
        # 2. Extract from page content
        content_data = self._extract_from_content(soup)
        # Update only None values
        for key, value in content_data.items():
            if result.get(key) is None and value is not None:
                result[key] = value
        
        # 3. Extract trait scores
        trait_data = self._extract_trait_scores(soup)
        for key, value in trait_data.items():
            if result.get(key) is None and value is not None:
                result[key] = value
        
        # Clean display name
        if not result['display_name']:
            result['display_name'] = breed_slug.replace('-', ' ').title()
        
        return result
    
    def _extract_from_json(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract from JSON data-js-props"""
        try:
            breed_div = soup.find('div', {'data-js-component': 'breedPage'})
            if not breed_div or not breed_div.get('data-js-props'):
                return {}
            
            data = json.loads(breed_div['data-js-props'])
            breed = data.get('breed', {})
            
            extracted = {}
            
            # Extract name
            if 'breed_name_formatted' in breed:
                extracted['display_name'] = breed['breed_name_formatted']
            
            # Extract history
            if 'history' in breed and isinstance(breed['history'], dict):
                history_content = breed['history'].get('content', '')
                if history_content:
                    # Clean HTML from content
                    history_soup = BeautifulSoup(history_content, 'html.parser')
                    extracted['history'] = history_soup.get_text(separator=' ', strip=True)
            
            # Extract health
            if 'health' in breed and isinstance(breed['health'], dict):
                health_desc = breed['health'].get('description', '')
                if health_desc:
                    health_soup = BeautifulSoup(health_desc, 'html.parser')
                    extracted['health'] = health_soup.get_text(separator=' ', strip=True)
            
            # Extract breed standard
            if 'standard' in breed and isinstance(breed['standard'], dict):
                standard_content = breed['standard'].get('content', '')
                if standard_content:
                    standard_soup = BeautifulSoup(standard_content, 'html.parser')
                    extracted['breed_standard'] = standard_soup.get_text(separator=' ', strip=True)
            
            # Extract puppies info
            if 'puppies' in breed and isinstance(breed['puppies'], dict):
                puppies_content = breed['puppies'].get('content', '')
                if puppies_content:
                    puppies_soup = BeautifulSoup(puppies_content, 'html.parser')
                    extracted['puppies_info'] = puppies_soup.get_text(separator=' ', strip=True)
            
            # Extract clubs
            if 'clubs' in breed and isinstance(breed['clubs'], dict):
                clubs_content = breed['clubs'].get('content', '')
                if clubs_content:
                    clubs_soup = BeautifulSoup(clubs_content, 'html.parser')
                    extracted['national_club'] = clubs_soup.get_text(separator=' ', strip=True)
            
            # Extract popularity
            if 'popularity' in breed:
                extracted['popularity_ranking'] = breed['popularity']
            
            # Extract colors
            if 'color' in breed and isinstance(breed['color'], dict):
                colors = breed['color'].get('colors', [])
                if colors:
                    extracted['colors'] = [c.get('color', '') for c in colors if c.get('color')]
                markings = breed['color'].get('markings', [])
                if markings:
                    extracted['markings'] = [m.get('marking', '') for m in markings if m.get('marking')]
            
            return extracted
            
        except Exception as e:
            logger.debug(f"JSON extraction failed: {e}")
            return {}
    
    def _extract_from_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract from page content"""
        extracted = {}
        
        # Extract physical measurements
        measurements = soup.find_all(string=re.compile(r'\d+[-–]\d+\s*(inches|pounds|lbs|years)'))
        for measure in measurements:
            text = measure.strip()
            if 'inches' in text.lower():
                nums = re.findall(r'(\d+(?:\.\d+)?)', text)
                if 'male' in text.lower() and len(nums) >= 2:
                    extracted['height_male_min'] = float(nums[0])
                    extracted['height_male_max'] = float(nums[1])
                elif 'female' in text.lower() and len(nums) >= 2:
                    extracted['height_female_min'] = float(nums[0])
                    extracted['height_female_max'] = float(nums[1])
            elif 'pounds' in text.lower() or 'lbs' in text.lower():
                nums = re.findall(r'(\d+(?:\.\d+)?)', text)
                if 'male' in text.lower() and len(nums) >= 2:
                    extracted['weight_male_min'] = float(nums[0])
                    extracted['weight_male_max'] = float(nums[1])
                elif 'female' in text.lower() and len(nums) >= 2:
                    extracted['weight_female_min'] = float(nums[0])
                    extracted['weight_female_max'] = float(nums[1])
            elif 'year' in text.lower():
                nums = re.findall(r'(\d+(?:\.\d+)?)', text)
                if len(nums) >= 2:
                    extracted['lifespan_min'] = int(float(nums[0]))
                    extracted['lifespan_max'] = int(float(nums[1]))
                elif len(nums) == 1:
                    extracted['lifespan_min'] = extracted['lifespan_max'] = int(float(nums[0]))
        
        # Extract breed group
        group_patterns = ['Sporting', 'Working', 'Terrier', 'Toy', 'Non-Sporting', 'Herding', 'Hound']
        for pattern in group_patterns:
            if soup.find(string=re.compile(pattern)):
                extracted['breed_group'] = pattern
                break
        
        # Extract main content sections
        sections_map = {
            'about': ['About the Breed', 'About', 'Overview'],
            'personality': ['Personality', 'Temperament', 'Character'],
            'care': ['Care', 'Caring for', 'What To Expect'],
            'training': ['Training', 'Trainability'],
            'grooming': ['Grooming', 'Coat Care'],
            'exercise': ['Exercise', 'Activity', 'Physical'],
            'feeding': ['Feeding', 'Nutrition', 'Diet']
        }
        
        for key, patterns in sections_map.items():
            for pattern in patterns:
                header = soup.find(['h2', 'h3'], string=re.compile(pattern, re.I))
                if header:
                    # Get content after header
                    content = []
                    for sibling in header.find_next_siblings():
                        if sibling.name in ['h2', 'h3']:
                            break
                        if sibling.name == 'p':
                            content.append(sibling.get_text(strip=True))
                    if content:
                        extracted[key] = ' '.join(content)
                        break
        
        return extracted
    
    def _extract_trait_scores(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract temperament trait scores (1-5 scale)"""
        extracted = {}
        
        # Map trait labels to our fields
        trait_map = {
            'Affectionate With Family': 'affection_family',
            'Good With Young Children': 'good_with_children',
            'Good With Other Dogs': 'good_with_dogs',
            'Shedding Level': 'shedding',
            'Coat Grooming Frequency': 'grooming_needs',
            'Drooling Level': 'drooling',
            'Openness To Strangers': 'good_with_strangers',
            'Playfulness Level': 'playfulness',
            'Watchdog/Protective Nature': 'protectiveness',
            'Adaptability Level': 'adaptability',
            'Trainability Level': 'trainability',
            'Energy Level': 'energy',
            'Barking Level': 'barking',
            'Mental Stimulation Needs': 'mental_stimulation'
        }
        
        # Find trait score elements
        trait_elements = soup.find_all('div', class_='breed-trait-score')
        
        for elem in trait_elements:
            # Get trait title
            title_elem = elem.find(class_='breed-trait-score__title')
            if not title_elem:
                continue
            
            trait_name = title_elem.get_text(strip=True)
            
            # Find matching field
            field_name = None
            for pattern, field in trait_map.items():
                if pattern.lower() in trait_name.lower():
                    field_name = field
                    break
            
            if not field_name:
                continue
            
            # Extract score (count filled circles/bars)
            score_elem = elem.find(class_='breed-trait-score__score')
            if score_elem:
                # Count active/filled indicators
                filled = len(score_elem.find_all(class_=re.compile('active|filled')))
                if filled > 0:
                    extracted[field_name] = min(filled, 5)  # Cap at 5
                else:
                    # Try to extract from aria-label or other attributes
                    label = score_elem.get('aria-label', '')
                    score_match = re.search(r'(\d+)\s*(?:of|out of|/)\s*5', label)
                    if score_match:
                        extracted[field_name] = int(score_match.group(1))
        
        return extracted


def test_extractor():
    """Test the comprehensive extractor"""
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Read the saved HTML
    with open('akc_10sec_wait.html', 'r') as f:
        html = f.read()
    
    extractor = AKCComprehensiveExtractor()
    data = extractor.extract_all_data(html, 'https://www.akc.org/dog-breeds/golden-retriever/')
    
    print("=== COMPREHENSIVE BREED DATA EXTRACTION ===\n")
    
    # Display results by category
    print("BASIC INFO:")
    for key in ['display_name', 'breed_group', 'popularity_ranking']:
        if data.get(key):
            print(f"  {key}: {data[key]}")
    
    print("\nPHYSICAL MEASUREMENTS:")
    for key in ['height_male_min', 'height_male_max', 'weight_male_min', 'weight_male_max', 
                'lifespan_min', 'lifespan_max']:
        if data.get(key):
            print(f"  {key}: {data[key]}")
    
    print("\nTEMPERAMENT TRAITS:")
    trait_count = 0
    for key in ['energy', 'trainability', 'shedding', 'barking', 'affection_family']:
        if data.get(key):
            print(f"  {key}: {data[key]}")
            trait_count += 1
    
    print("\nCONTENT SECTIONS:")
    for key in ['about', 'history', 'health', 'care', 'grooming']:
        if data.get(key):
            preview = data[key][:100] + "..." if len(data[key]) > 100 else data[key]
            print(f"  {key}: {preview}")
    
    # Calculate completeness
    total_fields = len([k for k in data.keys() if not k.startswith('_')])
    filled_fields = len([k for k, v in data.items() if v is not None and not k.startswith('_')])
    completeness = (filled_fields / total_fields) * 100
    
    print(f"\n=== EXTRACTION COMPLETENESS: {completeness:.1f}% ({filled_fields}/{total_fields} fields) ===")
    
    # Save to file
    with open('comprehensive_breed_data.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("\nFull data saved to: comprehensive_breed_data.json")
    
    return data


if __name__ == "__main__":
    test_extractor()