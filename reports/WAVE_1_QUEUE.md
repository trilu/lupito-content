# Wave 1 Brand Queue for Manufacturer Enrichment

**Generated:** 2025-09-11 18:10:22
**Total Candidates:** 43
**Selected for Wave 1:** 10

## Selection Criteria

- Must have manufacturer website
- Minimum 10 SKUs
- Completion < 90%
- Prioritized by Impact Score = SKU Count × (100 - Completion%) × Website Factor

## Wave 1 Queue

| Rank | Brand | SKUs | Completion | Website | Country | Platform | Strategy |
|------|-------|------|------------|---------|---------|----------|----------|
| 1 | alpha | 53 | 24.1% | [Link](https://www.alphapetfoods.com) | US | Custom | Focus on ingredients extraction; Identify product forms |
| 2 | brit | 73 | 53.4% | [Link](https://www.brit-petfood.com) | US | Custom | Focus on ingredients extraction; Look for nutrition tables/PDFs |
| 3 | briantos | 46 | 44.8% | [Link](https://www.briantos.de) | DE | Custom (EU) | German site - may need translation; Focus on ingredients extraction |
| 4 | canagan | 37 | 38.9% | [Link](https://canagan.com/uk/) | US | Custom | Focus on ingredients extraction; Identify product forms |
| 5 | cotswold | 28 | 20.0% | [Link](https://www.cotswoldnutrition.com/) | US | Custom | Focus on ingredients extraction; Look for nutrition tables/PDFs |
| 6 | burns | 40 | 46.0% | [Link](https://burns.de/) | DE | Custom (EU) | German site - may need translation; Focus on ingredients extraction |
| 7 | barking | 33 | 35.8% | [Link](https://www.barkingheads.co.uk) | UK | Custom | Focus on ingredients extraction; Identify product forms |
| 8 | bozita | 34 | 38.8% | [Link](https://www.bozita.com) | US | Custom | Focus on ingredients extraction; Identify product forms |
| 9 | forthglade | 31 | 34.2% | [Link](https://forthglade.com/) | US | Custom | Focus on ingredients extraction; Identify product forms |
| 10 | belcando | 34 | 40.0% | [Link](https://www.belcando.de) | DE | Custom (EU) | German site - may need translation; Focus on ingredients extraction |

## Detailed Metrics

| Brand | Form % | Life Stage % | Ingredients % | Kcal % | Price % | Impact Score |
|-------|--------|--------------|---------------|---------|---------|-------------|
| alpha | 9% | 11% | 0% | 100% | 0% | 60 |
| brit | 85% | 82% | 1% | 48% | 51% | 51 |
| briantos | 50% | 74% | 0% | 50% | 50% | 38 |
| canagan | 73% | 16% | 5% | 97% | 3% | 34 |
| cotswold | 68% | 0% | 0% | 32% | 0% | 34 |
| burns | 75% | 55% | 0% | 65% | 35% | 32 |
| barking | 70% | 12% | 0% | 97% | 0% | 32 |
| bozita | 41% | 53% | 0% | 59% | 41% | 31 |
| forthglade | 65% | 6% | 0% | 100% | 0% | 31 |
| belcando | 35% | 65% | 3% | 65% | 32% | 31 |

## Language Requirements

**German Sites (3):** briantos, burns, belcando
**English Sites (7):** alpha, brit, canagan, cotswold, barking, bozita, forthglade

## PDF Detection

Based on platform analysis, these brands likely have PDF datasheets:

- **alpha**: Check for product datasheets, nutrition PDFs
- **brit**: Check for product datasheets, nutrition PDFs
- **briantos**: Check for product datasheets, nutrition PDFs
- **canagan**: Check for product datasheets, nutrition PDFs
- **cotswold**: Check for product datasheets, nutrition PDFs
- **burns**: Check for product datasheets, nutrition PDFs
- **barking**: Check for product datasheets, nutrition PDFs
- **bozita**: Check for product datasheets, nutrition PDFs
- **forthglade**: Check for product datasheets, nutrition PDFs
- **belcando**: Check for product datasheets, nutrition PDFs

## Execution Strategy

1. **Batch 1 (English sites):** Start with English-language sites for quick wins
2. **Batch 2 (German sites):** Use translation API or ScrapingBee for German content
3. **Batch 3 (Other EU):** Italian/Spanish sites with appropriate translation
4. **PDF Priority:** Focus on brands with low nutrition coverage but likely PDFs

## Next Steps

1. Create harvest profiles for each brand (profiles/brands/{brand_slug}.yaml)
2. Test robots.txt compliance for each site
3. Identify specific product listing pages/sitemaps
4. Configure ScrapingBee for sites that block standard crawlers
5. Set up translation pipeline for non-English sites
