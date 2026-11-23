# p1-v1d (prepared, NOT approved)
Two separate axes per app (APP_STATUS.json):
- extraction_eligibility: may we call the model for this app? (identity ok, enough official usable pages, scope clear, phase assigned)
- research_completeness: how much do we actually know? (identity authority, auth, api_surface, access, mcp, buildability) - eligible apps can be INCOMPLETE.
Uncertainty is carried into every record (meta.uncertainty): `inferred_self_serve` is never reported as confirmed; `partial` may be reported as partial/unknown.
The extraction PROMPT and SCHEMA are unchanged (hash-verified). Adding per-field evidence states to the extraction schema is a separate change that needs approval.
No APPROVED.json exists. Runner: src/run_p1.py --run p1-v1d-gemini-20261124 [--dry-run]
