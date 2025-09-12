Discover & Decide (no DB writes)

Goal: Build/refresh a single brand normalization map from our authoritative list and show the impact before touching data.
Do:
	1.	Read docs/ALL-BRANDS.md and emit a clean canonical set (brand_slug, brand_display).
	2.	Scan foods_canonical, AADF stage, and Chewy stage for brand variants; propose brand_alias → brand_slug pairs (no substring guesses; use whole-word matching and known patterns).
	3.	Produce a report with: (a) unmapped brands, (b) conflicting variants, (c) suggested families/series (purely informational), (d) simulated before/after brand counts if we applied the mapping.
	4.	Output artifacts only (no DB writes):

	•	data/brand_alias_map.yaml (authoritative)
	•	reports/BRANDS-NORMALIZATION-PLAN.md (impact, edge cases like “Royal Canin Breed”, “Hill’s …”, “Pro Plan”).
Constraints: No network secrets, no writes; just analysis + proposed mapping + metrics.