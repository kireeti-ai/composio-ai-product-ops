# Pass 2 (verifier v2) REAL-PILOT test plan - prepared, NOT run (no Groq call has been made)

## What counts as evidence
- **Pilot evidence = REAL Groq calls on REAL stored source pages** (after approval). Nothing else.
- The unit/regression tests (`tests/test_verify_v2.py` etc., with fake model functions) are **regression tests, not evidence of verifier quality**. The evaluator tests use SYNTHETIC inputs and are not results.
- **Planted controls** (stage S1b) are *sensitivity checks*: a planted claim is false relative to the stored sources by construction. They say nothing about real-world accuracy.
- Stage S2 is judged against **source-grounding labels** (does the STORED text support/contradict the claim?), still NOT real-world truth. Real-world accuracy of the verifier comes only from the human-evaluation protocol (flag precision/recall against frozen truth).

## Stages and call budget (`pilot_call_budget.json`)
| Stage | What | Min calls | Expected attempts (x1.71 observed Groq retry ratio) |
|---|---|---|---|
| S1a | real-model replay of 4 known false-contradicted fields (Front MCP, Amazon MCP, WhatsApp OAuth, Twenty access); 5 more known cases (HubSpot, Attio, Twilio, Paygent enum conflict; Sherlock no-credentials) are deterministic and need 0 calls | 4 | 7 |
| S1b | **false-supported test:** 12 real records, each with ONE planted claim that no stored source supports (3x soap, 3x websocket, 3x jwt_or_signed, 3x 'official MCP'); validity proven offline (zero lexical support in every source page of that record) | 12 | 21 |
| S1c | **false-contradicted / false-insufficient test:** 12 real, strongly source-supported claims (verbatim Pass-1 quote naming the item) | 12 | 21 |
| S2 | real pilot: verifier v2 on the 12 Frame-A baseline records, all four evidence fields | 48 | 82 |
| **Total** | | **76** | **~131** |
Groq `max_calls` for the pilot must count attempts: set it >= 140 (about 2x the minimum), after the Groq limit check.

## The false-supported and false-contradicted cases covered
- **False-contradicted (known, from the old verifier):** 8 items. 5 are caught deterministically (enum-semantics conflict x4, 'no credentials required'); 3 plus the Twenty adversarial case (S1a) test the real model + guardrails.
- **False-supported:** S1b (planted, 12) and S2 (`false_supported` = verifier said supported while the human source label is not 'supports').
- **False-contradicted on good claims:** S1c (12) and S2 (`false_contradicted`).
- **Missed support/contradiction (false-insufficient):** S1c and S2.

## S2 labelling (independent, blind to verifier output)
`stage2_source_grounding_sheet_TEMPLATE.csv`: 68 claim items from Frame A, each with candidate passages and the full source page list; label columns are BLANK and no verifier verdicts are present. Two independent labelers label `supports | contradicts | neither | cannot_tell` with the decisive URL and quote; disagreements go to a third adjudicator. Only then are verifier verdicts joined (`eval_stage2`). `cannot_tell` items are excluded and counted.

## Proposed go/no-go criteria for using verifier v2 beyond the pilot (the user decides; not yet adopted)
1. S1a: none of the 8 known false contradictions is a final `contradicted` verdict.
2. S1b: 0 false-supported among the 12 planted claims; any false-supported is root-caused and fixed before scaling.
3. S1c: 0 false-contradicted among 12 positive controls; the supported rate (sensitivity) is reported, not hidden.
4. S2: false-supported and false-contradicted counts reported with Wilson intervals; no failure class with 2 or more instances sharing a cause.
5. All verifier output remains a review flag, never ground truth. A failed criterion means: fix, version the verifier (v2.1), re-run the affected stage.

## Order
S1a -> S1b -> S1c (stop on any criterion failure) -> S2 labelling and run -> decision. Total real calls ~76 minimum.
