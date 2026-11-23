"""Assemble the 100-position dataset from preserved runs (read-only inputs). One row per registry ID (asserted); every extraction version kept (never overwritten); claim-level states from evidence validation v2 (lexical; NOT correctness).
Usage: python src/assemble_dataset.py <out_dir> <run_spec> [<run_spec> ...]   run_spec = label=path_to_run_dir_with_outputs/groq_orgA+bundles_full  (order = ascending priority; later = primary)"""
import os, sys, json, csv, glob, time, hashlib, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
spec = importlib.util.spec_from_file_location("bench2", f"{ROOT}/runs/bench5-v2-20261123_192201/bench2.py"); X = importlib.util.module_from_spec(spec); sys.modules["bench2"] = X; spec.loader.exec_module(X); os.chdir(ROOT)
iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z"); sha = lambda b: hashlib.sha256(b).hexdigest()
D = json.load(open("data/apps.json")); CATS = D["categories"]; REG = {a[0]: a for a in D["apps"]}; MC = {int(r["registry_id"]): r for r in csv.DictReader(open("runs/master-coverage-v1-20261124/MASTER_COVERAGE.csv"))}
VERIFY_IDS = {int(os.path.basename(f)[:-5]) for f in glob.glob("baseline/p1_v1/verify/[0-9]*.json")}
MODEL_FIELDS = ("one_liner", "auth_methods", "access", "access_note", "api_types", "api_breadth", "existing_mcp", "buildability", "blocker")
def claims_from(rec, shown, full):
    ob = {k: rec[k] for k in MODEL_FIELDS + ("evidence",)}; v = X.validate_v2(dict(ob, evidence=[dict(field=e["field"], url=e["url"], quote=e["quote"]) for e in rec["evidence"]]), shown, full)
    ev = [dict(field=e["field"], url=e["url"], quote=e["quote"], valid=e["valid"], issues=e["issues"]) for e in v["evidence"]]; return v["claims"], ev, v["claim_state_counts"]
def baseline_versions():
    out = {}
    for f in glob.glob("baseline/p1_v1/pass1/*.json"):
        r = json.load(open(f)); i = r["id"]; raw = json.load(open(f"baseline/p1_v1/raw/{i}.json")); pages = [dict(url=p["url"], text=p["text"]) for p in raw["pages"]]
        cl, ev, cnt = claims_from(r, pages, pages); out.setdefault(i, []).append(dict(version="baseline_p1_v1", provider="gemini", model=r["model"], extraction_prompt="frozen V1 prompt (hash in baseline/MANIFEST.json)", schema="frozen V1", fields={k: r[k] for k in MODEL_FIELDS}, claims=cl, evidence=ev, claim_state_counts=cnt, sources=[dict(url=p["url"], chars=len(p["text"]), sha256=sha(p["text"].encode())) for p in pages], source_ref=f"baseline/p1_v1/raw/{i}.json (no per-page timestamps recorded in baseline raw)", run=f))
    return out
def run_versions(label, d):
    out = {}
    for f in glob.glob(f"{d}/outputs/groq_orgA/[0-9]*.json"):
        r = json.load(open(f)); i = r["app"]; fp = f"{d}/bundles_full/{i}.json"; sp = f"{d}/bundles/{i}.json"; full = json.load(open(fp))["pages"]; shown = json.load(open(sp))["pages"]
        o = r["output"]; cl, ev, cnt = claims_from(o, shown, full)
        out.setdefault(i, []).append(dict(version=label, provider="groq", model=r["model_returned"] or r["model"], model_identity_verified=r["model_identity_verified"], extraction_prompt=f"frozen v1f prompt sha256 13eaee38702b…; evidence reduction-v2", prompt_sha256=r["prompt_sha256"], schema="frozen v1f schema c5082c7feb4a…", fields={k: o[k] for k in MODEL_FIELDS}, claims=cl, evidence=ev, claim_state_counts=cnt, tokens=[r["tokens_in"], r["tokens_out"]], latency_s=r["latency_s"], extracted_at=r["at"], sources=[dict(url=p["url"], chars=len(p["text"]), sha256=sha(p["text"].encode())) for p in full], source_ref=fp, run=f))
    return out
def main():
    out = sys.argv[1]
    if os.path.isdir(out) and os.listdir(out): raise SystemExit(f"refusing to overwrite non-empty output directory: {out}")
    os.makedirs(out, exist_ok=True); V = baseline_versions(); GATE = {}; FAILED = {}
    for spec_ in sys.argv[2:]:
        label, d = spec_.split("=", 1)
        if label == "gate":
            for g in json.load(open(d)): GATE[g["id"]] = g
            continue
        for i, vs in run_versions(label, d).items(): V.setdefault(i, []).extend(vs)
        for f in glob.glob(f"{d}/outputs/groq_orgA/failed_*.json"):
            r = json.load(open(f)); FAILED.setdefault(r["app"], []).append(dict(run=label, category=r["category"], http=r["http"], error=r["error"][:300]))
    rows = []
    for i in range(1, 101):
        a = REG[i]; m = MC[i]; vs = V.get(i, []); prim = None
        if m["master_status"] not in ("EXCLUDED_IDENTITY_UNRESOLVED", "COMPLETED_BASELINE_QUARANTINED", "HELD_IDENTITY_PROVISIONAL") and vs: prim = vs[-1]["version"]
        status = m["master_status"]
        if vs and status in ("PLANNED_FROZEN_V1F", "UNPLANNED"): status = "EXTRACTED_" + prim
        elif not vs and i in FAILED:
            cats = [f["category"] for f in FAILED[i]]
            status = "EXTRACTION_FAILED_INVALID_JSON" if any("json_validate_failed" in f["error"] for f in FAILED[i]) else "PAUSED_PROVIDER_QUOTA" if cats and all(c == "daily_quota" for c in cats) else "EXTRACTION_FAILED"
        elif not vs and i in GATE and not GATE[i]["tier"].startswith(("A", "B")): status = "BLOCKED_" + GATE[i]["tier"]
        gate = GATE.get(i, {})
        identity = ("excluded_unresolved" if m["master_status"] == "EXCLUDED_IDENTITY_UNRESOLVED" else "held_provisional" if m["master_status"] == "HELD_IDENTITY_PROVISIONAL" else "quarantined_identity" if "QUARANTINED" in m["master_status"] else "identity_review_blocked" if gate.get("tier", "").startswith("C_") else "identity_review_pending" if gate.get("tier", "").startswith("D_") else "original_list_name" if i <= 50 else "reconstructed_candidate_unverified")
        retrieval = "evidence_bundle_used" if vs else "partial_retrieval_identity_review" if gate.get("tier", "").startswith("D_") and gate.get("pages_usable", 0) else "retrieval_gap" if gate.get("tier", "").startswith("D_") else "retrieval_available_not_extracted" if gate.get("pages_usable", 0) else "identity_blocked_before_retrieval" if gate.get("tier", "").startswith("C_") else "not_recorded_or_not_started"
        extraction = "quarantined" if "QUARANTINED" in m["master_status"] else "complete" if vs and prim else "paused_quota" if status == "PAUSED_PROVIDER_QUOTA" else "failed" if i in FAILED else "held" if m["master_status"].startswith("HELD") else "excluded" if m["master_status"].startswith("EXCLUDED") else "identity_blocked" if identity == "identity_review_blocked" else "not_started"
        counts = vs[-1].get("claim_state_counts", {}) if vs else {}
        evidence = "not_run" if not vs else "lexical_review_required" if counts.get("needs_human", 0) else "mixed_lexical_results" if counts.get("unsupported", 0) or counts.get("unknown", 0) or counts.get("not_found_in_provided_evidence", 0) else "all_quotes_lexically_supported"
        verification = "legacy_model_verification_record_present" if i in VERIFY_IDS else "not_run"
        rows.append(dict(registry_id=i, name=a[2], category=CATS[a[1] - 1], hint=a[3], provenance_class="verified_original_assignment_export", assignment_membership_status="verified_against_supplied_notion_export", master_status=m["master_status"], status=status, identity_status=identity, retrieval_status=retrieval, extraction_status=extraction, evidence_validation_status=evidence, verification_status=verification, human_review_status="not_started", primary_version=prim, versions=vs, failed_attempts=FAILED.get(i, []), identity_gate=gate or None, human_review="not_started", verification="not_started (Groq extraction != independent verification)"))
    ids = [r["registry_id"] for r in rows]; assert ids == list(range(1, 101)), "registry positions must be 1..100 exactly once"
    json.dump(dict(created=iso(), registry_source="supplied Notion export; see runs/registry-lock-v1-20261123_2110/RECONCILIATION.json", registry_sha256=sha(open("data/apps.json", "rb").read()), note="lexical evidence validation only; no accuracy claim; human_review blank", rows=rows), open(f"{out}/DATASET.json", "w"), indent=1)
    with open(f"{out}/DATASET_FLAT.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["id", "name", "category", "provenance", "status", "primary_version", "auth_methods", "access", "api_types", "api_breadth", "existing_mcp", "buildability", "blocker", "claims_supported_lexical", "claims_unsupported", "claims_unknown", "claims_not_found", "model"])
        for r in rows:
            p = next((v for v in r["versions"] if v["version"] == r["primary_version"]), None); f = p["fields"] if p else {}; c = p["claim_state_counts"] if p else {}
            w.writerow([r["registry_id"], r["name"], r["category"], r["provenance_class"], r["status"], r["primary_version"] or "", ";".join(f.get("auth_methods", [])) if p else "", f.get("access", ""), ";".join(f.get("api_types", [])) if p else "", f.get("api_breadth", ""), f.get("existing_mcp", ""), f.get("buildability", ""), f.get("blocker", ""), c.get("supported_lexical", ""), c.get("unsupported", ""), c.get("unknown", ""), c.get("not_found_in_provided_evidence", ""), p["model"] if p else ""])
    import collections; print(collections.Counter(r["status"] for r in rows))
if __name__ == "__main__": main()
