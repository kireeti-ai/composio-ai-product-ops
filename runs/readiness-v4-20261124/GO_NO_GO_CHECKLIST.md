# Go / No-Go checklist

**Verdict: NO-GO FOR EXECUTION until the pending gates are resolved; structural preparation is complete**

## Automatic gates (evaluated now by running the real checks)

| Gate | Check | Status | Detail |
|---|---|---|---|
| A1 | baseline intact (151 files) | **PASS** |  |
| A2 | first run index still matches (72 files) | **PASS** |  |
| A3 | previous 178-file index still matches (no earlier artifact was modified) | **PASS** | all match |
| A4 | frozen v1f + execution config (19 checks) | **PASS** |  |
| A5 | no approval files exist anywhere | **PASS** |  |
| A6 | ledger reconciles: 75 calls / 74 apps / 26 baseline / 100 total / groups 28+2+39+6 | **PASS** |  |
| A7 | offline test suites (regression; synthetic data; NOT evidence of accuracy) | **PASS** | {"eval_score": 12, "eval_agreement": 6, "verify_v2": 13, "pass2_pilot": 6, "quota_plan": 8, "eval_seal": 5, "claims_guard": 6, "pass2_pilot_v2": 7, "runner_v1f": 34, "neo4j_surfaces": 13} |
| A8 | dry runs make no network/model call (v1f, Neo4j, Neo4j retrieval, verifier, pilot) | **PASS** | {"v1f": true, "neo4j_optionB": true, "neo4j_retrieval": true, "verifier_v2": true, "pass2_pilot": true} |
| A9 | human-eval blind sheets empty + clean; 0 labels | **PASS** |  |
| A10 | secret audit: no key value outside .env | **PASS** |  |
| A11 | Pass 2 pilot items built: 4 replays + 12 negative + 12 positive controls; stage-2 sheet blank | **PASS** |  |
| A12 | quota templates are BLANK (limits not assumed) and the planner refuses blanks | **PASS** |  |
| A13 | Groq reconciliation: 75 pilot calls = 12 new + 63 identical (56 distinct + 7 repeats); baseline 99 actual (103 ceiling); recommended minimum 411 / expected 703 / worst 2055 | **PASS** |  |
| A14 | provenance-by-status cross-tab: original 50 / reconstructed 50 / every status column == master coverage / all derivation checks pass | **PASS** | 12 checks |
| A15 | pilot v2: 89 real calls = 50 (CORE) + 12 (S1b) + 27 (S2REST); 77 ledger + 12 new; criteria pre-registered by hash | **PASS** |  |
| A16 | claims policy present and enforced by a tested guard (only tier T3 may claim accuracy) | **PASS** |  |

## Pending gates (cannot be satisfied by the assistant)

| Gate | Requirement | Owner | Blocks |
|---|---|---|---|
| U1 | Gemini limits observed after the 13:30 IST reset (G1-G8) | user | ALL Gemini calls |
| U2 | Approve Gemini models + per-model caps + phases in APPROVED.json (Phase 1 first = 15 calls) | user | Phase 1 |
| U3 | Acknowledge reconstructed provenance: 8 of the 15 Phase-1 apps and 12 of the 28 v1f apps are from the reconstructed list (membership unverified) | user | Phase 1 reporting |
| U4 | Groq limits observed (Q1-Q2) + approve pilot-v2 max_calls (>= 170 attempts: 89 calls x 1.71 = 153 expected, + margin) and min_interval_s; confirm or change the PRE-REGISTERED S1/S2 criteria before the pilot (they are then hashed) | user | Pass 2 pilot |
| U5 | Identity decisions: Sherlock, Harvest, fanbasis, Linear, Coda, Waterfall.io, Clay (6 gated calls + #58 re-extraction) | user | group D (6 calls) |
| U6 | Approve free retrievals: Neo4j gaps (<=5 calls) and expansion (~300 calls) | user | groups B(recommended)/C |
| U7 | Name two independent labelers + one adjudicator | user | human evaluation + pilot stage 2 |
| U8 | Rotate all exposed keys; remove unused keys from .env | user | deployment / publication |
| U9 | Deployment / publication approval (secret audit must pass again first) | user | deployment |
| H1 | Human labels: independent labelling, agreement >= 0.70, blind adjudication, truth freeze | humans | any accuracy claim |

## Staged GO decisions

| Stage | Scope | Needs |
|---|---|---|
| GO-1 | Phase 1: 15 Gemini calls (v1f frozen) | A1-A12 PASS, U1, U2, U3 |
| GO-2 | Pass 2 pilot v2: CORE 50 -> S1b 12 -> S2REST 27 (89 real calls; challenge tests, NOT accuracy) | GO-1 outputs exist, U4, U7 for the S2 human labels |
| GO-3 | Phase 2 (13) + Neo4j (2) | GO-1 reviewed, U1/U2 caps renewed, U6 recommended for Neo4j |
| GO-4 | expansion retrieval then extraction (39) + gated (6) | U5, U6, new versioned plans after retrieval, U1/U2 |
| GO-5 | remaining Pass 2 verification (411 distinct planned calls in total, ~703 attempts; ceiling for the 300 new-record calls) | pilot criteria pass, U4 |
| GO-6 | human evaluation + analysis + HTML + deployment | U7, H1, U8, U9 |
