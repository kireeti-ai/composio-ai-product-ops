# Reconciliation: 46 newly researched positions (2026-11-23/24)

Full by-app, by-claim table (original earlier claim, current verdict, quotation + source, re-fetch result, whether the quotation covers the claim, remaining uncertainty): `RECONCILIATION.csv`. Machine-readable: `CONSOLIDATED.json`.

Method: 4 subagents opened real pages and saved page text + quote hashes (batch1-4/records.json); every quote was re-fetched independently by `refetch.py` (snapshots under batchN/refetch/, originals untouched); claim-level support was judged by model reviewers (relevance_v2/); `consolidate.py` merged them with the six Codex records (quote hashes + page re-fetch in runs/codex-evidence-validation-v1-20261123_2359). **All judgements are model-made. No human has labelled anything.**

| Measure | Count |
|---|---|
| Positions covered (40 new + 6 Codex) | 46 |
| Claims | 332 |
| Claims with >=1 quotation | 265 |
| Distinct quotations (by URL + hash) | 424 |
| Quotes reproduced on re-fetch | 411 of 424 |
| Supported by an official quotation (all components covered) | 112 |
| Partially supported | 118 |
| Researcher judgement from quoted facts (buildability) | 17 |
| Conflicting between sources | 4 |
| Unresolved (not reproduced 4, quote does not support 3, Codex-kept 5) | 12 |
| Unknown / not verified | 69 |
| Positions with >=1 officially supported claim | 41 of 46 |

Not reproduced on re-fetch: Datadog (8 quotes; live page content differs from the saved copy), Neo4j query-API page (1), MrScraper MCP page (1), Consensus MCP endpoint (401, 1), 2 Codex quotes that are not verbatim.
Known caveats: Otter, PitchBook, Consensus docs and Grain intro were 403 to automated fetching; Binance quotes come from its official GitHub docs repo; iPayX evidence is vendor self-published; Neo4j "official" MCP is inferred from the vendor docs domain; Paygent (historical record) stays identity-unresolved.
Earlier search-summary errors corrected: Snowflake (trial needs no card), Datadog (preview allow-listing not found), Jira/ClickUp (MCP auth restrictions not found in official pages), Bright Data (Bearer header confirmed), Cloudflare (official MCP confirmed), Consensus (official API + MCP exist), Reducto ($150 free usage, not 15,000 credits), QuickBooks/Xero (official MCP repos), Plaid (Development environment replaced).

## Historical 229 flagged claims (model-reviewed, not human-verified)
supported 137, partially supported 51, unsupported 27, conflicting 12, unverifiable 2 (outputs in runs/claim-review-v1-20261123_2359/). Original extractions are untouched.

## Records still needing human review
All 100 positions: no human labelling exists. Priority: 12 conflicting + 27 unsupported historical claims, the 12 unresolved and 4 conflicting new claims, Paygent identity.
