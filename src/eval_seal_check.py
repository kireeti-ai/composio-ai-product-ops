"""Seal check for the human-evaluation sheets: proves the BLIND label sheets are EMPTY (no truth, evidence, labeler or confidence cell filled), carry NO model/verifier/tier/plan columns, and that scoring sheets have BLANK label columns.
Records SHA-256 of every sheet so any later edit is detectable. Offline. Usage: python src/eval_seal_check.py [--write]   (--write stores runs/human-eval-seal-v1-20261124/SEAL.json)"""
import os, sys, csv, json, hashlib, glob, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
TRUTH_COLS = ["truth_value", "enum_fit(exact|forced)", "truth_evidence_url", "truth_quote", "accessed_at", "undeterminable_from_public_sources(Y/N)", "confidence(1-3)", "labeler_id", "notes"]
FORBIDDEN = ("model", "pass2", "verifier", "verdict", "tier", "plan", "quote_found", "groq", "gemini")
LABEL_COLS = ["evidence_support_label(supports|partial|none)", "blocker_label(correct|partial|incorrect|none_applicable)", "error_category", "adjudicator_id", "adjudication_notes"]
def check_blind(path):
    with open(path, newline="") as f: rows = list(csv.DictReader(f)); hdr = rows[0].keys() if rows else []
    bad_filled = [(i + 2, c) for i, r in enumerate(rows) for c in TRUTH_COLS if (r.get(c) or "").strip()]; leaks = [c for c in hdr if any(w in c.lower() for w in FORBIDDEN)]
    return dict(rows=len(rows), filled_truth_cells=len(bad_filled), forbidden_columns=leaks, ok=bool(rows) and not bad_filled and not leaks)
def check_scoring(path):
    with open(path, newline="") as f: rows = list(csv.DictReader(f))
    filled = [(i + 2, c) for i, r in enumerate(rows) for c in LABEL_COLS if (r.get(c) or "").strip()]; return dict(rows=len(rows), filled_label_cells=len(filled), ok=not filled)
def main():
    res = dict(created=time.strftime("%Y-%m-%dT%H:%M:%S%z"), blind_sheets={}, scoring_sheets={}, hashes={})
    for p in sorted(glob.glob("runs/human-eval-v*/label_sheet_blind_*.csv")): res["blind_sheets"][p] = check_blind(p); res["hashes"][p] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    for p in sorted(glob.glob("runs/human-eval-v*/scoring_sheet_*.csv")) + sorted(glob.glob("runs/pass2-pilot-plan-v1-20261124/stage2_source_grounding_sheet_TEMPLATE.csv")):
        if "stage2_source" in p:
            with open(p, newline="") as f: rows = list(csv.DictReader(f))
            res["scoring_sheets"][p] = dict(rows=len(rows), filled_label_cells=sum(bool((r.get("source_supports_claim(supports|contradicts|neither|cannot_tell)") or "").strip() or (r.get("labeler_id") or "").strip()) for r in rows), verdict_columns=[c for c in rows[0] if "verdict" in c.lower() or "pass2" in c.lower()], ok=True)
            res["scoring_sheets"][p]["ok"] = res["scoring_sheets"][p]["filled_label_cells"] == 0 and not res["scoring_sheets"][p]["verdict_columns"]
        else: res["scoring_sheets"][p] = check_scoring(p)
        res["hashes"][p] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    st = [json.load(open(p)) for p in glob.glob("runs/human-eval-v*/LABELS_STATUS.json")]; res["labels_status_all_zero"] = all(s.get("labels_completed") == 0 for s in st)
    res["all_blind_sheets_empty_and_clean"] = all(v["ok"] for v in res["blind_sheets"].values()) and all(v["ok"] for v in res["scoring_sheets"].values()) and res["labels_status_all_zero"] and bool(res["blind_sheets"])
    return res
if __name__ == "__main__":
    r = main(); print("blind sheets:", {os.path.basename(k): (v["rows"], v["filled_truth_cells"], v["forbidden_columns"]) for k, v in r["blind_sheets"].items()}); print("scoring/source sheets:", {os.path.basename(k): (v["rows"], v.get("filled_label_cells")) for k, v in r["scoring_sheets"].items()}); print("labels_status all zero:", r["labels_status_all_zero"], "| SEALED (all empty and clean):", r["all_blind_sheets_empty_and_clean"])
    if "--write" in sys.argv and r["all_blind_sheets_empty_and_clean"]:
        p = "runs/human-eval-seal-v1-20261124/SEAL.json"; json.dump(r, open(p, "w"), indent=1); os.chmod(p, 0o444); print("written:", p)
