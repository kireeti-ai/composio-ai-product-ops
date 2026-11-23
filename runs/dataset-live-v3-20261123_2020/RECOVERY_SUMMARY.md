# Recovery and execution snapshot

Snapshot time: **2026-11-23 20:16:44 IST**. This reflects files and provider logs available at that time; it is not a claim that the assignment is complete.

## Coverage

- Registry: 100 IDs, each represented exactly once. IDs 1–50 retain original-list provenance; IDs 51–100 remain reconstructed candidates whose original Notion membership, category and ordering are unverified.
- 54 positions have an accepted primary extraction: 25 completed baseline records, 27 of the 28 frozen v1f targets (five corrected pilot outputs plus 22 Batch A outputs), and two Batch B outputs.
- A further preserved record for #58 Sherlock is quarantined and is not counted as an accepted extraction.
- Frozen v1f: **27/28 extracted**. #71 Notion has an invalid-JSON failure preserved as `failed_71_10.json`; it was not regenerated.
- Batch B: #30 Vonage and #35 Mailchimp have outputs. The initial #35 quota failure is preserved alongside the later output. #37 systeme.io is paused after a daily-quota 429. The remaining identity gate has 30 READY targets total and nine blocked/held targets; no identity was guessed.
- Current matrix status counts: 25 baseline complete, 22 Batch A, five corrected pilot, two Batch B, 29 still unplanned, seven identity-review blocked, two retrieval-gap blocked, two excluded identity, two held identity, one Neo4j held, one quarantined, one quota-paused, and one invalid-JSON failure. Sum: 100.
- The dataset contains 55 stored result versions; 54 positions have accepted primary outputs and #58 has a separate quarantined record. There are 26 legacy model-verification records; they are not human ground truth. Human labels remain blank (0/100).

## Provider state and safe resume

- Groq last reported a TPD limit of 200,000, with 199,639 used and 4,028 requested at 20:05:38 IST; the response advised retrying after 1,585 seconds. The user-set 180,000 soft cap was already exceeded, so Batch B was stopped.
- The supervisor PID 98429 received SIGTERM and was confirmed absent. No Batch A process was found in the process inspection.
- The run-local quota file tracks 133,546 tokens across 37 request timestamps; it omits prior benchmark consumption and is not a sufficient provider-wide usage counter. Do not resume based on that local count or the short Retry-After alone. Wait for the provider's daily reset/confirmed capacity, then use a runner with a hard 180,000-token budget and a conservative seed for prior usage.
- Groq P2–P4, OpenRouter and Gemini Key 2 remain disabled. No Gemini cross-check was performed in this recovery stage.

## Integrity and UI

- All 151 entries in `baseline/SHA256SUMS.txt` verified. Frozen v1f plan, app-status file, eligibility file and runner v6 match their FROZEN.json hashes. Prompt/schema hashes remain `13eaee38702b…` and `c5082c7feb4a…`.
- The five-section report is self-contained at `report/index.html`; a copy is preserved as `REPORT.html` in this run. It uses the editorial blueprint visual system and adds six explicit status fields to each expandable app row. It makes no accuracy claim and keeps the 51–100 provenance caveat visible.
- Report status is a local artifact only. Nothing was deployed, published, or externally shared.

## Offline checks

- `tests/test_dataset_status.py`: passed; verifies 100 unique IDs, all six status fields, the quota pause, invalid-JSON failure, identity blocker, Sherlock quarantine, reconstructed provenance, and blank human review.
- `tests/test_eval_score.py`: 12 passed.
- `runs/bench5-v2-20261123_192201/test_bench2.py`: 26 passed.
- `runs/pilot5-v7-20261123_185728/test_pilot5_v7.py`: 26 passed.
- `tests/test_runner_v1f.py`: all self-tests passed.
- `tests/test_neo4j_surfaces.py`: all self-tests passed.
- `tests/test_verify_v2.py`: 13 passed; `tests/test_eval_agreement.py`: 6 passed; `tests/test_pass2_pilot.py`: 6 passed; `tests/test_pass2_pilot_v2.py`: 7 passed; `tests/test_claims_guard.py`: 6 passed; `tests/test_quota_plan.py`: 8 passed; `tests/test_eval_seal.py`: 5 passed.
- Inline report JavaScript passed `node --check`; report contains no external script or stylesheet dependencies.
- Existing tests emitted ResourceWarnings for unclosed files in older scripts; they passed and those unrelated files were left unchanged.

## Immediate next actions

1. Keep model execution paused until Groq daily capacity resets and the 180K ceiling can be enforced from an accurate usage baseline.
2. Resume the existing Batch B candidate set without rerunning successful app outputs; preserve new attempts and results in versioned storage.
3. Continue resolving the nine identity/retrieval blockers from official sources, keeping unresolved positions blocked.
4. Continue retrieval and extraction for the 29 unplanned positions in quota-safe batches.
5. Run independent verification only when separately available; human labels remain necessary for any accuracy claim.

No generation or retrieval calls were made during this recovery/report-build stage.
