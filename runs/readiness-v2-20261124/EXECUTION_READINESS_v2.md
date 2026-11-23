# Execution readiness v2 - full 100-app scope (offline preparation; NOTHING executed)
No Gemini or Groq call has been made for any new work, no approval file exists, no deployment, no extraction process is running. v1f and all earlier run versions are unchanged and hash-verified (`CONFIG_CHECK.json`, 19/19).

## 1. Coverage of all 100 registry apps (`runs/master-coverage-v1-20261124/`)
| Status | Apps |
|---|---|
| COMPLETED_BASELINE (Pass 1 + old Pass 2) | 25 |
| COMPLETED_BASELINE_QUARANTINED (#58 Sherlock, identity-contaminated) | 1 |
| PLANNED_FROZEN_V1F | 28 |
| HELD (Neo4j Option B prepared; Linear, Coda identity) | 3 |
| EXCLUDED (Harvest, fanbasis: identity unresolved) | 2 |
| UNPLANNED -> now planned as separately versioned expansion (`runs/p1-expansion-v1-20261124/`) | 41 |
Every ID 1..100 appears exactly once (hard-checked). Provenance: apps 1-50 verified from the original Notion page's data; apps 51-100 are a reconstructed secondary list, membership NOT verified (31 of the 41 expansion apps are reconstructed).
Expansion waves: **3A** 14 cached-retrieval apps needing an access top-up; **3B** 6 partial retrievals needing targeted re-retrieval; **3H** 2 provisional-identity holds (Waterfall.io, Clay); **4** 19 apps with no retrieval at all (Finance 81-90, AI/media 91-100). Nothing in the expansion is extractable until its retrieval, relevance audit and identity gates pass.

## 2. Changes since the last report
- Master coverage + expansion plan (item 1). Neo4j gap-retrieval plan, gated, nothing fetched (item 2: Aura authentication page; Query API page + one conditional targeted search; Aura availability page; max 5 free external calls; the exact Query API "Authorize requests" URL is not in stored data).
- **Pass 2 verifier v2** (item 3): nested + per-surface + frozen shapes; reads sources from any run, writes only to a writable run directory; independent deterministic retrieval; guardrails. All 8 known false-positive "contradicted" verdicts of the old verifier are regression tests: 4 enum-semantics conflicts (`rest` + `sdk_or_cli_only`), Front 'beta' vs 'official', Amazon (quote not about MCP), WhatsApp OAuth wording, Sherlock 'no credentials required'. An adversarial fake model that insists "contradicted" on everything produced 0 surviving false positives after one gap (Twenty/`access`) found during development was fixed and added as a test.
- Human-evaluation protocol v2 FINAL (item 4): independent labelling, calibration, agreement (kappa / Jaccard), blind adjudication, truth freeze, THEN unlock model outputs, field-level scoring; Frame C (12 of the 41 expansion apps) added; 0 labels exist.
- Execution configuration (item 6): legacy scripts neutralised, rotation path removed, config check 19/19, quota document.

## 3. Test and validation evidence (all offline, fake model functions)
eval_score 12; eval_agreement 6; verify_v2 13; runner v1f suite (34 PASS lines + Gladly checks); Neo4j runner suite (13 checks); registry validation 17/17; schema migration 26/26 lossless; secret audit clean; dry runs: v1f 28 apps / 167 pages, Neo4j 2 calls / 5 pages, verifier 26 baseline records / <=103 Groq calls.

## 4. Model-call estimate for all 100 apps (`CALL_ESTIMATE.json`)
| | Minimum | Expected | Worst case |
|---|---|---|---|
| **Gemini extraction** | **75** = 28 (v1f) + 2 (Neo4j) + 39 (expansion 3A/3B/4) + 6 (identity-gated after confirmation) | 87 (assumes 15% transient retries; replace with observed) | 225 (3 attempts each); 450 with both models failing |
| Optional extra | +2 re-extractions of defective baseline records (#58, #14) and ~+15 for a corrected pass on ~20% of new records -> up to ~92 | | |
| **Groq verification** | **401** = 75 new records x ~3.96 field calls + re-verify the 26 baseline records | 687 attempts (observed baseline retry ratio 1.71) ~ 0.67M tokens | 2005 (5 attempts each) |
| Composio retrieval (free, $0 asserted) | ~372 | ~558 | - |
Days needed depend on UNVERIFIED daily caps. Gemini, 75 calls: with 2 models at 20/day each = 2 days (expected 3, worst 6); at 50/day = 1 day; one model only at 20/day = 4 days (expected 5). Groq tokens (hypothetical daily caps, not data): 100k/day = 7 days, 250k = 3, 500k = 2, 1M = 1.
The 26 baseline apps need 0 Gemini calls (records exist, with known defects); the count falls if some apps' retrieval proves unusable.

## 5. Blockers
1. Your approval + active Gemini limits, models and per-model caps (after 13:30 IST). Groq `max_calls` sized for ~700+ attempts.
2. Identity: Sherlock, Harvest, fanbasis (excluded); Linear, Coda, Waterfall.io, Clay (held/provisional); membership of apps 51-100 against the original Notion table (31 expansion apps + 12 v1f targets + Neo4j). The original Notion page's hint column for #51-100, if you can paste it, resolves most of this.
3. Free retrievals needing approval: Neo4j gaps (<=5 calls) and the expansion retrievals (~300 calls for 41 apps); then relevance audit per app.
4. Human labelling needs two labelers and an adjudicator; no accuracy claim exists until then.
5. Not started: pattern analysis, HTML report, README, repo publication, live link, deployment (all need approval; the secret audit must pass before publishing).

## 6. Preserved gaps and provenance limitations
Registry provenance (above); V1 code reconstructed not byte-verified; baseline = 26 records across two Gemini models, ids 1,2,3,5 written twice, V0 smoke outputs deleted, #58 contaminated, #14 weak sources; 8 first-attempt URLs unrecovered; MCP candidate pages never fetched; Composio SDK itself never demonstrated (MCP + consumer key only); access states are provisional readings and the heuristic relevance check gave false negatives (Threads, Monday.com, Gladly's sandbox page); inferred-self-serve apps (Vercel, Netlify, Klaviyo) are never reported as confirmed; Gladly pricing unknown, MCP client-only; Groq verdicts are flags; Neo4j Query API call has one input page; the notion page may hold content after the first 50 apps' tables that was never read; keys pasted in chat persist in the session transcript store: rotate them.
