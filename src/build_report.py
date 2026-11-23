"""Build the single, self-contained assignment case study from the registry and run records."""
import csv
import glob
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))
from report_analytics import build_report_data


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_metadata():
    meta = {}
    patterns = ("runs/retrieval-wave-v*/raw/*.json", "runs/topup-v*/raw/*.json",
                "runs/correction5-v1-*/raw/*.json", "runs/*identity*topup*/raw/*.json")
    for pattern in patterns:
        for filename in glob.glob(pattern):
            try:
                rec = json.loads(Path(filename).read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(rec, dict):
                continue
            for item in rec.get("fetched", []):
                url = item.get("final_url") or item.get("url")
                stamp = item.get("retrieved_at") or item.get("fetched_at")
                if url and stamp and (url not in meta or stamp > meta[url]):
                    meta[url] = stamp
    return meta


def retrieval_stats():
    ok = failed = searches = 0
    patterns = ("runs/retrieval-wave-v*/raw/*.json", "runs/topup-v*/raw/*.json",
                "runs/correction5-v1-*/raw/github_official_*.json", "runs/*identity*topup*/raw/*.json")
    for pattern in patterns:
        for filename in glob.glob(pattern):
            try:
                rec = json.loads(Path(filename).read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(rec, dict):
                continue
            items = rec.get("fetched")
            if isinstance(items, list):
                ok += sum(item.get("status") == "ok" for item in items)
                failed += sum(item.get("status") != "ok" for item in items)
                searches += len(rec.get("searches", []))
            elif "status" in rec:
                ok += rec["status"] == "ok"
                failed += rec["status"] != "ok"
    return {"successful_page_fetches": ok, "failed_or_empty_page_fetches": failed,
            "search_requests": searches}


def legacy_verification():
    verdicts = {}
    files = glob.glob("baseline/p1_v1/verify/[0-9]*.json")
    for filename in files:
        try:
            record = json.loads(Path(filename).read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for items in record.get("fields", {}).values():
            for item in items:
                key = item.get("verdict", "unknown")
                verdicts[key] = verdicts.get(key, 0) + 1
    return {"app_records": len(files), "verdicts": verdicts}


def human_labels():
    count = reviewed_apps = 0
    for filename in glob.glob("runs/human-eval-*/label_sheet_blind_[ABC].csv"):
        try:
            with open(filename, newline="") as stream:
                for row in csv.DictReader(stream):
                    if row.get("truth_value", "").strip() and row.get("labeler_id", "").strip():
                        count += 1
                        reviewed_apps += bool(row.get("registry_id"))
        except OSError:
            continue
    return {"labelled_claims": count, "reviewed_rows": reviewed_apps}


def evidence_ledger(rd):
    """Separate evidence tiers; each count carries its denominator. Reads saved audit artefacts only."""
    out = {"human": {"sampled": 0, "labelled": 0, "comparable": 0, "agree": 0}}
    cf = sorted(glob.glob("runs/evidence-capture-*/CONSOLIDATED.json"))
    if cf:
        c = json.loads(Path(cf[-1]).read_text()); claims = c["claims"]
        quotes = {(e["url"], e["quote_sha256"]): e["refetch_status"] for x in claims for e in x["evidence"]}
        out["refetch"] = {"quotations": len(quotes), "reproduced": sum(v.startswith("reproduced") for v in quotes.values()),
                          "statuses": {k: sum(v == k for v in quotes.values()) for k in sorted(set(quotes.values()))}}
        out["new_claims"] = {"claims": len(claims), "with_quotation": sum(bool(x["evidence"]) for x in claims),
                             "verdicts": {k: sum(x["final_verdict"] == k for x in claims) for k in sorted({x["final_verdict"] for x in claims})}}
    chk = sorted(glob.glob("runs/human-review-worksheet-*/CLAUDE_INDEPENDENT_CHECK.csv"))
    if chk:
        rows = list(csv.DictReader(open(chk[-1], newline="")))
        out["recheck"] = {"claims": len(rows), "verdicts": {k: sum(r["claude_recheck_verdict"] == k for r in rows) for k in sorted({r["claude_recheck_verdict"] for r in rows})}}
    sheets = sorted(glob.glob("runs/human-review-worksheet-*/HUMAN_REVIEW_WORKSHEET.csv")); done = sorted(glob.glob("runs/human-review-worksheet-*/human_review_completed.csv"))
    if sheets:
        out["human"]["sampled"] = sum(1 for _ in csv.DictReader(open(sheets[-1], newline="")))
    if done:
        cmap = {"supported": "supported", "supported_by_official_quote": "supported", "supported_by_third_party_quote_only": "supported", "partially_supported": "partially_supported",
                "unsupported": "unsupported", "conflicting": "conflicting", "unverifiable": "unverifiable"}  # other model verdicts (unknown, unresolved_*, judgement) have no 5-way equivalent and are excluded
        rows = [r for r in csv.DictReader(open(done[-1], newline="")) if r.get("human_verdict", "").strip()]
        comp = [r for r in rows if r.get("model_verdict") in cmap]
        out["human"].update(labelled=len(rows), comparable=len(comp), agree=sum(cmap[r["model_verdict"]] == r["human_verdict"].strip() for r in comp))
        out["handcheck"] = [{"app": r.get("app", ""), "field": r.get("field", ""), "claim": r.get("claim", "")[:140], "model": r.get("model_verdict", ""), "human": r["human_verdict"].strip(),
                             "hit": ("n/a" if r.get("model_verdict") not in cmap else "hit" if cmap[r["model_verdict"]] == r["human_verdict"].strip() else "miss")} for r in rows]
    return out


def composio_demo():
    f = sorted(glob.glob("runs/composio-demo-*/DEMO_RESULT.json"))
    if not f:
        return None
    d = json.loads(Path(f[-1]).read_text())
    return {"run_at": d["run_at"], "summary": d.get("summary", {}), "path": f[-1],
            "steps": [{"step": x["step"], "layer": x.get("layer", "mcp_infrastructure" if x["step"][:2] in ("S2", "S3", "S4", "S7") else "app_toolkit" if x["step"][:2] in ("S5", "S6", "S8") else "sdk"), "status": x["status"], "detail": (x.get("error") or json.dumps(x.get("result"))[:240])} for x in d["steps"]]}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python3 -I src/build_report.py <DATASET.json> <output.html>")
    dataset_path, output_path = map(Path, sys.argv[1:])
    dataset = json.loads(dataset_path.read_text())
    registry = json.loads(Path("data/apps.json").read_text())
    comparison_path = Path(sorted(glob.glob("runs/correction5-v1-*/reports/COMPARISON_V1_VS_CORRECTED.json"))[-1])
    comparison = json.loads(comparison_path.read_text())
    lock = sorted(glob.glob("runs/registry-lock-v*/RECONCILIATION.json"))
    if lock:   # authoritative: registry locked against the supplied assignment export
        source_path = Path(lock[-1]); raw = json.loads(source_path.read_text())
        ok = raw.get("source_rows") == raw.get("id_category_name_matches") == 100
        source_check = {"checked_at": raw.get("created_at", "not recorded"), "reconciliation_status": "matched_supplied_export" if ok else "mismatch",
                        "access_result": f"All {raw.get('id_category_name_matches')} of {raw.get('source_rows')} entries match the supplied assignment export (ID, name and category); {raw.get('hints_restored', 0)} website hints were restored from it.",
                        "registry_changed": False}
    else:
        source_path = Path(sorted(glob.glob("runs/registry-reconciliation-v*/RECONCILIATION.json"))[-1])
        source_check = json.loads(source_path.read_text())
    legacy = legacy_verification()
    labels = human_labels()
    retrieval = retrieval_stats()
    report_data = build_report_data(dataset["rows"], registry, comparison, legacy, labels,
                                    retrieval, source_check, source_metadata())
    report_data["metrics"]["dataset_created"] = dataset.get("created", "not recorded")
    extraction_times = [v.get("extracted_at", "") for r in dataset["rows"] for v in r.get("versions", [])
                        if v.get("extracted_at")]
    report_data["metrics"]["data_as_of"] = max(extraction_times) if extraction_times else "not individually recorded"
    report_data["metrics"]["reconciliation_checked_at"] = source_check.get("checked_at", "not recorded")
    source_hashes = []
    for label, path in (("Registry", "data/apps.json"), ("Source reconciliation ledger", str(source_path)),
                        ("Dataset", str(dataset_path)), ("Dataset assembler", "src/assemble_dataset.py"),
                        ("Report analytics", "src/report_analytics.py"), ("Report builder", "src/build_report.py"),
                        ("HTML template", "src/report_template.html"),
                        ("Frozen v1f plan", "runs/p1-v1f-gemini-20261124/PLAN.json"),
                        ("Frozen runner v6", "src/run_p1.py"), ("Baseline manifest", "baseline/MANIFEST.json"),
                        ("Baseline checksums", "baseline/SHA256SUMS.txt"), ("Human evaluation protocol", "runs/human-eval-v2-20261124/PROTOCOL_v2_FINAL.md")):
        if Path(path).is_file():
            source_hashes.append({"label": label, "path": path, "sha256": sha(path)})
    report_data["ledger"] = evidence_ledger(report_data)
    report_data["composio_demo"] = composio_demo()
    report_data["hashes"] = source_hashes
    report_data["registry_provenance"] = registry.get("provenance", {})
    report_data["model_provenance"] = dict(__import__("collections").Counter(
        f'{a["provider_model"]}' for a in report_data["apps"] if a["provider_model"]))
    report_data["category_names"] = registry["categories"]

    template = Path("src/report_template.html").read_text()
    payload = json.dumps(report_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = template.replace("{{REPORT_DATA}}", payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"report written: {output_path} ({output_path.stat().st_size // 1024} KB); {len(report_data['apps'])} registry rows; {report_data['metrics']['extracted']} primary extractions")


if __name__ == "__main__":
    main()
