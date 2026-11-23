# Corrected report v4 (offline; NOTHING executed - no model call, no retrieval call, no approval file, no deployment)
Frozen artifacts and all earlier run versions are unchanged (automatic gates A1-A16 PASS, `GO_NO_GO_CHECKLIST.md`). Corrections are in new versioned directories: `runs/groq-call-reconciliation-v2-20261124`, `runs/pass2-pilot-plan-v2-20261124`, `runs/provenance-crosstab-v2-20261124`, `runs/readiness-v4-20261124`.

## 1. Groq call estimate: what was wrong and the corrected numbers
Errors in my earlier reports: (a) the pilot was "76" calls (4+12+12+48) and "adds 28" - 28 assumed S2 is reused while S1a/S1c are separate, without saying so; (b) the 103 baseline re-verification calls (and the 403 ledger total built on them) are planned CEILINGS: 4 of them would never be sent (the retriever returns no passage for records 7 auth_methods, 16/18/19 existing_mcp), so the actual baseline count is **99**; (c) S2 actually sends 47 calls, so the pilot is **75** calls.
Exactly which pilot calls overlap with the ledger (call = record+field; overlap = byte-identical prompt; `call_level_overlap.csv`): of the 75, **12 are new** (S1b planted controls: the planted item changes the prompt) and **63 are identical to ledger baseline calls - but only 56 are DISTINCT ledger calls; 7 are repeats inside the pilot itself** (S1c 28/auth_methods = S1a; S2 9/access = S1c; 14/api_types = S1c; 14/existing_mcp = S1a; 28/auth_methods = S1a; 49/existing_mcp = S1a; 84/auth_methods = S1c).
| Scenario | Minimum planned calls | Expected attempts | Worst-case attempts |
|---|---|---|---|
| As reported before (ceilings, 403 + 28) | 431 | 738 | 2,155 |
| A. actual calls, S2 reused, S1a/S1c separate | 427 | 731 | 2,135 |
| B. actual calls, nothing reused | 474 | 811 | 2,370 |
| **C. corrected and recommended: pilot v2, every distinct call once (99 + 300 + 12)** | **411** | **703** | **2,055** |
Assumptions: retry ratio 1.71 OBSERVED in the baseline Groq log; worst case 5 attempts per call; the 300 new-record calls (75 records x 4) remain an estimate/ceiling (shortcuts can only lower it). `max_calls` in any approval must count ATTEMPTS.
**Pilot v2** = CORE (13 records verified in full) 50 + S1b 12 + S2REST (7 records) 27 = **89 real calls (about 153 attempts, 445 worst case)**; 77 are ledger calls that are needed anyway and only the 12 planted-control calls are new. S1a/S1c/S2 become analyses of those results; the CORE and S2REST files are the official re-verification of 20 of the 26 baseline records. The Gemini estimate is unchanged: 75 minimum / 87 expected / 225 worst.

## 2. Provenance-by-status cross-tab (`runs/provenance-crosstab-v2-20261124/`)
Statuses were derived independently from primary artifacts, then reconciled cell by cell with the master coverage matrix and the ledger (12 checks, all pass).
| Provenance | Completed baseline | Completed, quarantined | Planned (frozen v1f) | Held: Neo4j | Held: identity | Excluded: identity | Unplanned | Row total |
|---|---|---|---|---|---|---|---|---|
| Original list (1-50) | 23 | 0 | 16 | 0 | 0 | 1 | 10 | **50** |
| Reconstructed list (51-100) | 2 | 1 | 12 | 1 | 2 | 1 | 31 | **50** |
| Column total | 25 | 1 | 28 | 1 | 2 | 2 | 41 | **100** |
| Master coverage count | 25 | 1 | 28 | 1 | 2 | 2 | 41 | 100 |
Exact IDs per cell, the phase split (15 + 13 = 28) and the expansion-wave split (14 + 6 + 2 + 19 = 41) are in `CROSSTAB.md`.

## 3. Controlled challenge tests vs real-world accuracy (`CLAIMS_POLICY_AND_CRITERIA.md`, `src/claims_guard.py`)
- **T0 regression tests** (synthetic/stored fixtures): no quality claim.
- **T1 controlled challenge tests** (S1a replay, S1b planted false claims, S1c supported claims): "on these constructed cases the verifier returned X"; NEVER an accuracy, precision, recall or error rate.
- **T2 source-grounded pilot** (S2): humans judge the STORED text; "agreement with human reading of stored text"; NOT real-world accuracy.
- **T3 independent human-labelled evaluation** (protocol v2: >= 2 labelers + adjudicator, truth frozen by hash, kappa/Jaccard >= 0.70, cluster-bootstrap intervals): **the only basis for any accuracy claim**, including Pass-1 field accuracy, verifier flag precision/recall, and any first-pass-to-corrected-pass improvement (paired on the same claims).
Pre-registered criteria (proposed; hashed `3f5d04f8…` before any run; you may change them first): S1a PASS = 0 of 4 replayed false items final 'contradicted'; S1b PASS = 0 of 12 planted claims 'supported'; S1c PASS = 0 'contradicted' and >= 9 of 12 'supported'; S2 needs >= 40 labelled items, PASS = false_supported <= 1 and false_contradicted <= 1 with no repeated cause, CONDITIONAL = total <= 3 with no repeated cause, else FAIL. Stop at the first FAIL; fix by versioning the verifier. A pass means "no blocking problem found on these cases", never an accuracy statement. The guard rejects any T0-T2 number labelled accuracy/precision/recall, and any T3 number lacking truth hash, 2 labelers, adjudication, n, interval or kappa >= 0.70. **Today: no accuracy claim exists, because 0 human labels exist.**

## 4. Other corrections and disclosures
- `runs/quota-checks-v1-20261124` still lists the old pilot sizes (28 + 48 calls) and the old 431 figure; superseded by this report. `src/quota_plan.py` default planned calls changed 431 -> 411 (with its test: expected attempts 703). It is a non-frozen tool; no frozen file changed.
- Newly added tools this step: `src/groq_reconcile.py`, `src/pass2_pilot_v2.py`, `src/provenance_crosstab.py`, `src/claims_guard.py`, `src/go_no_go_v4.py` (+ tests). Old pilot plan v1 is untouched (superseded for call accounting only).
- The test count in the automatic gate A7: 10 suites, all pass (regression only; not evidence of quality).

## 5. Go / No-Go
**NO-GO for execution until the pending gates are resolved; structural preparation is complete.** Automatic gates A1-A16: PASS. Pending: U1 Gemini limits after 13:30 IST; U2 approval with models + per-model caps (Phase 1 first, 15 calls); U3 acknowledgement of reconstructed provenance (8 of the 15 Phase-1 apps; 12 of the 28 v1f apps); U4 Groq limits + pilot-v2 approval (max_calls >= 170 attempts) + confirmation of the pre-registered criteria; U5 identity decisions (6 gated calls + #58 re-extraction); U6 retrieval approvals (Neo4j <= 5 calls; expansion ~300); U7 two labelers + an adjudicator; U8 key rotation; U9 deployment approval; H1 human labelling. Staged decisions GO-1..GO-6 are in `GO_NO_GO_CHECKLIST.md`.

## 6. Preserved gaps and provenance limitations
Apps 51-100 are a reconstructed list (membership, categories, order unverified; no hints; the original Notion page may hold unread content after the first 50 apps' tables). V1 code reconstructed, not byte-verified; 26 baseline records across two Gemini models; ids 1,2,3,5 written twice; V0 smoke outputs deleted; #58 contaminated; #14 weak sources. 8 first-attempt URLs unrecovered; MCP candidate pages never fetched; Composio SDK itself never demonstrated (MCP + consumer key only). Access states are provisional readings; the heuristic relevance check gave false negatives (Threads, Monday.com, Gladly sandbox page); inferred-self-serve apps (Vercel, Netlify, Klaviyo) are never reported as confirmed; Gladly pricing unknown, MCP client-only. The Neo4j Query API call has one input page. Groq verdicts are flags, not truth. Exposed keys persist in the session transcript store: rotate them.
