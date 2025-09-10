# FOODS BRAND SCOREBOARD

Generated: 2025-09-10 22:23:36  
Source: Brand Quality Metrics Views

## 📊 TOP 20 BRANDS BY SKU COUNT

| Rank | Brand | SKUs | Completion % | Form | Life Stage | Ingredients | Price | Kcal | Status |
|------|-------|------|--------------|------|------------|-------------|-------|------|--------|
| 1 | **Brit** | 73 | **90.5%** | 91.8% | **95.9%** | **100.0%** | **80.2%** | 84.6% | 🔶 NEAR |
| 2 | **Alpha** | 53 | **90.5%** | 94.3% | **98.1%** | **100.0%** | **81.4%** | 78.7% | 🔶 NEAR |
| 3 | **Briantos** | 46 | **95.7%** | **100.0%** | **97.8%** | **100.0%** | **88.9%** | **91.8%** | ✅ PASS |
| 4 | **Bozita** | 34 | **92.9%** | **97.1%** | **97.1%** | **100.0%** | **84.2%** | **85.9%** | ✅ PASS |
| 5 | **Belcando** | 34 | **89.8%** | **97.1%** | 94.1% | **100.0%** | **82.2%** | 75.5% | 🔶 NEAR |
| 6 | **Acana** | 32 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 7 | **Advance** | 28 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 8 | **Almo Nature** | 26 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 9 | **Animonda** | 25 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 10 | **Applaws** | 24 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 11 | **Arden Grange** | 23 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 12 | **Bosch** | 22 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 13 | **Burns** | 21 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 14 | **Carnilove** | 20 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 15 | **Concept For Life** | 19 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 16 | **Eukanuba** | 18 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 17 | **Farmina** | 17 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 18 | **Genesis** | 16 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 19 | **Happy Dog** | 15 | **0.0%** | - | - | - | - | - | ❌ TODO |
| 20 | **Hills** | 14 | **0.0%** | - | - | - | - | - | ❌ TODO |


## 📈 STATUS DISTRIBUTION

| Status | Count | Percentage | Brands |
|--------|-------|------------|--------|
| ✅ **PASS** | 2 | 10.0% | Meets all quality gates |
| 🔶 **NEAR** | 3 | 15.0% | Within 5pp of passing |
| ❌ **TODO** | 15 | 75.0% | Needs enrichment |

## 🎯 QUALITY GATE THRESHOLDS

| Metric | PASS Threshold | NEAR Threshold |
|--------|----------------|----------------|
| Form Coverage | ≥ 95% | ≥ 90% |
| Life Stage Coverage | ≥ 95% | ≥ 90% |
| Ingredients Coverage | ≥ 85% | ≥ 80% |
| Price Bucket Coverage | ≥ 70% | ≥ 65% |
| Kcal Outliers | = 0 | ≤ 2 |

## 🚀 PRODUCTION STATUS

### Currently in Production
- **Briantos**: 46 SKUs (95.7% complete)
- **Bozita**: 34 SKUs (92.9% complete)


### Ready for Production (PASS Status)
- No additional brands ready yet


### Close to Ready (NEAR Status)
- **Brit**: 73 SKUs (Form: 3.2pp gap)
- **Alpha**: 53 SKUs (Form: 0.7pp gap)
- **Belcando**: 34 SKUs (Life Stage: 0.9pp gap)


## 📊 AGGREGATE METRICS

### Overall Coverage (Top 20 Brands)

- **Average Completion**: 91.9%
- **Average Form Coverage**: 96.1%
- **Average Life Stage Coverage**: 96.6%
- **Average Ingredients Coverage**: 100.0%
- **Average Price Coverage**: 83.4%


### Total SKUs by Status
- **PASS Brands**: 80 SKUs
- **NEAR Brands**: 160 SKUs
- **TODO Brands**: 320 SKUs
- **Total**: 560 SKUs

## 🔄 REFRESH INFORMATION

- **Last Refreshed**: 2025-09-10 22:23:36
- **Refresh Schedule**: Nightly at 02:00 UTC
- **Manual Refresh**: `SELECT refresh_all_brand_quality();`

## 📋 NEXT ACTIONS

1. **Fix NEAR Brands**: Focus on Brit, Alpha, and Belcando to reach PASS status
2. **Deploy PASS Brands**: Add qualifying brands to production allowlist
3. **Start TODO Brands**: Begin harvesting top SKU count brands without data
4. **Monitor Outliers**: Investigate any brands with kcal outliers

---

*This scoreboard is automatically generated from the brand quality metrics views.*
*For real-time data, query: `SELECT * FROM foods_brand_quality_preview ORDER BY sku_count DESC;`*
