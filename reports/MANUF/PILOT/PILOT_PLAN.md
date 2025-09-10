# TOP 5 BRANDS PRODUCTION PILOT PLAN
Generated: 2025-09-10 20:34:01

## Selected Brands (by SKU count)

| Rank | Brand | SKUs | Website | Form Gap | Life Stage Gap | Ingredients Gap | Price Gap |
|------|-------|------|---------|----------|----------------|-----------------|-----------|
| 1 | Brit | 73 | ✅ | 11 | 13 | 0 | 36 |
| 2 | Alpha | 53 | ✅ | 48 | 47 | 0 | 53 |
| 3 | Briantos | 46 | ✅ | 23 | 12 | 0 | 23 |
| 4 | Bozita | 34 | ✅ | 20 | 16 | 0 | 20 |
| 5 | Belcando | 34 | ✅ | 22 | 12 | 0 | 23 |


## Pilot Impact Potential

- **Total SKUs in Pilot**: 240 (24.1% of catalog)
- **Form Coverage Gap**: 124 products
- **Life Stage Gap**: 100 products
- **Expected Form Improvement**: 51.7pp
- **Expected Life Stage Improvement**: 41.7pp

## Quality Gates (Per Brand)

| Metric | Target | Current (Avg) | Gap |
|--------|--------|---------------|-----|
| Form | ≥95% | 48.3% | 46.7pp |
| Life Stage | ≥95% | 58.3% | 36.7pp |
| Ingredients | ≥85% | 100.0% | 0.0pp |
| Price Bucket | ≥70% | 35.4% | 34.6pp |

## Execution Steps

1. **Profile Enhancement** ✅
   - Created enhanced profiles with multi-method discovery
   - Added headless browser support
   - Configured ScrapingBee integration points

2. **Harvest Phase** (Next)
   - Run sequential harvests for each brand
   - Expected duration: 2-3 hours per brand
   - Cache all responses locally

3. **Enrichment Phase**
   - Parse harvested data
   - Match to catalog products
   - Calculate enrichment metrics

4. **Validation Phase**
   - Check brand-level quality gates
   - Generate conflict reports
   - Prepare preview table

5. **Delivery**
   - Brand quality reports
   - 50-row samples per brand
   - foods_published_preview table

## Risk Mitigation

- **Website Issues**: 3 of 5 brands have verified websites
- **Rate Limiting**: 3s delay + 2s jitter configured
- **Fallback**: ScrapingBee API ready if needed
- **Manual Override**: Admin interface for corrections

## Next Command

```bash
python3 pilot_harvest_top5.py --brand <brand_slug> --limit 50
```
