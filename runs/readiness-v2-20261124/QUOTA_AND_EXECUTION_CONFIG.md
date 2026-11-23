# Quota use and execution configuration (documentation only; nothing has been executed)

## Principles
- **One key per provider, never rotated to bypass quotas.** Gemini: `GEMINI_API_KEY` only. Groq: `GROQ_API_KEY` only. Quotas are enforced per Google Cloud project, not per key, so a second key would not add capacity anyway; using another account/project to circumvent a limit is not done. `GEMINI_API_KEY_2` and the OpenRouter key are unused by any executable script (the legacy rotation path was removed from the working copy and the legacy scripts refuse to run). Recommendation: delete both from `.env`.
- **No spending, provider change or billing change without your explicit approval.** If a quota is exhausted the run stops and resumes later; escalation options (waiting for the reset, a billing upgrade, another provider) are your decision.

## Gemini (extraction; frozen runner `src/run_p1.py` v6, Neo4j via `src/run_neo4j_surfaces.py`)
- **Gate:** no call without `APPROVED.json` containing `models`, `cap_per_model` (mandatory for every model) and `phases`. v1f is hash-frozen; the runner refuses if the plan or runner changed.
- **Counting:** every attempt (including retries and failures) counts against the per-model cap. Per app: up to 3 attempts per model, only for rate (429 per-minute) and transient (5xx/timeout) errors, with 15/30 s waits.
- **Daily quota:** the FIRST per-day 429 marks that model exhausted (no retry loop). The run falls back to the next approved model, and stops with `STOPPED.json` (`quota_or_cap_exhausted`) when none is left. Finished records are read-only; a later run resumes without regenerating them.
- **Learning the real limits:** the first 429 body is written to `logs/run.jsonl` (`model_exhausted`, first 200 characters) so the real limit can be read from the log. The active limits must be checked in AI Studio before approval (last observed: 20 requests/day on one model for one project; the other model's number was never seen). Reset: midnight Pacific = 13:30 IST while Pacific is on standard time.
- **Models:** `gemini-2.5-flash` may be withdrawn for this project; `gemini-3.5-flash` is the fallback. Records carry their model, so mixed-model results stay separable.
- **Staging:** approve Phase 1 (15 apps) first; Phase 2 (13) and Neo4j (2) afterwards; the expansion waves (39 apps + 6 identity-gated) only after their retrieval and identity gates, as separately versioned runs.

## Groq (verification; `src/verify_v2.py`)
- **Gate:** no call without `<out>/APPROVED_PASS2.json` containing `max_calls`. The cap counts attempts, not just successes; size it for retries (observed baseline ratio: 1.71 attempts per call).
- **Pacing:** concurrency 1; on 429 it waits for `Retry-After` (capped 60 s) or an increasing backoff; after 5 failed attempts for one call it STOPS (`retries_exhausted`), checkpoints partial work atomically and exits. A rerun resumes from the checkpoint. No second key, no fallback provider.
- **Independent of Pass 1:** model family differs; evidence passages come from a deterministic retriever over ALL stored sources of the app/surface, not only Pass-1's cited quote; deterministic guardrails (absence is not contradiction, quote must be about the item and negate it, enum-semantics conflicts, OAuth wording, 'no credentials required', verbatim-quote requirement) run after every model answer. Verdicts are flags for human review, never ground truth.
- **Output location:** a writable run directory only; refuses `baseline/` and `work/`.

## Composio (free retrieval)
Free TinyFish tools only; every call asserts `instant_charge == 0`. Neo4j gap retrievals need `RETRIEVAL_APPROVED.json`.

## Verified by `src/check_execution_config.py` (19/19 PASS) and the test suites listed in EXECUTION_READINESS_v2.md.
