# Execution readiness v3 (offline; NOTHING executed)
No Gemini/Groq call, no retrieval call, no approval file, no deployment. All frozen artifacts and earlier run versions are unchanged (automatic gates A1-A12 PASS: `GO_NO_GO_CHECKLIST.md`). Everything new is in new versioned directories.

## What was produced for the seven items
| # | Item | Artifact |
|---|---|---|
| 1 | App-ID execution ledger, 100 apps; every proposed Gemini call mapped to app, surface, model policy, purpose, prerequisites | `runs/execution-ledger-v1-20261124/` (`ledger_apps_100.csv`, `ledger_gemini_calls_75.csv`, `ledger_verification_tasks.csv`, `EXECUTION_LEDGER.json`) |
| 2 | Call-estimate reconciliation (75 = 28 + 2 + 39 + 6) with the six gated apps named and no double counting (asserted in code) | `CALL_ESTIMATE_RECONCILED.md`, `RECONCILIATION.json` |
| 3 | Exact 100-app status matrix, original-list provenance (1-50) separated from reconstructed membership (51-100) | `STATUS_MATRIX_100.md/csv` |
| 4 | Pass 2 REAL-pilot plan (false-supported and false-contradicted cases); synthetic tests labelled as regression only | `runs/pass2-pilot-plan-v1-20261124/` |
| 5 | Exact Gemini and Groq quota checks; blank limit templates; deterministic planner; paced Groq wrapper | `runs/quota-checks-v1-20261124/`, `src/quota_plan.py`, `src/verify_v2_paced.py` |
| 6 | Blind human-evaluation sheets sealed: empty, no model/verifier columns, hashed | `runs/human-eval-seal-v1-20261124/SEAL.json`, `src/eval_seal_check.py` |
| 7 | Frozen artifacts preserved; changes versioned | automatic gates A1-A4 |

## Ledger headline
75 Gemini calls over 74 apps; 26 baseline apps need none; 100 = 26 + 74. Groups: A frozen v1f 28 | B Neo4j 2 (1 app, 2 surfaces) | C expansion 39 | D identity-gated 6 (Linear, Coda, Harvest, fanbasis, Waterfall.io, Clay). Committed after approval: 28; conditional: 47. Model: assigned at run time (primary `gemini-2.5-flash`, fallback `gemini-3.5-flash`, by approved list + per-model caps); each record stores the model actually used, so the ledger lists the policy, not a guessed assignment.
Provenance split of the 74 apps with a new call: 27 original-list, 47 reconstructed-list (A 16/12, B 0/1, C 10/29, D 1/5).

## Real measurements used for quota sizing (offline)
Gemini prompts of the 28 v1f calls: average ~8.5k input tokens, maximum ~17.4k (Netlify, Supabase, Vercel), ~238k tokens in total; Neo4j: ~5.6k (Aura) and ~1.1k (Query API). Groq verifier: ~982 tokens per call (3,327 characters average over 26 baseline records), observed retry ratio 1.71.

## Pass 2 pilot (not run)
S1a 4 real-model replays of known false-contradicted fields (+5 deterministic cases, 0 calls); S1b 12 planted false claims with zero lexical support in their sources (false-supported sensitivity); S1c 12 strongly supported real claims (false-contradicted sensitivity); S2 12 Frame-A records (48 calls) judged against blind human SOURCE-grounding labels (68 items, sheet blank). Minimum 76 calls (~131 attempts). Controls are sensitivity checks, not accuracy; S2 is source-grounded, not world truth; real verifier quality comes only from the human-evaluation flag precision/recall.

## Go / No-Go
**NO-GO for execution until the pending gates are resolved; structural preparation is complete.** Pending (user): Gemini limits (U1), approval with models + caps (U2), acknowledgement of reconstructed provenance (U3: 8 of the 15 Phase-1 apps and 12 of the 28 v1f apps), Groq limits + pilot approval (U4), identity decisions (U5), retrieval approvals (U6), named labelers/adjudicator (U7), key rotation (U8), deployment approval (U9); human labelling (H1). Staged GO decisions GO-1..GO-6 are in `GO_NO_GO_CHECKLIST.md` (GO-1 = Phase 1, 15 Gemini calls).

## Preserved gaps and provenance limitations
Apps 51-100 are a reconstructed list (membership, categories, order unverified; no hints); the original Notion page may hold content after the first 50 apps' tables that was never read. V1 code reconstructed, not byte-verified; 26 baseline records across two models; ids 1,2,3,5 written twice; V0 smoke outputs deleted; #58 contaminated; #14 weak sources. 8 first-attempt URLs unrecovered; MCP candidate pages never fetched; the Composio SDK itself never demonstrated (MCP + consumer key only). Access states are provisional readings; heuristic relevance gave false negatives (Threads, Monday.com, Gladly sandbox page); inferred-self-serve apps (Vercel, Netlify, Klaviyo) are never reported as confirmed; Gladly pricing unknown, MCP client-only. Groq verdicts are flags, not truth. The Neo4j Query API call has one input page. 0 human labels exist, so no accuracy claim is possible. Exposed keys persist in the session transcript store: rotate them.
