"""
Robust HTML nutrition parser for pet food products
Extracts protein%, fat%, fiber%, ash%, moisture% and kcal/100g from various HTML formats
"""
import re
from typing import Dict, Optional, Tuple, Any
from bs4 import BeautifulSoup, Tag
import logging

logger = logging.getLogger(__name__)


class NutritionParser:
    """Robust parser for extracting nutrition data from HTML"""
    
    # Keywords that indicate a nutrition section
    NUTRITION_SECTION_KEYWORDS = [
        'analytical constituent',
        'analytical composition',
        'nutrition',
        'typical analysis',
        'constituent',
        'guaranteed analysis',
        'nutritional content',
        'composition',
        'analysis'
    ]
    
    # Mapping of nutrition terms to our standard fields
    NUTRIENT_PATTERNS = {
        'protein': [r'protein', r'crude\s*protein', r'proteínas'],
        'fat': [r'fat', r'crude\s*fat', r'oil(?:s)?\s*(?:and|&)?\s*fat', r'crude\s*oil', r'grasas', r'lipid'],
        'fiber': [r'fib(?:re|er)', r'crude\s*fib(?:re|er)', r'fibra'],
        'ash': [r'ash', r'crude\s*ash', r'inorganic\s*matter', r'cenizas'],
        'moisture': [r'moisture', r'water', r'humidity', r'humedad'],
        'energy': [r'energy', r'kcal', r'calor', r'metabol(?:is|iz)able\s*energy', r'kj']
    }
    
    def parse_html(self, html: str) -> Dict[str, Any]:
        """
        Parse nutrition data from HTML
        
        Returns:
            Dict with keys: protein_percent, fat_percent, fiber_percent, 
                          ash_percent, moisture_percent, kcal_per_100g, kcal_basis
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try multiple strategies in order
        result = {}
        
        # Strategy 1: Find nutrition section and parse structured data
        nutrition_section = self._find_nutrition_section(soup)
        if nutrition_section:
            result = self._parse_nutrition_section(nutrition_section)
        
        # Strategy 2: If no structured data, try regex on full text
        if not result:
            result = self._parse_with_regex(soup.get_text())
        
        # Strategy 3: Look for definition lists (dl/dt/dd)
        if not result:
            result = self._parse_definition_lists(soup)
        
        # Calculate estimated kcal if we have macros but no energy
        if result and not result.get('kcal_per_100g'):
            estimated = self._estimate_kcal(result)
            if estimated:
                result['kcal_per_100g'] = estimated
                result['kcal_basis'] = 'estimated'
        
        return result
    
    def _find_nutrition_section(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the section containing nutrition information"""
        
        # Look for headings that mention nutrition/constituents
        for keyword in self.NUTRITION_SECTION_KEYWORDS:
            # Check h1-h6 headings
            for heading_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                headings = soup.find_all(heading_tag)
                for heading in headings:
                    if keyword in heading.get_text().lower():
                        # Return the parent section or next sibling
                        parent = heading.find_parent(['section', 'div', 'article'])
                        if parent:
                            return parent
                        # Try next sibling if no parent section
                        next_elem = heading.find_next_sibling()
                        if next_elem:
                            return next_elem
            
            # Also check for divs/sections with class or id containing keyword
            for elem in soup.find_all(['div', 'section'], class_=re.compile(keyword.replace(' ', '[-_]'), re.I)):
                return elem
            
            for elem in soup.find_all(['div', 'section'], id=re.compile(keyword.replace(' ', '[-_]'), re.I)):
                return elem
        
        # Fallback: look for tables that might contain nutrition
        tables = soup.find_all('table')
        for table in tables:
            text = table.get_text().lower()
            if any(kw in text for kw in ['protein', 'fat', 'ash', 'moisture']):
                return table
        
        return None
    
    def _parse_nutrition_section(self, section: Tag) -> Dict[str, Any]:
        """Parse nutrition data from a section"""
        result = {}
        
        # Try table parsing first
        table = section.find('table') if section.name != 'table' else section
        if table:
            result = self._parse_table(table)
        
        # If no table or incomplete data, try text parsing
        if not result or len(result) < 2:
            text = section.get_text()
            text_result = self._parse_with_regex(text)
            # Merge results, preferring table data
            for key, value in text_result.items():
                if key not in result:
                    result[key] = value
        
        return result
    
    def _parse_table(self, table: Tag) -> Dict[str, Any]:
        """Parse nutrition from table structure"""
        result = {}
        
        # Parse rows looking for nutrient/value pairs
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text().strip().lower()
                value = cells[1].get_text().strip()
                
                # Match label against patterns
                for nutrient, patterns in self.NUTRIENT_PATTERNS.items():
                    if any(re.search(pattern, label, re.I) for pattern in patterns):
                        if nutrient == 'energy':
                            kcal = self._parse_energy(value)
                            if kcal:
                                result['kcal_per_100g'] = kcal
                                result['kcal_basis'] = 'measured'
                        else:
                            percent = self._parse_percent(value)
                            if percent is not None:
                                result[f'{nutrient}_percent'] = percent
                        break
        
        return result
    
    def _parse_definition_lists(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse nutrition from dl/dt/dd structure"""
        result = {}
        
        for dl in soup.find_all('dl'):
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            
            for dt, dd in zip(dts, dds):
                label = dt.get_text().strip().lower()
                value = dd.get_text().strip()
                
                for nutrient, patterns in self.NUTRIENT_PATTERNS.items():
                    if any(re.search(pattern, label, re.I) for pattern in patterns):
                        if nutrient == 'energy':
                            kcal = self._parse_energy(value)
                            if kcal:
                                result['kcal_per_100g'] = kcal
                                result['kcal_basis'] = 'measured'
                        else:
                            percent = self._parse_percent(value)
                            if percent is not None:
                                result[f'{nutrient}_percent'] = percent
                        break
        
        return result
    
    def _parse_with_regex(self, text: str) -> Dict[str, Any]:
        """Parse nutrition using regex patterns on text"""
        result = {}
        
        # Normalize text (handle various spacings and punctuation)
        text = re.sub(r'\s+', ' ', text)
        
        # Pattern for nutrient: value% (handles various formats)
        # Matches: "Protein 25%", "Protein: 25%", "Protein - 25%", "Protein 25.5%", "Protein 25,5%"
        pattern = r'(\w+(?:\s*(?:and|&)\s*\w+)?)\s*[:–-]?\s*(\d+(?:[.,]\d+)?)\s*%'
        
        matches = re.finditer(pattern, text, re.I)
        for match in matches:
            label = match.group(1).lower()
            value_str = match.group(2)
            
            # Check if this matches any nutrient pattern
            for nutrient, patterns in self.NUTRIENT_PATTERNS.items():
                if nutrient != 'energy' and any(re.search(p, label, re.I) for p in patterns):
                    percent = self._parse_percent(value_str)
                    if percent is not None:
                        result[f'{nutrient}_percent'] = percent
                    break
        
        # Special pattern for energy (kcal or kJ)
        energy_pattern = r'(\d+(?:[.,]\d+)?)\s*(?:kcal|kj)(?:/100\s*g)?'
        energy_match = re.search(energy_pattern, text, re.I)
        if energy_match:
            value = energy_match.group(1)
            unit = 'kj' if 'kj' in energy_match.group(0).lower() else 'kcal'
            kcal = self._parse_energy(f"{value} {unit}")
            if kcal:
                result['kcal_per_100g'] = kcal
                result['kcal_basis'] = 'measured'
        
        return result
    
    def _parse_percent(self, value: str) -> Optional[float]:
        """Parse percentage value, handling comma decimals"""
        if not value:
            return None
        
        # Extract number, handling comma as decimal separator
        match = re.search(r'(\d+(?:[.,]\d+)?)', value)
        if match:
            number_str = match.group(1).replace(',', '.')
            try:
                percent = float(number_str)
                # Sanity check
                if 0 <= percent <= 100:
                    return round(percent, 2)
            except ValueError:
                pass
        
        return None
    
    def _parse_energy(self, value: str) -> Optional[float]:
        """Parse energy value and convert to kcal/100g"""
        if not value:
            return None
        
        value = value.lower()
        
        # Extract number
        match = re.search(r'(\d+(?:[.,]\d+)?)', value)
        if not match:
            return None
        
        number = float(match.group(1).replace(',', '.'))
        
        # Check unit and convert
        if 'kj' in value:
            # Convert kJ to kcal
            number = number / 4.184
        elif 'kcal' not in value:
            # If no unit specified, assume kcal if reasonable range
            if number > 1000:
                # Probably kJ
                number = number / 4.184
        
        # Check if per kg (need to divide by 10)
        if '/kg' in value or 'per kg' in value:
            number = number / 10
        
        # Sanity check - dog food typically 250-500 kcal/100g
        if 100 <= number <= 700:
            return round(number, 1)
        
        return None
    
    def _estimate_kcal(self, nutrients: Dict[str, Any]) -> Optional[float]:
        """
        Estimate kcal/100g using modified Atwater factors
        """
        protein = nutrients.get('protein_percent', 0) or 0
        fat = nutrients.get('fat_percent', 0) or 0
        fiber = nutrients.get('fiber_percent', 0) or 0
        ash = nutrients.get('ash_percent', 0) or 0
        moisture = nutrients.get('moisture_percent', 0) or 0
        
        # Need at least protein and fat to estimate
        if protein == 0 or fat == 0:
            return None
        
        # Estimate carbohydrates (NFE - Nitrogen Free Extract)
        carb_est = max(0, 100 - (protein + fat + fiber + ash + moisture))
        
        # Modified Atwater factors for pet food
        # Protein: 3.5 kcal/g, Fat: 8.5 kcal/g, Carbs: 3.5 kcal/g
        kcal = (3.5 * protein) + (8.5 * fat) + (3.5 * carb_est)
        
        # Sanity check
        if 150 <= kcal <= 700:
            return round(kcal, 1)
        
        return None


def parse_nutrition_from_html(html: str) -> Dict[str, Any]:
    """
    Convenience function to parse nutrition from HTML
    
    Returns:
        Dict with nutrition data or empty dict if none found
    """
    parser = NutritionParser()
    return parser.parse_html(html)