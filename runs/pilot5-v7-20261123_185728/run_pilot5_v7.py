"""Runner v7 - controlled FIVE-APP extraction-only pilot (Gemini gemini-2.5-flash, Key 1 only). Separate from frozen runner v6 (unchanged).
Reuses v6 (src/run_p1.py, hash-verified) for: frozen() prompt/schema loading, check_quotes. Everything else here is new.
GATED: live execution needs <run_dir>/APPROVED.json whose manifest_sha256 matches the manifest. This file never creates it.
Sequential only: a single-writer lock plus a threading-safe pacer. Usage: python run_pilot5_v7.py --run-dir <dir> [--dry-run]"""
import os, sys, json, time, hashlib, datetime, threading, importlib.util, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sha = lambda b: hashlib.sha256(b).hexdigest()
iso = lambda t=None: datetime.datetime.fromtimestamp(t or time.time()).astimezone().isoformat(timespec="seconds")
MODEL, PROVIDER, CAP, MIN_GAP, MAX_RETRY, BACKOFF = "gemini-2.5-flash", "google_gemini", 8, 13.0, 2, (30.0, 60.0)   # hard-coded; manifest must agree
SERVER_5XX = (500, 502, 503, 504)

class Stop(Exception):
    def __init__(s, reason, **info): s.reason, s.info = reason, info

def load_v6():
    """Import the frozen runner copy at src/run_p1.py (byte-identical to the v6 recovery copy) after verifying its hash; module import has no side effects except chdir(ROOT)."""
    cwd = os.getcwd(); spec = importlib.util.spec_from_file_location("run_p1_v6", f"{ROOT}/src/run_p1.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); os.chdir(cwd); return m

def atomic_json(path, obj, ro=False):
    tmp = path + ".tmp"
    with open(tmp, "w") as f: json.dump(obj, f, indent=1); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
    if ro: os.chmod(path, 0o444)

# ---------------- pacing (monotonic in-process, wall-clock across restarts, thread-safe)
class Pacer:
    def __init__(s, gap, mono, wall, sleep, last_wall=None): s.gap, s.mono, s.wall, s.sleep, s.lock, s.last_mono, s.last_wall = gap, mono, wall, sleep, threading.Lock(), None, last_wall
    def wait(s):
        with s.lock:                                     # concurrent callers queue here; nobody can skip the wait
            if s.last_mono is not None: need = s.gap - (s.mono() - s.last_mono)
            elif s.last_wall is not None: el = s.wall() - s.last_wall; need = s.gap if el < 0 else s.gap - el   # resumed process: wall-clock, clock-went-backwards => full gap
            else: need = 0
            if need > 0: s.sleep(need)
            return s.stamp()
    def stamp(s): s.last_mono, s.last_wall = s.mono(), s.wall(); return s.last_wall

# ---------------- durable store: state.json (atomic), hash-chained append-only activity log
class Store:
    def __init__(s, out): s.out = out; s.state_p = f"{out}/state.json"; s.log_p = f"{out}/logs/activity.jsonl"; os.makedirs(f"{out}/logs", exist_ok=True); os.makedirs(f"{out}/pass1", exist_ok=True); os.makedirs(f"{out}/stops", exist_ok=True); s.prev = "0" * 64
    def read_log(s):
        rows, prev = [], "0" * 64
        if not os.path.exists(s.log_p): return rows
        for ln in open(s.log_p).read().splitlines():
            try: r = json.loads(ln)
            except Exception: raise Stop("refused_corrupt_activity_log", detail="unparseable line")
            if r.get("prev") != prev: raise Stop("refused_corrupt_activity_log", detail="hash chain broken (log was edited or truncated)")
            prev = sha(ln.encode()); rows.append(r)
        s.prev = prev; return rows
    def log(s, **k):
        ln = json.dumps({"t": iso(), "prev": s.prev, **k}); fd = os.open(s.log_p, os.O_WRONLY | os.O_APPEND | os.O_CREAT); os.write(fd, (ln + "\n").encode()); os.fsync(fd); os.close(fd); s.prev = sha(ln.encode())
    def load_state(s, log_rows):
        n_log = sum(r.get("ev") == "request_start" for r in log_rows)
        if os.path.exists(s.state_p):
            try: st = json.load(open(s.state_p))
            except Exception: raise Stop("refused_corrupt_state", detail="state.json unreadable; not guessing")
        elif log_rows: raise Stop("refused_corrupt_state", detail="log exists but state.json missing; not guessing")
        else: st = dict(attempts_total=0, per_app={}, last_request_wall=None, in_flight=None, consec_5xx=[], accept_missing_identity=False)
        st["attempts_total"] = max(st["attempts_total"], n_log)    # conservative: never lower the count
        return st
    def save(s, st): atomic_json(s.state_p, st)

# ---------------- classification (pure)
def norm_flat(t): return "".join(c for c in t.lower() if c.isalnum())
def classify_429(body):
    """-> daily_quota | rate_limit | ambiguous_429. Evidence = quotaId/quotaMetric/message text containing 'perday' / 'perminute' (case/space-insensitive). Both present => daily (conservative stop)."""
    t = norm_flat(body or ""); d, m = "perday" in t or "requestsperday" in t, "perminute" in t
    return "daily_quota" if d else ("rate_limit" if m else "ambiguous_429")
def classify(res):
    if res.get("exc"): return "network_error"
    h = res.get("http")
    if h == 200: return "ok" if isinstance(res.get("payload"), dict) else "malformed_response"
    if h == 429: return classify_429(res.get("body", ""))
    if h in SERVER_5XX: return "server_5xx"
    return "client_error"
def validate(v, sch, path="$"):
    """minimal validator for the frozen Gemini schema subset (OBJECT/ARRAY/STRING/enum/required, unknown keys rejected). -> list of problems"""
    t = sch["type"]; p = []
    if t == "OBJECT":
        if not isinstance(v, dict): return [f"{path}: not object"]
        p += [f"{path}.{k}: missing" for k in sch.get("required", []) if k not in v]; p += [f"{path}.{k}: unexpected key" for k in v if k not in sch["properties"]]
        for k, s2 in sch["properties"].items():
            if k in v: p += validate(v[k], s2, f"{path}.{k}")
    elif t == "ARRAY":
        if not isinstance(v, list): return [f"{path}: not array"]
        for i, x in enumerate(v): p += validate(x, sch["items"], f"{path}[{i}]")
    elif t == "STRING":
        if not isinstance(v, str): return [f"{path}: not string"]
        if "enum" in sch and v not in sch["enum"]: p.append(f"{path}: '{v}' not in enum")
    return p

# ---------------- the one real network function: model and key are NOT parameters (no fallback possible)
def make_gemini_call(key):
    def call(prompt, schema):
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema, "temperature": 0}}
        r = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent", json.dumps(body).encode(), {"content-type": "application/json", "x-goog-api-key": key})
        try:
            d = json.load(urllib.request.urlopen(r, timeout=150))
            try: return dict(http=200, payload=json.loads(d["candidates"][0]["content"]["parts"][0]["text"]), model_version=d.get("modelVersion"))
            except Exception: return dict(http=200, payload=None, model_version=d.get("modelVersion"), body=str(d)[:300])
        except urllib.error.HTTPError as e: return dict(http=e.code, body=e.read().decode()[:1500])
        except Exception as e: return dict(exc=type(e).__name__)
    return call

# ---------------- manifest / integrity
def check_manifest(M, run_dir):
    v6 = load_v6(); F = json.load(open(f"{ROOT}/runs/p1-v1f-gemini-20261124/FROZEN.json"))
    assert (M["provider"], M["model"], M["max_generation_requests"], M["min_seconds_between_requests"]) == (PROVIDER, MODEL, CAP, MIN_GAP), "manifest disagrees with runner constants"
    assert M["key_alias"] == "GEMINI_API_KEY" and not M["verification_included"] and not M["groq_used"] and M["execution_authorized"] is False
    assert sha(open(f"{ROOT}/src/run_p1.py", "rb").read()) == F["runner_sha256"] == M["v6_runner_sha256"], "v6 runner differs from frozen"
    assert sha(open(f"{ROOT}/runs/p1-v1f-gemini-20261124/PLAN.json", "rb").read()) == F["plan_sha256"], "frozen v1f plan changed"
    assert sha(open(__file__, "rb").read()) == M["runner_v7_sha256"], "v7 runner differs from manifest"
    sch, pr, h_sch, h_pr = v6.frozen(); assert (h_sch, h_pr) == (M["schema_sha256"], M["prompt_sha256"]); return v6, sch, pr

def build_prompt(v6, M, app, pr, plan):
    D = json.load(open(f"{ROOT}/baseline/data/apps.json")); a = {x[0]: dict(name=x[2], cat=x[1], hint=x[3]) for x in D["apps"]}[app["id"]]; assert a["name"] == app["name"], "registry name mismatch"
    raw = json.load(open(f"{ROOT}/baseline/p1_v1/raw/{app['id']}.json")); pages = list(raw["pages"]); top = []
    for ex in plan.get("extra_retrieval", {}).get(str(app["id"])) or []:
        xr = json.load(open(f"{ROOT}/{ex['raw']}")); use = set(ex["use_urls"]); xs = [e for e in xr[ex.get("list_key", "fetched")] if e["url"] in use and e.get("status") == "ok"]
        top.append(dict(path=ex["raw"], raw_sha256=sha(open(f"{ROOT}/{ex['raw']}", "rb").read()), pages=[dict(url=e["url"], sha256=e["sha256"], chars=len(e["text"]), used_chars=min(len(e["text"]), 9000)) for e in xs])); pages += [{"url": e["url"], "text": e["text"][:9000]} for e in xs]
    src = "\n\n".join(f"### {p['url']}\n{p['text']}" for p in pages)
    return pr.format(name=a["name"], cat=D["categories"][a["cat"] - 1], hint=a["hint"] or "none", src=src), pages, top

# ---------------- main execution (injectable call/clocks for offline tests)
def execute(run_dir, out, call, *, mono=time.monotonic, wall=time.time, sleep=time.sleep, dry_run=False, manifest_path=None):
    mp = manifest_path or f"{run_dir}/PILOT5_MANIFEST.json"; M = json.load(open(mp)); msha = sha(open(mp, "rb").read()); v6, schema, pr = check_manifest(M, run_dir); plan = json.load(open(f"{ROOT}/runs/p1-v1f-gemini-20261124/PLAN.json")); apps = M["apps"]
    lock = f"{out}/.lock"
    if dry_run:                                          # builds prompts only; `call` is never touched
        info = []; [info.append(dict(id=a["id"], prompt_chars=len(build_prompt(v6, M, a, pr, plan)[0]))) for a in apps]; return dict(dry_run=True, generation_calls=0, authorized=os.path.exists(f"{run_dir}/APPROVED.json"), apps=info)
    ap = f"{run_dir}/APPROVED.json"
    if not os.path.exists(ap): return dict(stopped="refused_no_authorization", info="APPROVED.json missing; no generation call possible")
    A = json.load(open(ap))
    if A.get("manifest_sha256") != msha or A.get("model") != MODEL or int(A.get("max_requests", 0)) != CAP: return dict(stopped="refused_authorization_mismatch", info="APPROVED.json must carry this manifest's sha256, model gemini-2.5-flash and max_requests 8")
    os.makedirs(out, exist_ok=True)
    try: fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd)   # single writer => sequential only
    except FileExistsError: return dict(stopped="refused_lock_held", info="another run holds .lock or crashed; human review")
    S = Store(out); st = None
    try:
        rows = S.read_log(); st = S.load_state(rows); pr_stop = latest_stop(out)
        for f in os.listdir(f"{out}/pass1"):                     # corrupted/partial checkpoints => stop, never guess
            if f.endswith(".tmp"): raise Stop("refused_corrupt_checkpoint", detail=f"partial write {f}")
            try: r = json.load(open(f"{out}/pass1/{f}")); assert r["id"] == int(f[:-5]) and r["model"] == MODEL
            except Exception: raise Stop("refused_corrupt_checkpoint", detail=f"unreadable/invalid {f}")
        if st["in_flight"]: raise Stop("refused_in_flight_request_unknown_outcome", detail=str(st["in_flight"]))
        if pr_stop and pr_stop["reason"] != "completed":
            rv = f"{out}/STOP_REVIEWED.json"
            if not os.path.exists(rv) or json.load(open(rv)).get("stop_sha256") != pr_stop["sha256"]: raise Stop("refused_previous_stop_not_reviewed", detail=pr_stop["reason"])
            st["accept_missing_identity"] = st["accept_missing_identity"] or bool(json.load(open(rv)).get("accept_missing_model_identity"))
        S.log(ev="run_start", runner="v7", manifest_sha256=msha, attempts_so_far=st["attempts_total"]); pacer = Pacer(MIN_GAP, mono, wall, sleep, st["last_request_wall"])
        for idx, app in enumerate(apps):
            i = app["id"]; cp = f"{out}/pass1/{i}.json"
            if os.path.exists(cp): continue                      # completed apps are never re-run
            prompt, pages, top = build_prompt(v6, M, app, pr, plan); retries = 0
            while True:
                if st["attempts_total"] >= CAP: raise Stop("budget_exhausted", app=i)
                t = pacer.wait(); st["attempts_total"] += 1; st["per_app"][str(i)] = st["per_app"].get(str(i), 0) + 1; st["last_request_wall"] = t; st["in_flight"] = dict(app=i, n=st["attempts_total"]); S.save(st)   # write-ahead: counted even if we crash
                S.log(ev="request_start", id=i, n_total=st["attempts_total"], n_app=st["per_app"][str(i)], model=MODEL)
                res = call(prompt, schema); st["in_flight"] = None; st["last_request_wall"] = pacer.stamp(); cat = classify(res); S.save(st)
                S.log(ev="request_end", id=i, category=cat, http=res.get("http"), exc=res.get("exc"), model_version=res.get("model_version"))
                if cat == "ok": break
                if cat == "daily_quota": raise Stop("daily_quota_429", app=i, http=429, category=cat)
                if cat == "ambiguous_429": raise Stop("ambiguous_429_human_review", app=i, http=429, category=cat, body=res.get("body", "")[:300])
                if cat == "rate_limit":
                    if retries >= MAX_RETRY: raise Stop("rate_limit_retries_exhausted", app=i, http=429, category=cat)
                    S.log(ev="backoff", id=i, seconds=BACKOFF[retries]); sleep(BACKOFF[retries]); retries += 1; continue
                if cat == "server_5xx":
                    st["consec_5xx"].append(i); S.save(st); S.log(ev="app_failed_not_cached", id=i, http=res["http"])
                    if len(set(st["consec_5xx"])) >= 2: raise Stop("two_consecutive_5xx_different_apps", app=i, http=res["http"], category=cat)
                    break
                raise Stop(cat, app=i, http=res.get("http"), category=cat, detail=(res.get("exc") or res.get("body") or "")[:200])
            if cat != "ok": continue                             # single 5xx: move on, app stays un-checkpointed
            mv = res.get("model_version")
            if mv is not None and mv != MODEL: atomic_json(f"{out}/stops/rejected_{i}.json", res); raise Stop("unexpected_model_identity", app=i, returned=mv)
            problems = validate(res["payload"], schema)
            if problems: atomic_json(f"{out}/stops/rejected_{i}.json", res); raise Stop("schema_violation", app=i, problems=problems[:10])
            pl = dict(res["payload"]); pl["evidence"] = v6.check_quotes(pl["evidence"], pages); bad = [e for e in pl["evidence"] if not (e["quote_found"] and e["url_in_sources"])]
            rec = dict(id=i, name=app["name"], category=app.get("category"), model=MODEL, pages_read=[p["url"] for p in pages], **pl, meta=dict(runner="v7", runner_sha256=M["runner_v7_sha256"], manifest_sha256=msha, prompt_sha256=M["prompt_sha256"], schema_sha256=M["schema_sha256"], temperature=0, key_id="GEMINI_API_KEY",
                        extracted_at=iso(), request_attempts=st["per_app"][str(i)], returned_model_version=mv, model_identity_verified=mv == MODEL, registry_provenance=app["provenance"], retrieval_topup=top, evidence_quote_failures=len(bad), pilot="smoke test, not an accuracy evaluation"))
            atomic_json(cp, rec, ro=True); st["consec_5xx"] = []; S.save(st); S.log(ev="done", id=i, evidence_failures=len(bad))
            if idx == 0 and bad: raise Stop("review_app1_evidence_quote_failure", app=i, failures=len(bad))
            if mv is None and not st["accept_missing_identity"]: raise Stop("model_identity_unverified_review_required", app=i, note="response carried no modelVersion; identity NOT verified")
        raise Stop("completed" if all(os.path.exists(f"{out}/pass1/{x['id']}.json") for x in apps) else "finished_with_uncheckpointed_apps")
    except Stop as s: return finish(out, S, st, s)
    finally: os.remove(lock)

def latest_stop(out):
    p = f"{out}/STOPPED.json"; return dict(json.load(open(p)), sha256=sha(open(p, "rb").read())) if os.path.exists(p) else None
def finish(out, S, st, s):
    if s.reason.startswith("refused_"): return dict(stopped=s.reason, info=s.info)         # startup refusal: nothing ran, so no stop record (keeps the reviewed stop's hash valid)
    rec = dict(reason=s.reason, at=iso(), app_id=s.info.get("app"), model=MODEL, total_generation_attempts=(st or {}).get("attempts_total"), per_app_attempts=(st or {}).get("per_app"), http_status=s.info.get("http"), category=s.info.get("category"), info={k: v for k, v in s.info.items() if k not in ("app", "http", "category")})
    n = len(os.listdir(f"{out}/stops")); atomic_json(f"{out}/stops/stop_{n:03d}.json", rec, ro=True); atomic_json(f"{out}/STOPPED.json", rec)
    try: S.log(ev="stop", reason=s.reason)
    except Exception: pass
    return dict(stopped=s.reason, record=rec)

if __name__ == "__main__":
    rd = os.path.abspath(sys.argv[sys.argv.index("--run-dir") + 1]); dry = "--dry-run" in sys.argv; out = f"{rd}/output"
    if dry: print(json.dumps(execute(rd, out, None, dry_run=True), indent=1)); sys.exit(0)
    if not os.path.exists(f"{rd}/APPROVED.json"): sys.exit("REFUSING: no APPROVED.json (explicit human approval of the manifest is required)")
    key = None
    for l in open(f"{ROOT}/.env"):
        if l.startswith("GEMINI_API_KEY="): key = l.strip().split("=", 1)[1]    # only this variable is ever read
    assert key, "GEMINI_API_KEY missing"; print(json.dumps(execute(rd, out, make_gemini_call(key)), indent=1))
