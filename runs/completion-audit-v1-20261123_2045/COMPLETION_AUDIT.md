# Completion state audit

Snapshot: 2026-11-23T20:51:36+05:30

Registry positions: 100; accepted primary extraction records: 54; positions without an accepted primary extraction: 46; positions certified complete against the current requirements: 0.

## Reconciled status totals

| Current dataset status | Positions |
|---|---:|
| BLOCKED_C_identity_review | 7 |
| BLOCKED_D_retrieval_gap | 2 |
| COMPLETED_BASELINE | 25 |
| COMPLETED_BASELINE_QUARANTINED | 1 |
| EXCLUDED_IDENTITY_UNRESOLVED | 2 |
| EXTRACTED_batchA | 22 |
| EXTRACTED_batchB | 2 |
| EXTRACTED_corrected5 | 5 |
| EXTRACTION_FAILED_INVALID_JSON | 1 |
| HELD_IDENTITY_PROVISIONAL | 2 |
| HELD_NEO4J_OPTION_B_PREPARED | 1 |
| PAUSED_PROVIDER_QUOTA | 1 |
| UNPLANNED | 29 |

## Filesystem and ledger reconciliation

Filesystem: 26 baseline Pass 1 files exist, but one is quarantined Sherlock; 25 accepted baseline positions. Batch A has 22 numeric outputs and the separate #71 invalid-JSON attempt. Batch B has two numeric outputs (#30, #35) and a separate #37 daily-quota failure. The corrected-five run has five numeric outputs. These yield 54 accepted primary extraction positions.

The frozen v1f plan has 28 targets; 27 have accepted outputs and #71 failed. The older master coverage file predates later execution and lists 41 unplanned positions. Exactly 12 of those positions have since moved status: #30 and #35 extracted; #37 quota-paused; #68, #74, #86, #91, #92, #93, #98 identity-blocked; #83 and #99 retrieval-blocked. The remaining 29 are still unplanned. The execution ledger is a prospective plan for 75 Gemini calls, not an execution log. Its planned counts are not current completion status.

## Remaining 46 positions

| ID | Application | Current status | Identity status | Retrieval status |
|---:|---|---|---|---|
| 15 | Pylon | UNPLANNED | original_list_name | retrieval_available_not_extracted |
| 24 | Lark (Larksuite) | UNPLANNED | original_list_name | retrieval_available_not_extracted |
| 31 | Google Ads | UNPLANNED | original_list_name | retrieval_available_not_extracted |
| 37 | systeme.io | PAUSED_PROVIDER_QUOTA | original_list_name | retrieval_available_not_extracted |
| 40 | SendGrid | UNPLANNED | original_list_name | retrieval_available_not_extracted |
| 42 | WooCommerce | UNPLANNED | original_list_name | retrieval_available_not_extracted |
| 45 | Magento (Adobe Commerce) | UNPLANNED | original_list_name | retrieval_available_not_extracted |
| 48 | Gumroad | UNPLANNED | original_list_name | retrieval_available_not_extracted |
| 50 | fanbasis | EXCLUDED_IDENTITY_UNRESOLVED | excluded_unresolved | not_recorded_or_not_started |
| 54 | MrScraper | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 55 | Apify | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 57 | Bright Data | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 58 | Sherlock | COMPLETED_BASELINE_QUARANTINED | quarantined_identity | evidence_bundle_used |
| 59 | Waterfall.io | UNPLANNED | reconstructed_candidate_unverified | not_recorded_or_not_started |
| 60 | Clay | UNPLANNED | reconstructed_candidate_unverified | not_recorded_or_not_started |
| 64 | Cloudflare | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 66 | Neo4j | HELD_NEO4J_OPTION_B_PREPARED | reconstructed_candidate_unverified | not_recorded_or_not_started |
| 67 | Snowflake | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 68 | MongoDB Atlas | BLOCKED_C_identity_review | identity_review_blocked | identity_blocked_before_retrieval |
| 69 | Datadog | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 71 | Notion | EXTRACTION_FAILED_INVALID_JSON | reconstructed_candidate_unverified | not_recorded_or_not_started |
| 73 | Linear | HELD_IDENTITY_PROVISIONAL | held_provisional | not_recorded_or_not_started |
| 74 | Jira | BLOCKED_C_identity_review | identity_review_blocked | identity_blocked_before_retrieval |
| 77 | ClickUp | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 78 | Coda | HELD_IDENTITY_PROVISIONAL | held_provisional | not_recorded_or_not_started |
| 79 | Smartsheet | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 80 | Harvest | EXCLUDED_IDENTITY_UNRESOLVED | excluded_unresolved | not_recorded_or_not_started |
| 81 | Stripe | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 82 | Plaid | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 83 | Binance | BLOCKED_D_retrieval_gap | identity_review_pending | partial_retrieval_identity_review |
| 85 | iPayX | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 86 | QuickBooks | BLOCKED_C_identity_review | identity_review_blocked | identity_blocked_before_retrieval |
| 87 | Xero | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 88 | Brex | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 89 | Ramp | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 90 | PitchBook | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 91 | NotebookLM | BLOCKED_C_identity_review | identity_review_blocked | identity_blocked_before_retrieval |
| 92 | Otter AI | BLOCKED_C_identity_review | identity_review_blocked | identity_blocked_before_retrieval |
| 93 | Fathom | BLOCKED_C_identity_review | identity_review_blocked | retrieval_available_not_extracted |
| 94 | Consensus | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 95 | Reducto | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 96 | Devin | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 97 | higgsfield | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |
| 98 | Mermaid CLI | BLOCKED_C_identity_review | identity_review_blocked | identity_blocked_before_retrieval |
| 99 | YouTube Transcript | BLOCKED_D_retrieval_gap | identity_review_pending | retrieval_gap |
| 100 | Grain | UNPLANNED | reconstructed_candidate_unverified | retrieval_available_not_extracted |

## Identity and quota blockers

The original Notion URL is inaccessible through the normal reader. No alternate access path was attempted and no registry entries were changed. No ID was marked membership-verified by this audit. IDs 1–50 retain their existing original-list attribution but were not rechecked against Notion. IDs 51–100 remain reconstructed candidates; official product documentation cannot establish which products the assignment intended. An authoritative list export is required before correcting or certifying those positions.

No research process is active. Groq is paused after a daily-quota 429; the last recorded Retry-After does not establish daily token availability. The 180K user-set soft cap had already been exceeded. Do not resume model generation until actual remaining quota and a safe token budget are established.

This audit made one normal-reader attempt to open the supplied Notion URL; it was inaccessible. It made no official documentation retrievals, model generation calls, registry edits, deployment, or publication.
