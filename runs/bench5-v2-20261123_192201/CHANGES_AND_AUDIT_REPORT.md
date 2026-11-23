# Benchmark v2: changes, offline tests, evidence audit, blockers
Created 2026-11-23T19:26:33+0530. Versioned on top of `runs/bench5-v1-20261123_191136/` (not modified; hashes verified by test20). No Groq/Gemini generation calls were made for this report. One OpenRouter probe request was made (below). No paid access, deployment, publication, or `APPROVED.json`.

## 1. OpenRouter circuit breaker and backoff (implemented, bench2.py)
- **Backoff:** 30 s floor (provider `retry_after: 1 s` can no longer shorten it), doubling per consecutive failure, capped at 300 s. `retry_after_seconds` is read from the response body as well as the header.
- **Breaker:** 2 consecutive rate-limit/5xx/network failures -> OPEN (cooldown 600 s, doubling to 3600 s) -> after cooldown exactly ONE probe -> success closes / failure reopens with doubled cooldown; after 3 opens it gives up until a human resets. State persisted in `breaker.json`. Ambiguous 429 and client errors stop the provider for human review.
- **Seeded** OPEN from the v1 log (5 consecutive upstream 429 `fleet_capacity_exhausted`). The five failed requests were NOT rerun.
- **Minimum spacing** between requests added (OpenRouter 10 s, Gemini 13 s).
- **Controlled probe after cooldown: made once -> HTTP 429 (rate_limit) again.** Breaker reopened, cooldown now 1200 s, opens=2. OpenRouter remains unavailable; no further requests until the breaker allows it and you approve the five-app run.
- Bugs found and fixed while doing this (both caught before any harm): a granted-but-unsent probe was being consumed (first probe attempt sent NO request); log hash-chain restarted in each process (now continues).

## 2. Gemini 2.5 Flash benchmark prepared for 2026-11-24 after 13:30 IST
`python bench2.py gemini25` refuses before 2026-11-24 08:00 UTC (it did so when tested, no call made). After the reset it sends ONE small structured capability request; only if that succeeds (HTTP 200, valid JSON, model identity matches `gemini-2.5-flash`) does it run the five-app benchmark (cap 5, 13 s spacing, breaker and quota checks, stop on daily quota). Total budget 6 of 20 daily requests. A capability failure blocks the benchmark. Not scheduled or run; you start it.

## 3. Evidence validation v2 (validate_v2)
Rejected as evidence: placeholder quotes ("unknown", "none", <20 chars / <4 words), ellipsis-stitched quotes, quotes not contiguous in the CITED page (catches stitched, unrelated, paraphrased), URLs not in the sources. Every non-unknown claim needs a valid quote whose text mentions item-specific terms (`supported_lexical`, a lexical check, NOT semantic correctness); `other` needs a human. States kept separate: `unknown` (sources silent) vs `not_found_in_provided_evidence` (MCP `none_found`; explicitly NOT a claim that no MCP exists). Absence is never inferred from search failure.

## 4. Audit of the five Groq v1 outputs against full evidence (offline, deterministic; not human ground truth)
v1's lenient check passed 18/24 quotes; v2 passes **17/24**. Issue counts: {'placeholder_or_too_short': 4, 'stitched_ellipsis': 3, 'too_long': 0, 'url_not_in_sources': 2, 'not_contiguous_in_cited_page': 4, 'not_in_shown_evidence': 0}. Claim states across 5 apps: {'unsupported': 10, 'supported_lexical': 12, 'not_found_in_provided_evidence': 4}.

| app | v1 existing_mcp | MCP mentions in FULL evidence | in evidence shown to model | valid evidence | claim states |
|---|---|---|---|---|---|
| 27 Telegram | none_found | 0 | 0 | 2/5 | unsupported:3, supported_lexical:1, not_found_in_provided_evidence:1 |
| 32 Meta Ads | none_found | 0 | 0 | 3/4 | unsupported:2, supported_lexical:1, not_found_in_provided_evidence:1 |
| 41 Shopify | official | 2 | 2 | 4/4 | supported_lexical:4, unsupported:2 |
| 53 Ahrefs | none_found | 3 | 0 | 2/4 | supported_lexical:2, unsupported:1, not_found_in_provided_evidence:1 |
| 61 GitHub | none_found | 0 | 0 | 6/7 | supported_lexical:4, unsupported:2, not_found_in_provided_evidence:1 |

Findings:
- **Ahrefs: v1 `none_found` is contradicted by the stored evidence.** The page docs.ahrefs.com/ lists an MCP section ("connect your Ahrefs data to AI assistants and agents", Claude/ChatGPT setup). The model never saw it: **reduction-v1 dropped all 3 mentions.** This is a reduction defect, not a Groq failure. Do not use the v1 Ahrefs `existing_mcp`.
- **GitHub: the stored evidence contains NO MCP mention at all.** `none_found` therefore only means "not in the evidence provided"; it says nothing about whether GitHub has an MCP server. The cited "quote" was an unrelated pricing sentence stitched with an ellipsis. Needs retrieval of the right page (retrieval requires your approval). The GitHub auth quotes cite versioned GitHub Enterprise Server docs (`/enterprise/11.10.340/`), i.e. a possibly stale product-version page, and the `self_serve_free` claim cites only "Click Generate new token." (no statement about cost) -> unsupported.
- **Shopify `official`:** supported by a verbatim quote ("Shopify MCP lets merchants and partners set up and manage a store...") from shopify.dev. `api_key` and `self_serve_free` unsupported.
- **Telegram / Meta Ads:** `existing_mcp` evidence was the word "unknown" (rejected); Telegram `oauth2`/`api_key`/`rest` and Meta `oauth2`/`rest` lack a valid item-specific quote (quotes stitched, or "access token" without OAuth wording). Each needs human labelling; I make no correctness judgement.
- Overall: the 5 v1 outputs remain preserved and unchanged; none should be treated as accurate. All 5 need independent human labelling.

**Reduction-v2 (implemented, versioned; NOT yet applied to any model call):** keeps ±350 chars around every MCP mention in addition to reduction-v1 blocks. MCP mentions in full / v1-shown / v2-shown:

| app | full | v1 | v2 |
|---|---|---|---|
| Telegram | 0 | 0 | 0 |
| Meta Ads | 0 | 0 | 0 |
| Shopify | 2 | 2 | 3 |
| Ahrefs | 3 | 0 | 3 |
| GitHub | 0 | 0 | 0 |

Any model rerun using reduction-v2 needs a new benchmark run (a Groq call per app); not done.

## 5. Groq daily token limit
- Response headers (6 per call, inspected across all recorded observations) carry only `x-ratelimit-limit-requests` (=1000, daily requests), `limit-tokens` (=8000, per-minute tokens) and the matching remaining/reset fields. **No header exposes a daily token limit; it cannot be established from headers.**
- Groq's published rate-limit page (https://console.groq.com/docs/rate-limits, fetched this session) lists the free-tier row for `openai/gpt-oss-120b` as RPM 30, RPD 1K, TPM 8K, **TPD 200K**. RPD and TPM match what we observed, which corroborates the table, but the 200K TPD is a *documented* value, not confirmed for this organization; the Groq console limits page is the authority. Treated as "documented, unverified": the quota manager now enforces it as a soft 90% cap (Quota2).
- Measured use: the 5-app benchmark used 13,899 tokens (about 2.8k per app, reduced evidence). At that size the documented 200K/day is about 70 extractions/day on one bucket; full-evidence prompts (~8.5k tokens in) would be about 20/day. Verification (about 411-703 calls at roughly 1.3k tokens each, an estimate) is about 0.5-0.9M tokens = 3-5 days on one bucket.

## 6. P2-P4
Hard-disabled in bench2: `secret()` raises PermissionError for GROQ_KEY_P1..P4 (P1 is same org as GROQ_API_KEY and adds no capacity). Never read, tested. They stay in `.env` (not deleted) until you authorize.

## 7. Offline tests
bench2: 25 tests OK (breaker/backoff, probe semantics, spacing, validation v2, unknown vs not-found, Gemini gating and capability-first, reduction v2, P2-P4 disabled, TPD cap, v1 files unchanged by hash, frozen hashes, no APPROVED). Also re-run: bench v1 25 OK, runner v7 26 OK. Captured in `reports/`.

## 8. Remaining blockers
1. OpenRouter unavailable: upstream capacity 429 on 6 consecutive requests; breaker open (cooldown 1200 s). Your approval needed before the OpenRouter 5-app run.
2. Gemini 2.5: wait until 2026-11-24 13:30 IST, then you start the staged run; Gemini 3.6 generation unverified (timeouts).
3. Groq TPD (200K) is documented-only; confirm in the Groq console.
4. Evidence gaps: GitHub MCP page not in the evidence; Ahrefs needs reduction-v2 rerun. Retrieval needs your approval.
5. P2-P4 authorization pending.
6. All accuracy claims still need independent human labels (0 so far).
