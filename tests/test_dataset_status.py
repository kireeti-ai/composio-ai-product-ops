"""Offline regression for the 100-position status fields and live run merge."""
import json
import hashlib
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPECS = [
    "bench5v1=runs/bench5-v1-20261123_191136",
    "corrected5=runs/correction5-v1-20261123_192852",
    "batchA=runs/p1-batchA-groq-20261123_193428",
    "batchB=runs/p1-batchB-groq-20261123_195002",
    "gate=runs/p1-batchB-groq-20261123_195002/IDENTITY_GATE.json",
]

with tempfile.TemporaryDirectory() as tmp:
    out = pathlib.Path(tmp) / "dataset"
    subprocess.run([sys.executable, "-I", "src/assemble_dataset.py", str(out), *SPECS], cwd=ROOT, check=True, capture_output=True, text=True)
    rows = json.loads((out / "DATASET.json").read_text())["rows"]
    assert [r["registry_id"] for r in rows] == list(range(1, 101))
    fields = ("identity_status", "retrieval_status", "extraction_status", "evidence_validation_status", "verification_status", "human_review_status")
    assert all(all(r.get(k) for k in fields) for r in rows)
    by_id = {r["registry_id"]: r for r in rows}
    assert by_id[71]["extraction_status"] == "failed" and by_id[71]["failed_attempts"]
    assert by_id[37]["status"] == "PAUSED_PROVIDER_QUOTA" and by_id[37]["extraction_status"] == "paused_quota"
    assert by_id[83]["retrieval_status"] == "partial_retrieval_identity_review"
    assert by_id[93]["identity_status"] == "identity_review_blocked"
    assert by_id[58]["identity_status"] == "quarantined_identity" and by_id[58]["extraction_status"] == "quarantined"
    assert all(r["provenance_class"] == "verified_original_assignment_export" for r in rows)
    assert all(r["assignment_membership_status"] == "verified_against_supplied_notion_export" for r in rows)
    assert all(r["human_review_status"] == "not_started" for r in rows)
    before = hashlib.sha256((out / "DATASET.json").read_bytes()).hexdigest()
    refused = subprocess.run([sys.executable, "-I", "src/assemble_dataset.py", str(out), *SPECS], cwd=ROOT, capture_output=True, text=True)
    assert refused.returncode != 0 and "refusing to overwrite" in refused.stderr
    assert hashlib.sha256((out / "DATASET.json").read_bytes()).hexdigest() == before
print("PASS: 100 unique IDs, six status fields, preserved failure/provenance, blank human review")
