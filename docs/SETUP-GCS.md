Goal: Use Google Cloud Storage for snapshots (HTML/PDF/images), not local disk. Non-interactive auth via a service account key stored in Secret Manager.

Given:
	•	Project ID: careful-drummer-468512-p0
	•	Bucket: lupito-content-raw-eu (region: europe-west1)
	•	We already have gcloud CLI available.

Do this end-to-end (no manual steps from me):
	1.	Create + secure a dedicated service account

	•	Name: content-snapshots
	•	Email should be: content-snapshots@careful-drummer-468512-p0.iam.gserviceaccount.com
	•	Grant least privilege on this bucket only:
	•	roles/storage.objectAdmin on gs://lupito-content-raw-eu
	•	Also allow listing bucket objects (included in objectAdmin) — if you need bucket metadata operations, add roles/storage.legacyBucketReader at bucket level.
	•	Generate a JSON key for this SA, but do not print it to the console. Immediately store it in Secret Manager as:
	•	Secret name: GCS_SA_KEY_CONTENT
	•	Add only my user and this repo’s CI identity (if any) as secret viewers. Do not grant public or broad roles.

	2.	Materialize the key locally (git-ignored) for dev runs

	•	Create secrets/ (ensure it’s in .gitignore).
	•	Retrieve secret to secrets/gcp-sa.json only for the current session:
	•	Use gcloud secrets versions access latest --secret=GCS_SA_KEY_CONTENT > secrets/gcp-sa.json
	•	Never commit this file.

	3.	Standardize env config

	•	Add/update .env.example with:
	•	GCS_BUCKET=lupito-content-raw-eu
	•	GCS_PREFIX=manufacturers
	•	GOOGLE_APPLICATION_CREDENTIALS=./secrets/gcp-sa.json
	•	Create/update .env accordingly (don’t print secrets).
	•	Ensure all snapshot/harvest scripts read these env vars. Default to GCS when GOOGLE_APPLICATION_CREDENTIALS + GCS_BUCKET exist; fall back to local only if explicitly USE_LOCAL_SNAPSHOTS=true.

	4.	Wire the snapshot writer to GCS

	•	Use google-cloud-storage client lib with Application Default Credentials (it will pick up GOOGLE_APPLICATION_CREDENTIALS).
	•	Pathing convention (no spaces, stable slugs):
	•	gs://lupito-content-raw-eu/<source>/<brand>/<YYYY-MM-DD>/<slug or hash>.{html,pdf,json}
	•	Example for manufacturers: manufacturers/brit/2025-09-11/puppy-lamb.html
	•	On write success, return and persist the GCS URI (e.g., gs://...) in the DB row (where we previously stored local paths), keeping provenance fields.

	5.	Add a tiny “GCS doctor”

	•	Script: scripts/gcs_doctor.sh
	•	Checks: env present, bucket exists, can upload→stat→download→delete a tempfile under manufacturers/_healthcheck/.
	•	Exit non-zero with a readable message if any step fails.
	•	Run it and include a short PASS/FAIL summary at the end of your output.

	6.	Harvester default: snapshot to GCS

	•	Update snapshot codepaths (HTML + PDF/image fetch) to write to GCS by default.
	•	Keep a --local override flag for emergencies that writes to ./snapshots/ with the same folder structure.

	7.	DB plumbing

	•	Wherever we store snapshot paths (e.g., food_raw.storage_path or similar), ensure entries are GCS URIs after this change.
	•	Do not change previously stored local paths; only new runs should use GCS.
	•	Add a tiny migration note in docs/STORAGE_MIGRATION.md explaining the mixed history (local→GCS) and how readers should handle both.

	8.	Verification (must run these and show results)

	•	scripts/gcs_doctor.sh → show PASS summary.
	•	Run the snapshot-only pass for one known brand profile (no parsing), e.g., “brit”:
	•	Fetch 3 product pages + any linked PDFs
	•	Confirm objects appear in gs://lupito-content-raw-eu/manufacturers/brit/<today>/...
	•	Print the exact GCS URIs captured.
	•	Write a minimal read-back check using the same client to confirm we can list and read the uploaded objects.

	9.	Safety & hygiene

	•	Ensure secrets/ is in .gitignore.
	•	Do not log credentials or object content.
	•	If organization policy forbids SA keys, automatically fall back to:
	•	gcloud auth application-default login (only if absolutely needed and you confirm it’s interactive), or
	•	instruct me clearly with the exact error and the alternative (Workload Identity, etc.).
	•	Otherwise, proceed only with the SA key from Secret Manager.

	10.	Deliverables

	•	scripts/gcs_doctor.sh
	•	.env.example (with the three vars above)
	•	Updated snapshot code writing to GCS
	•	docs/STORAGE_MIGRATION.md (what changed, how to read from GCS, mixed-history note)
	•	Final summary printing:
	•	SA email used
	•	Bucket verified
	•	Sample URIs uploaded
	•	Doctor script PASS
	•	Next step: enable parsing pass to read from GCS URIs

Success = I can see new objects at gs://lupito-content-raw-eu/manufacturers/... and the repo prints the URIs + a green PASS from gcs_doctor.sh.