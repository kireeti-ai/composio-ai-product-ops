# Offline audit of accepted primary records

Audited 54 accepted records from the preserved v4 dataset.

This is a deterministic source-quote and source-URL audit only. It does not establish factual correctness or model accuracy. No network or model calls were made.

## Results

- Evidence items: 262
- Lexically valid evidence items: 174
- Claim states: `{"needs_human": 2, "not_found_in_provided_evidence": 27, "supported_lexical": 124, "unknown": 2, "unsupported": 143}`
- Evidence issue counts: `{"not_contiguous_in_cited_page": 74, "not_in_shown_evidence": 3, "placeholder_or_too_short": 29, "stitched_ellipsis": 30, "url_not_in_sources": 3}`

## Records with evidence issues

| ID | App | Version | Evidence items | Valid | Issues |
|---:|---|---|---:|---:|---|
| 1 | Salesforce | baseline_p1_v1 | 7 | 6 | not_contiguous_in_cited_page: 1 |
| 2 | HubSpot | baseline_p1_v1 | 9 | 8 | not_contiguous_in_cited_page: 1, stitched_ellipsis: 1 |
| 3 | Pipedrive | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 5 | Twenty | baseline_p1_v1 | 4 | 2 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1, stitched_ellipsis: 1 |
| 6 | Podio | baseline_p1_v1 | 7 | 5 | not_contiguous_in_cited_page: 2, placeholder_or_too_short: 1 |
| 9 | Copper | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 10 | DealCloud | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 11 | Zendesk | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 13 | Freshdesk | baseline_p1_v1 | 4 | 2 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 2 |
| 14 | Front | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 16 | LiveAgent | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 18 | Help Scout | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 19 | Gorgias | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 20 | Gladly | batchA | 5 | 3 | not_contiguous_in_cited_page: 2 |
| 23 | Zoho Cliq | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 25 | Pumble | batchA | 4 | 2 | not_contiguous_in_cited_page: 2, stitched_ellipsis: 2 |
| 26 | Discord | batchA | 4 | 1 | not_contiguous_in_cited_page: 3, stitched_ellipsis: 2 |
| 27 | Telegram | corrected5 | 5 | 2 | not_contiguous_in_cited_page: 3, placeholder_or_too_short: 1, stitched_ellipsis: 2 |
| 28 | WhatsApp Business | baseline_p1_v1 | 7 | 5 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1, stitched_ellipsis: 1 |
| 29 | Aircall | batchA | 4 | 2 | not_contiguous_in_cited_page: 2, stitched_ellipsis: 1 |
| 30 | Vonage | batchB | 5 | 4 | not_contiguous_in_cited_page: 1, stitched_ellipsis: 1 |
| 32 | Meta Ads | corrected5 | 4 | 1 | not_contiguous_in_cited_page: 1, not_in_shown_evidence: 2, placeholder_or_too_short: 1 |
| 33 | LinkedIn Ads | batchA | 5 | 4 | not_contiguous_in_cited_page: 1 |
| 34 | GoHighLevel | batchA | 4 | 3 | not_contiguous_in_cited_page: 1 |
| 35 | Mailchimp | batchB | 6 | 1 | not_contiguous_in_cited_page: 5, stitched_ellipsis: 2 |
| 36 | Klaviyo | batchA | 4 | 3 | not_contiguous_in_cited_page: 1, stitched_ellipsis: 1 |
| 38 | Pinterest | batchA | 4 | 0 | not_contiguous_in_cited_page: 4, placeholder_or_too_short: 1 |
| 39 | Threads (Meta) | batchA | 4 | 3 | placeholder_or_too_short: 1, url_not_in_sources: 1 |
| 41 | Shopify | corrected5 | 7 | 6 | not_contiguous_in_cited_page: 1, stitched_ellipsis: 1 |
| 43 | BigCommerce | batchA | 6 | 1 | not_contiguous_in_cited_page: 5, placeholder_or_too_short: 1, stitched_ellipsis: 2 |
| 44 | Salesforce Commerce Cloud | batchA | 5 | 2 | not_contiguous_in_cited_page: 3, stitched_ellipsis: 2 |
| 46 | Squarespace | batchA | 5 | 4 | not_contiguous_in_cited_page: 1, stitched_ellipsis: 1 |
| 47 | Ecwid | batchA | 5 | 3 | not_contiguous_in_cited_page: 2, placeholder_or_too_short: 2 |
| 49 | Amazon Selling Partner | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 51 | DataForSEO | baseline_p1_v1 | 4 | 3 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 52 | SE Ranking | batchA | 4 | 3 | placeholder_or_too_short: 1 |
| 53 | Ahrefs | corrected5 | 4 | 3 | not_contiguous_in_cited_page: 1, stitched_ellipsis: 1 |
| 56 | Firecrawl | batchA | 5 | 2 | not_contiguous_in_cited_page: 3, stitched_ellipsis: 3 |
| 63 | Netlify | batchA | 5 | 2 | not_contiguous_in_cited_page: 3, stitched_ellipsis: 2 |
| 65 | Supabase | batchA | 6 | 3 | not_contiguous_in_cited_page: 3, stitched_ellipsis: 2 |
| 70 | Sentry | batchA | 6 | 4 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1 |
| 72 | Airtable | batchA | 6 | 2 | not_contiguous_in_cited_page: 3, placeholder_or_too_short: 1, url_not_in_sources: 1 |
| 75 | Asana | batchA | 5 | 1 | not_contiguous_in_cited_page: 3, not_in_shown_evidence: 1, stitched_ellipsis: 1 |
| 76 | Monday.com | batchA | 4 | 2 | not_contiguous_in_cited_page: 1, placeholder_or_too_short: 1, url_not_in_sources: 1 |
| 84 | Paygent Connect | baseline_p1_v1 | 6 | 3 | placeholder_or_too_short: 2, stitched_ellipsis: 1 |

## Limitations

- A matching contiguous quotation is not proof that the quotation entails the claim.
- Source URLs were checked against saved page ledgers, not refetched in this audit.
- No independent human labels are available; accuracy remains unmeasured.
