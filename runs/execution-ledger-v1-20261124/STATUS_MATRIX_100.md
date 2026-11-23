# Exact 100-app status matrix

**Provenance is kept separate.** Block 1 = apps 1-50: read from the ORIGINAL Notion page's public data (membership verified at fetch time). Block 2 = apps 51-100: a RECONSTRUCTED secondary list; names, categories and order are NOT verified against the original Notion table and carry no website hints.

## Cross-tab: status x provenance

| Status | Original list (1-50) | Reconstructed list (51-100) | Total |
|---|---|---|---|
| COMPLETED_BASELINE | 23 | 2 | 25 |
| COMPLETED_BASELINE_QUARANTINED | 0 | 1 | 1 |
| EXCLUDED_IDENTITY_UNRESOLVED | 1 | 1 | 2 |
| HELD_IDENTITY_PROVISIONAL | 0 | 2 | 2 |
| HELD_NEO4J_OPTION_B_PREPARED | 0 | 1 | 1 |
| PLANNED_FROZEN_V1F | 16 | 12 | 28 |
| UNPLANNED | 10 | 31 | 41 |
| **Total** | **50** | **50** | **100** |

## Cross-tab: Gemini call group x provenance (75 proposed calls over 74 apps)

| Group | Original | Reconstructed | Apps | Calls |
|---|---|---|---|---|
| A_v1f_frozen | 16 | 12 | 28 | 28 |
| B_neo4j_optionB | 0 | 1 | 1 | 2 |
| C_expansion | 10 | 29 | 39 | 39 |
| D_identity_gated | 1 | 5 | 6 | 6 |
| E_baseline_record_exists_no_new_gemini_call | 23 | 3 | 26 | 0 |

## Block 1 - ORIGINAL Notion list (1-50), membership verified

| ID | App | Status | Plan reference | Gemini call(s) | Flags |
|---|---|---|---|---|---|
| 1 | Salesforce | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | baseline_record_written_twice(final version verified) |
| 2 | HubSpot | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | baseline_record_written_twice(final version verified) |
| 3 | Pipedrive | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | baseline_record_written_twice(final version verified) |
| 4 | Attio | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 5 | Twenty | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | baseline_record_written_twice(final version verified) |
| 6 | Podio | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 7 | Zoho CRM | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 8 | Close | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 9 | Copper | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 10 | DealCloud | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 11 | Zendesk | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 12 | Intercom | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 13 | Freshdesk | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 14 | Front | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | baseline_record_weak_sources(dev.frontapp.com never fetched) |
| 15 | Pylon | UNPLANNED | p1-expansion-v1 3B_partial_targeted_reretrieval | G045 | - |
| 16 | LiveAgent | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 17 | Plain | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 18 | Help Scout | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 19 | Gorgias | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 20 | Gladly | PLANNED_FROZEN_V1F | p1-v1f phase 2 (D_added_access_explicit_account_gated) | G028 | - |
| 21 | Slack | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 22 | Twilio | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 23 | Zoho Cliq | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 24 | Lark (Larksuite) | UNPLANNED | p1-expansion-v1 3B_partial_targeted_reretrieval | G046 | - |
| 25 | Pumble | PLANNED_FROZEN_V1F | p1-v1f phase 2 (C_access_partial) | G025 | - |
| 26 | Discord | PLANNED_FROZEN_V1F | p1-v1f phase 2 (C_access_partial) | G023 | - |
| 27 | Telegram | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G001 | - |
| 28 | WhatsApp Business | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 29 | Aircall | PLANNED_FROZEN_V1F | p1-v1f phase 2 (C_access_partial) | G020 | - |
| 30 | Vonage | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G031 | - |
| 31 | Google Ads | UNPLANNED | p1-expansion-v1 3B_partial_targeted_reretrieval | G047 | - |
| 32 | Meta Ads | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G002 | - |
| 33 | LinkedIn Ads | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G003 | - |
| 34 | GoHighLevel | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G004 | - |
| 35 | Mailchimp | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G032 | - |
| 36 | Klaviyo | PLANNED_FROZEN_V1F | p1-v1f phase 2 (B_access_inferred_self_serve) | G019 | - |
| 37 | systeme.io | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G033 | - |
| 38 | Pinterest | PLANNED_FROZEN_V1F | p1-v1f phase 2 (B2_topup_access_explicit_phase2) | G016 | - |
| 39 | Threads (Meta) | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G005 | - |
| 40 | SendGrid | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G034 | - |
| 41 | Shopify | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G006 | - |
| 42 | WooCommerce | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G035 | - |
| 43 | BigCommerce | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G007 | - |
| 44 | Salesforce Commerce Cloud | PLANNED_FROZEN_V1F | p1-v1f phase 2 (C_access_partial) | G022 | - |
| 45 | Magento (Adobe Commerce) | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G036 | - |
| 46 | Squarespace | PLANNED_FROZEN_V1F | p1-v1f phase 2 (C_access_partial) | G027 | - |
| 47 | Ecwid | PLANNED_FROZEN_V1F | p1-v1f phase 2 (C_access_partial) | G021 | - |
| 48 | Gumroad | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G037 | - |
| 49 | Amazon Selling Partner | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | - |
| 50 | fanbasis | EXCLUDED_IDENTITY_UNRESOLVED | excluded pending authoritative identity resolution | G073 | - |

## Block 2 - RECONSTRUCTED list (51-100), membership NOT verified

| ID | App | Status | Plan reference | Gemini call(s) | Flags |
|---|---|---|---|---|---|
| 51 | DataForSEO | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | RECONSTRUCTED |
| 52 | SE Ranking | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G008 | RECONSTRUCTED |
| 53 | Ahrefs | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G009 | RECONSTRUCTED |
| 54 | MrScraper | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G038 | RECONSTRUCTED |
| 55 | Apify | UNPLANNED | p1-expansion-v1 3B_partial_targeted_reretrieval | G048 | RECONSTRUCTED |
| 56 | Firecrawl | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G010 | RECONSTRUCTED |
| 57 | Bright Data | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G039 | RECONSTRUCTED |
| 58 | Sherlock | COMPLETED_BASELINE_QUARANTINED | baseline Pass 1 + Pass 2 exist | - | RECONSTRUCTED;baseline_record_identity_contaminated_QUARANTINED |
| 59 | Waterfall.io | UNPLANNED | p1-expansion-v1 3H_provisional_identity_hold | G074 | RECONSTRUCTED;identity_PROVISIONAL_not_confirmed |
| 60 | Clay | UNPLANNED | p1-expansion-v1 3H_provisional_identity_hold | G075 | RECONSTRUCTED;identity_PROVISIONAL_not_confirmed |
| 61 | GitHub | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_topup_access_explicit) | G015 | RECONSTRUCTED |
| 62 | Vercel | PLANNED_FROZEN_V1F | p1-v1f phase 2 (B_access_inferred_self_serve) | G017 | RECONSTRUCTED |
| 63 | Netlify | PLANNED_FROZEN_V1F | p1-v1f phase 2 (B_access_inferred_self_serve) | G018 | RECONSTRUCTED |
| 64 | Cloudflare | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G040 | RECONSTRUCTED |
| 65 | Supabase | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_topup_access_explicit) | G012 | RECONSTRUCTED |
| 66 | Neo4j | HELD_NEO4J_OPTION_B_PREPARED | p1-neo4j-optionB (2 surface calls), outside the 28 | G029,G030 | RECONSTRUCTED |
| 67 | Snowflake | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G041 | RECONSTRUCTED |
| 68 | MongoDB Atlas | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G042 | RECONSTRUCTED |
| 69 | Datadog | UNPLANNED | p1-expansion-v1 3B_partial_targeted_reretrieval | G049 | RECONSTRUCTED |
| 70 | Sentry | PLANNED_FROZEN_V1F | p1-v1f phase 2 (C_access_partial) | G024 | RECONSTRUCTED |
| 71 | Notion | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_topup_access_explicit) | G014 | RECONSTRUCTED |
| 72 | Airtable | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_topup_access_explicit) | G013 | RECONSTRUCTED |
| 73 | Linear | HELD_IDENTITY_PROVISIONAL | held pending identity confirmation (no authority for #51-100) | G070 | RECONSTRUCTED |
| 74 | Jira | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G043 | RECONSTRUCTED |
| 75 | Asana | PLANNED_FROZEN_V1F | p1-v1f phase 2 (C_access_partial) | G026 | RECONSTRUCTED |
| 76 | Monday.com | PLANNED_FROZEN_V1F | p1-v1f phase 1 (A_prior_access_evidence_sufficient) | G011 | RECONSTRUCTED |
| 77 | ClickUp | UNPLANNED | p1-expansion-v1 3A_core_ready_access_topup | G044 | RECONSTRUCTED |
| 78 | Coda | HELD_IDENTITY_PROVISIONAL | held pending identity confirmation (no authority for #51-100) | G071 | RECONSTRUCTED |
| 79 | Smartsheet | UNPLANNED | p1-expansion-v1 3B_partial_targeted_reretrieval | G050 | RECONSTRUCTED |
| 80 | Harvest | EXCLUDED_IDENTITY_UNRESOLVED | excluded pending authoritative identity resolution | G072 | RECONSTRUCTED |
| 81 | Stripe | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G051 | RECONSTRUCTED |
| 82 | Plaid | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G052 | RECONSTRUCTED |
| 83 | Binance | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G053 | RECONSTRUCTED |
| 84 | Paygent Connect | COMPLETED_BASELINE | baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags) | - | RECONSTRUCTED |
| 85 | iPayX | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G054 | RECONSTRUCTED |
| 86 | QuickBooks | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G055 | RECONSTRUCTED |
| 87 | Xero | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G056 | RECONSTRUCTED |
| 88 | Brex | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G057 | RECONSTRUCTED |
| 89 | Ramp | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G058 | RECONSTRUCTED |
| 90 | PitchBook | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G059 | RECONSTRUCTED |
| 91 | NotebookLM | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G060 | RECONSTRUCTED |
| 92 | Otter AI | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G061 | RECONSTRUCTED |
| 93 | Fathom | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G062 | RECONSTRUCTED |
| 94 | Consensus | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G063 | RECONSTRUCTED |
| 95 | Reducto | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G064 | RECONSTRUCTED |
| 96 | Devin | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G065 | RECONSTRUCTED |
| 97 | higgsfield | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G066 | RECONSTRUCTED |
| 98 | Mermaid CLI | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G067 | RECONSTRUCTED |
| 99 | YouTube Transcript | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G068 | RECONSTRUCTED |
| 100 | Grain | UNPLANNED | p1-expansion-v1 4_no_retrieval_full_discovery | G069 | RECONSTRUCTED |
