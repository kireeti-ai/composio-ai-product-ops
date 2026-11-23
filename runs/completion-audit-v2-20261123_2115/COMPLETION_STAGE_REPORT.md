# Completion stage report — authoritative registry and 54-record audit

As of 2026-11-23 21:48 IST. This is a progress checkpoint, not a claim that the 100-app assignment is complete.

## Registry lock

- Source: supplied Notion export ZIP `1a4e2f2d-ee13-4234-80be-ef2ec6af30b0_ExportBlock-f24b1f34-8e4e-4e7f-a056-ba241f715ea7.zip`.
- ZIP SHA-256: `936c083b10dbcc36c3bad3863ce5cdb96a14dad2b680f910e018a4433e21930c`.
- Parsed 100 rows; IDs 1–100 unique and ordered; names unique; all 10 categories contain 10 rows.
- All 100 IDs, names, categories, and hints match the export. The prior registry had blank hints for IDs 51–100; those 50 values were restored. No candidate was replaced or renamed.
- All 100 positions are now confirmed as assignment entries from the supplied export. The earlier reconstructed-list caveat remains in historical records because those records were created before this source was supplied.
- Full table-level reconciliation and the previous registry bytes are in `runs/registry-lock-v1-20261123_2110/`.

## Research state

The current assembled snapshot is `runs/dataset-live-v5-20261123_2120/DATASET.json` (100 positions; source-list provenance updated). It contains 54 historical accepted primary extraction records and 46 positions without an accepted primary extraction. Existing status counts remain preserved:

- 29 unplanned
- 7 product-identity review / retrieval gates
- 2 retrieval gaps
- 2 identity exclusions pending product evidence
- 2 provisional product-identity holds
- 1 Neo4j two-surface hold
- 1 Groq quota pause
- 1 invalid-JSON failure
- 1 Sherlock quarantine
- 54 accepted historical primary records

These statuses describe research/execution state, not assignment-list membership; the export resolves list membership for all 100. The 54 records are not certified complete under the current evidence standard.

## Offline evidence audit of the 54 historical records

- 262 stored evidence items rechecked against their saved source bundles.
- 174 passed lexical URL/quote checks; 88 failed at least one check.
- Failure issue counts may overlap: 74 non-contiguous quotes, 30 ellipsis-stitching flags, 29 placeholder/too-short quotes, 3 URLs not in the source ledger, and 3 quotes absent from the shown extraction evidence.
- Claim-state counts from the deterministic validator: 124 supported-lexically, 143 unsupported, 27 not-found-in-provided-evidence, 2 needs-human, and 2 unknown.
- This is lexical validation, not semantic correctness or accuracy. No human labels exist; no accuracy claim is made.
- Per-record findings are in `AUDIT.json`; historical result files were not rewritten.

## Additional official-source retrieval

The saved retrieval union previously covered 93/100 IDs. A bounded hint-page attempt for the seven missing IDs (#83, #86, #91–93, #98–99) returned six pages and one 404 (#83 legacy Binance hint URL). The six raw pages and hashes are preserved in `runs/official-hint-topup-v1-20261123_2130/raw/` and `ATTEMPTS.json`.

Official first-party documentation was then inspected through the web research tool for all seven. Partial excerpts are recorded in `WEB_RESEARCH_EXCERPTS.json`; its hashes are hashes of the retained quotation strings, not of full page bodies. Full-page bytes for these browser-retrieved pages are unavailable, so these excerpts remain preliminary and are not accepted extraction records. A secondary direct HTTP fetch hung and was interrupted; this attempt is explicitly recorded.

## Provider / execution state

- No model-generation calls were made in this stage.
- Groq remains paused after the recorded daily-quota 429. A safe remaining daily-token budget is not confirmed; no Groq retry was made.
- No paid service, alternate key, OpenRouter request, or deployment was used.
- The full 46-app extraction is therefore still incomplete. Public-source retrieval and deterministic validation can continue; model extraction dependent on Groq must remain paused until legitimate available capacity is established.

## Tests and integrity

- Registry parser/export comparison: passed.
- `src/validate_apps.py`: passed (100 rows, 10 categories × 10, no empty hints).
- Dataset-status regression: passed after updating the test to require export-confirmed provenance and verify non-empty output directories are never overwritten.
- Neo4j surface and runner v1f executable offline self-tests: passed when each was invoked separately with a fresh temporary output directory.
- `test_verify_v2.py` in isolation: 13 passed.
- Full unittest discovery: 72 tests, 1 failure and 2 import errors. The import errors are from CLI-style self-test files (`test_neo4j_surfaces.py` and `test_runner_v1f.py`) that require a positional temp directory; both passed when run as intended. The quota test failure occurred only in the combined discovery run and passed in isolation. This suite is not fully green.
- Frozen baseline integrity: all 151 files in `baseline/SHA256SUMS.txt` verified successfully. No baseline, frozen v1f plan, prompt, schema, runner v6, or historic research output was modified.

## Next work

Continue with zero-cost official-source retrieval and manual claim/evidence review for the 46 positions with no accepted primary extraction, preserving every attempt. Do not resume Groq extraction until the existing authorized bucket has documented, legitimate remaining capacity. Rebuild the final HTML only after research records and evidence statuses are reconciled; this checkpoint does not replace the submission report.
