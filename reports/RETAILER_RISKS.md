# RETAILER DATA RISKS & WARNINGS
Generated: 2025-09-12T08:28:17.254181

## Data Quality Risks

### 1. Product Classification Errors

**Treats Misclassified as Complete Foods**
- Chewy: 33 products marked as treats
- Risk: Bowl boosters, toppers may be included in complete food metrics
- Mitigation: Filter by form != 'treat' for food coverage calculations

### 2. Brand Normalization Issues

**Inconsistent Brand Names**
- Example: "Hill's Science Diet" vs "Hills" vs "Hill's"
- Example: "Stella & Chewy's" vs "Stella and Chewys"
- Impact: Same brand counted multiple times
- Mitigation: Requires brand_phrase_map.csv updates

### 3. Price Data Reliability

**Chewy Price Risks**
- Weight extraction from product names may be inaccurate
- Multi-pack products may show unit price vs pack price
- Example: "4-pack of 3.5oz" might extract wrong weight

**AADF Price Risks**
- Price per day based on feeding assumptions
- Large vs small dog feeding amounts vary significantly
- Currency conversion uses static rate

## False Positive Patterns

### Products Incorrectly Included
- Chewy: 'Stella & Chewy's Chewy's Chicken Meal Mixers Freez...' marked as dry, likely treat/topper
- Chewy: 'Primal Cupboard Cuts Chicken Grain-Free Freeze-Dri...' marked as raw, likely treat/topper
- Chewy: 'Wellness Bowl Boosters Simply Shreds Variety Pack ...' marked as wet, likely treat/topper
- Chewy: 'Bundle: Wellness CORE Bowl Boosters Bare Turkey + ...' marked as raw, likely treat/topper
- Chewy: 'Portland Pet Food Company Homestyle Variety Pack W...' marked as wet, likely treat/topper
- Chewy: 'Stella & Chewy's Stella's Super Beef Meal Mixers F...' marked as dry, likely treat/topper
- Chewy: 'Jinx Freeze-Dried Salmon Dry Dog Food Topper, 3-oz...' marked as raw, likely treat/topper
- Chewy: 'The Honest Kitchen Bone Broth POUR OVERS Beef Stew...' marked as dry, likely treat/topper
- Chewy: 'Solid Gold Homestyle Meal Skin & Coat Health Chick...' marked as dry, likely treat/topper
- Chewy: 'Solid Gold Beef Bone Broth with Turmeric Dog Food ...' marked as dry, likely treat/topper
... and 142 more potential misclassifications

## Duplicate Risk Assessment

### Within-Dataset Duplicates
- Chewy: 111 duplicate keys
- AADF: 0 duplicate keys

### Cross-Dataset Duplicates
- Same product in both datasets: Estimated 10-20% overlap for major brands
- Different sizes of same product: May create multiple entries
- Regional variations: US vs UK formulations may differ

## Merge Safety Checklist

✅ **SAFE**:
- All products have unique product_keys (hash-based)
- All products have sources array with retailer attribution
- Form and life_stage use controlled vocabulary
- JSON arrays properly formatted

⚠️ **NEEDS ATTENTION**:
- Brand normalization requires review
- Price data should be marked as "estimated"
- Treats/toppers should be filtered for food metrics
- Ingredients from AADF should be marked as "retailer-sourced"

❌ **DO NOT**:
- Trust retailer ingredients as authoritative
- Assume prices are current (dataset date unknown)
- Merge without brand deduplication
- Override manufacturer data with retailer data

## Recommended Safeguards

1. **Staging First**: Keep in retailer_staging tables for review
2. **Brand Review**: Manual check of top 50 brands before merge
3. **Confidence Scoring**: Use staging_confidence field for filtering
4. **Source Attribution**: Always preserve retailer source in sources array
5. **Incremental Merge**: Start with high-confidence matches only
