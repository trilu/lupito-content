# Brand Website Discovery Plan - Path to 100% Coverage

## Current Status
- **Total Brands**: 278 (from ALL-BRANDS.md)
- **Mapped**: 85 brands (30.6%)
- **With Websites**: 75 brands
- **Without Websites**: 10 brands
- **Unmapped**: 193 brands (69.4%)

## Goal
Achieve 100% brand website discovery and documentation for all 278 brands in our catalog.

## Discovery Strategy

### Phase 1: Multi-Method Automated Discovery

#### 1.1 Primary Discovery Methods (In Priority Order)

1. **ScrapingBee Enhanced Search** (Available - Use First)
   - Leverage existing ScrapingBee integration
   - Search Google/Bing through ScrapingBee's rendering engine
   - Query pattern: `"{brand name}" dog food official website`
   - Advantages: Handles JavaScript, bypasses rate limits, includes screenshots

2. **Direct Domain Pattern Testing**
   ```python
   patterns = [
       f"{brand_slug}.com",
       f"{brand_slug}petfood.com", 
       f"{brand_slug}-pets.com",
       f"{brand_slug}dogfood.com",
       f"www.{brand_slug}.co.uk",  # UK brands
       f"www.{brand_slug}.de",      # German brands
       f"www.{brand_slug}.eu"       # European brands
   ]
   ```

3. **Web Search Fallbacks**
   - DuckDuckGo Instant Answers API (no rate limits)
   - Bing Web Search API (if API key available)
   - Google Custom Search Engine (if within quota)

4. **Social Media Discovery**
   - Facebook Graph API (find official pages → website links)
   - Instagram business profiles (bio links)
   - LinkedIn company pages

5. **Marketplace Vendor Extraction**
   - Amazon brand stores
   - Chewy brand pages
   - Petco/PetSmart vendor pages
   - Zooplus brand listings

#### 1.2 Validation Pipeline

Each discovered URL must pass:
1. **DNS Resolution**: Domain must resolve
2. **HTTP/HTTPS Accessibility**: Returns 200/301/302
3. **Content Validation**: 
   - Contains brand name
   - Contains pet/dog/food keywords
   - Not a generic retailer page
4. **Robots.txt Check**: Verify crawl permissions
5. **SSL Certificate**: Valid for e-commerce sites

### Phase 2: Semi-Automated Processing

#### 2.1 Batch Processing Script Structure

```python
# discover_remaining_brands_enhanced.py

class BrandWebsiteDiscovery:
    def __init__(self):
        self.strategies = [
            ScrapingBeeStrategy(),      # PRIMARY - Use this first
            DomainPatternStrategy(),    
            DuckDuckGoStrategy(),
            SocialMediaStrategy(),
            MarketplaceStrategy(),
            WikidataStrategy()
        ]
    
    def discover_website(self, brand):
        for strategy in self.strategies:
            result = strategy.find_website(brand)
            if result.confidence >= 0.8:
                return result
        return None
```

#### 2.2 Confidence Scoring

- **1.0**: Direct official website confirmed
- **0.9**: Parent company website with brand section
- **0.8**: Verified through multiple sources
- **0.7**: Single source, content validated
- **0.6**: Domain pattern match only
- **< 0.6**: Requires manual review

### Phase 3: Manual Research Categories

#### 3.1 Special Cases Requiring Human Input

1. **Private Label Brands**
   - ASDA, Aldi, Amazon, etc.
   - Solution: Link to retailer's pet food section
   
2. **Regional/Local Brands**
   - Search local business directories
   - Check regional trade associations
   
3. **Discontinued Brands**
   - Check Archive.org for last known website
   - Mark as "discontinued" status
   
4. **Acquisition/Merger Cases**
   - Find current parent company
   - Document ownership chain

#### 3.2 Manual Research Sources

- Pet Food Manufacturers Association (PFMA) directory
- European Pet Food Industry (FEDIAF) members
- Industry publications (Pet Food Industry, PetfoodIndustry.com)
- Trademark databases (USPTO, EUIPO)
- Company registries (Companies House UK, etc.)

### Phase 4: Documentation Structure

#### 4.1 Enhanced brand_sites.yaml Schema

```yaml
brand_slug:
  brand_name: "Official Brand Name"
  website_url: "https://..."
  website_status: active|parent|retailer|discontinued|none
  website_type: manufacturer|distributor|retailer|parent_company
  discovery_method: scrapingbee|pattern|search|manual|social
  confidence_score: 0.0-1.0
  parent_company: "Parent Co Name" (if applicable)
  alternate_urls:
    - "https://regional-site.co.uk"
    - "https://parent-company.com/brands/brand"
  validation:
    dns_valid: true
    ssl_valid: true
    content_valid: true
    last_checked: "2024-01-11"
  robots:
    can_crawl: true
    crawl_delay: 2.0
  notes: "Additional context"
```

## Implementation Plan

### Week 1: Automated Discovery
**Day 1-2**: Build Enhanced Discovery Script
- [ ] Implement ScrapingBee strategy (PRIMARY)
- [ ] Add domain pattern checking
- [ ] Integrate DuckDuckGo API
- [ ] Add validation pipeline

**Day 3-4**: Execute Batch Discovery
- [ ] Process remaining 193 brands
- [ ] Run through all strategies
- [ ] Generate confidence scores
- [ ] Create preliminary mapping

**Day 5**: Review & Refine
- [ ] Validate high-confidence discoveries
- [ ] Identify manual research needs
- [ ] Prepare gap analysis

### Week 2: Manual Completion
**Day 6-7**: Manual Research
- [ ] Research low-confidence brands
- [ ] Handle special cases
- [ ] Contact manufacturers if needed
- [ ] Complete documentation

## Expected Outcomes

| Category | Expected Count | Percentage |
|----------|---------------|------------|
| Direct manufacturer websites | 220-240 | 79-86% |
| Parent company sites | 20-30 | 7-11% |
| Retailer-only brands | 10-15 | 4-5% |
| Discontinued/No web presence | 5-10 | 2-4% |
| **Total Documented** | **278** | **100%** |

## Technical Requirements

### APIs/Services Needed
- ✅ **ScrapingBee** (Already integrated - PRIMARY METHOD)
- ❓ DuckDuckGo Instant Answers (Free, no key needed)
- ❓ Facebook Graph API (Need access token?)
- ❓ Google Custom Search (API key available?)

### Questions for User

1. **ScrapingBee Usage**:
   - What's our current API quota/limits?
   - Any specific configuration needed?

2. **Other APIs**:
   - Do we have Google Custom Search API key?
   - Facebook/Instagram API access?
   - Bing Search API key?

3. **Manual Research**:
   - Should we prioritize brands by SKU count?
   - Any known brand acquisitions/mergers to document?
   - Specific regional markets to focus on?

4. **Special Cases**:
   - How to handle white-label/private brands?
   - Document discontinued brands or skip?
   - Include distributor sites as fallback?

## Success Metrics

- **Primary**: 100% of 278 brands documented
- **Quality**: 85%+ with direct manufacturer websites
- **Validation**: All URLs tested and verified
- **Robots**: Crawl permissions documented
- **Timeline**: Complete within 2 weeks

## Next Steps

1. **Immediate**: Answer questions above to finalize approach
2. **Then**: Build ScrapingBee-powered discovery script
3. **Execute**: Run batch discovery on 193 unmapped brands
4. **Complete**: Manual research for remaining gaps

---

*This plan prioritizes using available tools (ScrapingBee) and automation to minimize manual effort while ensuring comprehensive coverage.*