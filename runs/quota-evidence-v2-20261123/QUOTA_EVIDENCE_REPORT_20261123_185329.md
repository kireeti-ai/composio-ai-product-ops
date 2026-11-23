# Quota evidence report (2026-11-23T18:53:29+0530)
Evidence only. No frozen plan, prompt, schema or model config changed. No APPROVED.json. No extraction/verification.

## Dashboard (Key 1 project, assumed mapping)
| Model | RPM peak | TPM peak | RPD peak |
|---|---|---|---|
| gemini-2.5-flash | 6/5 | 27.41K/250K | 25/20 |
| gemini-3.6-flash | 3/5 | 21.07K/250K | 25/20 |
Limits per model per project: 5 RPM, 250K TPM, 20 RPD. Key 2 panel (excluded): 3.6 Flash only, 3/20 RPD peak.

## What "25/20" means
The panel header says *peak usage per model over the last 28 days*. It is the maximum in any single day (RPD) or minute (RPM/TPM) in that window. So 25/20 = on some day within 28 days, 25 requests were counted against a 20-request limit. It does not identify the day, does not say it was today, and is not used-today or remaining. **Today's remaining quota is unknown and is not inferred.** Whether 429-rejected requests are included in the 25 is also unknown. The same applies to 6/5 RPM and to Key 2's 3/20.

## Model decisions recorded
- `gemini-2.5-flash`: only demonstrated working model (accepted call 18:48 IST). Plan max 20 requests/day.
- `gemini-3.5-flash`: stays in the frozen plan; marked temporarily unavailable (503 high demand, capacity not quota).
- `gemini-3.6-flash`: models.list on Key 1 shows exact ID `models/gemini-3.6-flash` with generateContent; generation availability untested. Not introduced; needs a separate change proposal and evaluation. (3.7 and 3.8 are also listed; also not adopted.)
- Key 2 and OpenRouter: excluded.

## Still missing
Groq RPM and daily token limit (seen: 1000 RPD, 8000 TPM). Pilot stays unapproved until documented and you approve.

Note: this session made one more Google **metadata** call (models.list, no generation) to verify model IDs.
