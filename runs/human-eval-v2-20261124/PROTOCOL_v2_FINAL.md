# Human evaluation protocol v2 (FINAL, prepared; NOT yet run; supersedes v1 in this respect: truth is fixed before any model output is seen)
**Status: 0 labels exist** (`LABELS_STATUS.json`). The assistant prepares instruments and arithmetic only; it never labels or adjudicates. Version 1 (`runs/human-eval-v1-20261124`) is preserved.

## 1. Unit and fields
A **claim** = (app, field). Fields: `auth_methods`, `access`, `api_types`, `api_breadth`, `existing_mcp`, `buildability` (compared with human truth) and `blocker` (free text, judged later). Neo4j (#66) is evaluated per surface after its Option B run (surfaces are sub-rows of one app).

## 2. Samples (pre-registered, seeded, deterministic; `sample_frames_v2.json`)
| Frame | Apps | What it measures | Selected from |
|---|---|---|---|
| A | 12 of the 26 baseline records | historical V1 Pass-1 output + old verifier flags (pilot, can start now) | existing records |
| B | 12 of the 28 frozen v1f targets | the v1f run | plan metadata only |
| C | 12 of the 41 expansion apps (waves 3A/3B/4) | the expansion run | plan metadata only |
| CAL | 3 baseline apps outside A | calibration of labelers; NOT scored | seeded |
12 apps x 7 fields = 84 claims per frame (252 scored). Confidence intervals will be wide; results are descriptive for the sampled apps and must not be presented as the accuracy of all 100 apps. Reconstructed-list apps have no identity authority and are flagged in every sheet.

## 3. Roles
Labelers L1 and L2: independent humans. Adjudicator: a third human. Scorer: the code in `src/eval_score.py` (the assistant only runs it). Nobody uses an LLM to decide truth.

## 4. Workflow (order matters; each step is recorded with a file hash)
1. **Calibrate:** L1 and L2 label the CAL sheet alone, then meet once to align definitions. Definitions (incl. the proposed `api_breadth` thresholds and the `buildability` definition) are then FROZEN; any later change needs a dated written amendment before the next frame.
2. **Blind labelling:** L1 and L2 each fill `label_sheet_blind_{A,B,C}.csv` independently (instructions: `labeler_instructions.md`). They see no model output, verifier flag, tier or run result.
3. **Agreement:** `python src/eval_agreement.py L1.csv L2.csv --out DIR` -> `agreement.json`, `adjudication_queue.csv`, `truth_sheet.csv`. Reported: Cohen's kappa for enum fields (category 'undeterminable' included), mean Jaccard for set fields. If pooled kappa < 0.70 or Jaccard < 0.70, stop and revise definitions by amendment BEFORE adjudicating; re-label affected fields.
4. **Adjudication (still blind to model output):** the adjudicator resolves only queued disagreements from primary sources, fills `adjudication_log_TEMPLATE.csv` with URL, quote, access date and written rationale, then re-runs the merge with `--adjudicated`. Disagreements with no adjudication stay BLANK and are excluded, never guessed.
5. **Freeze truth:** record the SHA-256 of the final `truth_sheet.csv`. After this, truth is immutable.
6. **Unlock model outputs:** only now are `scoring_sheet_*.csv` opened (model claims, quote_found, Groq verdicts). The adjudicator (or a fourth person) fills `evidence_support_label` (supports / partial / none), `blocker_label` (correct / partial / incorrect / none_applicable) and `error_category` per claim.
7. **Score:** `python src/eval_score.py truth_sheet.csv scoring_sheet.csv`.

## 5. Labelling rules
Primary sources only (docs, pricing, developer portal, official repos). URL + verbatim quote + access date for every non-blank truth cell; keep a page copy or hash. `undeterminable_from_public_sources = Y` when no public source decides the field. `enum_fit = forced` when no value fits (e.g. customer-account-gated APIs). `none_required` is a valid auth truth although the frozen model enum cannot express it. `existing_mcp = none_found` requires the queries listed in `notes`.

## 6. Field-level scoring (`src/eval_score.py`; `tests/test_eval_score.py`)
`unknown` (or `["unknown"]`) is an **abstention**.
| Model says | Truth | Outcome | Strict | Lenient |
|---|---|---|---|---|
| = truth | determinable | CORRECT | 1 | 1 |
| != truth | determinable | INCORRECT | 0 | 0 (ordinal field adjacent value 0.5) |
| unknown | determinable | ABSTAINED_MISSED | 0 | 0 |
| unknown | undeterminable | CORRECT_ABSTENTION | 1 | 1 |
| any value | undeterminable | UNSUPPORTABLE_CLAIM | 0 | 0 |
| set equal | determinable | CORRECT | 1 | 1 |
| set overlaps | determinable | PARTIAL | 0 | set F1 |
| set disjoint | determinable | INCORRECT | 0 | 0 |
| any | truth = none_required | SCHEMA_LIMITATION | excluded, reported | excluded |
| blocker | judged | correct / partial / incorrect | 1 / 0 / 0 | 1 / 0.5 / 0 |
Two axes for partially supported claims: **correctness** (above) and **evidence support** (human label supports / partial / none). A correct claim whose cited evidence does not support it is counted as `right_for_wrong_reasons`. The automatic `quote_found` flag is NOT evidence support.
Aggregates per field and overall: accuracy_all (strict and lenient), accuracy_answered (excludes abstentions), coverage of determinable claims, missed abstentions, correct abstentions, over-claim rate when undeterminable, mean set F1, evidence-supported rate, right-for-wrong-reasons count, accuracy excluding forced-fit claims. Excluded outcomes (schema limitation, unlabelled, not applicable) are always reported separately. Uncertainty: Wilson 95% interval (optimistic) and the primary **cluster bootstrap over apps** (2000 resamples, fixed seed).

## 7. Evaluating Pass 2 (verifier v2) and comparing passes
Verifier verdicts are **flags, not truth**. Evaluate `needs_human` as a detector of wrong/partial claims against frozen truth (precision, recall); report separately the verdict classes `supported`, `insufficient_evidence`, `schema_limitation`, `ambiguous_needs_human`, `contradicted`. Gemini-Groq agreement is never accuracy. First-pass vs corrected-pass comparisons are paired on the same claims (exact McNemar on discordant pairs + cluster-bootstrap difference); a corrected pass is a new versioned run.

## 8. Error taxonomy (one per wrong claim)
wrong_value; over_claim; under_claim; abstention_missed; unsupportable_assertion; identity_error; stale_docs; evidence_mismatch; source_gap; schema_limitation; forced_fit.

## 9. Integrity rules
Truth sheets and scoring outputs are hashed and read-only once frozen; amendments are dated and listed; no frame is relabelled after its truth is frozen; any assistant-prepared file is hash-indexed in `runs/RUNS_SHA256SUMS_*.txt`.

## 10. Preserved limitations
Small samples; two model-output frames plus a pilot; proposed thresholds for breadth/buildability; the reconstructed-list apps have no identity authority; Groq sees different evidence but a similar task framing; documentation drifts over time; labels are only as good as the labelers; Frame C depends on retrieval that has not happened yet.

## 11. Tools and tests
`src/eval_sample_v2.py`, `src/eval_agreement.py` (+ `tests/test_eval_agreement.py`), `src/eval_score.py` (+ `tests/test_eval_score.py`), `src/verify_v2.py` (+ `tests/test_verify_v2.py`). All tests use synthetic or stored data only.
