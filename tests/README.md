# Offline tests (no network, no Gemini/Groq; fake model functions only; outputs go to a temp dir you pass in)
python -I tests/test_eval_score.py                       # scorer arithmetic (SYNTHETIC data only) + blank real sheets => no metrics
python -I tests/test_runner_v1f.py  <empty_tmp_dir>      # frozen runner v6 on the 28-target plan: quota stop, resume, lock, top-up merge, provenance, uncertainty, Gladly inputs
python -I tests/test_neo4j_surfaces.py <empty_tmp_dir>   # Neo4j Option B runner: labelled calls, isolation, quota stop/resume, combined nested record
python -I src/run_p1.py --run p1-v1f-gemini-20261124 --dry-run
python -I src/run_neo4j_surfaces.py --dry-run
