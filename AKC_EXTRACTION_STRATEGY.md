# AKC Breed Data Extraction Strategy

## Executive Summary
The AKC website uses React SPA with client-side rendering. Our current extraction captures only ~5% of content. This document outlines a comprehensive strategy to achieve 95%+ content capture.

## Current State Analysis

### Problems Identified
1. **Navigation Content Extraction**: Current selectors match generic classes that appear in navigation menus
2. **Missing Physical Data**: Height, weight, and lifespan exist but aren't extracted
3. **Non-numeric Trait Scores**: Extracting concatenated strings instead of 1-5 scores
4. **Low Content Capture**: Only ~5% of available content is being extracted

### Key Discovery
AKC stores **ALL breed data in structured JSON** within the page HTML:
- Location: `<div data-js-component="breedPage" data-js-props="{...}">`
- Format: Structured JSON with complete breed information
- Content: Physical traits, temperament scores, text sections, metadata

## Three-Tier Extraction Strategy

### Tier 1: JSON Extraction (Primary - 95% reliability)
Extract from `data-js-props` attribute containing structured data:

```python
# Find the breed page component
breed_div = soup.find('div', {'data-js-component': 'breedPage'})
if breed_div and breed_div.get('data-js-props'):
    data = json.loads(breed_div['data-js-props'])
    breed_data = data['breed']
```

**Data Structure:**
```json
{
  "breed": {
    "name": "Golden Retriever",
    "slug": "golden-retriever",
    "description": "...",
    "traits": {
      "energy": 5,
      "shedding": 4,
      "trainability": 5,
      "barking": 3,
      "friendliness_family": 5,
      "friendliness_strangers": 5,
      "friendliness_dogs": 5,
      "grooming": 2
    },
    "physical": {
      "height": "23-24 inches",
      "weight": "65-75 pounds",
      "lifespan": "10-12 years"
    },
    "sections": {
      "about": "...",
      "personality": "...",
      "health": "...",
      "care": "...",
      "history": "..."
    }
  }
}
```

### Tier 2: Metadata Extraction (Fallback - 80% reliability)
Extract from structured metadata in `<script type="application/ld+json">`:

```python
# PageMap metadata
scripts = soup.find_all('script', type='application/ld+json')
for script in scripts:
    data = json.loads(script.string)
    # Extract breed information
```

**Available Formats:**
- CSV-W Table Schema
- PageMap with breed attributes
- Structured Data with breed properties

### Tier 3: CSS Selector Extraction (Last Resort - 60% reliability)
Use breed-specific CSS classes:

```python
# Breed-specific selectors
selectors = {
    'about': '.breed-page__hero__overview',
    'personality': '.breed-page__personality',
    'health': '.breed-page__health',
    'traits': '.breed-trait-score__score',
    'physical': '.breed-vital__text'
}
```

## Implementation Plan

### Phase 1: JSON Extraction Implementation
**Priority:** HIGH  
**Impact:** Improves capture from 5% to 95%

1. Update `extract_from_scrapingbee()` method
2. Parse JSON from `data-js-props`
3. Map JSON fields to database schema
4. Handle edge cases and missing data

### Phase 2: CSS Selector Optimization
**Priority:** MEDIUM  
**Impact:** Backup extraction method

1. Replace generic selectors with breed-specific ones
2. Use classes prefixed with `breed-page__`
3. Extract numeric scores from trait elements
4. Parse physical measurements from text

### Phase 3: Fallback System Implementation
**Priority:** LOW  
**Impact:** Ensures 100% extraction coverage

1. Implement tiered extraction logic
2. Try JSON first, then metadata, then CSS
3. Merge data from multiple sources
4. Log extraction method used

### Phase 4: Testing & Validation
**Priority:** HIGH  
**Impact:** Ensures reliability

1. Test with 5 diverse breeds:
   - Golden Retriever (popular)
   - Xoloitzcuintli (rare)
   - French Bulldog (brachycephalic)
   - Greyhound (sighthound)
   - Poodle (multiple sizes)

2. Validate extraction completeness:
   - Physical measurements present
   - All 8 trait scores numeric (1-5)
   - Content sections > 100 chars each
   - Total content > 5000 chars

## Expected Outcomes

### Before Implementation
- Content Capture: ~5%
- Physical Data: 0%
- Trait Scores: Non-numeric strings
- Content Quality: Navigation text

### After Implementation
- Content Capture: 95%+
- Physical Data: 100%
- Trait Scores: Numeric 1-5 scale
- Content Quality: Actual breed information

## Technical Requirements

### ScrapingBee Configuration
```python
params = {
    'wait': '10000',          # Wait for React rendering
    'premium_proxy': 'true',  # Use premium proxy
    'country_code': 'us',     # US IP for access
    'block_ads': 'true',      # Reduce payload
    'block_resources': 'false' # Keep JS for rendering
}
```

### Data Mapping

| JSON Field | Database Column | Type | Example |
|------------|----------------|------|---------|
| breed.name | display_name | str | "Golden Retriever" |
| breed.slug | breed_slug | str | "golden-retriever" |
| traits.energy | energy | int | 5 |
| traits.shedding | shedding | int | 4 |
| physical.height | height_cm_min/max | float | 58.4-61.0 |
| physical.weight | weight_kg_min/max | float | 29.5-34.0 |
| physical.lifespan | lifespan_years_min/max | int | 10-12 |
| sections.about | about | text | "The Golden Retriever..." |

## Error Handling

1. **Missing JSON**: Fall back to metadata extraction
2. **Malformed JSON**: Use try/except, log error, try CSS
3. **No ScrapingBee credits**: Fall back to BeautifulSoup
4. **Timeout**: Retry with increased wait time
5. **Rate limiting**: Implement exponential backoff

## Monitoring & Metrics

Track extraction success:
- Extraction method used (json/metadata/css)
- Content completeness score
- ScrapingBee credit usage
- Error rates by extraction tier
- Processing time per breed

## Conclusion

This three-tier extraction strategy ensures maximum content capture while maintaining efficiency. The JSON extraction alone will improve our capture rate from 5% to 95%, with fallback methods ensuring we never miss critical breed data.