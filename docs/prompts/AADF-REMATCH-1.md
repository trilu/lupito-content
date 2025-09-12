AADF safe-merge (high confidence only)”

Goal: Enrich only where we’re sure. Keep it surgical and auditable.

Instruction (paste to content repo):
Upsert only matches ≥0.8 from AADF into foods_canonical, updating these fields when missing:
form, life_stage, ingredients_raw, ingredients_tokens, ingredients_language, ingredients_source='aadf'.
Requirements:
	•	Idempotent upsert with dry-run preview (10 rows) then full run
	•	Write a before/after brand scoreboard (completion %) to reports/AADF_MERGE_BEFORE_AFTER.md
	•	Refresh preview/prod brand MVs
	•	Print a one-line delta: “brands improved: X; SKUs enriched: Y; new SKUs: Z”
	•	If new brands are introduced, insert them into brand_allowlist as PENDING (don’t flip prod).