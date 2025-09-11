# PROMOTION CANDIDATES REPORT
Generated: 2025-09-11 11:09:56

## Summary

- Total brands analyzed: 50
- Brands meeting criteria: 1
- Total SKUs to add: 14

## Promotion Criteria

- Minimum SKUs: 5
- Minimum completion: 75%
- Form coverage: ≥70%
- Life stage coverage: ≥70%
- Ingredients coverage: ≥85%
- Valid kcal: ≥70%

## Top Promotion Candidates

| Brand | SKUs | Completion | Adult | Puppy | Senior |
|-------|------|------------|-------|-------|--------|
| arden_grange | 14 | 100.0% | 11 | 2 | 1 |


## Production Impact

What Prod will gain if all candidates promoted:
- New SKUs: 14
- Adult products: 11
- Puppy products: 2
- Senior products: 1

## SQL Updates

To promote these brands, execute:

```sql

-- Promote arden_grange to ACTIVE
UPDATE brand_allowlist 
SET status = 'ACTIVE', 
    updated_at = NOW(),
    notes = 'Promoted via PROMPT D - 14 SKUs, 100.0% complete'
WHERE brand_slug = 'arden_grange';

```

## Next Steps

1. Review candidates and approve promotions
2. Execute SQL updates for approved brands
3. Run Prompt E to verify production
