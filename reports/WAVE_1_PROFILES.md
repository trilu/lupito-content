# Wave 1 Brand Profiles Summary

**Generated:** 2025-09-11 18:13:49
**Created:** 10 profiles
**Updated:** 0 profiles

## Profile Coverage

| Brand | Language | Platform | Selectors | JSON-LD | PDF Support | Anti-Bot Notes |
|-------|----------|----------|-----------|---------|-------------|----------------|
| alpha | en | Custom | 9 types | ✓ | ✓ | None |
| brit | en | Custom | 9 types | ✓ | ✓ | None |
| briantos | de | Custom | 9 types | ✓ | ✓ | German site - may need translation or ScrapingBee |
| canagan | en | Custom | 9 types | ✓ | ✓ | None |
| cotswold | en | WooCommerce | 9 types | ✓ | ✓ | None |
| burns | en | Custom | 9 types | ✓ | ✓ | None |
| barking | en | Custom | 9 types | ✓ | ✓ | None |
| bozita | en | Custom | 9 types | ✓ | ✓ | None |
| forthglade | en | Shopify | 9 types | ✓ | ✓ | None |
| belcando | de | Custom | 9 types | ✓ | ✓ | German site - may need translation or ScrapingBee |

## Selector Details

All profiles include comprehensive selectors for:

- **Product Discovery**: Sitemap + category page crawling
- **Product Name**: Multiple CSS/XPath selectors + JSON-LD
- **Pack Sizes**: Variant selectors, regex patterns
- **Ingredients**: Multiple selectors for different formats
- **Nutrition**: Analytical constituents table parsing
- **Energy**: kcal/100g extraction patterns
- **PDFs**: Specification, label, datasheet links
- **Metadata**: Price, form, life stage

## Language-Specific Configurations

### German Sites (3 brands)
- **briantos, burns, belcando**
- Added German-specific selectors (Zutaten, Analytische)
- Configured for ScrapingBee/translation if needed

### English Sites (7 brands)
- **alpha, brit, canagan, cotswold, barking, bozita, forthglade**
- Standard English selectors

## Platform-Specific Optimizations

- **Shopify** (forthglade): Enhanced with Shopify-specific selectors
- **WooCommerce** (cotswold): Added WooCommerce class patterns
- **Custom** (8 brands): Comprehensive selector coverage

## Rate Limiting

All profiles configured with:
- Base delay: 2 seconds
- Jitter: 1 second
- Max concurrent: 1
- Robots.txt: Respected

## Next Steps

1. Test each profile with sample product URLs
2. Verify robots.txt compliance for each site
3. Configure ScrapingBee for German sites if needed
4. Run test harvest on 5 products per brand
5. Adjust selectors based on test results
