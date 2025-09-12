 “AADF re-match (report-only)”

Goal: Re-run matching now that brands are normalized. Don’t write to DB yet—just tell us what can be safely merged.

Instruction (paste to content repo):
Re-run AADF→catalog matching using brand_slug (respecting brand_alias) and current product_key rules. Produce a report only (no DB writes) with:
	•	Totals: AADF rows, candidates ≥0.7, ≥0.8, ≥0.9
	•	Top 15 brands by “matchable SKUs”
	•	For 20 random matches, show AADF name vs. catalog brand + product_name and the computed product_key
	•	A count of would-be new products (no key match)
	•	A safety section confirming arrays/JSON types are valid
Save to reports/AADF_REMATCH_SUMMARY.md.

If the report shows a healthy set of high-confidence matches (≥0.8), proceed.