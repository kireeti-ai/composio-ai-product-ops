# Human evaluation protocol (v1, prepared, NOT yet run)

**Status: no labels exist** (`LABELS_STATUS.json`: 0 of 168 rows). The assistant prepares the instrument and the arithmetic; it does not produce ground truth. Labels must come from humans reading primary sources.

## 1. What is evaluated
The unit is a **claim** = (app, field). Fields: `auth_methods`, `access`, `api_types`, `api_breadth`, `existing_mcp`, `buildability` (all vs a human truth value) and `blocker` (free text, judged correct / partial / incorrect). `category` and `one_liner` are not scored here.

## 2. Samples (pre-registered, seeded, deterministic)
- **Frame A (pilot, usable now):** 12 of the 26 existing baseline Pass-1 records (6 categories, both Gemini models, 6 with and 6 without Groq verifier flags; Sherlock #58 excluded as identity-contaminated). Measures the historical V1 output, not the v1f run.
- **Frame B (the real test):** 12 of the 28 frozen v1f targets, chosen from plan metadata only, before any v1f output exists (6 categories, every evidence tier, 7 Notion-verified and 5 reconstructed-list apps).
- Neo4j (#66) is evaluated separately per surface after its Option B run.
- Files: `sample_frames.json` (seed, attempts, quotas, balance), `sample_overview.csv`.
- Limits: 12 apps x 7 fields = 84 claims per frame. Confidence intervals will be wide. Results are descriptive for the sampled apps and must not be presented as a measured accuracy for all 100 apps.

## 3. Roles and blindness
1. **Labelers (>= 2, independent, human):** fill `label_sheet_blind_*.csv` using ONLY the blind sheet. They must not see model outputs, Groq verdicts, tiers or this repo's results. They must not use an LLM to decide truth.
2. **Adjudicator (a third human):** only after both labelers finish, opens `scoring_sheet_*.csv`, resolves disagreements (written rationale), fills evidence-support and blocker labels and an error category.
3. The assistant does not label or adjudicate.

## 4. Labelling rules
- Sources: vendor documentation, pricing, developer portal, official repositories. No third-party blogs as truth.
- Record URL, a verbatim quote, and the **access date** (documentation changes; truth is "as of" that date). Keep a page copy or hash if possible.
- Reconstructed-list apps (#51-100): first confirm the product from the vendor's own site and flag any identity doubt in `notes`. Do not label Sherlock, Harvest, fanbasis, Linear, Coda until their identity is confirmed.
- `undeterminable_from_public_sources = Y` when no public source decides the field (e.g. docs behind login). That is a valid truth state, not a failure.
- `enum_fit = forced` when no enum value fits (e.g. customer-account-gated APIs). `none_required` for auth is allowed as truth although the frozen model enum cannot express it.
- `api_breadth` thresholds are PROPOSED (narrow < ~15 operations; medium ~15-100; broad > 100). Fix them before labelling starts and do not change them afterwards.
- `existing_mcp = none_found` requires the search queries to be listed in `notes`.
- Agreement: report Cohen's kappa for enum fields and mean Jaccard for set fields. If kappa < 0.7 or Jaccard < 0.7, hold an adjudication meeting and revise the definitions BEFORE scoring.

## 5. Scoring (implemented in `src/eval_score.py`, tested in `tests/test_eval_score.py`)
`unknown` (or `["unknown"]`) is an **abstention**.

| Model says | Truth | Outcome | Strict | Lenient |
|---|---|---|---|---|
| value = truth | determinable | CORRECT | 1 | 1 |
| value != truth | determinable | INCORRECT | 0 | 0 (ordinal field adjacent value: 0.5) |
| unknown | determinable | ABSTAINED_MISSED | 0 | 0 |
| unknown | undeterminable | CORRECT_ABSTENTION | 1 | 1 |
| any value | undeterminable | UNSUPPORTABLE_CLAIM | 0 | 0 |
| set, exactly equal | determinable | CORRECT | 1 | 1 |
| set, overlaps | determinable | PARTIAL | 0 | set F1 |
| set, no overlap | determinable | INCORRECT | 0 | 0 |
| any | truth = none_required | SCHEMA_LIMITATION | excluded and reported | excluded |
| blocker | judged | correct / partial / incorrect | 1/0/0 | 1/0.5/0 |

**Partially supported claims** are scored on two separate axes:
- *Correctness* as above (set claims get partial credit through F1 in the lenient score).
- *Evidence support* (human label per claim: supports / partial / none). A claim can be correct for the wrong reasons: `right_for_wrong_reasons` counts CORRECT claims whose cited evidence does not support them. The automatic `quote_found` flag is NOT evidence support.

**Aggregates** (per field and overall; excluded outcomes are reported separately): accuracy_all (strict, lenient), accuracy_answered (excludes abstentions), coverage of determinable claims, missed abstentions, correct abstentions, over-claim rate when undeterminable, mean set F1, evidence-supported rate, right-for-wrong-reasons count, and accuracy with forced-fit claims excluded.
**Uncertainty:** Wilson 95% interval for proportions (claim-level, optimistic because claims within an app are correlated) and a **cluster bootstrap over apps** (2000 resamples, fixed seed) as the primary interval.
**Pass 2 (Groq) flags** are evaluated against human truth: precision and recall of `needs_human` as a detector of wrong or partial claims. Agreement between Gemini and Groq is never treated as accuracy.
**Pass comparisons** (first pass vs a corrected pass): paired on the same claims, exact McNemar test on discordant pairs plus a cluster-bootstrap difference.

**Worked arithmetic (SYNTHETIC, for illustration only; not data):** 6 claims = CORRECT, CORRECT, INCORRECT, ABSTAINED_MISSED, CORRECT_ABSTENTION, UNSUPPORTABLE_CLAIM -> strict accuracy 3/6 = 0.50; answered accuracy 2/3; coverage of determinable 3/4; over-claim rate when undeterminable 1/2. A set claim {oauth2, basic} vs truth {oauth2, api_key} -> PARTIAL, strict 0, F1 0.50.

## 6. Error taxonomy (adjudicator picks one per wrong claim)
wrong_value; over_claim (unsupported set element); under_claim (missed element); abstention_missed; unsupportable_assertion; identity_error; stale_docs; evidence_mismatch (quote does not support claim); source_gap (needed page never retrieved); schema_limitation; forced_fit.

## 7. Preserved limitations of this protocol
Small sample; two frames differ in what they measure; thresholds for breadth and buildability are proposals; the reconstructed-list apps have no identity authority; Groq is a different model family but sees only Gemini-cited evidence; documentation changes over time; labels are only as good as the labelers.

## 8. Files
`label_sheet_blind_A.csv`, `label_sheet_blind_B.csv` (blank, no model output), `scoring_sheet_A.csv` (model claims + verifier flags prefilled, label columns blank), `scoring_sheet_B_TEMPLATE.csv` (header only until the v1f run produces outputs), `sample_frames.json`, `sample_overview.csv`, `LABELS_STATUS.json`.
