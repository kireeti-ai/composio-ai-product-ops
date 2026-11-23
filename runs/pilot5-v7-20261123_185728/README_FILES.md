# pilot5-v7 files (all new; nothing existing modified)
- run_pilot5_v7.py - runner v7 (gated; sequential; reuses v6 frozen()/check_quotes via src/run_p1.py)
- PILOT5_MANIFEST.json - five-app manifest, execution_authorized=false (built by build_manifest.py)
- test_pilot5_v7.py - 26 offline tests; results/ holds captured outputs of these and the regression suites
- FREEZE_v7_<ts>.json, SHA256SUMS_<ts>.txt - freeze record and hashes
Authorization (NOT created): <this dir>/APPROVED.json = {"manifest_sha256": <manifest sha>, "model": "gemini-2.5-flash", "max_requests": 8}
Resume after any stop: write output/STOP_REVIEWED.json = {"stop_sha256": <sha256 of output/STOPPED.json>, "reviewer": ..., "accept_missing_model_identity": optional bool}
Dry run (no calls): python -I run_pilot5_v7.py --run-dir <this dir> --dry-run
