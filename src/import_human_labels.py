"""Validate and import the human-review CSV exported from HUMAN_REVIEW_INTERFACE.html.
Usage: python3 src/import_human_labels.py <exported.csv> [--reviewer=NAME --date=YYYY-MM-DD]
Copies it to runs/human-review-worksheet-v1-20261124/human_review_completed.csv (refuses to overwrite) after checking: unique review_ids from the 30-row worksheet (a subset is allowed), verdicts from the fixed vocabulary, reviewer + date present on labelled rows, model verdict untouched."""
import csv, sys, shutil
from pathlib import Path
import os
D = Path(os.environ.get("HUMAN_REVIEW_DIR") or Path(__file__).resolve().parents[1] / "runs/human-review-worksheet-v1-20261124")
VOC = {"supported", "partially_supported", "unsupported", "conflicting", "unverifiable"}
args = [a for a in sys.argv[1:] if not a.startswith("--")]; opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
src = Path(args[0]); dest = D / "human_review_completed.csv"
if dest.exists(): raise SystemExit(f"{dest} exists; move it aside first (labels are never overwritten)")
ws = {r["review_id"]: r for r in csv.DictReader(open(D / "HUMAN_REVIEW_WORKSHEET.csv", newline=""))}
rows = list(csv.DictReader(open(src, newline="")))
for r in rows:   # optional: fill ONLY blank reviewer/date on rows that already carry a verdict (the reviewer states who they are; verdicts are never touched)
    if r.get("human_verdict", "").strip():
        r["reviewer"] = r.get("reviewer", "").strip() or opt.get("reviewer", ""); r["review_date"] = r.get("review_date", "").strip() or opt.get("date", "")
errs = []
ids = [r["review_id"] for r in rows]
if not ids or len(ids) != len(set(ids)) or not set(ids) <= set(ws): errs.append("review_ids must be unique and belong to the 30-row worksheet (a subset is fine)")
for r in rows:
    w = ws.get(r["review_id"])
    if not w: continue
    if r["model_verdict"] != w["model_verdict"]: errs.append(f'{r["review_id"]}: model verdict altered')
    v = r.get("human_verdict", "").strip()
    if v and v not in VOC: errs.append(f'{r["review_id"]}: verdict "{v}" not in {sorted(VOC)}')
    if v and not (r.get("reviewer", "").strip() and r.get("review_date", "").strip()): errs.append(f'{r["review_id"]}: reviewer/date missing')
if errs: raise SystemExit("NOT imported:\n  " + "\n  ".join(errs))
w = csv.DictWriter(open(dest, "w", newline=""), fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows); print(f"imported {sum(1 for r in rows if r['human_verdict'].strip())} of {len(rows)} labels -> {dest}\nnext: python3 -I src/build_report.py runs/dataset-live-v7-20261124_0010/DATASET.json report/index.html")
