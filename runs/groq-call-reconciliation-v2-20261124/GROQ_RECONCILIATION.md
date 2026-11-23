# Groq call reconciliation (call-level, computed from captured prompts; no model call)
A call = (record, surface, field). Two calls OVERLAP only if their prompts are byte-identical (`call_level_overlap.csv`, one row per pilot call).

## 1. Corrections to what was reported
| Item | Reported | Correct | Why |
|---|---|---|---|
| Baseline re-verification | 103 | **99 actual** (103 is a ceiling) | 4 planned calls would never be sent: the retriever returns no passage for (7 auth_methods), (16, 18, 19 existing_mcp) |
| Ledger Groq total | 403 | **399** (99 + 300); 403 is the ceiling | the 300 (= 75 new records x 4) remain an estimate/ceiling: shortcuts can only lower it |
| Pilot v1 calls | "76" (4+12+12+48) | **75** (4+12+12+47) | S2 sends 47 actual calls, not 48 |
| "The pilot adds 28" | 28 | not a defensible figure | it assumed S2 is reused but S1a/S1c are separate, without saying so |

## 2. Exactly which pilot calls overlap with the ledger
| Pilot stage | Calls | Identical to a ledger call | Repeated inside the pilot (also identical to an earlier pilot call) | New |
|---|---|---|---|---|
| S1a (4 replays) | 4 | 4 | 0 | 0 |
| S1b (12 planted) | 12 | 0 | 0 | **12** (prompts differ: the planted item is in the item list) |
| S1c (12 positive controls) | 12 | 11 | 1 (record 28 auth_methods = S1a) | 0 |
| S2 (47) | 47 | 41 | 6 (records 9 access, 14 api_types, 14 existing_mcp, 28 auth_methods, 49 existing_mcp, 84 auth_methods) | 0 |
| **Total** | **75** | **56 distinct ledger calls + 7 repeats = 63** | **7** | **12** |
So 75 = 12 new + 63 identical-to-ledger, and those 63 are only 56 DISTINCT ledger calls.

## 3. Corrected estimates (no double counting)
Assumptions: retry ratio 1.71 (OBSERVED in the baseline Groq log); worst case 5 attempts per call (verifier limit); the 300 new-record calls are a ceiling.
| Scenario | Minimum planned calls | Expected attempts | Worst-case attempts |
|---|---|---|---|
| As reported before (ceilings: 403 + 28) | 431 | 738 | 2,155 |
| A. actual calls; S2 reused, S1a/S1c run separately | 427 | 731 | 2,135 |
| B. actual calls; nothing reused (all 75 pilot calls extra) | 474 | 811 | 2,370 |
| **C. RECOMMENDED pilot v2: every distinct call once** | **411** = 99 + 300 + 12 | **703** | **2,055** |
Pilot v2 (`runs/pass2-pilot-plan-v2-20261124`): CORE (13 records, full-record verification) 50 calls + S1b 12 + S2REST (7 records) 27 = **89 real calls (~153 attempts expected, 445 worst)**; 77 of them are ledger calls that are needed anyway and only the 12 planted-control calls are new. S1a/S1c/S2 become analyses of those results. The CORE and S2REST result files are the OFFICIAL baseline re-verification for 20 of the 26 baseline records; the remaining 6 records are verified later (their calls are part of the 99).

## 4. Why the earlier design double counted
Stages S1a and S1c re-ran fields that S2 (and the final baseline verification) run again, using restricted-field result files that cannot be reused by the full-record run. Pilot v2 verifies each record once in full, in priority order (S1 records first), so every call is made once.
