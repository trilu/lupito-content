# Breed Data Completion Plan - Wikipedia Integration

## Executive Summary

This document outlines the comprehensive plan to complete breed data coverage from 36% to 90%+ by scraping Wikipedia for the missing 391 breeds not covered by the BARK/Dogo scraper project.

## Current State Analysis

### Database Coverage
| Table | Breeds Count | Description |
|-------|-------------|-------------|
| `breeds` | 546 | Master list of all breeds |
| `breeds_details` | 198 | Detailed data from BARK/Dogo scraper |
| `akc_breeds` | 160 | AKC data (to be discarded - poor quality) |
| **Missing** | **391** | **Breeds without detailed data (71.6%)** |

### Data Structure - breeds_details Table
```sql
breeds_details (
    id, breed_slug, display_name, aliases,
    size, energy, coat_length, shedding, 
    trainability, bark_level,
    lifespan_years_min, lifespan_years_max,
    weight_kg_min, weight_kg_max,
    height_cm_min, height_cm_max,
    origin, friendliness_to_dogs, friendliness_to_humans,
    comprehensive_content (JSON)
)
```

### Controlled Vocabularies (from BARK Project)
- **Size**: tiny, small, medium, large, giant
- **Energy**: low, moderate, high, very_high
- **Coat Length**: short, medium, long
- **Shedding**: minimal, low, moderate, high, very_high
- **Trainability**: challenging, moderate, easy, very_easy
- **Bark Level**: quiet, occasional, moderate, frequent, very_vocal

## Wikipedia as Data Source

### Advantages
- ✅ **Free** - No API credits needed
- ✅ **Static HTML** - No JavaScript rendering required
- ✅ **Comprehensive** - Most breeds have dedicated pages
- ✅ **Structured** - Consistent infobox format
- ✅ **Rich Content** - Detailed sections on history, temperament, health

### Data Available from Wikipedia
1. **Infobox Data**:
   - Origin/Country
   - Height (inches → cm conversion needed)
   - Weight (lbs → kg conversion needed)
   - Lifespan
   - Coat type and colors
   - Breed group/classification

2. **Article Sections**:
   - History/Origin
   - Temperament/Personality
   - Health concerns
   - Care requirements
   - Training information

## Implementation Strategy

### Phase 1: URL Mapping (30 minutes)
```python
# wikipedia_breed_mapping.py
- Load 391 missing breeds from missing_breeds.txt
- Generate Wikipedia URLs:
  - Handle special characters (é → %C3%A9)
  - Handle spaces (→ underscores)
  - Test URL validity
- Output: wikipedia_urls.txt
```

### Phase 2: Scraper Development (2 hours)
```python
# jobs/wikipedia_breed_scraper.py

class WikipediaBreedScraper:
    def __init__(self):
        self.session = requests.Session()
        self.supabase = create_client(url, key)
    
    def extract_infobox(self, soup):
        # Extract structured data from infobox
        # Convert measurements to metric
        # Return dict with breed characteristics
    
    def extract_content(self, soup):
        # Parse article sections
        # Extract temperament, care, health info
        # Return comprehensive_content JSON
    
    def map_to_controlled_vocab(self, raw_data):
        # Map extracted data to enums
        # Apply business logic for categorization
        # Return breeds_details compatible dict
    
    def save_to_database(self, breed_data):
        # Insert/update breeds_details table
        # Store raw HTML in breed_raw
        # Save narratives in breed_text_versions
```

### Phase 3: Data Mapping Logic

#### Size Determination
```python
def determine_size(weight_kg):
    if weight_kg < 5: return 'tiny'
    elif weight_kg < 10: return 'small'
    elif weight_kg < 25: return 'medium'
    elif weight_kg < 45: return 'large'
    else: return 'giant'
```

#### Energy Level Inference
```python
def infer_energy(content):
    high_energy_keywords = ['active', 'energetic', 'athletic', 'working']
    low_energy_keywords = ['calm', 'relaxed', 'laid-back', 'gentle']
    # Analyze keyword frequency in temperament section
```

#### Trainability Assessment
```python
def assess_trainability(content):
    easy_keywords = ['intelligent', 'eager to please', 'trainable', 'obedient']
    difficult_keywords = ['stubborn', 'independent', 'strong-willed', 'challenging']
    # Score based on keyword presence
```

### Phase 4: Execution Plan (3-4 hours)

#### Batch Processing Strategy
```python
BATCH_SIZE = 50
RATE_LIMIT = 1  # second between requests

for batch in chunks(missing_breeds, BATCH_SIZE):
    for breed in batch:
        try:
            data = scrape_breed(breed)
            save_to_database(data)
            time.sleep(RATE_LIMIT)
        except Exception as e:
            log_error(breed, e)
            continue
```

#### Progress Tracking
```csv
# wikipedia_scraping_report.csv
breed_name,wikipedia_url,status,fields_extracted,completeness_score,error
Africanis,https://en.wikipedia.org/wiki/Africanis,success,18/22,82%,
Aidi,https://en.wikipedia.org/wiki/Aidi,success,15/22,68%,
Akbash,https://en.wikipedia.org/wiki/Akbash,failed,0/22,0%,Page not found
```

### Phase 5: Quality Assurance (1 hour)

#### Data Validation Rules
1. **Required Fields**: breed_slug, display_name, size
2. **Range Checks**:
   - Weight: 0.5 - 100 kg
   - Height: 15 - 100 cm
   - Lifespan: 5 - 20 years
3. **Enum Validation**: All controlled vocabulary fields must use valid enum values
4. **Completeness Score**: Minimum 40% fields populated for acceptance

#### Final Reports
```python
# Generate coverage statistics
total_breeds = 546
breeds_with_details = count(breeds_details)
coverage_percentage = (breeds_with_details / total_breeds) * 100

# Quality metrics
avg_completeness = avg(completeness_scores)
breeds_needing_review = filter(lambda b: b.completeness < 40%)
```

## Expected Outcomes

### Coverage Improvement
| Metric | Before | After |
|--------|--------|-------|
| Total Breeds | 546 | 546 |
| Breeds with Details | 198 | ~540 |
| Coverage % | 36% | 98%+ |
| Missing Data | 348 | ~6 |

### Data Quality
- **Primary Fields**: 80%+ completeness
- **Comprehensive Content**: 100% populated
- **Controlled Vocabularies**: 100% valid enums
- **Source Attribution**: All Wikipedia sources tracked

## File Deliverables

1. **Code Files**:
   - `wikipedia_breed_mapping.py` - URL generator
   - `jobs/wikipedia_breed_scraper.py` - Main scraper
   - `etl/wikipedia_normalizer.py` - Data normalization

2. **Data Files**:
   - `missing_breeds.txt` - 391 breeds to scrape
   - `wikipedia_urls.txt` - Mapped Wikipedia URLs
   - `wikipedia_scraping_report.csv` - Execution report

3. **Documentation**:
   - `BREED_DATA_COMPLETION_PLAN.md` - This document
   - `WIKIPEDIA_SCRAPER_DOCS.md` - Technical documentation

## Risk Mitigation

### Potential Issues & Solutions
| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing Wikipedia pages | Data gaps | Use alternative sources (DogTime, PetMD) |
| Inconsistent data format | Parsing errors | Flexible parser with fallbacks |
| Rate limiting | Slow execution | Respectful 1 req/sec limit |
| Data quality variations | Poor completeness | Manual review queue for low scores |

## Success Criteria

✅ **391 missing breeds processed**  
✅ **90%+ total coverage achieved**  
✅ **breeds_details table fully populated**  
✅ **All data validated and normalized**  
✅ **Comprehensive documentation delivered**  
✅ **Zero ScrapingBee credits consumed**  

## Summary

This plan provides a systematic approach to complete the breed database using Wikipedia as a free, comprehensive data source. By leveraging the existing BARK project infrastructure and controlled vocabularies, we can achieve 98%+ coverage while maintaining data consistency and quality. The entire process can be completed in approximately 6-8 hours with minimal cost and maximum reliability.