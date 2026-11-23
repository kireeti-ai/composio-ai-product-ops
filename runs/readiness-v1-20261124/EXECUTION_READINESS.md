# Execution readiness (offline preparation complete; NOTHING has been executed)
Verdict: **prepared and frozen, NOT approved.** No Gemini/Groq call has been made for the v1f targets, no `APPROVED.json` exists, no extraction process is running.

## 1. Frozen
- `runs/p1-v1f-gemini-20261124` = 28 targets (27 of v1e + Gladly at registry ID 20). `FROZEN.json` records plan/status/runner hashes; the runner (v6) REFUSES to start if `PLAN.json` or `src/run_p1.py` differs (tamper-tested both ways). Recovery copy of the runner is stored in the run dir.
- Frozen extraction prompt `13eaee3870…` and schema `c5082c7feb…` (== baseline manifest) for all 28 targets and for both Neo4j calls.
- All previous run versions preserved (16 run directories under `runs/`, hash indexes `RUNS_SHA256SUMS_*.txt`), baseline 151/151 files intact.

## 2. Execution plan (after approval)
- Phase 1: 15 targets (explicit access evidence). Phase 2: 13 targets (inferred / partial / Gladly). Neo4j Option B: 2 calls (separate plan, held). Total >= 30 model requests (+ retries <= 2 per call for transient errors); per-model caps are mandatory in `APPROVED.json`; stops at the first daily-quota 429.
- Suggested staging: approve Phase 1 first, inspect results, then Phase 2 and Neo4j.
- Gemini active limits are UNVERIFIED (check AI Studio after the 13:30 IST reset); `gemini-2.5-flash` may be withdrawn.

## 3. Validation evidence (all offline, fake model functions)
registry integrity 17/17; dry runs (28 apps / 167 cached pages; Neo4j 2 calls / 5 pages, none shared); `tests/test_runner_v1f.py` (quota stop, resume, lock, top-up merge, provenance, uncertainty, Gladly inputs, held apps absent); `tests/test_neo4j_surfaces.py` 13 checks; `tests/test_eval_score.py` 12 tests (synthetic data); schema migration 26/26 valid + lossless; secret audit clean.

## 4. Blockers before execution
1. Your explicit approval + active Gemini limits, models and per-model caps.
2. Identities: Sherlock, Harvest, fanbasis (excluded); Linear, Coda (held). #51-100 membership vs the original Notion table is unverified (12 of the 28 targets, plus Neo4j).
3. Neo4j: the Query API call has ONE input page (expect mostly `unknown`); three free official fetches are recommended first (Aura authentication, Query API authorize requests, tier availability) - not executed, need approval.

## 5. Not ready / not yet built (does not block extraction)
- **Pass 2 verification for the new runs:** `src/verify.py` reads hard-coded `work/` paths (now read-only) and has no per-surface mode; it must be adapted (and its false-positive contradiction rule improved) before the new records can be verified. Not approved or built.
- Human labels: none exist (0 of 168 rows); labelers and an adjudicator are required. No accuracy claim is possible until then.
- Pattern analysis, HTML report, README, live link and repo publication are not started.
- **Coverage of the 100-app set (recomputed): 59 of 100 apps are accounted for** = 26 baseline Pass-1 records (incl. contaminated Sherlock #58) + 28 v1f targets + Neo4j + Linear/Coda held + Harvest/fanbasis excluded (no overlaps). **41 apps have no extraction record, plan or hold:** 22 of them have a cached retrieval (not validated for relevance) and 19 have no retrieval at all. Ids: 15, 24, 30, 31, 35, 37, 40, 42, 45, 48, 54, 55, 57, 59, 60, 64, 67-69, 74, 77, 79, 81-83, 85-100.

## 6. Evidence gaps and provenance limitations (preserved)
- Registry: apps 1-50 from the original Notion page's public data; apps 51-100 from a reconstructed secondary list (names/categories/order unverified, no hints). The Notion page may contain content after the first 50 apps' tables that was never read.
- V1 code is reconstructed (not byte-verified); Pass 1 baseline = 26 records across two Gemini models; ids 1,2,3,5 written twice; V0 smoke outputs deleted; record #58 (Sherlock) contaminated; #14 (Front) weak sources.
- Retrieval: free TinyFish via Composio only; pages truncated to 9000 chars in prompts; 8 first-attempt URLs unrecovered; MCP candidate pages never fetched; Composio SDK itself never demonstrated (MCP + consumer key only).
- Access states are the assistant's provisional readings (verified quotes, but heuristic relevance gave false negatives: Threads, Monday.com, Gladly's sandbox page). Inferred-self-serve apps (Vercel, Netlify, Klaviyo) must never be reported as confirmed. Gladly pricing unknown; MCP client-only evidence.
- Groq verdicts are flags, not ground truth; the verifier produced false positives.
- Security: keys pasted in chat persist in the session transcript store; rotate them.
