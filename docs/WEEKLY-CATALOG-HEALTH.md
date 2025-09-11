# WEEKLY CATALOG HEALTH REPORT
Generated: 2025-09-11 11:12:21

## Executive Summary

- **Production Status**: OK (80 SKUs)
- **Failing Gates**: 3
- **Brand Alerts**: 3

## Enrichment Needs

- Products missing form: 1622
- Products missing life_stage: 1640
- Invalid kcal values: 0

## Gate Compliance

| Field | Current | Target | Status |
|-------|---------|--------|--------|
| form | 68.5% | 90% | ❌ FAIL |
| life_stage | 68.2% | 95% | ❌ FAIL |
| ingredients | 100.0% | 85% | ✅ PASS |
| kcal_valid | 76.0% | 90% | ❌ FAIL |

## Brand Alerts

- ⚠️  royal_canin: Low life stage coverage (63.2%)
- ⚠️  purina: Low form coverage (0.0%)
- ⚠️  purina_pro_plan: Low life stage coverage (56.8%)

## Action Required

The following gates are failing:
- form (68.5% < 90%)
- life_stage (68.2% < 95%)
- kcal_valid (76.0% < 90%)


## Automated Actions Taken

1. ✅ Enrichment needs assessed
2. ✅ Materialized views refresh attempted
3. ✅ Brand health checked
4. ✅ Production health verified
5. ✅ Gate compliance measured

## Recommendations

- Some quality gates are failing. Run enrichment pipeline.
- Some brands have quality issues. Review and fix.

---
*This report was generated automatically by the weekly maintenance script.*