# Secret-handling assessment (offline audit; values never printed or stored)
**Result: no key value is present in source, tests, data, runs, baseline, work logs/evidence, scratch files or background-task outputs.** Search was by the exact values read from `.env` at runtime plus generic key formats.
- Two generic-format matches (`work/raw/42.json`, `baseline/p1_v1/raw/42.json`) are the placeholder `ck_xxxxxxxxxxxxxxxx` inside WooCommerce's own fetched documentation: not a secret, not our key.
- `.env`: mode 600 (owner-only), gitignored. `work/` is gitignored. `Assignment/` is untracked in the parent repo and no commit has ever touched it, so nothing was committed.
- The audit output contains metadata only (paths, key NAMES, counts).
## Exposure that remains (cannot be fixed from inside the project)
- The five keys were pasted into the chat, so they exist in the Claude Code session transcript store outside the project (1 transcript file contains key values). **Rotation is the only remedy: rotate Composio, Gemini (both), Groq and OpenRouter keys.**
## Recommendations (not applied)
1. Rotate all five keys now or immediately after the project; update `.env` only.
2. Remove unused keys from `.env` (OpenRouter, GEMINI_API_KEY_2): least privilege, smaller blast radius. I did not edit `.env`.
3. Legacy scripts `src/research.py` and `src/verify.py` load EVERY `.env` variable into the environment (`setdefault`). The new scripts read only the one variable they need (run_p1 / run_neo4j_surfaces: GEMINI_API_KEY; topup*/mcp: COMPOSIO_API_KEY). I did not change the legacy scripts because exact copies are part of the baseline provenance (`baseline/code/`).
4. Before any publish or deploy: re-run `python -I src/secret_audit.py` and publish only the HTML/report artifacts, never `.env`, `work/` or transcripts.
5. Keys must never be passed on command lines or echoed in error messages (current code truncates and masks errors; the audit found no leak).
