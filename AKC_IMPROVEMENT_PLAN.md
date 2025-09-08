# AKC Breed Data Extraction Improvement Plan
## Goal: Achieve 90%+ Completeness Score

## Current State Analysis (30% Completeness)

### ✅ What We're Getting (17/47 fields)
1. **Physical Data** (Partial)
   - Male height/weight only
   - Lifespan
   - Missing: Female measurements

2. **Content** (Limited)
   - History (from JSON)
   - Basic health/care text
   - Missing: About, Personality, Training, Exercise, Grooming

3. **Metadata**
   - Breed name, group, popularity text
   - URL

### ❌ Critical Missing Data (30 fields)
1. **All 16 Temperament Trait Scores** (0% captured)
2. **Female Physical Measurements**
3. **Key Content Sections** (7 missing)
4. **Breed Group Classification**
5. **Colors and Markings**

## Root Cause Analysis

After analyzing the HTML and JSON:

1. **JSON data is LIMITED** - Only contains history, health snippet, media, and metadata
2. **Trait scores are NOT in JSON** - They're rendered client-side by React
3. **Most content is NOT in initial HTML** - It's loaded dynamically
4. **Physical measurements split by gender** - Need separate extraction

## Improvement Strategy

### Phase 1: Extract ALL Available Static Data (Target: 60%)

#### 1.1 Parse More HTML Sections
```python
# Current: Only checking JSON
# Improvement: Parse multiple HTML sections

sections_to_extract = {
    'breed-stats': 'div.breed-statistics',
    'at-a-glance': 'section.breed-at-a-glance',
    'about-section': 'div.breed-about-section',
    'care-section': 'div.breed-care-content',
    'vital-stats': 'div.vital-statistics'
}
```

#### 1.2 Extract Female Measurements
```python
# Look for patterns like:
# "Females: 21.5-22.5 inches"
# "Female: 55-65 pounds"
```

#### 1.3 Get Breed Group from Breadcrumb
```python
# Parse: <nav class="breadcrumb">
# Pattern: Home > Dog Breeds > [GROUP] > Golden Retriever
```

### Phase 2: Advanced Scraping for Dynamic Content (Target: 90%+)

#### 2.1 Wait for Full React Rendering
```python
scrapingbee_params = {
    'wait': '15000',  # Increase from 10s to 15s
    'wait_for': '.breed-trait-score',  # Wait for specific element
    'js_scenario': {
        'instructions': [
            {'wait': 5000},
            {'scroll': 'bottom'},  # Trigger lazy loading
            {'wait': 5000},
            {'click': '.show-more-traits'},  # If exists
            {'wait': 3000}
        ]
    }
}
```

#### 2.2 Execute JavaScript to Extract React State
```python
js_code = """
// Get React props from components
const getReactProps = (selector) => {
    const elem = document.querySelector(selector);
    if (!elem) return null;
    
    // React 16+ stores props in __reactInternalInstance
    const key = Object.keys(elem).find(k => k.startsWith('__react'));
    if (key) {
        return elem[key].memoizedProps || elem[key].pendingProps;
    }
    return null;
};

// Extract all trait scores
const traits = [];
document.querySelectorAll('[data-testid*="trait"]').forEach(el => {
    const props = getReactProps(el);
    if (props) traits.push(props);
});

return {
    traits: traits,
    atAGlance: document.querySelector('.at-a-glance')?.innerText,
    aboutText: document.querySelector('.breed-about')?.innerText
};
"""
```

#### 2.3 Alternative: Multiple API Calls
```python
# AKC might have internal APIs
# Monitor network tab to find:
# - /api/breeds/{slug}/traits
# - /api/breeds/{slug}/characteristics
# - /api/breeds/{slug}/content
```

### Phase 3: Fallback HTML Parsing (If React fails)

#### 3.1 Parse Visual Elements
```python
def extract_trait_from_visual(soup):
    """Count filled vs unfilled indicators"""
    traits = {}
    for trait_div in soup.find_all('div', class_='breed-trait'):
        name = trait_div.find(class_='trait-name').text
        # Count filled circles/bars
        filled = len(trait_div.find_all(class_=['filled', 'active']))
        total = len(trait_div.find_all(class_=['indicator', 'bar']))
        score = filled if filled else 0
        traits[name] = score
    return traits
```

#### 3.2 Text Mining from Descriptions
```python
def infer_traits_from_text(text):
    """Extract traits from descriptive text"""
    traits = {}
    
    # Energy level
    if 'high energy' in text.lower():
        traits['energy'] = 5
    elif 'moderate energy' in text.lower():
        traits['energy'] = 3
    
    # Friendliness
    if 'excellent with children' in text.lower():
        traits['good_with_children'] = 5
    
    return traits
```

## Implementation Plan

### Step 1: Enhanced Data Extraction (2 hours)
1. Update `akc_comprehensive_extractor.py`:
   - Add HTML section parsers
   - Extract female measurements
   - Parse breed group from navigation
   - Add fallback extractors

### Step 2: ScrapingBee Optimization (1 hour)
1. Update scraper configuration:
   - Increase wait time
   - Add JavaScript execution
   - Implement scroll triggers
   - Wait for specific elements

### Step 3: Testing & Validation (1 hour)
1. Test with multiple breeds:
   - Golden Retriever (current)
   - Poodle (different structure)
   - Bulldog (edge cases)

### Step 4: Quality Assurance
1. Validate extracted data
2. Handle missing fields gracefully
3. Implement confidence scores

## Expected Results

| Category | Current | Target | Method |
|----------|---------|--------|--------|
| Physical Data | 40% | 100% | Parse gendered text |
| Trait Scores | 0% | 100% | JS execution + visual parsing |
| Content Sections | 30% | 90% | Multiple selectors + wait |
| Metadata | 60% | 100% | Breadcrumb + HTML parsing |
| **Overall** | **30%** | **90%+** | Combined approach |

## Next Immediate Actions

1. **Quick Win**: Extract female measurements and breed group (30% → 45%)
2. **Medium**: Parse HTML sections for content (45% → 60%)
3. **Complex**: Implement JS execution for traits (60% → 90%+)

## Success Criteria

- [ ] All 16 temperament traits captured
- [ ] Both male and female measurements
- [ ] At least 5 content sections with text
- [ ] Breed group classification
- [ ] 90%+ completeness score
- [ ] Works for at least 3 different breeds