# B4: Database Write Diagnosis Report

**Generated:** 2025-09-11T21:22:37.184132
**Records Analyzed:** 58

## Hit/Miss Metrics

| Match Type | Hits | Miss | Hit Rate |
|------------|------|------|----------|
| Product Key Exact | 0 | 58 | 0.0% |
| Brand + Name Slug | 0 | 58 | 0.0% |
| Loose Name Match (diagnostic) | 2 | 56 | 3.4% |

## Writer's Current Match Path (Pseudocode)

```python
# B1 Current Logic:
def generate_product_key(brand, product_name):
    combined = f'{brand}_{product_name}'.lower()
    combined = re.sub(r'[^a-z0-9]+', '_', combined)
    combined = re.sub(r'_+', '_', combined).strip('_')
    hash_suffix = hashlib.md5(combined.encode()).hexdigest()[:8]
    return f'{brand}_{hash_suffix}'

# Update Logic:
1. Check if product exists: SELECT * WHERE product_key = generated_key
2. If not exists: INSERT new product
3. UPDATE product SET ... WHERE product_key = generated_key
4. Expect response.data to contain updated row(s)
```

## Top 20 Failed Matches Analysis

### 1. Dog food...

**Candidate IDs:**
- Product Key: `bozita_d623e2d0`
- Brand Slug: `bozita`
- Name Slug: `dog_food`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.16)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.23)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.21)

**Best Loose Match Score:** 0.29

### 2. Purely Adult Large Salmon & Beef...

**Candidate IDs:**
- Product Key: `bozita_9c6e9910`
- Brand Slug: `bozita`
- Name Slug: `purely_adult_large_salmon_beef`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.30)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.29)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.28)

**Best Loose Match Score:** 0.44

### 3. BOZITA MEATY BITES DUCK...

**Candidate IDs:**
- Product Key: `bozita_7dace070`
- Brand Slug: `bozita`
- Name Slug: `bozita_meaty_bites_duck`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.31)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.44)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.42)

**Best Loose Match Score:** 0.50

### 4. BOZITA MEATY BITES ELK & DUCK...

**Candidate IDs:**
- Product Key: `bozita_4ac9eb88`
- Brand Slug: `bozita`
- Name Slug: `bozita_meaty_bites_elk_duck`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.29)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.43)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.44)

**Best Loose Match Score:** 0.52

### 5. BOZITA MEATY BITES LAMB...

**Candidate IDs:**
- Product Key: `bozita_fdc3890c`
- Brand Slug: `bozita`
- Name Slug: `bozita_meaty_bites_lamb`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.41)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.44)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.42)

**Best Loose Match Score:** 0.50

### 6. BOZITA MEATY BITES REINDEER & DUCK...

**Candidate IDs:**
- Product Key: `bozita_09390306`
- Brand Slug: `bozita`
- Name Slug: `bozita_meaty_bites_reindeer_duck`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.27)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.54)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.52)

**Best Loose Match Score:** 0.60

### 7. BOZITA MEATY BITES VENISON & DUCK...

**Candidate IDs:**
- Product Key: `bozita_e4b72c2b`
- Brand Slug: `bozita`
- Name Slug: `bozita_meaty_bites_venison_duck`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.35)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.41)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.39)

**Best Loose Match Score:** 0.48

### 8. ORIGINAL ADULT CLASSIC...

**Candidate IDs:**
- Product Key: `bozita_c87d9567`
- Brand Slug: `bozita`
- Name Slug: `original_adult_classic`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.13)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.17)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.23)

**Best Loose Match Score:** 0.69

### 9. ORIGINAL ADULT FLAVOUR PLUS...

**Candidate IDs:**
- Product Key: `bozita_b4dbfe49`
- Brand Slug: `bozita`
- Name Slug: `original_adult_flavour_plus`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.18)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.35)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.21)

**Best Loose Match Score:** 0.61

### 10. ORIGINAL ADULT LIGHT...

**Candidate IDs:**
- Product Key: `bozita_8c574464`
- Brand Slug: `bozita`
- Name Slug: `original_adult_light`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.10)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.18)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.24)

**Best Loose Match Score:** 0.85

### 11. ORIGINAL ADULT SENSITIVE DIGESTION...

**Candidate IDs:**
- Product Key: `bozita_bd4fe446`
- Brand Slug: `bozita`
- Name Slug: `original_adult_sensitive_digestion`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.51)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.26)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.19)

**Best Loose Match Score:** 0.59

### 12. ORIGINAL ADULT SENSITIVE SKIN & COAT...

**Candidate IDs:**
- Product Key: `bozita_89db1bf8`
- Brand Slug: `bozita`
- Name Slug: `original_adult_sensitive_skin_coat`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.49)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.25)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.24)

**Best Loose Match Score:** 0.54

### 13. ORIGINAL ADULT XL...

**Candidate IDs:**
- Product Key: `bozita_954a9336`
- Brand Slug: `bozita`
- Name Slug: `original_adult_xl`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.10)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.19)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.32)

**Best Loose Match Score:** 0.73

### 14. ORIGINAL ADULT...

**Candidate IDs:**
- Product Key: `bozita_e3f8b3af`
- Brand Slug: `bozita`
- Name Slug: `original_adult`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.11)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.20)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.26)

**Best Loose Match Score:** 0.68

### 15. ORIGINAL PUPPY & JUNIOR XL...

**Candidate IDs:**
- Product Key: `bozita_3b628fe6`
- Brand Slug: `bozita`
- Name Slug: `original_puppy_junior_xl`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.09)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.39)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.40)

**Best Loose Match Score:** 0.59

### 16. ORIGINAL PUPPY & JUNIOR...

**Candidate IDs:**
- Product Key: `bozita_40b57527`
- Brand Slug: `bozita`
- Name Slug: `original_puppy_junior`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.09)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.37)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.39)

**Best Loose Match Score:** 0.58

### 17. ORIGINAL SENIOR...

**Candidate IDs:**
- Product Key: `bozita_9be4c189`
- Brand Slug: `bozita`
- Name Slug: `original_senior`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.32)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.20)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.26)

**Best Loose Match Score:** 0.48

### 18. Bozita...

**Candidate IDs:**
- Product Key: `bozita_115a8f55`
- Brand Slug: `bozita`
- Name Slug: `bozita`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.17)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.29)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.27)

**Best Loose Match Score:** 0.44

### 19. Bozita Robur Active Performance Reindeer | Bozita ...

**Candidate IDs:**
- Product Key: `bozita_7687355d`
- Brand Slug: `bozita`
- Name Slug: `bozita_robur_active_performance_reindeer_bozita_in`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.37)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.38)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.37)

**Best Loose Match Score:** 0.45

### 20. ROBUR ADULT MAINTENANCE SMALL...

**Candidate IDs:**
- Product Key: `bozita_abf60f06`
- Brand Slug: `bozita`
- Name Slug: `robur_adult_maintenance_small`

**Brand Exists:** Yes

**Similar Products in Same Brand:**
- `bozita|robur_sensitive_single_protein_lamb__rice|unknown`: Robur Sensitive Single Protein Lamb  Ric... (similarity: 0.34)
- `bozita|bozita_grain_free_mother_&_puppy_elk|dry`: Bozita Grain Free Mother & Puppy Elk... (similarity: 0.28)
- `bozita|bozita_grain_free_mother_&_puppy_xl_elk|dry`: Bozita Grain Free Mother & Puppy XL Elk... (similarity: 0.29)

**Best Loose Match Score:** 0.36

## Supabase Response Analysis

### INSERT Response
- Data Returned: True
- Data Length: 1
- Sample: {'product_key': 'test_diagnostic_key', 'brand': None, 'brand_slug': 'test_brand', 'product_name': 'Test Diagnostic Product', 'name_slug': None, 'form': None, 'life_stage': None, 'kcal_per_100g': None, 'kcal_is_estimated': None, 'kcal_per_100g_final': None, 'protein_percent': None, 'fat_percent': None, 'ingredients_tokens': None, 'primary_protein': None, 'has_chicken': None, 'has_poultry': None, 'available_countries': None, 'price_per_kg': None, 'price_bucket': None, 'image_url': None, 'product_url': None, 'source': None, 'updated_at': None, 'quality_score': None, 'sources': None, 'ingredients_raw': None, 'ingredients_source': None, 'ingredients_parsed_at': None, 'ingredients_language': 'en', 'fiber_percent': None, 'ash_percent': None, 'moisture_percent': None, 'macros_source': None, 'kcal_source': None}

### UPDATE Response
- Data Returned: False
- Data Length: 0
- Status Code: None

### SELECT Response (Normal)
- Data Returned: True
- Data Length: 1
- Sample: {'product_key': '4paws|supplies_premium_cold_pressed_omega_salmon|unknown', 'product_name': 'Supplies Premium Cold Pressed Omega Salmon'}

## Root Cause Analysis

### 🚨 CRITICAL: Zero Exact Matches Found

**Hypothesis:**
1. **New Products**: All B1 extractions are creating new products not in database
2. **Key Generation Mismatch**: Product key algorithm differs between systems
3. **Brand Slug Issues**: Brand slugs in B1 don't match database values

### ✅ Products Exist with Similar Names
Found 2 products with >80% name similarity, suggesting products exist but key generation differs.

### UPDATE Response Issue
**Confirmed Bug**: UPDATE operations return empty data arrays when no rows match.
B1 expects response.data to contain updated rows, but gets empty array for non-matching keys.

## Recommendations

### Immediate Fixes
1. **Check Product Key Generation**: Verify B1 key generation matches existing products
2. **Handle Empty UPDATE Response**: Modify B1 to not treat empty response.data as error
3. **Add Logging**: Log generated keys vs existing keys to identify mismatches

### Verification Steps
1. **Manual Check**: Query database for existing products from these brands
2. **Key Comparison**: Compare B1 generated keys with actual database keys
3. **Brand Validation**: Confirm brand_slug values match between B1 and database

