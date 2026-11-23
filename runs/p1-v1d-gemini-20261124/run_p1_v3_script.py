"""Pass-1 RESUME run (p1-v1b). Same PROMPT / SCHEMA / temperature / models as baseline V1 (hash-verified against baseline/MANIFEST.json).
GATED: refuses to run unless runs/<run>/APPROVED.json exists. Reads cached retrievals from baseline/ (never modifies baseline/ or work/), writes only runs/<run>/.
Stops at the first daily-quota 429 (no retry loop); per-model request cap is mandatory (from APPROVED.json); uses ONLY GEMINI_API_KEY (never GEMINI_API_KEY_2).
Version 3 (multi-source top-up, uncertainty + api-surface state in meta). Version 2: merges the free evidence top-up pages (runs/topup-v1-20261123) into each app's sources, with per-page provenance; plans are split into phases.
Usage: python src/run_p1.py --run <run_id> [--dry-run]"""
import os, sys, re, json, time, hashlib, datetime, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
sha = lambda b: hashlib.sha256(b).hexdigest()
iso = lambda t: datetime.datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")

def frozen():
    """Load SCHEMA and PROMPT from the preserved V1 (reconstructed) source and verify their hashes against the baseline manifest."""
    src = open("baseline/code/research_v1_RECONSTRUCTED_not_byte_verified.py").read(); man = json.load(open("baseline/MANIFEST.json"))["hashes"]
    s0 = src.index("SCHEMA = {"); sch = src[s0:src.index("\n\nPROMPT", s0)]; p0 = src.index('PROMPT = """'); pr = src[p0:src.index('"""\n', p0 + 12)]
    assert sha(sch.encode()) == man["SCHEMA_sha256_V1"], "SCHEMA hash mismatch - refusing to run"
    assert sha(pr.encode()) == man["PROMPT_sha256_V1"], "PROMPT hash mismatch - refusing to run"
    ns = {}; exec(sch + "\n" + pr + '"""', ns); return ns["SCHEMA"], ns["PROMPT"], man["SCHEMA_sha256_V1"], man["PROMPT_sha256_V1"]

def norm(s): return re.sub(r"[\s​]+", " ", re.sub(r"[*_`#>\[\]()]", "", s)).strip().lower()
def check_quotes(ev, pages):  # identical logic to V1
    by = {p["url"]: norm(p["text"]) for p in pages}; allt = " ".join(by.values())
    for e in ev:
        q = norm(e["quote"]); e["quote_found"] = bool(q) and (q in by.get(e["url"], "") or q in allt); e["url_in_sources"] = e["url"] in by
    return ev

def call_gemini(model, prompt, schema, key):
    """-> (kind, payload). kind: ok | daily_quota | rate | transient | error"""
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema, "temperature": 0}}
    r = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", json.dumps(body).encode(), {"content-type": "application/json", "x-goog-api-key": key})
    try: d = json.load(urllib.request.urlopen(r, timeout=150)); return "ok", json.loads(d["candidates"][0]["content"]["parts"][0]["text"])
    except urllib.error.HTTPError as e:
        b = e.read().decode(); bl = b.lower()
        if e.code == 429 and "per day" in bl: return "daily_quota", b[:400]
        if e.code == 429: return "rate", b[:200]
        if e.code in (500, 503, 504): return "transient", f"{e.code}"
        return "error", f"{e.code} {b[:200]}"
    except Exception as e: return "transient", type(e).__name__

def run(plan, approved, out, call, schema, prompt, hashes, apps, cats, sleep=time.sleep):
    """Core loop (injectable `call` so it can be self-tested without the network). Returns stop reason or 'completed'."""
    os.makedirs(f"{out}/pass1", exist_ok=True); os.makedirs(f"{out}/logs", exist_ok=True)
    lock = f"{out}/.lock"; fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd)   # single writer
    code_sha = sha(open(__file__, "rb").read()); man_sha = sha(open("baseline/MANIFEST.json", "rb").read())
    log = lambda **k: open(f"{out}/logs/run.jsonl", "a").write(json.dumps({"t": iso(time.time()), **k}) + "\n")
    caps = dict(approved["cap_per_model"]); used = {m: 0 for m in caps}; dead = set(); reason = "completed"
    try:
        for i in plan["ids"]:
            f = f"{out}/pass1/{i}.json"
            if os.path.exists(f) or os.path.exists(f"baseline/p1_v1/pass1/{i}.json"): continue          # never overwrite / regenerate
            rawp = f"baseline/p1_v1/raw/{i}.json"; raw = json.load(open(rawp)); a = apps[i]
            skip = set(plan.get("exclude_urls", {}).get(str(i), [])); pages = [p for p in raw["pages"] if p["url"] not in skip]; top = None
            exs = plan.get("extra_retrieval", {}).get(str(i)) or []; exs = [exs] if isinstance(exs, dict) else exs   # list of sources: first-attempt top-up and/or retry run
            for ex in exs:   # top-up pages: only usable_unique URLs; text capped at 9000 chars like V1 (truncation recorded per page)
                xr = json.load(open(ex["raw"])); use = set(ex["use_urls"]); xs = [e for e in xr[ex.get("list_key", "fetched")] if e["url"] in use and e.get("status") == "ok"]
                top = (top or []) + [{"path": ex["raw"], "raw_sha256": sha(open(ex["raw"], "rb").read()), "tool": xr["tool"], "pages": [{"url": e["url"], "sha256": e["sha256"], "fetched_at": e["completed_at"], "chars": e["chars"], "truncated_in_prompt": e["chars"] > 9000} for e in xs]}]
                pages = pages + [{"url": e["url"], "text": e["text"][:9000]} for e in xs]
            src = "\n\n".join(f"### {p['url']}\n{p['text']}" for p in pages)
            pr = prompt.format(name=a["name"], cat=cats[a["cat"] - 1], hint=a["hint"] or "none", src=src); attempts = 0; res = model = None
            for m in approved["models"]:
                if m in dead or used[m] >= caps[m]: continue
                for tr in range(3):                                     # <=2 retries, only for rate/transient
                    used[m] += 1; attempts += 1; kind, pay = call(m, pr, schema); log(ev="request", id=i, model=m, kind=kind, n_model=used[m])
                    if kind == "ok": res, model = pay, m; break
                    if kind == "daily_quota": dead.add(m); log(ev="model_exhausted", model=m, msg=pay[:200]); break
                    if kind == "error" or used[m] >= caps[m]: break
                    sleep(15 * (tr + 1))
                if res is not None: break
            if res is None:
                if all(m in dead or used[m] >= caps[m] for m in approved["models"]): reason = "quota_or_cap_exhausted"; break
                log(ev="app_failed_not_cached", id=i); continue
            res["evidence"] = check_quotes(res["evidence"], pages)
            rec = {"id": i, "name": a["name"], "category": cats[a["cat"] - 1], "model": model, "pages_read": [p["url"] for p in pages], **res,
                   "meta": {"run_id": plan["run_id"], "code_sha256": code_sha, "prompt_sha256": hashes[1], "schema_sha256": hashes[0], "baseline_manifest_sha256": man_sha, "temperature": 0, "key_id": "GEMINI_API_KEY",
                            "extracted_at": iso(time.time()), "request_attempts": attempts, "excluded_pages": sorted(skip),
                            "tier": plan.get("tiers", {}).get(str(i)), "uncertainty": plan.get("uncertainty", {}).get(str(i)), "api_surface_state": plan.get("api_surface", {}).get(str(i)), "retrieval_topup": top, "retrieval": {"path": rawp, "raw_sha256": sha(open(rawp, "rb").read()), "fetched_at": iso(os.stat(rawp).st_mtime), "tool": "composio:TINYFISH_FETCH_URLS", "pages": [{"url": p["url"], "chars": len(p["text"])} for p in pages if not top or p["url"] not in {x["url"] for t in top for x in t["pages"]}]}}}
            tmp = f + ".tmp"; json.dump(rec, open(tmp, "w"), indent=1); os.replace(tmp, f); os.chmod(f, 0o444); log(ev="done", id=i, model=model)
    finally:
        os.remove(lock)
        json.dump({"reason": reason, "at": iso(time.time()), "requests_by_model": used, "exhausted_models": sorted(dead)}, open(f"{out}/STOPPED.json", "w"), indent=1)
    return reason

if __name__ == "__main__":
    run_id = sys.argv[sys.argv.index("--run") + 1]; out = f"runs/{run_id}"; dry = "--dry-run" in sys.argv
    plan = json.load(open(f"{out}/PLAN.json")); schema, prompt, h_sch, h_pr = frozen(); D = json.load(open("baseline/data/apps.json"))
    apps = {a[0]: dict(name=a[2], cat=a[1], hint=a[3]) for a in D["apps"]}; todo = [i for i in plan.get("ids") or [i for v in plan["phases"].values() for i in v] if not os.path.exists(f"baseline/p1_v1/pass1/{i}.json") and not os.path.exists(f"{out}/pass1/{i}.json")]
    print(f"run={run_id} planned={len(plan.get('ids') or [i for v in plan['phases'].values() for i in v])} to_process={len(todo)} prompt/schema hashes verified ({h_pr[:10]}.. / {h_sch[:10]}..)")
    miss = [i for i in (plan.get("ids") or [i for v in plan["phases"].values() for i in v]) if not os.path.exists(f"baseline/p1_v1/raw/{i}.json")]; print("missing cached retrievals:", miss)
    if dry:
        n = sum(len(json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]) + sum(len(x["use_urls"]) for x in (plan.get("extra_retrieval", {}).get(str(i)) or [])) for i in todo); print(f"[dry-run] no network. total cached pages to be read: {n}. approval file present: {os.path.exists(out + '/APPROVED.json')}"); sys.exit(0)
    if not os.path.exists(f"{out}/APPROVED.json"): sys.exit("REFUSING: no APPROVED.json (explicit user approval and per-model caps are required)")
    approved = json.load(open(f"{out}/APPROVED.json")); plan = dict(plan, ids=[i for ph in approved.get("phases", [1]) for i in plan["phases"][str(ph)]]); assert set(approved["models"]) == set(approved["cap_per_model"]), "every model needs a cap"
    key = None
    for l in open(".env"):
        if l.startswith("GEMINI_API_KEY="): key = l.strip().split("=", 1)[1]            # only this variable is ever read
    assert key, "GEMINI_API_KEY missing"
    print("STOPPED:", run(plan, approved, out, lambda m, p, s: call_gemini(m, p, s, key), schema, prompt, (h_sch, h_pr), apps, D["categories"]))
