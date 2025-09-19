# Breed Database Technical Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT APPLICATIONS                        │
├─────────────────────────────────────────────────────────────────────┤
│  Web App  │  Mobile App  │  Partner APIs  │  Admin Dashboard       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY                                │
├─────────────────────────────────────────────────────────────────────┤
│  Rate Limiting  │  Authentication  │  Request Routing  │  Logging   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BREED API SERVICE                            │
├─────────────────────────────────────────────────────────────────────┤
│  Controllers  │  Business Logic  │  Data Mappers  │  Cache Layer    │
└─────────────────────────────────────────────────────────────────────┘
                          │                        │
                          ▼                        ▼
┌─────────────────────────────────────┐  ┌─────────────────────────────┐
│            REDIS CACHE              │  │       SEARCH ENGINE         │
├─────────────────────────────────────┤  ├─────────────────────────────┤
│  • Breed Details Cache             │  │  • Elasticsearch/Solr       │
│  • Search Results Cache            │  │  • Full-text Search         │
│  • Statistics Cache                │  │  • Faceted Search           │
│  • Session Storage                 │  │  • Recommendations          │
└─────────────────────────────────────┘  └─────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL DATABASE                              │
├─────────────────────────────────────────────────────────────────────┤
│  Primary DB (Write)           │  Read Replicas (Read)              │
│  • breeds_published           │  • Load Balanced Reads              │
│  • breeds_comprehensive_content│  • Analytics Queries              │
│  • breeds_details             │  • Background Processing           │
└─────────────────────────────────────────────────────────────────────┘
```

## Database Schema Detail

### Table Relationships

```sql
-- Core relationship diagram
breeds_details (1) ←──── breeds_published (view)
      │                        │
      │                        │
      └──→ breeds_comprehensive_content (1:1)
                               │
                               └──→ Generated care_content (enriched)
```

### Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raw Sources   │───▶│  Data Pipeline  │───▶│  Quality Gates  │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Wikipedia     │    │ • Validation    │    │ • 96.9% Quality │
│ • AKC Data      │    │ • Enrichment    │    │ • 100% Weight   │
│ • Breed Clubs   │    │ • Transformation│    │ • 100% Care     │
│ • Manual Entry  │    │ • Care Generation│    │ • 69.6% Energy  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
                                                      ▼
                                       ┌─────────────────┐
                                       │  breeds_details │
                                       │   (Base Table)  │
                                       └─────────────────┘
                                                      │
                                                      ▼
                                       ┌─────────────────┐
                                       │breeds_published │
                                       │    (API View)   │
                                       └─────────────────┘
```

## API Architecture Layers

### 1. Presentation Layer (Controllers)
```javascript
// Example controller structure
class BreedsController {
  async getBreed(req, res) {
    const { breed_slug } = req.params;
    const breed = await this.breedService.getBreedDetail(breed_slug);
    res.json(this.formatter.formatBreedDetail(breed));
  }

  async searchBreeds(req, res) {
    const filters = this.validator.validateFilters(req.query);
    const results = await this.breedService.searchBreeds(filters);
    res.json(this.formatter.formatBreedList(results));
  }

  async getRecommendations(req, res) {
    const preferences = this.validator.validatePreferences(req.body);
    const recommendations = await this.recommendationService.getRecommendations(preferences);
    res.json(this.formatter.formatRecommendations(recommendations));
  }
}
```

### 2. Business Logic Layer (Services)
```javascript
// Example service structure
class BreedService {
  constructor(breedRepository, cacheService, searchService) {
    this.repository = breedRepository;
    this.cache = cacheService;
    this.search = searchService;
  }

  async getBreedDetail(breed_slug) {
    // Try cache first
    let breed = await this.cache.get(`breed:detail:${breed_slug}`);

    if (!breed) {
      // Fetch from database with joins
      breed = await this.repository.getBreedWithContent(breed_slug);

      if (breed) {
        // Transform and cache
        breed = this.transformBreedData(breed);
        await this.cache.set(`breed:detail:${breed_slug}`, breed, 3600);
      }
    }

    return breed;
  }

  transformBreedData(rawBreed) {
    return {
      breed_slug: rawBreed.breed_slug,
      display_name: rawBreed.display_name,
      basic_info: {
        size_category: rawBreed.size_category,
        adult_weight: {
          min_kg: rawBreed.adult_weight_min_kg,
          max_kg: rawBreed.adult_weight_max_kg,
          avg_kg: rawBreed.adult_weight_avg_kg
        }
      },
      care_guide: this.parseCareContent(rawBreed.general_care)
    };
  }
}
```

### 3. Data Access Layer (Repositories)
```javascript
// Example repository structure
class BreedRepository {
  constructor(database) {
    this.db = database;
  }

  async getBreedWithContent(breed_slug) {
    const query = `
      SELECT
        bp.*,
        bcc.introduction,
        bcc.personality_description,
        bcc.general_care,
        bcc.health_issues,
        bcc.grooming_needs,
        bcc.exercise_needs_detail,
        bcc.training_tips
      FROM breeds_published bp
      LEFT JOIN breeds_comprehensive_content bcc ON bp.breed_slug = bcc.breed_slug
      WHERE bp.breed_slug = $1
        AND bp.data_quality_grade IN ('A', 'B')
    `;

    const result = await this.db.query(query, [breed_slug]);
    return result.rows[0] || null;
  }

  async searchBreeds(filters, pagination) {
    let query = `
      SELECT breed_slug, display_name, size_category, energy, adult_weight_avg_kg
      FROM breeds_published
      WHERE data_quality_grade IN ('A', 'B')
    `;

    const conditions = [];
    const params = [];

    if (filters.size?.length) {
      conditions.push(`size_category = ANY($${params.length + 1})`);
      params.push(filters.size);
    }

    if (filters.energy?.length) {
      conditions.push(`energy = ANY($${params.length + 1})`);
      params.push(filters.energy);
    }

    if (conditions.length) {
      query += ' AND ' + conditions.join(' AND ');
    }

    query += ` ORDER BY display_name LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
    params.push(pagination.limit, pagination.offset);

    const result = await this.db.query(query, params);
    return result.rows;
  }
}
```

## Performance Architecture

### Caching Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CACHE LAYERS                               │
├─────────────────────────────────────────────────────────────────────┤
│  Level 1: Application Cache (In-Memory)                            │
│  • Static reference data (size categories, enums)                  │
│  • Configuration settings                                          │
│  • TTL: Application lifetime                                       │
├─────────────────────────────────────────────────────────────────────┤
│  Level 2: Redis Cache (Distributed)                               │
│  • Individual breed details                                        │
│  • Search results                                                  │
│  • Statistics and aggregations                                     │
│  • TTL: 1-6 hours based on data type                              │
├─────────────────────────────────────────────────────────────────────┤
│  Level 3: Database Query Cache                                     │
│  • PostgreSQL query result cache                                   │
│  • Prepared statement cache                                        │
│  • Connection pooling                                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Cache Keys Strategy
```
# Pattern: {service}:{operation}:{identifier}:{version}
breed:detail:golden-retriever:v1         # Individual breed
breeds:list:size=large&energy=high:v1    # Filtered lists
breeds:search:friendly+large:v1          # Search results
breeds:stats:overview:v1                  # Statistics
breeds:recommendations:{user_hash}:v1    # User recommendations
```

## Search Architecture

### Full-Text Search Implementation
```
┌─────────────────────────────────────────────────────────────────────┐
│                     SEARCH ENGINE LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│  Document Structure:                                                │
│  {                                                                  │
│    "breed_slug": "golden-retriever",                              │
│    "display_name": "Golden Retriever",                            │
│    "aliases": ["Golden", "Goldie"],                               │
│    "searchable_content": "friendly intelligent loyal...",          │
│    "characteristics": {                                             │
│      "size": "large",                                             │
│      "energy": "high",                                            │
│      "good_with_children": "high"                                 │
│    },                                                              │
│    "boost_fields": {                                               │
│      "popularity_score": 0.8,                                     │
│      "data_quality_grade": "A"                                    │
│    }                                                               │
│  }                                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Search Features:                                                  │
│  • Auto-complete suggestions                                       │
│  • Fuzzy matching for breed names                                 │
│  • Faceted search (filters)                                       │
│  • Relevance scoring                                              │
│  • Synonym support (e.g., "Lab" → "Labrador")                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Recommendation Engine Architecture

### Machine Learning Pipeline
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ User Preferences│───▶│ Feature Vector  │───▶│ Similarity Score│
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Living space  │    │ • Normalized    │    │ • Cosine        │
│ • Experience    │    │ • Weighted      │    │ • Euclidean     │
│ • Activity level│    │ • Encoded       │    │ • Custom        │
│ • Family size   │    │ • Vectorized    │    │ • Hybrid        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
                                                      ▼
                                       ┌─────────────────┐
                                       │ Ranked Results  │
                                       ├─────────────────┤
                                       │ • Match score   │
                                       │ • Confidence    │
                                       │ • Explanation   │
                                       │ • Alternatives  │
                                       └─────────────────┘
```

### Recommendation Algorithm
```javascript
class RecommendationEngine {
  calculateMatchScore(userPreferences, breed) {
    const weights = {
      size_compatibility: 0.25,
      energy_match: 0.20,
      experience_level: 0.15,
      family_compatibility: 0.15,
      grooming_tolerance: 0.10,
      space_requirements: 0.10,
      health_considerations: 0.05
    };

    let totalScore = 0;

    // Size compatibility
    totalScore += this.calculateSizeScore(userPreferences, breed) * weights.size_compatibility;

    // Energy level matching
    totalScore += this.calculateEnergyScore(userPreferences, breed) * weights.energy_match;

    // Experience level requirements
    totalScore += this.calculateExperienceScore(userPreferences, breed) * weights.experience_level;

    return Math.min(totalScore, 1.0); // Cap at 1.0
  }
}
```

## Security Architecture

### Authentication & Authorization
```
┌─────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                              │
├─────────────────────────────────────────────────────────────────────┤
│  API Gateway Security:                                              │
│  • API Key validation                                               │
│  • Rate limiting (per key/IP)                                      │
│  • Request/response logging                                         │
│  • DDoS protection                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Application Security:                                              │
│  • Input validation & sanitization                                 │
│  • SQL injection prevention                                        │
│  • XSS protection                                                  │
│  • CORS configuration                                              │
├─────────────────────────────────────────────────────────────────────┤
│  Database Security:                                                │
│  • Connection encryption (TLS)                                     │
│  • Read-only user for API queries                                  │
│  • Network isolation                                               │
│  • Audit logging                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Monitoring & Observability

### Metrics & Alerts
```
Application Metrics:
├── Response Times
│   ├── P50: <100ms (target)
│   ├── P95: <500ms (target)
│   └── P99: <1000ms (target)
├── Error Rates
│   ├── 4xx errors: <5% (alert)
│   ├── 5xx errors: <1% (alert)
│   └── Database errors: <0.5% (alert)
├── Cache Performance
│   ├── Hit rate: >90% (target)
│   ├── Miss rate: <10% (alert)
│   └── Eviction rate: Monitor
└── Business Metrics
    ├── API usage per endpoint
    ├── Popular breed searches
    ├── Recommendation accuracy
    └── User engagement patterns
```

### Logging Strategy
```javascript
// Structured logging example
const log = {
  timestamp: '2025-09-17T19:10:00Z',
  level: 'INFO',
  service: 'breed-api',
  endpoint: '/v1/breeds/golden-retriever',
  method: 'GET',
  user_id: 'api_key_hash',
  request_id: 'req_123456',
  response_time_ms: 95,
  cache_hit: true,
  database_queries: 0,
  response_size_bytes: 2048
};
```

## Deployment Architecture

### Infrastructure Components
```
Production Environment:
├── Load Balancer (AWS ALB / Nginx)
│   ├── SSL Termination
│   ├── Health Checks
│   └── Request Distribution
├── API Servers (Auto-scaling Group)
│   ├── Docker Containers
│   ├── Health Monitoring
│   └── Blue/Green Deployment
├── Cache Layer (Redis Cluster)
│   ├── Master/Replica Setup
│   ├── Cluster Mode
│   └── Failover Support
├── Database (PostgreSQL)
│   ├── Primary (Write)
│   ├── Read Replicas (2-3)
│   └── Backup & Recovery
└── Search Engine (Elasticsearch)
    ├── Multi-node Cluster
    ├── Index Management
    └── Query Optimization
```

### Development Workflow
```
Git Repository Structure:
├── /src
│   ├── /controllers     # API endpoints
│   ├── /services       # Business logic
│   ├── /repositories   # Data access
│   ├── /models         # Data models
│   ├── /middleware     # Auth, validation, etc.
│   └── /utils          # Helper functions
├── /tests
│   ├── /unit          # Unit tests
│   ├── /integration   # Integration tests
│   └── /performance   # Load tests
├── /docker
│   ├── Dockerfile
│   └── docker-compose.yml
├── /docs
│   ├── api-spec.yml   # OpenAPI specification
│   └── README.md
└── /scripts
    ├── migration.sql  # Database migrations
    └── seed-data.sql  # Test data
```

## Data Backup & Recovery

### Backup Strategy
```
Database Backups:
├── Continuous WAL Archiving
├── Daily Full Backups (retained 30 days)
├── Weekly Full Backups (retained 12 weeks)
├── Monthly Full Backups (retained 12 months)
└── Point-in-time Recovery (7 days)

Cache Backups:
├── Redis persistence enabled
├── Daily snapshots
└── Cluster replication

Search Index Backups:
├── Daily index snapshots
├── Index recreation scripts
└── Mapping configurations
```

This architecture provides a robust, scalable foundation for your breed database API with the high-quality data we've enriched. The 96.9% quality score and comprehensive coverage ensure excellent performance across all system components.