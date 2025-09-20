# Breed API Unified View Specification

## Overview
A comprehensive unified database view (`breeds_unified_api`) has been created to consolidate all breed information from multiple tables into a single source of truth for the API team.

**View Name:** `breeds_unified_api`
**Total Records:** 583 breeds
**Average Content Completeness:** 57.3%
**Rich Content Coverage:** 390 breeds (67%)

---

## Data Structure

### Core Identification Fields
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | BIGINT | Unique breed identifier | 1 |
| `breed_slug` | TEXT | URL-friendly unique identifier | "golden-retriever" |
| `display_name` | TEXT | Human-readable breed name | "Golden Retriever" |
| `aliases` | TEXT[] | Alternative breed names | ["Golden", "Yellow Retriever"] |

### Physical Characteristics
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `size_category` | TEXT | Size classification (xs/s/m/l/xl) | "l" |
| `adult_weight_min_kg` | FLOAT | Minimum adult weight in kg | 25.0 |
| `adult_weight_max_kg` | FLOAT | Maximum adult weight in kg | 34.0 |
| `adult_weight_avg_kg` | FLOAT | Average adult weight in kg | 29.5 |
| `height_min_cm` | INTEGER | Minimum height in cm | 51 |
| `height_max_cm` | INTEGER | Maximum height in cm | 61 |
| `lifespan_min_years` | INTEGER | Minimum lifespan | 10 |
| `lifespan_max_years` | INTEGER | Maximum lifespan | 12 |
| `lifespan_avg_years` | FLOAT | Average lifespan | 11.0 |

### Life Stages
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `growth_end_months` | INTEGER | Age when growth ends (months) | 18 |
| `senior_start_months` | INTEGER | Age when senior stage begins (months) | 84 |

### Behavioral Traits
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `energy` | TEXT | Energy level (low/moderate/high) | "high" |
| `trainability` | TEXT | Training difficulty | "easy" |
| `coat_length` | TEXT | Coat length classification | "medium" |
| `shedding` | TEXT | Shedding level | "moderate" |
| `bark_level` | TEXT | Barking tendency | "occasional" |
| `friendliness_to_dogs` | INTEGER | Dog friendliness (0-5) | 4 |
| `friendliness_to_humans` | INTEGER | Human friendliness (0-5) | 5 |

### Content Fields
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `origin` | TEXT | Country/region of origin | "Scotland" |
| `introduction` | TEXT | Brief introduction | "The Golden Retriever is..." |
| `history` | TEXT | Detailed history | "Developed in Scotland..." |
| `history_brief` | TEXT | Short history summary | "Bred in the 1860s..." |
| `personality_description` | TEXT | Personality overview | "Friendly and intelligent..." |
| `personality_traits` | TEXT[] | Key personality traits | ["friendly", "intelligent", "loyal"] |
| `temperament` | TEXT | Temperament description | "Gentle and patient..." |
| `good_with_children` | BOOLEAN | Child-friendly indicator | true |
| `good_with_pets` | BOOLEAN | Pet-friendly indicator | true |
| `intelligence_noted` | BOOLEAN | Notable intelligence flag | true |

### Care Requirements
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `general_care` | TEXT | Comprehensive care guide | "Golden Retrievers require..." |
| `grooming_needs` | TEXT | Grooming requirements | "Regular brushing needed..." |
| `grooming_frequency` | TEXT | How often grooming needed | "weekly" |
| `exercise_needs_detail` | TEXT | Exercise requirements | "60-90 minutes daily..." |
| `exercise_level` | TEXT | Exercise intensity | "high" |
| `training_tips` | TEXT | Training recommendations | "Start early with..." |
| `health_issues` | TEXT | Common health concerns | "Hip dysplasia, eye conditions..." |

### Appearance
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `coat` | TEXT | Coat type description | "Dense, water-repellent double coat" |
| `colors` | TEXT | Common colors | "Golden, cream, dark golden" |
| `color_varieties` | TEXT | Color variations | "Light golden to dark golden" |

### Enrichment Content
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `fun_facts` | TEXT[] | Interesting facts | ["3rd most popular breed", "Excellent swimmers"] |
| `has_world_records` | BOOLEAN | Has world records | true |
| `working_roles` | TEXT[] | Working capabilities | ["therapy", "search-rescue", "guide-dog"] |
| `breed_standard` | TEXT | Official breed standard | "AKC standard states..." |
| `recognized_by` | TEXT[] | Kennel club recognition | ["AKC", "UKC", "FCI"] |

### Metadata & Quality
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `data_quality_grade` | TEXT | Data quality rating (A+/A/B) | "A+" |
| `content_completeness_score` | NUMERIC | Completeness score (0-100) | 85.0 |
| `has_rich_content` | BOOLEAN | Has comprehensive content | true |
| `care_content_word_count` | INTEGER | Word count of care content | 672 |
| `size_category_display` | TEXT | Human-readable size | "Large" |
| `energy_level_display` | TEXT | Human-readable energy | "High Energy" |

### Tracking Fields
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `created_at` | TIMESTAMP | Record creation date | "2025-09-06T20:33:37" |
| `updated_at` | TIMESTAMP | Last update date | "2025-09-17T15:52:27" |
| `content_updated_at` | TIMESTAMP | Content last updated | "2025-09-17T19:05:22" |

---

## API Query Examples

### Get Single Breed
```sql
SELECT * FROM breeds_unified_api
WHERE breed_slug = 'golden-retriever';
```

### Search by Size and Energy
```sql
SELECT breed_slug, display_name, size_category, energy,
       content_completeness_score
FROM breeds_unified_api
WHERE size_category IN ('l', 'xl')
  AND energy = 'high'
ORDER BY content_completeness_score DESC;
```

### Get Family-Friendly Breeds
```sql
SELECT breed_slug, display_name, size_category_display,
       energy_level_display, personality_description
FROM breeds_unified_api
WHERE good_with_children = true
  AND good_with_pets = true
  AND has_rich_content = true
ORDER BY display_name;
```

### Top Quality Content Breeds
```sql
SELECT breed_slug, display_name, content_completeness_score,
       care_content_word_count
FROM breeds_unified_api
WHERE data_quality_grade = 'A+'
  AND content_completeness_score >= 80
ORDER BY content_completeness_score DESC
LIMIT 10;
```

---

## Helper Functions

### 1. Get Complete Breed Details
```sql
SELECT * FROM get_breed_complete('golden-retriever');
```
Returns: Single row with all breed details

### 2. Search Breeds with Filters
```sql
SELECT * FROM search_breeds_complete(
    p_size_categories => ARRAY['l', 'xl'],
    p_energy_levels => ARRAY['high'],
    p_good_with_children => true,
    p_good_with_pets => true,
    p_limit => 10,
    p_offset => 0
);
```
Returns: Filtered list with key fields

### 3. Get Similar Breeds
```sql
SELECT * FROM get_similar_breeds('golden-retriever', 5);
```
Returns: Top 5 similar breeds with similarity scores

---

## Data Quality Metrics

### Overall Statistics
- **Total Breeds:** 583
- **Average Completeness:** 57.3%
- **Breeds with Rich Content:** 390 (67%)

### Quality Grade Distribution
- **Grade A+:** Comprehensive data with all critical fields
- **Grade A:** Complete basic data with most content fields
- **Grade B:** Good basic data, some content gaps

### Content Coverage
| Content Type | Coverage | Count |
|--------------|----------|-------|
| Weight Data | 100% | 583 |
| Care Content | 100% | 583 |
| Personality Description | 72% | 420 |
| Energy Levels (accurate) | 69.6% | 406 |
| Fun Facts | 67% | 390 |
| Health Information | 41% | 239 |

---

## Performance Considerations

### View Type
- **Type:** Standard VIEW (not materialized)
- **Updates:** Real-time (instant reflection of source table changes)
- **Performance:** Optimized with indexes on underlying tables

### Indexes
Created on base tables:
- `breeds_details.breed_slug`
- `breeds_comprehensive_content.breed_slug`

### Caching Recommendations
- Cache individual breed pages for 1-6 hours
- Cache search results for 15-30 minutes
- Use `updated_at` and `content_updated_at` for cache invalidation

---

## Implementation Guidelines

### 1. Basic Breed Page
Required fields for minimal viable breed page:
- `display_name`, `breed_slug`
- `size_category_display`, `energy_level_display`
- `adult_weight_avg_kg`, `lifespan_avg_years`
- `personality_description` or `introduction`
- `general_care`

### 2. Enhanced Breed Page
Additional fields for rich experience:
- `fun_facts`, `working_roles`
- `good_with_children`, `good_with_pets`
- `grooming_needs`, `exercise_needs_detail`
- `health_issues`
- `history_brief`

### 3. Content Fallbacks
When fields are NULL:
- Use `introduction` if `personality_description` is NULL
- Display "Information coming soon" for missing care content
- Hide sections entirely if no fun facts exist

### 4. Quality Filtering
Recommended filters for production:
```sql
WHERE data_quality_grade IN ('A+', 'A', 'B')
  AND content_completeness_score >= 50
```

---

## Update Workflow

### Content Updates
1. Updates to `breeds_comprehensive_content` table
2. Instantly reflected in `breeds_unified_api` view
3. No manual refresh needed

### Data Quality Improvements
1. Track breeds with low `content_completeness_score`
2. Prioritize enrichment for popular breeds
3. Monitor `NULL` fields for data gaps

---

## Contact & Support

**Database:** Supabase PostgreSQL
**View Location:** Public schema
**Permissions:** SELECT granted to authenticated, anon, service_role

For questions or issues with the unified view, please refer to:
- SQL source: `create_unified_breed_view.sql`
- Structure validation: `check_breed_tables_structure.py`
- This documentation: `BREED_API_UNIFIED_VIEW_SPECS.md`

---

*Last Updated: 2025-09-19*
*View Version: 1.0*