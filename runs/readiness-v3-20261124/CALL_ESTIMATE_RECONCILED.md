# Reconciled call estimate (generated from the execution ledger; every number below is computed, not typed)

## Gemini extraction: 75 calls = 28 + 2 + 39 + 6, over 74 apps
| Group | Calls | Apps | Original-list / reconstructed apps | Commitment |
|---|---|---|---|---|
| A. frozen v1f plan | 28 | 28 | 16 / 12 | approvable now (needs approval + quota check only) |
| B. Neo4j Option B (ONE app, TWO surfaces) | 2 | 1 | 0 / 1 | conditional: 3 gap retrievals recommended first |
| C. expansion waves 3A+3B+4 | 39 | 39 | 10 / 29 | conditional: retrieval + relevance audit + identity |
| D. identity-gated | 6 | 6 | 1 / 5 | conditional: identity confirmation (then retrieval) |
| **Total** | **75** | **74** | | 28 committed-after-approval + 47 conditional |

## The six identity-gated calls (group D) - exactly which apps
| ID | App | Master status | Why gated | What unlocks it | Provenance |
|---|---|---|---|---|---|
| 73 | Linear | HELD_IDENTITY_PROVISIONAL | identity provisional (name + domain consistency only) | user confirms identity; access-evidence top-up (free retrieval) | reconstructed |
| 78 | Coda | HELD_IDENTITY_PROVISIONAL | identity provisional; superhuman.com hits suggest docs migration | user confirms identity and canonical docs; access top-up | reconstructed |
| 80 | Harvest | EXCLUDED_IDENTITY_UNRESOLVED | 3 different products retrieved (getharvest / harvestapi / Greenhouse Harvest API); #80 has NO hint (reconstructed list) | authoritative identity (Notion hint) then fresh targeted retrieval | reconstructed |
| 50 | fanbasis | EXCLUDED_IDENTITY_UNRESOLVED | fanbasis.io unconfirmed; openstage.live excluded; dev-docs password-gated | user confirms fanbasis.io; retrieval of public docs may be impossible (docs gated) | original |
| 59 | Waterfall.io | EXPANSION_3H_PROVISIONAL_IDENTITY | provisional identity (user decision); reconstructed list | user confirms identity; access top-up | reconstructed |
| 60 | Clay | EXPANSION_3H_PROVISIONAL_IDENTITY | provisional identity (user decision); reconstructed list | user confirms identity; access top-up | reconstructed |

The six come from three places in the master matrix: HELD_IDENTITY_PROVISIONAL (73 Linear, 78 Coda) + EXCLUDED_IDENTITY_UNRESOLVED (80 Harvest, 50 fanbasis) + expansion wave 3H (59 Waterfall.io, 60 Clay) = 2 + 2 + 2.

## Why there is no double counting (all asserted in code: src/execution_ledger.py)
- the 6 gated apps are NOT in the 28 (v1f) nor in the 39: wave 3H (Waterfall.io, Clay) is excluded from the 39 and counted once in the 6
- Neo4j (#66) is not in the 28 and not in the 39; its 2 calls are 1 app x 2 surfaces
- Sherlock (#58) and Front (#14) already have baseline records and are NOT counted (optional re-extraction listed separately)
- 41 unplanned apps = 39 (group C) + 2 (3H, counted in group D): checked
- unique (app, surface) pairs = 75; apps with a new call = 74; 26 baseline + 74 = 100: checked
- Group A ids are exactly the 28 frozen ids; group C = the 41 expansion apps minus the two 3H apps (39); group D ids are disjoint from A, B and C.
- Apps by group: {'A_v1f_frozen': 28, 'B_neo4j_optionB': 1, 'C_expansion': 39, 'D_identity_gated': 6}; unique (app, surface) pairs = 75; 74 apps with a new call + 26 baseline records = 100.

## NOT in the 75
- Sherlock (#58) and Front (#14) re-extraction (2, optional, after identity/source fixes) and a corrected pass for ~20% of new records (~15); both would be new versioned runs.
- The 26 baseline apps need 0 new Gemini calls.

## Gemini: minimum / expected / worst
75 minimum; 87 expected (ASSUMES 15% transient retries: replace with the first run's observed ratio); 225 worst case at 3 attempts per app; 450 if both models fail 3 times each. Up to ~92 with the optional items.

## Groq verification (verifier v2), reconciled with the ledger
| Item | Calls |
|---|---|
| re-verify the 26 baseline records (measured plan) | 103 |
| verify the 75 new records (75 x 4, estimate) | 300 |
| **ledger total** | **403** |
| Pass 2 pilot stage 1 (28 controls/replays: extra work) | 28 |
| Pass 2 pilot stage 2 (the 12 Frame-A records) | 48 (a SUBSET of the 103 baseline re-verification: no extra calls if its results are kept as the official re-verification) |
| **minimum including the pilot** | **431** |
Expected attempts at the observed baseline retry ratio 1.71: about 737; `max_calls` must count ATTEMPTS. (The earlier report's 401 was a rounded per-record estimate; the ledger's exact plan is 403.)

## Free Composio retrieval (unchanged estimate): ~372 calls minimum (~558 with retries); $0 asserted per call; Neo4j <= 5; expansion ~300.
