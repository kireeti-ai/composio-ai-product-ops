# Exact quota checks required BEFORE any model execution (documentation; nothing has been checked or executed)
Principles: no key rotation, no second account/project to get extra quota, no billing/provider change without your explicit approval. Limits are NOT assumed: the last observed Gemini figure (20 requests/day on one model, one project) is historical and may no longer apply. Quotas are per PROJECT, not per key.

## A. Gemini (after the 13:30 IST reset; reset rule = midnight Pacific)
| # | Check | How | Pass criterion | Evidence to keep |
|---|---|---|---|---|
| G1 | Identify the project behind `GEMINI_API_KEY` | AI Studio -> API keys: record project number (never the key) | one project, free or paid tier recorded | `limits_observed_gemini.json` (`project_number`, `tier`) |
| G2 | Confirm tier and that NO billing is attached (or that you approve spend) | AI Studio tier/billing view | free tier, or an explicit written spend approval and budget alert | tier field + screenshot hash |
| G3 | Read per-model limits and today's usage for EACH candidate model (`gemini-2.5-flash`, `gemini-3.5-flash`) | AI Studio rate-limit page: RPM, TPM, RPD, used today | all integers filled; `available_to_project` true/false per model | filled template |
| G4 | Model availability | prefer the AI Studio model list; an API `models.list` metadata call is a Google API call and needs your approval | each model confirmed usable by THIS project (the second account got a 404 'no longer available to new users' for 2.5-flash) | availability flag per model |
| G5 | RPM >= 15 | the frozen runner is sequential with no pacing (peak ~15 requests/min) | if RPM < 15: NO-GO until a paced runner version exists | `quota_plan.py` flag |
| G6 | TPM fits the real prompts | measured: avg ~8.5k input tokens per call, max ~17.4k (Netlify/Supabase/Vercel), ~238k tokens total for the 28 calls (`measured_inputs.json`) | TPM >= 15 x 8.5k = 127k for peak pacing, and TPM >= 18.5k for the largest single call; otherwise flag/NO-GO | `quota_plan.py` flags |
| G7 | Size the per-model caps | run `python src/quota_plan.py gemini limits_observed_gemini.json` | cap = floor(0.9 x (RPD - used today)) per model; Phase 1 needs ~18 attempts (15 x 1.15) | suggested caps (NOT an approval) |
| G8 | Decide the model order and phases | you decide; record in your approval | models listed in APPROVED.json order; per-model caps for EVERY model; phases (start with `[1]`) | your `APPROVED.json` |
| G9 | Reading the real limit during the run | the runner logs the first daily-quota 429 (`model_exhausted`, first 200 chars) | after a stop, record the real limit in a new `limits_observed_*` file before resuming | `logs/run.jsonl` |

## B. Groq (verification; verifier v2 and the pilot)
| # | Check | How | Pass criterion | Evidence |
|---|---|---|---|---|
| Q1 | Tier and model access | Groq console limits page, model `openai/gpt-oss-120b` | model listed and usable | `limits_observed_groq.json` |
| Q2 | Read RPM, RPD, TPM, TPD and today's usage | console limits page | all integers filled | filled template |
| Q3 | Compute `max_calls` and the pacing interval | `python src/quota_plan.py groq limits_observed_groq.json` | max_calls = floor(0.9 x min(RPD left, TPD left / 982 tokens)); it counts ATTEMPTS; `min_interval_s` = max(60/RPM, 982 x 60/TPM) | suggested values (NOT an approval) |
| Q4 | Use pacing | run through `src/verify_v2_paced.py` (reads `min_interval_s` from the approval file); verify_v2 is unchanged | interval enforced between calls; 429 backoff honours Retry-After; 5 failed tries stop the run | approval file |
| Q5 | Size to the work | pilot stage 1 = 28 calls (~48 attempts); pilot stage 2 = 48 (~82); full verification = 403 planned calls (~689 attempts) | the pilot first; scale only after the pilot criteria pass | `PILOT_PLAN.md` |

## C. Composio (free retrieval)
Free only: every call asserts `instant_charge == 0`; no quota or billing assumption is made; Neo4j (max 5 calls) and expansion retrievals each need their own approval file.

## D. Order of operations
1. You fill the two templates (G1-G4, Q1-Q2). 2. Run `quota_plan.py` for each (offline). 3. You write the approval files yourself, with caps no larger than the suggestion. 4. Only then any model call. Any failed check = NO-GO; nothing is retried around a limit.
