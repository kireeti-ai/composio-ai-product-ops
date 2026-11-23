"""Neo4j OPTION B: two separately labelled extraction calls (Aura Management API, Database Query API), frozen prompt+schema UNCHANGED, results combined under ONE app record in REPORTING only.
GATED: needs runs/p1-neo4j-optionB-20261124/APPROVED.json (explicit user approval + per-model caps). Same quota semantics as src/run_p1.py: stop on first daily-quota 429, mandatory caps,
single writer, atomic read-only writes, never overwrites, reads ONLY GEMINI_API_KEY. Isolated from the frozen 28-target runner (src/run_p1.py is not modified by this feature).
Usage: python src/run_neo4j_surfaces.py [--dry-run] [--combine-only]"""
import os, sys, re, json, copy, time, hashlib, importlib.util, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
spec = importlib.util.spec_from_file_location("run_p1", ROOT + "/src/run_p1.py"); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)   # reuses frozen(), call_gemini(), check_quotes()
RUN = "runs/p1-neo4j-optionB-20261124"; sha = lambda b: hashlib.sha256(b).hexdigest(); iso = lambda t: datetime.datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")

def build_inputs(call):
    pages, prov = [], []
    for s in call["inputs"]:
        raw = json.load(open(s["raw"])); lst = raw[s["list_key"]]; by = {e["url"]: e for e in lst if e.get("status", "ok") == "ok"}
        for u in s["urls"]:
            e = by[u]; pages.append({"url": u, "text": e["text"][:9000]})
            prov.append({"path": s["raw"], "raw_sha256": sha(open(s["raw"], "rb").read()), "url": u, "chars": len(e["text"]), "truncated_in_prompt": len(e["text"]) > 9000, "sha256": e.get("sha256") or sha(e["text"].encode()), "fetched_at": e.get("completed_at") or iso(os.stat(s["raw"]).st_mtime)})
    return pages, prov

def validate(v, s, path="$"):                                                   # same logic as the schema proposal's validator
    errs = []; t = s["type"]
    if t == "OBJECT":
        if not isinstance(v, dict): return [f"{path}: not an object"]
        errs += [f"{path}.{k}: required field missing" for k in s.get("required", []) if k not in v]
        for k, sub in s.get("properties", {}).items():
            if k in v: errs += validate(v[k], sub, f"{path}.{k}")
    elif t == "ARRAY":
        if not isinstance(v, list): return [f"{path}: not an array"]
        for i, x in enumerate(v): errs += validate(x, s["items"], f"{path}[{i}]")
    elif t == "STRING":
        if not isinstance(v, str): return [f"{path}: not a string"]
        if "enum" in s and v not in s["enum"]: errs.append(f"{path}: '{v}' not in enum")
    return errs

def combine(plan, recs, out):
    """REPORTING record (not model output): nested per-surface shape from the schema proposal; one_liner is a labelled concatenation of the two surface one-liners."""
    nested = json.load(open("runs/schema-proposal-v1-20261124/nested_schema_gemini_dialect.json")); fields = [k for k in nested["properties"]["surfaces"]["items"]["properties"] if k not in ("surface_id", "surface_name", "surface_description")]
    surfaces = []
    for c, r in zip(plan["calls"], recs):
        surfaces.append({"surface_id": c["surface_id"], "surface_name": c["display_name"].split(" - ", 1)[1], **{k: copy.deepcopy(r[k]) for k in fields}, "_call_meta": r["meta"]})
    rec = {"id": plan["app"]["id"], "name": plan["app"]["name"], "category": recs[0]["category"], "schema_version": "nested-v1-PROPOSAL (reporting only; extraction used the frozen schema)",
           "one_liner": " | ".join(r["one_liner"] for r in recs), "one_liner_source": "concatenated from the two surface calls (not a model output of its own)", "surfaces": surfaces,
           "registry_provenance": plan["app"]["provenance"], "annotations_not_model_output": plan["composio_annotation"], "evidence_gaps": plan["evidence_gaps"], "uncertainty": plan["uncertainty"]}
    errs = validate({k: v for k, v in rec.items()}, nested); assert not errs, errs
    os.makedirs(f"{out}/reports", exist_ok=True); f = f"{out}/reports/66_neo4j_combined.json"; json.dump(rec, open(f + ".tmp", "w"), indent=1); os.replace(f + ".tmp", f); os.chmod(f, 0o444); return rec

def run(plan, approved, out, call_fn, schema, prompt, hashes, cats, sleep=time.sleep):
    os.makedirs(f"{out}/pass1", exist_ok=True); os.makedirs(f"{out}/logs", exist_ok=True)
    fd = os.open(f"{out}/.lock", os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd)
    code_sha = sha(open(__file__, "rb").read()); man = sha(open("baseline/MANIFEST.json", "rb").read()); log = lambda **k: open(f"{out}/logs/run.jsonl", "a").write(json.dumps({"t": iso(time.time()), **k}) + "\n")
    caps = dict(approved["cap_per_model"]); used = {m: 0 for m in caps}; dead = set(); reason = "completed"; recs = []
    try:
        for c in plan["calls"]:
            f = f"{out}/pass1/66__{c['surface_id']}.json"
            if os.path.exists(f): recs.append(json.load(open(f))); continue                       # resume; never overwrite
            pages, prov = build_inputs(c); src = "\n\n".join(f"### {p['url']}\n{p['text']}" for p in pages)
            pr = prompt.format(name=c["display_name"], cat=cats[plan["app"]["registry_category"] - 1], hint="none", src=src); attempts = 0; res = model = None
            for m in approved["models"]:
                if m in dead or used[m] >= caps[m]: continue
                for tr in range(3):
                    used[m] += 1; attempts += 1; kind, pay = call_fn(m, pr, schema); log(ev="request", surface=c["surface_id"], model=m, kind=kind, n_model=used[m])
                    if kind == "ok": res, model = pay, m; break
                    if kind == "daily_quota": dead.add(m); log(ev="model_exhausted", model=m); break
                    if kind == "error" or used[m] >= caps[m]: break
                    sleep(15 * (tr + 1))
                if res is not None: break
            if res is None: reason = "quota_or_cap_exhausted"; break
            res["evidence"] = R.check_quotes(res["evidence"], pages)
            rec = {"id": 66, "name": plan["app"]["name"], "surface_id": c["surface_id"], "category": cats[plan["app"]["registry_category"] - 1], "model": model, "pages_read": [p["url"] for p in pages], **res,
                   "meta": {"run_id": plan["run_id"], "code_sha256": code_sha, "prompt_sha256": hashes[1], "schema_sha256": hashes[0], "baseline_manifest_sha256": man, "temperature": 0, "key_id": "GEMINI_API_KEY", "extracted_at": iso(time.time()), "request_attempts": attempts,
                            "prompt_app_label": c["display_name"], "uncertainty": plan["uncertainty"][c["surface_id"]], "registry_provenance": plan["app"]["provenance"], "retrieval": prov}}
            tmp = f + ".tmp"; json.dump(rec, open(tmp, "w"), indent=1); os.replace(tmp, f); os.chmod(f, 0o444); recs.append(rec); log(ev="done", surface=c["surface_id"], model=model)
        if len(recs) == len(plan["calls"]): combine(plan, recs, out)
    finally:
        os.remove(f"{out}/.lock"); json.dump({"reason": reason, "at": iso(time.time()), "requests_by_model": used, "exhausted_models": sorted(dead)}, open(f"{out}/STOPPED.json", "w"), indent=1)
    return reason

if __name__ == "__main__":
    plan = json.load(open(f"{RUN}/PLAN.json")); schema, prompt, h_sch, h_pr = R.frozen(); D = json.load(open("baseline/data/apps.json"))
    fz = f"{RUN}/FROZEN.json"
    if os.path.exists(fz):
        F = json.load(open(fz)); assert sha(open(f"{RUN}/PLAN.json", "rb").read()) == F["plan_sha256"], "PLAN.json differs from frozen"; assert sha(open(__file__, "rb").read()) == F["runner_sha256"], "runner differs from frozen"; print("frozen plan + runner hashes verified")
    print(f"prompt/schema hashes verified ({h_pr[:10]}.. / {h_sch[:10]}..) | calls planned: {len(plan['calls'])}")
    seen = {}
    for c in plan["calls"]:
        pages, prov = build_inputs(c); print(f"  call {c['order']} {c['display_name']!r}: {len(pages)} pages, {sum(len(p['text']) for p in pages)} chars -> {[p['url'][8:70] for p in pages]}")
        for p in pages: seen.setdefault(p["url"], []).append(c["surface_id"])
    print("pages shared between the two calls (must be none):", [u for u, v in seen.items() if len(v) > 1])
    if "--dry-run" in sys.argv: print("[dry-run] no network, no model call. approval file present:", os.path.exists(f"{RUN}/APPROVED.json")); sys.exit(0)
    if not os.path.exists(f"{RUN}/APPROVED.json"): sys.exit("REFUSING: no APPROVED.json (explicit user approval and per-model caps are required)")
    approved = json.load(open(f"{RUN}/APPROVED.json")); assert set(approved["models"]) == set(approved["cap_per_model"]), "every model needs a cap"
    key = None
    for l in open(".env"):
        if l.startswith("GEMINI_API_KEY="): key = l.strip().split("=", 1)[1]          # only this variable is ever read
    assert key, "GEMINI_API_KEY missing"
    print("STOPPED:", run(plan, approved, RUN, lambda m, p, s: R.call_gemini(m, p, s, key), schema, prompt, (h_sch, h_pr), D["categories"]))
