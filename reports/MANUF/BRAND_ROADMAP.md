# BRAND ROADMAP: MANUFACTURER ENRICHMENT SCALE PLAN

Generated: 2025-09-10 21:10:00  
Target: 55+ Brands by Q2 2025

## 📊 CURRENT STATUS

### ✅ In Production (2 brands, 80 SKUs)
1. **Briantos** - 46 SKUs (100% form, 97.8% life_stage)
2. **Bozita** - 34 SKUs (97.1% form, 97.1% life_stage)

### 🔧 Ready After Fixes (3 brands, 160 SKUs)
3. **Brit** - 73 SKUs (fixing: 91.8% → 95% form)
4. **Alpha** - 53 SKUs (fixing: 94.3% → 95% form)
5. **Belcando** - 34 SKUs (fixing: 94.1% → 95% life_stage)

## 🚀 NEXT 10 BRANDS BY SKU COUNT

### Wave 1: Top Priority (Week 3)
| # | Brand | SKUs | Website | Priority | Complexity |
|---|-------|------|---------|----------|------------|
| 6 | **Acana** | 32 | acana.com | HIGH | Medium |
| 7 | **Advance** | 28 | advance.com | HIGH | Low |
| 8 | **Almo Nature** | 26 | almonature.com | HIGH | Medium |
| 9 | **Animonda** | 25 | animonda.com | MEDIUM | Low |
| 10 | **Applaws** | 24 | applaws.com | MEDIUM | Low |

**Wave 1 Total**: 135 SKUs

### Wave 2: Secondary Priority (Week 4)
| # | Brand | SKUs | Website | Priority | Complexity |
|---|-------|------|---------|----------|------------|
| 11 | **Arden Grange** | 23 | ardengrange.com | MEDIUM | Low |
| 12 | **Bosch** | 22 | bosch-tiernahrung.de | MEDIUM | Medium |
| 13 | **Burns** | 21 | burns-pet.co.uk | LOW | Low |
| 14 | **Carnilove** | 20 | carnilove.com | LOW | Low |
| 15 | **Concept for Life** | 19 | zooplus.com/concept | LOW | High* |

**Wave 2 Total**: 105 SKUs

*Note: Concept for Life is Zooplus private label - may require special handling

## 📈 SCALING TIMELINE (GANTT CHART)

```
Week 1  |██████| Production: Briantos, Bozita
Week 2  |██████| Fix & Deploy: Brit, Alpha, Belcando
Week 3  |██████| Wave 1: Acana, Advance, Almo, Animonda, Applaws
Week 4  |██████| Wave 2: Arden, Bosch, Burns, Carnilove, Concept
Week 5  |██████| Wave 3: Next 5 brands (18-17 SKUs each)
Week 6  |██████| Wave 4: Next 5 brands (16-15 SKUs each)
Week 7  |██████| Wave 5: Next 5 brands (14-13 SKUs each)
Week 8  |██████| Wave 6: Remaining brands (<12 SKUs each)
```

## 🎯 ACCEPTANCE CRITERIA PER BRAND

### Quality Gates (Required for Production)
- **Form Coverage**: ≥ 95%
- **Life Stage Coverage**: ≥ 95%
- **Ingredients Coverage**: ≥ 85%
- **Price/Bucket Coverage**: ≥ 70%
- **Zero Outliers**: Kcal 200-600, Price €1-200

### Technical Requirements
- Rate limiting: 3s delay + 2s jitter
- ScrapingBee credits: ~50 per brand
- Error rate: < 2%
- Harvest time: < 30 min per brand

## 💰 COST PROJECTIONS

### Per Brand Costs
- **Discovery**: 10-20 pages (sitemap, categories)
- **Harvest**: 1 page per SKU
- **Retry Budget**: 10% of SKUs
- **Total**: ~50-100 ScrapingBee credits

### Wave Costs
- **Wave 1** (135 SKUs): ~750 credits
- **Wave 2** (105 SKUs): ~600 credits
- **Monthly Refresh**: ~2000 credits
- **Buffer**: 20% for retries

### Monthly Budget
- Initial harvest: 3000 credits
- Weekly refresh: 2000 credits
- **Total**: 5000 credits/month

## 🔄 REFRESH STRATEGY

### Nightly Light Refresh (Allowlisted Brands)
- Check 10% sample for changes
- Full refresh if >5% changed
- Skip unchanged products

### Weekly Deep Refresh
- All allowlisted brands
- JSON-LD updates
- PDF re-extraction
- Price updates

### Monthly Full Harvest
- All products
- New product discovery
- Discontinued product removal

## 📊 SUCCESS METRICS

### Coverage Targets (by Week 8)
- **Brands in Production**: 30+
- **Total SKUs Enriched**: 1000+
- **Overall Form Coverage**: 95%+
- **Overall Life Stage**: 95%+
- **Overall Ingredients**: 90%+

### Business Impact
- **User Experience**: Rich filtering and search
- **Data Quality**: Consistent allergen detection
- **Price Intelligence**: Market positioning insights
- **Nutritional Analysis**: Health recommendations

## ⚠️ RISK MITIGATION

### Technical Risks
- **Rate Limiting**: Implement exponential backoff
- **Site Changes**: Monitor selector performance
- **Credit Overrun**: Daily budget caps

### Data Quality Risks
- **Coverage Drops**: Alert on -5pp change
- **Outlier Detection**: Flag suspicious values
- **Missing Fields**: Fallback inference rules

### Business Risks
- **Brand Prioritization**: Follow SKU count ranking
- **Resource Allocation**: Dedicated harvest windows
- **Stakeholder Communication**: Weekly progress reports

## 📋 NEXT ACTIONS

### Immediate (This Week)
1. ✅ Deploy Briantos & Bozita to production
2. ✅ Apply fixes to Brit, Alpha, Belcando
3. Prepare Wave 1 brand profiles
4. Set up monitoring dashboard

### Next Week
1. Validate fixed brands' quality gates
2. Add fixed brands to production
3. Begin Wave 1 harvest
4. Generate weekly summary

### Ongoing
1. Daily monitoring of production brands
2. Weekly quality reports
3. Monthly cost tracking
4. Quarterly roadmap review

## 📞 ESCALATION PATH

### Coverage Issues
→ Engineering: Enhance selectors
→ Data: Manual verification

### Performance Issues
→ DevOps: Scale infrastructure
→ Product: Adjust requirements

### Business Decisions
→ Product: Brand prioritization
→ Finance: Budget approval

---

**Status**: APPROVED  
**Owner**: Data Engineering  
**Review**: Weekly on Fridays  
**Next Review**: Week 2 completion