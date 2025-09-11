# Wave 1 Snapshot Harvest Summary

**Generated:** 2025-09-11 18:38:51
**Duration:** 5.1 minutes
**Bucket:** gs://lupito-content-raw-eu/
**Brands Processed:** 10/10

## Overall Statistics

- **Total Pages Fetched:** 64
- **Total Pages Uploaded:** 63
- **Total PDFs Found:** 1
- **Total Size:** 35.8 MB
- **Success Rate:** 10/10

## Per-Brand Results

| Brand | Status | Pages | PDFs | Size (MB) | Failures | GCS Path |
|-------|--------|-------|------|-----------|----------|----------|
| alpha | ✅ | 4 | 0 | 0.0 | None | [View](gs://lupito-content-raw-eu/manufacturers/alpha/2025-09-11/) |
| brit | ✅ | 4 | 0 | 0.2 | None | [View](gs://lupito-content-raw-eu/manufacturers/brit/2025-09-11/) |
| briantos | ✅ | 2 | 0 | 0.0 | http_unknown:2 | [View](gs://lupito-content-raw-eu/manufacturers/briantos/2025-09-11/) |
| canagan | ✅ | 1 | 0 | 0.2 | other:1, http_unknown:2 | [View](gs://lupito-content-raw-eu/manufacturers/canagan/2025-09-11/) |
| cotswold | ✅ | 0 | 0 | 0.0 | http_unknown:4 | [View](gs://lupito-content-raw-eu/manufacturers/cotswold/2025-09-11/) |
| burns | ✅ | 22 | 1 | 21.9 | http_unknown:2 | [View](gs://lupito-content-raw-eu/manufacturers/burns/2025-09-11/) |
| barking | ✅ | 24 | 0 | 12.2 | None | [View](gs://lupito-content-raw-eu/manufacturers/barking/2025-09-11/) |
| bozita | ✅ | 1 | 0 | 0.0 | http_unknown:3 | [View](gs://lupito-content-raw-eu/manufacturers/bozita/2025-09-11/) |
| forthglade | ✅ | 3 | 0 | 1.0 | http_unknown:1 | [View](gs://lupito-content-raw-eu/manufacturers/forthglade/2025-09-11/) |
| belcando | ✅ | 2 | 0 | 0.2 | http_unknown:2 | [View](gs://lupito-content-raw-eu/manufacturers/belcando/2025-09-11/) |

## HTTP Failure Breakdown

| Failure Type | Count |
|--------------|-------|
| http_unknown | 16 |
| other | 1 |

## GCS Storage Structure

```
gs://lupito-content-raw-eu/
└── manufacturers/
    ├── alpha/
    │   └── 2025-09-11/
    │       ├── *.html (4 files)
    ├── brit/
    │   └── 2025-09-11/
    │       ├── *.html (4 files)
    ├── briantos/
    │   └── 2025-09-11/
    │       ├── *.html (2 files)
    ├── canagan/
    │   └── 2025-09-11/
    │       ├── *.html (1 files)
    ├── cotswold/
    │   └── 2025-09-11/
    │       ├── *.html (0 files)
    ├── burns/
    │   └── 2025-09-11/
    │       ├── *.html (22 files)
    │       └── *.pdf (1 files)
    ├── barking/
    │   └── 2025-09-11/
    │       ├── *.html (24 files)
    ├── bozita/
    │   └── 2025-09-11/
    │       ├── *.html (1 files)
    ├── forthglade/
    │   └── 2025-09-11/
    │       ├── *.html (3 files)
    ├── belcando/
    │   └── 2025-09-11/
    │       ├── *.html (2 files)
```

## Sample URLs Captured

### alpha
- https://www.alphapetfoods.com/sitemap.xml
- https://www.alphapetfoods.com/dog-food/
- https://www.alphapetfoods.com/products/dog/
- https://www.alphapetfoods.com/shop/dog/

### brit
- https://www.brit-petfood.com/dog/
- https://www.brit-petfood.com/sitemap.xml
- https://www.brit-petfood.com/products/
- https://www.brit-petfood.com/dog-food/

### briantos
- https://www.briantos.de/sitemap.xml
- https://www.briantos.de/produkte/

## Notes

- Rate limiting: 2-3 seconds between requests
- robots.txt: Respected for all brands
- Product limit: 20 products per brand
- Storage: All content stored in GCS, no local files
- Parsing: Not performed (snapshot only)

## Next Steps

1. Verify GCS uploads via Console or gsutil
2. Review captured content quality
3. Run parsing pipeline to extract structured data
4. Update foods_canonical with parsed data
5. Run quality gates validation
