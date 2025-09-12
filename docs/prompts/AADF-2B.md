Apply (small, surgical, safe)

Goal: Apply the approved brand_alias_map.yaml to the DB safely and refresh views.
Do:
	1.	Create/refresh a brand_alias table and upsert all alias→slug pairs.
	2.	Update foods_canonical.brand and brand_slug using the mapping only when:
	•	current brand_slug ≠ mapped slug, or
	•	current brand is a known alias variant.
	3.	Do not change product names; do not infer brand from product names unless brand is null and match is whole-word.
	4.	Rebuild/refresh foods_published_preview and foods_published_prod so AI/Admin see normalized brands.
	5.	Produce a before/after audit: per-brand SKU counts, duplicates resolved, and a rollback SQL.
Constraints: Idempotent, transactional where possible; print a short success summary + paths to the audit & rollback.