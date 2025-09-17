# Breed Database API Specification

## Overview

This document provides comprehensive technical specifications for the Breed Database API, including database architecture, data models, endpoint specifications, and implementation guidelines for the API development team.

## Database Architecture

### Core Tables

#### 1. `breeds_published` (Primary View)
**Purpose:** Main public-facing breed data with computed fields and quality validations
**Usage:** Primary source for all API endpoints

```sql
-- Key Fields
id                    SERIAL PRIMARY KEY
breed_slug           VARCHAR UNIQUE -- URL-safe identifier (e.g., 'golden-retriever')
display_name         VARCHAR        -- Human-readable name (e.g., 'Golden Retriever')
aliases              TEXT[]         -- Alternative names
size_category        ENUM('tiny', 'small', 'medium', 'large', 'giant')
adult_weight_min_kg  DECIMAL
adult_weight_max_kg  DECIMAL
adult_weight_avg_kg  DECIMAL        -- Computed average
height_min_cm        INTEGER
height_max_cm        INTEGER
energy               ENUM('low', 'moderate', 'high')
trainability         ENUM('low', 'moderate', 'high')
coat_length          ENUM('short', 'medium', 'long')
shedding            ENUM('low', 'moderate', 'high')
bark_level          ENUM('low', 'moderate', 'high')
lifespan_min_years  INTEGER
lifespan_max_years  INTEGER
lifespan_avg_years  DECIMAL        -- Computed average
origin              VARCHAR        -- Country/region of origin
friendliness_to_dogs     ENUM('low', 'moderate', 'high')
friendliness_to_humans   ENUM('low', 'moderate', 'high')
growth_end_months   INTEGER        -- When dog reaches adult size
senior_start_months INTEGER        -- When dog enters senior phase
comprehensive_content TEXT         -- Rich JSON content
data_quality_grade  VARCHAR        -- Quality assessment (A, B, C, etc.)
```

#### 2. `breeds_comprehensive_content` (Content Repository)
**Purpose:** Rich content including descriptions, care guides, and extended information

```sql
-- Key Fields
breed_slug              VARCHAR PRIMARY KEY
introduction           TEXT    -- Brief breed overview
history                TEXT    -- Breed history and origins
personality_description TEXT    -- Detailed personality traits
temperament            TEXT    -- Behavioral characteristics
good_with_children     TEXT    -- Child compatibility info
good_with_pets         TEXT    -- Pet compatibility info
intelligence_noted     TEXT    -- Intelligence characteristics
grooming_needs         TEXT    -- Grooming requirements
grooming_frequency     VARCHAR -- How often to groom
exercise_needs_detail  TEXT    -- Detailed exercise requirements
training_tips          TEXT    -- Training guidance
general_care          TEXT    -- Comprehensive care guide (NEW - 100% coverage)
health_issues         TEXT    -- Common health concerns
working_roles         TEXT    -- Historical/current work roles
fun_facts            TEXT    -- Interesting breed facts
recognized_by        TEXT    -- Kennel club recognition
color_varieties      TEXT    -- Available colors/patterns
coat                TEXT    -- Coat description
```

#### 3. `breeds_details` (Base Data)
**Purpose:** Core breed characteristics and source tracking

```sql
-- Source tracking fields
size_from            VARCHAR -- Data source for size info
weight_from          VARCHAR -- Data source for weight info
height_from          VARCHAR -- Data source for height info
lifespan_from        VARCHAR -- Data source for lifespan info
age_bounds_from      VARCHAR -- Data source for age boundaries
conflict_flags       JSONB   -- Data inconsistency flags
```

### Data Quality Metrics

Current database quality status:
- **Overall Quality Score:** 96.9%
- **Weight Coverage:** 100% (583/583 breeds)
- **Care Content Coverage:** 100% (571/571 breeds)
- **Energy Accuracy:** 69.6% (406/583 breeds)
- **Data Quality Issues:** 0

## API Endpoints Specification

### Base URL
```
https://api.yourplatform.com/v1/breeds
```

### Authentication
```http
Authorization: Bearer {api_key}
Content-Type: application/json
```

### 1. List All Breeds

```http
GET /breeds
```

**Query Parameters:**
```
?size=small,medium          # Filter by size categories
?energy=high                # Filter by energy level
?origin=Germany             # Filter by country of origin
?good_with_children=high     # Filter by child compatibility
?trainability=high          # Filter by trainability
?coat_length=short          # Filter by coat length
?shedding=low               # Filter by shedding level
?weight_min=10              # Minimum weight in kg
?weight_max=30              # Maximum weight in kg
?lifespan_min=12            # Minimum lifespan in years
?page=1                     # Pagination
?limit=20                   # Results per page (max 100)
?sort=name                  # Sort by: name, size, weight, lifespan
?order=asc                  # Order: asc, desc
```

**Response:**
```json
{
  "data": [
    {
      "breed_slug": "golden-retriever",
      "display_name": "Golden Retriever",
      "aliases": ["Golden", "Goldie"],
      "size_category": "large",
      "adult_weight": {
        "min_kg": 25,
        "max_kg": 34,
        "avg_kg": 29.5
      },
      "height_cm": {
        "min": 51,
        "max": 61
      },
      "energy": "high",
      "trainability": "high",
      "coat_length": "medium",
      "shedding": "high",
      "bark_level": "moderate",
      "lifespan_years": {
        "min": 10,
        "max": 12,
        "avg": 11
      },
      "origin": "Scotland",
      "friendliness": {
        "to_dogs": "high",
        "to_humans": "high"
      },
      "life_stages": {
        "growth_end_months": 18,
        "senior_start_months": 84
      },
      "data_quality_grade": "A"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 583,
    "pages": 30
  },
  "filters_applied": {
    "energy": ["high"],
    "size": ["large"]
  }
}
```

### 2. Get Single Breed

```http
GET /breeds/{breed_slug}
```

**Response:**
```json
{
  "breed_slug": "golden-retriever",
  "display_name": "Golden Retriever",
  "aliases": ["Golden", "Goldie"],
  "basic_info": {
    "size_category": "large",
    "adult_weight": {
      "min_kg": 25,
      "max_kg": 34,
      "avg_kg": 29.5
    },
    "height_cm": {
      "min": 51,
      "max": 61
    },
    "lifespan_years": {
      "min": 10,
      "max": 12,
      "avg": 11
    },
    "origin": "Scotland"
  },
  "characteristics": {
    "energy": "high",
    "trainability": "high",
    "coat_length": "medium",
    "shedding": "high",
    "bark_level": "moderate",
    "friendliness": {
      "to_dogs": "high",
      "to_humans": "high"
    }
  },
  "life_stages": {
    "growth_end_months": 18,
    "senior_start_months": 84
  },
  "content": {
    "introduction": "The Golden Retriever is a Scottish breed of retriever dog...",
    "history": "The breed was originally developed in Scotland...",
    "personality_description": "Golden Retrievers are friendly, intelligent...",
    "temperament": "Gentle, friendly, confident",
    "compatibility": {
      "with_children": "Excellent with children of all ages...",
      "with_pets": "Generally good with other pets..."
    },
    "intelligence_noted": "Highly intelligent and eager to please...",
    "working_roles": "Originally bred for retrieving game birds..."
  },
  "care_guide": {
    "grooming": {
      "needs": "Regular brushing 2-3 times per week...",
      "frequency": "2-3 times weekly"
    },
    "exercise": {
      "needs": "Requires substantial daily exercise...",
      "level": "high"
    },
    "training": {
      "tips": "Highly trainable and responds well...",
      "difficulty": "easy"
    },
    "health": {
      "common_issues": "Hip dysplasia, elbow dysplasia...",
      "considerations": "Large breeds benefit from joint supplements..."
    },
    "feeding": {
      "guidelines": "Large dogs typically need 2 to 3 cups...",
      "notes": "High-energy dogs may need additional calories..."
    }
  },
  "additional_info": {
    "fun_facts": "Golden Retrievers have webbed feet...",
    "recognized_by": "AKC, FCI, KC, CKC",
    "color_varieties": "Light cream to dark golden",
    "coat_description": "Dense, water-repellent outer coat..."
  },
  "data_quality_grade": "A",
  "last_updated": "2025-09-17T19:06:02Z"
}
```

### 3. Search Breeds

```http
GET /breeds/search?q={query}
```

**Query Parameters:**
```
?q=friendly large dog       # Natural language search
?fields=name,description     # Search specific fields
?fuzzy=true                 # Enable fuzzy matching
?limit=10                   # Max results
```

**Response:**
```json
{
  "query": "friendly large dog",
  "results": [
    {
      "breed_slug": "golden-retriever",
      "display_name": "Golden Retriever",
      "relevance_score": 0.95,
      "match_reasons": [
        "High friendliness rating",
        "Large size category",
        "Description mentions 'friendly'"
      ],
      "basic_info": {
        "size_category": "large",
        "friendliness": {
          "to_humans": "high"
        }
      }
    }
  ],
  "total_results": 15,
  "search_time_ms": 23
}
```

### 4. Get Breed Recommendations

```http
POST /breeds/recommendations
```

**Request Body:**
```json
{
  "preferences": {
    "living_situation": "apartment", // apartment, house_small_yard, house_large_yard
    "experience_level": "beginner",  // beginner, intermediate, experienced
    "activity_level": "moderate",    // low, moderate, high
    "time_availability": {
      "daily_exercise_minutes": 60,
      "grooming_frequency": "weekly"
    },
    "family_situation": {
      "has_children": true,
      "children_ages": [5, 10],
      "has_other_pets": false
    },
    "preferences": {
      "size": ["medium", "large"],
      "coat_length": ["short", "medium"],
      "shedding": ["low", "moderate"],
      "energy": ["moderate", "high"]
    },
    "deal_breakers": {
      "high_shedding": true,
      "excessive_barking": true
    }
  }
}
```

**Response:**
```json
{
  "recommendations": [
    {
      "breed_slug": "labrador-retriever",
      "display_name": "Labrador Retriever",
      "match_score": 0.92,
      "match_reasons": [
        "Excellent with children",
        "Moderate exercise needs match your availability",
        "Trainable for beginners",
        "Size preference match"
      ],
      "potential_concerns": [
        "Moderate shedding (you prefer low-moderate)"
      ],
      "basic_info": {
        "size_category": "large",
        "energy": "high",
        "trainability": "high"
      }
    }
  ],
  "total_matches": 8,
  "algorithm_version": "v2.1"
}
```

### 5. Compare Breeds

```http
POST /breeds/compare
```

**Request Body:**
```json
{
  "breeds": ["golden-retriever", "labrador-retriever", "german-shepherd"]
}
```

**Response:**
```json
{
  "comparison": {
    "breeds": [
      {
        "breed_slug": "golden-retriever",
        "display_name": "Golden Retriever"
      },
      {
        "breed_slug": "labrador-retriever",
        "display_name": "Labrador Retriever"
      },
      {
        "breed_slug": "german-shepherd",
        "display_name": "German Shepherd"
      }
    ],
    "characteristics": {
      "size_category": ["large", "large", "large"],
      "adult_weight_avg_kg": [29.5, 30.0, 32.5],
      "energy": ["high", "high", "high"],
      "trainability": ["high", "high", "high"],
      "shedding": ["high", "moderate", "high"],
      "friendliness_to_children": ["high", "high", "moderate"]
    },
    "care_requirements": {
      "exercise_needs": [
        "Substantial daily exercise including vigorous activities",
        "High energy requiring regular exercise and mental stimulation",
        "Requires substantial daily exercise and mental challenges"
      ],
      "grooming_frequency": ["2-3 times weekly", "Weekly", "2-3 times weekly"]
    },
    "summary": {
      "similarities": [
        "All are large breeds",
        "All have high energy and trainability",
        "All require substantial exercise"
      ],
      "differences": [
        "German Shepherd has moderate child-friendliness vs high for others",
        "Labrador has moderate shedding vs high for others"
      ]
    }
  }
}
```

### 6. Get Breed Statistics

```http
GET /breeds/statistics
```

**Response:**
```json
{
  "database_stats": {
    "total_breeds": 583,
    "quality_score": 96.9,
    "last_updated": "2025-09-17T19:06:02Z"
  },
  "coverage_metrics": {
    "weight_data": 100.0,
    "care_content": 100.0,
    "energy_classifications": 69.6,
    "health_information": 85.2
  },
  "distribution": {
    "by_size": {
      "tiny": 45,
      "small": 128,
      "medium": 156,
      "large": 189,
      "giant": 65
    },
    "by_energy": {
      "low": 115,
      "moderate": 177,
      "high": 291
    },
    "by_origin": {
      "Germany": 67,
      "United Kingdom": 89,
      "United States": 23,
      "France": 34
    }
  }
}
```

## Implementation Guidelines

### 1. Database Connection

**Primary Table:** Always use `breeds_published` as the main data source
```sql
-- Example query for breed listing
SELECT
  breed_slug,
  display_name,
  aliases,
  size_category,
  adult_weight_min_kg,
  adult_weight_max_kg,
  adult_weight_avg_kg,
  energy,
  trainability,
  data_quality_grade
FROM breeds_published
WHERE data_quality_grade IN ('A', 'B')
ORDER BY display_name;
```

**Join for Rich Content:**
```sql
-- Example query for detailed breed view
SELECT
  bp.*,
  bcc.introduction,
  bcc.personality_description,
  bcc.general_care,
  bcc.health_issues
FROM breeds_published bp
LEFT JOIN breeds_comprehensive_content bcc ON bp.breed_slug = bcc.breed_slug
WHERE bp.breed_slug = $1;
```

### 2. Data Transformation

**Weight Object:**
```javascript
// Transform database fields to API format
const transformWeight = (row) => ({
  min_kg: row.adult_weight_min_kg,
  max_kg: row.adult_weight_max_kg,
  avg_kg: row.adult_weight_avg_kg
});
```

**Care Guide Parsing:**
```javascript
// Parse structured care content
const parseCareGuide = (general_care) => {
  const sections = general_care.split('\n\n');
  const care = {};

  sections.forEach(section => {
    if (section.startsWith('**Grooming:**')) {
      care.grooming = { needs: section.replace('**Grooming:**', '').trim() };
    }
    // Parse other sections...
  });

  return care;
};
```

### 3. Caching Strategy

**Redis Cache Keys:**
```
breed:detail:{breed_slug}     # Individual breed cache (1 hour)
breeds:list:{hash}           # List results cache (30 minutes)
breeds:stats                 # Statistics cache (6 hours)
breeds:search:{query_hash}   # Search results cache (1 hour)
```

**Cache Implementation:**
```javascript
const getCachedBreed = async (breed_slug) => {
  const cacheKey = `breed:detail:${breed_slug}`;
  let breed = await redis.get(cacheKey);

  if (!breed) {
    breed = await fetchBreedFromDB(breed_slug);
    await redis.setex(cacheKey, 3600, JSON.stringify(breed));
  }

  return JSON.parse(breed);
};
```

### 4. Error Handling

**Standard Error Responses:**
```json
{
  "error": {
    "code": "BREED_NOT_FOUND",
    "message": "Breed with slug 'invalid-breed' not found",
    "details": {
      "breed_slug": "invalid-breed",
      "suggestions": ["golden-retriever", "german-shepherd"]
    }
  }
}
```

**HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Breed Not Found
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

### 5. Rate Limiting

**Recommended Limits:**
- Public endpoints: 100 requests/minute
- Search endpoints: 60 requests/minute
- Recommendations: 20 requests/minute

### 6. API Versioning

**URL Versioning:**
```
/v1/breeds          # Current stable version
/v2/breeds          # Future version with enhanced features
```

**Version Header Support:**
```http
API-Version: 1.0
Accept: application/vnd.breedapi.v1+json
```

## Data Quality Indicators

### Quality Grades
- **A Grade:** Complete data, high accuracy (85%+ coverage)
- **B Grade:** Good data, minor gaps (70-84% coverage)
- **C Grade:** Acceptable data, some gaps (50-69% coverage)
- **D Grade:** Limited data, major gaps (<50% coverage)

### Coverage Metrics
Current coverage levels to expose in API:
- Weight data: 100% coverage
- Care content: 100% coverage
- Energy classifications: 69.6% coverage
- Health information: Variable by breed

## Performance Considerations

### Database Optimization
1. **Indexes:** Ensure indexes on `breed_slug`, `size_category`, `energy`, `origin`
2. **Query Optimization:** Use prepared statements and connection pooling
3. **Read Replicas:** Consider read replicas for high-traffic scenarios

### Response Optimization
1. **Field Selection:** Allow clients to specify required fields
2. **Pagination:** Implement cursor-based pagination for large datasets
3. **Compression:** Use gzip compression for responses

### Monitoring
1. **Query Performance:** Monitor slow queries (>100ms)
2. **Cache Hit Rate:** Target >90% cache hit rate
3. **API Response Times:** Target <200ms for breed details, <500ms for search

## Security Considerations

### API Key Management
- Rate limiting per API key
- Usage analytics and billing
- Key rotation capabilities

### Data Validation
- Input sanitization for all parameters
- SQL injection prevention
- XSS protection for user-generated content

### Privacy
- No PII stored in breed data
- Optional user preference storage with consent
- GDPR compliance for EU users

## Deployment Recommendations

### Infrastructure
- **Database:** PostgreSQL 13+ with read replicas
- **Cache:** Redis cluster for high availability
- **API Server:** Node.js/Express or Python/FastAPI
- **Load Balancer:** Nginx or AWS ALB

### Monitoring & Logging
- **APM:** Application performance monitoring
- **Error Tracking:** Centralized error logging
- **Usage Analytics:** API usage patterns and trends

---

## Quick Start Examples

### Basic Breed Lookup
```bash
curl -X GET "https://api.yourplatform.com/v1/breeds/golden-retriever" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Filtered Breed Search
```bash
curl -X GET "https://api.yourplatform.com/v1/breeds?size=large&energy=high&good_with_children=high" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Breed Recommendations
```bash
curl -X POST "https://api.yourplatform.com/v1/breeds/recommendations" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"preferences": {"living_situation": "apartment", "has_children": true}}'
```

This specification provides a complete foundation for implementing a robust, scalable breed database API with the enriched data we've created. The 96.9% quality score and 100% care content coverage ensure excellent user experiences across all endpoints.