# runs/ — all future output goes here, one directory per run
Layout: runs/<run_id>/{raw,pass1,verify,logs,RUN.json}. run_id = <stage>-<schema>-<provider>-<date>, e.g. p1-v1resume-gemini-20261124.
- Never write into work/ or baseline/ (both read-only; work/ = frozen original evidence, baseline/p1_v1 = verified copy with MANIFEST.json + SHA256SUMS.txt).
- Every record must carry: run_id, code_sha, prompt_sha, schema_sha, model, fetched_at, extracted_at, raw_sha.
- Cached retrievals are READ from baseline/p1_v1/raw; newer retrievals are written to the run's own raw/.
- Single writer per run (lock file); writes are atomic (tmp + rename).
- To undo write-protection on work/: chmod -R u+w work   (not recommended)
