# Claims policy and pass/fail criteria (pre-registered; nothing has been run)

## 1. Four evidence tiers - what each may and may not support
| Tier | What it is | Produced by | May support | May NOT support |
|---|---|---|---|---|
| **T0** | regression tests (fake model functions, synthetic or stored fixtures) | `tests/*.py` | "the code behaves as specified on these cases" | any statement about verifier or extraction quality |
| **T1** | **controlled challenge tests**: S1a replay of known failures, S1b planted false claims, S1c strongly supported claims | real Groq calls on real stored sources, constructed inputs | "on these N constructed cases the verifier returned X" (e.g. 0 of 12 planted claims came back 'supported') | an accuracy, precision, recall or error rate; any real-world rate. A planted claim is false by construction relative to the stored text only |
| **T2** | **source-grounded pilot** S2: independent humans judge whether the STORED text supports each claim; verdicts compared | humans blind to verifier output | "verdicts agreed with human reading of the stored text on N sampled items" | real-world accuracy (the stored text can be incomplete, stale or about the wrong product) |
| **T3** | **independent human-labelled evaluation** (protocol v2): >= 2 independent labelers + adjudicator, truth from primary sources frozen by hash, agreement kappa/Jaccard >= 0.70, cluster-bootstrap intervals | humans | **the only basis for an accuracy claim**: field-level accuracy of Pass 1, flag precision/recall of Pass 2, and any before/after improvement (paired on the same claims) | generalising beyond the sampled apps to all 100 |
Nothing from T0, T1 or T2 may be reported with the words accuracy, precision, recall, error rate or reliability. `src/claims_guard.py` enforces this: every reported number must carry a tier and a label; a T3 number additionally needs the truth-sheet hash, >= 2 labelers, adjudication, n, a 95% interval and pooled kappa >= 0.70.

## 2. Pass/fail criteria (proposed; the user may change them BEFORE the pilot; they are then hashed - `CRITERIA_SHA256.txt` - and frozen)
| Stage | Calls | Question | PASS | FAIL |
|---|---|---|---|---|
| S1a (T1) | 4 items inside CORE | do the old false contradictions survive with the real model? | 0 of 4 final 'contradicted' | any final 'contradicted' |
| S1b (T1) | 12 new calls | does a planted unsupported claim come back 'supported'? | 0 of 12 'supported' | any 'supported'; a 'contradicted' is reported and must carry an explicit negating quote |
| S1c (T1) | 12 items inside CORE | do well-supported claims survive? | 0 'contradicted' AND >= 9 of 12 'supported' (sensitivity floor, proposed) | any 'contradicted', or fewer than 9 supported |
| S2 (T2) | 68 claim items, human-labelled | source-grounded false-supported / false-contradicted | needs >= 40 labelled items; false_supported <= 1 AND false_contradicted <= 1 AND no cause repeated | CONDITIONAL if (false_supported + false_contradicted) <= 3 with no repeated cause; FAIL otherwise; INCONCLUSIVE if < 40 labelled |
Stop rule: CORE (grade S1a/S1c) -> S1b -> S2REST (then S2); stop at the first FAIL; fix by versioning the verifier (v2.1) and re-run only the affected stage. A passing S1 or S2 means only "no blocking problem found on these cases"; it never becomes an accuracy statement.

## 3. Phrasing rules (examples)
- Allowed (T1): "Challenge test: 0 of 12 planted claims were returned as 'supported' (Wilson 95% upper bound 24.3%); this is not an accuracy estimate."
- Allowed (T2): "Source-grounded: of N verdicts 'supported', k disagreed with human reading of the stored text; this is not real-world accuracy."
- Forbidden: "The verifier is 100% accurate", "0% false-support rate", "precision 1.0" (unless tier T3).
- Real-world accuracy of Pass 1 or the verifier, and the first-pass-to-corrected-pass improvement, may be stated only from T3 evidence on the SAME claims, with intervals and the sample limits (12 apps per frame).

## 4. Reporting layout
Separate sections in every report and in the HTML: "Controlled challenge tests (T1)", "Source-grounded pilot (T2)", "Human-labelled accuracy (T3)". Until T3 exists the third section states: "No accuracy claim: no human labels exist."
