# Benchmark summary (5 apps; pipeline/model evaluation, NOT an accuracy claim)

STRUCTURAL/automatic measures only (schema, verbatim quotes, unknown rates, latency). NO accuracy claim: there is no independent human-labelled ground truth. Use review_aid_side_by_side.csv for labelling.

| provider tag | model | apps valid/returned | verbatim quotes / evidence | claim fields w/o verified quote | unknown fields | mean latency s | tokens in/out | cost USD |
|---|---|---|---|---|---|---|---|---|
| groq_orgA | openai/gpt-oss-120b | 5/5 | 18/24 | 5 | 1 | 2.3 | 10147/3752 | 0.0 |

Not run / deferred: openrouter_particle, gemini25_key1, gemini36_key2
Failed requests recorded: 6

## Pairwise agreement (same apps, same evidence)
