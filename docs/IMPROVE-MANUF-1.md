Goal: Promote passing brands to production, fix near-pass brands, then scale in waves of 10 brands with monitoring. Read-additive only; atomic swaps for each brand cohort.

A) Promote passing brands now
	1.	Create foods_published_prod as a reconciled view that includes manufacturer enrichment only for brands in an allowlist (start with ['briantos','bozita']).
	2.	Keep foods_published_preview for all-enriched testing; AI/Admin can toggle between views.
	3.	Emit /reports/MANUF/PILOT/GO-LIVE-PACK.md with before→after coverage for the two brands and a rollback note.

B) Fix pack for near-pass brands (Brit, Alpha, Belcando)
	1.	Tighten PDP selectors + brand-line rules; add 5–10 extra patterns per brand (life-stage & form keywords, pack-size regex).
	2.	Re-harvest only failing SKUs; re-run enrichment; regenerate brand reports.
	3.	Pass gate when form ≥95% AND life_stage ≥95% for each brand; then add each brand to the production allowlist and re-publish foods_published_prod.

C) Scale plan
	1.	Create /reports/MANUF/BRAND_ROADMAP.md listing the next 10 brands by SKU count.
	2.	Harvest/enrich in two waves of 5 brands; keep the same acceptance gates per brand; promote to allowlist on pass.
	3.	Cost guardrails: 3s delay + jitter; cap concurrent pages; budget ScrapingBee credits; write /reports/MANUF/COST_TRACKER.md.

D) Monitoring & schedule
	1.	Nightly “light refresh” for allowlisted brands (re-pull PDPs; skip unchanged).
	2.	Weekly deeper refresh (JSON-LD & PDFs) and alerts: coverage drop >5pp, outliers>0, error rate>2%.
	3.	Produce /reports/MANUF/WEEKLY_SUMMARY.md with brand deltas, failures, and next actions.

E) Deliver back:
	•	Confirmation that foods_published_prod is live with Briantos & Bozita.
	•	Fix-pack results for Brit, Alpha, Belcando (pass/fail).
	•	The 10-brand roadmap and a simple Gantt in the report.
	•	Links to the weekly summaries & cost tracker.