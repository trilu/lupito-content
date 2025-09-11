Objective: Implement brand-family + series normalization across the catalog, fix the last edge cases (especially Royal Canin), and prove it with before/after checks.

Tasks:
	1.	Load the map
	•	Add data/brand_family_map.yaml
	•	Build a tiny resolver that:
a) normalizes brand to a canonical brand_slug,
b) assigns brand_family, and
c) derives series using series_rules on brand+name.
	2.	Apply at the view layer
	•	Update foods_published_preview and foods_published_prod to expose:
brand_family, series (nullable), and keep brand_slug as-is.
	•	Do not rewrite base tables; compute in views so it’s safe and reversible.
	3.	Royal Canin validation
	•	Produce before/after counts for (brand_slug, brand_family) where brand like %royal% or name like %royal%canin%.
	•	Expect: all RC SKUs consolidate to brand_family='royal_canin' and a sensible distribution of series (breed/size/care/veterinary/expert).
	4.	Hill’s & Purina validation
	•	Show before/after consolidation for Hill’s (split between Science Plan / Prescription Diet) and Purina (Pro Plan / ONE / Dog Chow / Veterinary).
	•	Verify the family totals increase and that series are populated.
	5.	JSON array gate re-check
	•	Confirm ingredients_tokens, available_countries, sources are jsonb arrays in the published views (≥99% rows). If not, cast at view level.
	6.	Reports
	•	BRAND_FAMILY_BEFORE_AFTER.md: per-family SKU counts, top 10 families.
	•	ROYAL_CANIN_CONSOLIDATION.md: detailed RC consolidation (sample SKUs, series split).
	•	FAMILY_SERIES_COVERAGE.md: percent of rows with non-null brand_family and series.
	•	Update FOODS_BRAND_QUALITY_* views to include brand_family columns (in addition to brand_slug) for rollups.

Acceptance gates (must pass):
	•	brand_family non-null on ≥95% of published rows.
	•	Royal Canin: consolidated to one family with ≥95% of its SKUs assigned a series.
	•	Hill’s & Purina: family consolidation demonstrated with series split shown.
	•	JSON array gate: ≥99% arrays typed correctly in published views.