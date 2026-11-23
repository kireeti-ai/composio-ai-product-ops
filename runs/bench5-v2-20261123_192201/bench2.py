"""Benchmark v2 (versioned change set on top of bench v1; v1 files are imported/read, NEVER modified; v1 outputs are preserved).
Changes: (1) circuit breaker + corrected backoff (OpenRouter incident), (2) Gemini 2.5 staged run gated by the daily reset (capability request first), (3) strict evidence validation v2 (placeholder/stitched/off-page quotes rejected, per-claim support states,
unknown / not_found kept separate, MCP absence never inferred), (4) offline re-audit of the five v1 Groq outputs against FULL evidence, (5) P2-P4 hard-disabled.
Usage: python bench2.py audit | or_probe | gemini25 | report"""
import os, sys, re, json, time, glob, hashlib, importlib.util, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V1DIR = f"{ROOT}/runs/bench5-v1-20261123_191136"
spec = importlib.util.spec_from_file_location("bench_v1", f"{V1DIR}/bench.py"); B = importlib.util.module_from_spec(spec); sys.modules["bench_v1"] = B; spec.loader.exec_module(B)
iso, sha, atomic, APPS = B.iso, B.sha, B.atomic, B.APPS
DISABLED_ENV = ("GROQ_KEY_P1", "GROQ_KEY_P2", "GROQ_KEY_P3", "GROQ_KEY_P4")   # P1 = same org as GROQ_API_KEY (no extra capacity); P2-P4 disabled until the user confirms authorization
_secret = B.secret
def secret(name):
    if name in DISABLED_ENV: raise PermissionError(f"{name} is disabled until the user explicitly authorizes it")
    return _secret(name)
B.secret = secret                                            # B.scrub / adapters resolve secrets through this guard
def scrub(t):
    for n in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GROQ_API_KEY", "OPENROUTER_API_KEY", "COMPOSIO_API_KEY") + DISABLED_ENV:
        try: v = _secret(n); t = t.replace(v, "[REDACTED]") if len(v) > 12 else t
        except Exception: pass
    return t
B.scrub = scrub
PROVIDERS = {t: dict(c) for t, c in B.PROVIDERS.items()}; PROVIDERS["groq_orgA"]["min_gap_s"] = 0; PROVIDERS["openrouter_particle"]["min_gap_s"] = 10; PROVIDERS["gemini25_key1"]["min_gap_s"] = 13; PROVIDERS["gemini36_key2"]["min_gap_s"] = 13
GEMINI_RESET_UTC = datetime.datetime(2026, 11, 24, 8, 0, tzinfo=datetime.timezone.utc).timestamp()     # midnight Pacific (PST) = 13:30 IST on 2026-11-24
BACKOFF_BASE, BACKOFF_CAP, BREAKER_THRESHOLD, COOLDOWN0, COOLDOWN_CAP, MAX_OPENS = 30.0, 300.0, 2, 600.0, 3600.0, 3

class Log(B.Log):
    """v1 Log + hash chain continues across processes (v1 restarted the chain at each process start)."""
    def __init__(s, p):
        super().__init__(p)
        if os.path.exists(p) and os.path.getsize(p): s.prev = sha(open(p).read().splitlines()[-1])
# ---------------- circuit breaker (persisted)
class Breaker:
    """closed -> (2 consecutive rate-limit/5xx/network failures) -> open(cooldown 600 s, doubling, cap 3600) -> after cooldown: exactly ONE probe (half_open) -> success: closed | failure: open (doubled). After 3 opens: gave_up (human reset)."""
    def __init__(s, path, clock=time.time): s.path, s.clock = path, clock; s.d = json.load(open(path)) if os.path.exists(path) else {}
    def b(s, k): return s.d.setdefault(k, dict(state="closed", consec=0, opened_at=None, cooldown_s=COOLDOWN0, opens=0, probes=0))
    def save(s): atomic(s.path, s.d)
    def gate(s, k):
        """-> ('go'|'probe'|'wait'|'gave_up', seconds_remaining)"""
        b = s.b(k)
        if b["state"] == "closed": return "go", 0
        if b["state"] == "gave_up": return "gave_up", 0
        if b["state"] == "half_open": return ("wait", 0) if b.get("probe_started") else ("probe", 0)     # a probe that was granted but never sent is not consumed; a SENT probe allows no second request
        rem = b["opened_at"] + b["cooldown_s"] - s.clock()
        if rem > 0: return "wait", rem
        b["state"] = "half_open"; b["probes"] += 1; s.save(); return "probe", 0
    def probe_started(s, k): b = s.b(k); b["probe_started"] = True; s.save()
    def success(s, k): b = s.b(k); b.update(state="closed", consec=0, probe_started=False); s.save()
    def failure(s, k):
        b = s.b(k); b["consec"] += 1
        if b["state"] == "half_open" or b["consec"] >= BREAKER_THRESHOLD:
            b["opens"] += 1; b["cooldown_s"] = min(COOLDOWN_CAP, b["cooldown_s"] * 2 if b["opens"] > 1 else COOLDOWN0); b.update(state="gave_up" if b["opens"] > MAX_OPENS else "open", opened_at=s.clock(), probe_started=False)
        s.save(); return b["state"]
def retry_after_s(res):
    ra = res["headers"].get("retry-after") or res["headers"].get("Retry-After"); v = None
    try: v = float(ra) if ra is not None else None
    except ValueError: pass
    m = re.search(r'"retry_after_seconds"\s*:\s*([0-9.]+)', res.get("error") or "")
    return max(v or 0, float(m.group(1)) if m else 0) or None
def backoff_s(ra, consec): return min(BACKOFF_CAP, max(BACKOFF_BASE, ra or 0) * (2 ** max(0, consec - 1)))      # provider 'retry after 1 s' never shortens the 30 s floor

# ---------------- strict evidence validation v2
norm = lambda t: re.sub(r"[\s​]+", " ", re.sub(r"[*_`#>\[\]()]", "", t)).strip().lower()
PLACEHOLDERS = {"", "unknown", "none", "n/a", "na", "not found", "none found", "none_found", "no evidence", "not specified", "null", "not available", "no quote"}
ACCESS_ANCHORS = {"self_serve_free": r"\bfree\b|self[- ]serve|sign up|register|create (an? )?(app|account|api key)|get (your )?(own )?(api )?(key|token|id)|obtain", "self_serve_trial_or_paid_plan": r"paid|\bplans?\b|subscription|trial|pricing|upgrade|premium|enterprise", "approval_or_review_required": r"review|approv|apply|application|request access|permission|verification|vetted", "partner_or_contact_sales": r"partner|contact (us|sales)|sales|inquir|enterprise", "no_public_api": r"no (public )?api|not (publicly )?available|private api"}
def anchors():
    sys.path.insert(0, f"{ROOT}/src"); import verify_v2 as V; sys.path.pop(0); return V.ANCHOR
def quote_issues(e, full_by_url, shown_by_url):
    q = e.get("quote", ""); nq = norm(q); iss = []
    if nq in PLACEHOLDERS or len(nq) < 20 or len(nq.split()) < 4: iss.append("placeholder_or_too_short")
    if re.search(r"\.\.\.|…", q): iss.append("stitched_ellipsis")
    if len(q) > 400: iss.append("too_long")
    u = e.get("url")
    if u not in full_by_url: iss.append("url_not_in_sources")
    elif nq and nq not in full_by_url[u]: iss.append("not_contiguous_in_cited_page")        # catches stitched / unrelated / paraphrased text
    elif nq and nq not in shown_by_url.get(u, ""): iss.append("not_in_shown_evidence")
    return iss
def validate_v2(obj, shown_pages, full_pages):
    """-> dict(evidence=[{..., issues, valid}], claims=[{field,item,state}], counts). States: unknown | not_found_in_provided_evidence (MCP only; NOT absence) | supported_lexical | unsupported | needs_human. 'supported_lexical' = valid verbatim contiguous quote in the cited page that mentions item-specific terms; it is NOT a semantic correctness judgement."""
    A = anchors(); full = {p["url"]: norm(p["text"]) for p in full_pages}; shown = {p["url"]: norm(p["text"]) for p in shown_pages}; ev = []
    for e in obj["evidence"]: iss = quote_issues(e, full, shown); ev.append(dict(e, issues=iss, valid=not iss))
    claims = []
    for f in ("auth_methods", "access", "api_types", "existing_mcp"):
        v = obj[f]; items = v if isinstance(v, list) else [v]
        for it in items:
            if it == "unknown": st = "unknown"
            elif f == "existing_mcp" and it == "none_found": st = "not_found_in_provided_evidence"
            else:
                good = [e for e in ev if e["field"] == f and e["valid"]]; rx = ACCESS_ANCHORS.get(it) if f == "access" else A[f].get(it)
                if it == "other" or rx is None: st = "needs_human" if good else "unsupported"
                else: st = "supported_lexical" if any(re.search(rx, e["quote"], re.I) for e in good) else "unsupported"
            claims.append(dict(field=f, item=it, state=st))
    c = {}
    for x in claims: c[x["state"]] = c.get(x["state"], 0) + 1
    return dict(evidence=ev, claims=claims, claim_state_counts=c, evidence_total=len(ev), evidence_valid=sum(e["valid"] for e in ev), issue_counts={k: sum(k in e["issues"] for e in ev) for k in ("placeholder_or_too_short", "stitched_ellipsis", "too_long", "url_not_in_sources", "not_contiguous_in_cited_page", "not_in_shown_evidence")})

def schema_check(text):
    vr = dict(json_ok=False, schema_ok=False, errors=[])
    try: obj = json.loads(text); vr["json_ok"] = True
    except Exception as e: vr["errors"].append("invalid_json: " + str(e)[:100]); return vr, None
    try: B.AppResearch.model_validate(obj); vr["schema_ok"] = True
    except B.ValidationError as e: vr["errors"] += [f"{'.'.join(map(str, x['loc']))}: {x['type']}" for x in e.errors()[:8]]
    return vr, obj
# ---------------- runner v2 (breaker + backoff + validation v2). Same adapter/quota/log code as v1.
def run_provider2(tag, cfg, apps, prompts, shown_map, full_map, schema_g, call, quota, breaker, out, log, sleep=time.sleep, key=None, clock=time.time):
    d = f"{out}/outputs/{tag}"; os.makedirs(d, exist_ok=True); used = 0; k = cfg["bucket"]; done = lambda i: os.path.exists(f"{d}/{i}.json") or any("json_validate_failed" in open(f).read() for f in glob.glob(f"{d}/failed_{i}_*.json"))     # an app whose output failed JSON validation is not re-sent
    for i, name in apps:
        if done(i): continue
        remaining_apps = sum(not done(j) for j, _ in apps) - 1; tries = 0
        while True:
            if used >= cfg["cap"]: log(ev="stop", tag=tag, reason="provider_call_cap", app=i, used=used); return "cap_reached"
            g, rem = breaker.gate(k)
            if g == "gave_up": log(ev="stop", tag=tag, reason="breaker_gave_up"); return "breaker_gave_up"
            if g == "wait": log(ev="stop", tag=tag, reason="breaker_open", seconds_remaining=round(rem)); return "breaker_open"
            est = B.est_tokens(len(prompts[i])) + cfg["max_out"]
            try: w = quota.wait_needed(k, est)
            except B.QuotaStop as e: log(ev="stop", tag=tag, reason="quota", app=i, detail=str(e)); return "quota_stop"
            reqs = quota.b(k)["req"]
            if reqs and cfg.get("min_gap_s"): w = max(w, reqs[-1] + cfg["min_gap_s"] - quota.clock())
            if w > 0: log(ev="wait", tag=tag, seconds=round(w, 1)); sleep(w)
            if g == "probe": breaker.probe_started(k)
            quota.reserve(k, est); used += 1; log(ev="request_start", tag=tag, app=i, model=cfg["model"], n=used, est_tokens=est, probe=g == "probe")
            res = call(cfg, prompts[i], schema_g, key); quota.settle(k, (res["tin"] or 0) + (res["tout"] or 0) if res["tin"] is not None else None)
            if res["headers"]: quota.observe(k, headers=res["headers"], app=i)
            cat = "ok" if res["http"] == 200 and res["text"] else B.classify_error(res); ra = retry_after_s(res)
            log(ev="request_end", tag=tag, app=i, model=cfg["model"], model_returned=res["model_returned"], http=res["http"], category=cat, latency=round(res["latency"], 2), tin=res["tin"], tout=res["tout"], cost=res["cost"], retry_after=ra)
            if res["cost"] and float(res["cost"]) > 0: log(ev="stop_all", reason="non_zero_cost"); raise B.StopAll("non-zero cost")
            if cat == "payment_required": log(ev="stop_all", reason="payment_required"); raise B.StopAll("payment required")
            if cat == "ok":
                if not B.model_ok(cfg, res["model_returned"]): log(ev="stop", tag=tag, reason="model_mismatch", returned=res["model_returned"]); return "model_mismatch"
                breaker.success(k); break
            atomic(f"{d}/failed_{i}_{used}.json", dict(tag=tag, app=i, name=name, status="failed", category=cat, http=res["http"], error=scrub(res["error"] or ""), model=cfg["model"], attempt=used, retry_after=ra, at=iso()))
            if cat == "daily_quota": quota.block(k, 86400 if not ra else ra, "daily"); log(ev="stop", tag=tag, reason="daily_quota", app=i); return "daily_quota"
            if cat == "client_error" and "json_validate_failed" in (res["error"] or ""): log(ev="app_failed", tag=tag, app=i, category="generation_invalid_json"); break       # app-specific: model output violated the JSON schema; recorded, not retried (same input => same output), batch continues
            if cat in ("ambiguous_429", "client_error"): log(ev="stop", tag=tag, reason="needs_human_review", category=cat, app=i); return "needs_human_review"
            st = breaker.failure(k); tries += 1
            if st != "closed": log(ev="stop", tag=tag, reason="breaker_" + st, category=cat, app=i); return "breaker_" + st
            bo = backoff_s(ra, breaker.b(k)["consec"]); log(ev="backoff", tag=tag, app=i, seconds=bo, category=cat); sleep(bo)
            if tries >= 2 or used + remaining_apps >= cfg["cap"]: log(ev="app_failed", tag=tag, app=i, category=cat); break      # a retry may not starve apps not yet attempted
        if cat != "ok": continue
        vr, obj = schema_check(res["text"])                                              # schema/json only; evidence judged by validate_v2 below
        ok2 = validate_v2(obj, shown_map[i], full_map[i]) if vr["schema_ok"] else None
        atomic(f"{d}/{i}.json", dict(tag=tag, app=i, name=name, status="ok" if vr["schema_ok"] else "invalid", model=cfg["model"], model_returned=res["model_returned"], model_identity_verified=res["model_returned"] is not None, attempts_for_app=used, latency_s=round(res["latency"], 2), tokens_in=res["tin"], tokens_out=res["tout"], cost_usd=res["cost"] or 0, validation_schema=vr, validation_v2=ok2, output=obj, raw_text=None if vr["schema_ok"] else scrub(res["text"])[:6000], prompt_sha256=sha(prompts[i]), at=iso())); log(ev="checkpoint", tag=tag, app=i)
    return "completed"

# ---------------- capability request + gated Gemini stage
TINY_SCHEMA = {"type": "OBJECT", "properties": {"ok": {"type": "BOOLEAN"}}, "required": ["ok"]}
def capability_request(tag, cfg, quota, breaker, log, call, key, clock=time.time, sleep=time.sleep, gate=None):
    """ONE small structured generation request. Returns True only on HTTP 200 + parseable {"ok":true} + matching model identity."""
    k = cfg["bucket"]; g = gate or breaker.gate(k)[0]
    if g != "go" and g != "probe": log(ev="capability_skipped", tag=tag, gate=g); return False
    try: w = quota.wait_needed(k, 200)
    except B.QuotaStop as e: log(ev="capability_skipped", tag=tag, reason=str(e)); return False
    if w > 0: sleep(w)
    if g == "probe": breaker.probe_started(k)
    quota.reserve(k, 200); log(ev="capability_start", tag=tag, model=cfg["model"]); res = call(dict(cfg, max_out=64), 'Return the JSON object {"ok": true}.', TINY_SCHEMA, key); quota.settle(k, (res["tin"] or 0) + (res["tout"] or 0) if res["tin"] is not None else None)
    cat = "ok" if res["http"] == 200 and res["text"] else B.classify_error(res); good = False
    if cat == "ok":
        try: good = json.loads(res["text"]).get("ok") is True and B.model_ok(cfg, res["model_returned"])
        except Exception: good = False
    log(ev="capability_end", tag=tag, model=cfg["model"], model_returned=res["model_returned"], http=res["http"], category=cat, ok=good, latency=round(res["latency"], 2))
    if good: breaker.success(k)
    else:
        if cat == "daily_quota": quota.block(k, 86400, "daily")
        elif cat in ("rate_limit", "server_5xx", "network_error"): breaker.failure(k)
        od = f"{os.path.dirname(os.path.dirname(log.p))}/outputs/{tag}"; os.makedirs(od, exist_ok=True); atomic(f"{od}/capability_failed_{int(clock())}.json", dict(tag=tag, category=cat, http=res["http"], error=scrub(res["error"] or ""), at=iso()))
    return good
def gemini_stage(tag, cfg, prompts, shown, full, schema_g, call, quota, breaker, out, log, key, clock=time.time, sleep=time.sleep):
    if clock() < GEMINI_RESET_UTC: log(ev="gemini_stage_refused", tag=tag, reason="before daily reset 2026-11-24 08:00 UTC (13:30 IST)"); return "before_reset"
    os.makedirs(f"{out}/outputs/{tag}", exist_ok=True)
    if not capability_request(tag, cfg, quota, breaker, log, call, key, clock, sleep): return "capability_failed"
    return run_provider2(tag, dict(cfg, cap=5), APPS, prompts, shown, full, schema_g, call, quota, breaker, out, log, sleep=sleep, key=key, clock=clock)

# ---------------- audit of the five v1 Groq outputs against FULL evidence (offline)
MCP = r"\bmcp\b|model context protocol"
def audit():
    P = {}; out = dict(created=iso(), method="offline deterministic re-validation (validate_v2) + MCP mention search over FULL and SHOWN evidence; NOT independent human ground truth", apps=[])
    for i, name in APPS:
        r = json.load(open(f"{V1DIR}/outputs/groq_orgA/{i}.json")); shown = json.load(open(f"{V1DIR}/bundles/{i}.json"))["pages"]; full = json.load(open(f"{V1DIR}/bundles_full/{i}.json"))["pages"]; v = validate_v2(r["output"], shown, full)
        ms = lambda pages: [dict(url=p["url"], ctx=norm(p["text"])[max(0, m.start() - 120): m.end() + 160]) for p in pages for m in re.finditer(MCP, norm(p["text"]))]
        mf, msn = ms(full), ms(shown)
        out["apps"].append(dict(id=i, name=name, existing_mcp_v1=r["output"]["existing_mcp"], mcp_mentions_in_full_evidence=len(mf), mcp_mentions_in_shown_evidence=len(msn), mcp_mentions_dropped_by_reduction=len(mf) - len(msn), mcp_full_examples=mf[:6], validation_v2=v, v1_validation=dict(quote_found=r["validation"]["quote_found"], n_evidence=r["validation"]["n_evidence"])))
    atomic(f"{HERE}/reports/GROQ_V1_AUDIT.json", out); return out

# ---------------- reduction v2: guarantees every MCP mention is kept (v1 dropped Ahrefs' MCP nav block); same budget rule otherwise
MCP_WIN = 350
def reduce_pages_v2(pages, budget=B.RED_BUDGET, win_budget=None):
    """v1 blocks + a +-350 char window (capped 1400 chars) around every MCP mention that the v1 blocks did NOT already keep (max 3 windows/page)."""
    base = B.reduce_pages(pages, budget); by = {p["url"]: p["text"] for p in base}; out = []; wused = 0
    for p in pages:
        txt = by.get(p["url"], ""); nt = norm(txt); spans = []
        for m in re.finditer(MCP, p["text"], re.I):
            if norm(p["text"][max(0, m.start() - 60): m.end() + 60]) in nt: continue            # mention already visible in a kept block
            a, b = max(0, m.start() - MCP_WIN), min(len(p["text"]), m.end() + MCP_WIN)
            if spans and a <= spans[-1][1]: spans[-1][1] = min(b, spans[-1][0] + 1400)
            else: spans.append([a, min(b, a + 1400)])
        add = []
        for a, b in spans[:3]:
            if win_budget is not None and wused + (b - a) > win_budget: break              # optional global cap on window text (None = v2 behaviour used so far)
            add.append(p["text"][a:b]); wused += b - a
        if txt or add: out.append({"url": p["url"], "text": "\n\n".join([t for t in (txt,) if t] + add)})
    return out
class Quota2(B.Quota):
    """v1 quota + daily-token (TPD) soft limit when the bucket config has tpd (source recorded in manifest: published docs, NOT header-observed)."""
    def wait_needed(s, k, est):
        w = super().wait_needed(k, est); L = s.limits[k]
        if L.get("tpd"):
            used = sum(e[1] for e in s.b(k)["tok"]); 
            if used + est > int(L["tpd"] * 0.9): raise B.QuotaStop(f"daily token budget: used {used} + est {est} > 90% of TPD {L['tpd']}")
        return w
def make_ctx(call=None, clock=time.time):
    lim = {c["bucket"]: dict(c["limits"], **({"tpd": 200000} if t == "groq_orgA" else {})) for t, c in PROVIDERS.items()}
    return Quota2(f"{HERE}/quota.json", lim, clock=clock), Breaker(f"{HERE}/breaker.json", clock=clock), Log(f"{HERE}/logs/requests_v2.jsonl")
def seed_or_breaker(breaker):
    """OpenRouter incident: 5 consecutive upstream 429s in v1 (log). Seed the breaker OPEN from the last failure time, cooldown 600 s (documented)."""
    k = PROVIDERS["openrouter_particle"]["bucket"]
    if k in breaker.d: return
    last = [json.loads(l) for l in open(f"{V1DIR}/logs/requests.jsonl") if '"tag": "openrouter_particle"' in l and '"request_end"' in l][-1]; t = datetime.datetime.fromisoformat(last["t"]).timestamp()
    breaker.d[k] = dict(state="open", consec=5, opened_at=t, cooldown_s=COOLDOWN0, opens=1, probes=0, seeded_from="bench5-v1 log: 5 consecutive 429 fleet_capacity_exhausted"); breaker.save()
def load_v1_bundles():
    P, SH, FU = {}, {}, {}
    for i, _ in APPS: b = json.load(open(f"{V1DIR}/bundles/{i}.json")); P[i], SH[i] = b["prompt"], b["pages"]; FU[i] = json.load(open(f"{V1DIR}/bundles_full/{i}.json"))["pages"]
    return P, SH, FU
if __name__ == "__main__":
    a = sys.argv[1:]; cmd = a[0] if a else ""
    if cmd == "audit":
        o = audit()
        for x in o["apps"]: print(x["id"], x["name"], "mcp_v1=", x["existing_mcp_v1"], "full_mentions=", x["mcp_mentions_in_full_evidence"], "shown=", x["mcp_mentions_in_shown_evidence"], "claims=", x["validation_v2"]["claim_state_counts"], "evidence valid", x["validation_v2"]["evidence_valid"], "/", x["validation_v2"]["evidence_total"])
    elif cmd == "reduction_v2":
        P, SH, FU = load_v1_bundles(); res = []
        for i, n in APPS:
            r2 = reduce_pages_v2(FU[i]); cnt = lambda pg: sum(len(re.findall(MCP, p["text"], re.I)) for p in pg); res.append(dict(id=i, name=n, mcp_full=cnt(FU[i]), mcp_v1=cnt(SH[i]), mcp_v2=cnt(r2), chars_v1=sum(len(p["text"]) for p in SH[i]), chars_v2=sum(len(p["text"]) for p in r2)))
        atomic(f"{HERE}/reports/REDUCTION_V2_IMPACT.json", res); print(json.dumps(res))
    elif cmd in ("or_probe", "gemini25"):
        quota, breaker, log = make_ctx(); tag = "openrouter_particle" if cmd == "or_probe" else "gemini25_key1"; cfg = PROVIDERS[tag]; os.makedirs(f"{HERE}/outputs/{tag}", exist_ok=True)
        if cmd == "or_probe":
            seed_or_breaker(breaker); g, rem = breaker.gate(cfg["bucket"])
            if g == "wait": print(f"OPEN: cooldown remaining {round(rem)} s; no request made"); sys.exit(0)
            if g == "gave_up": print("breaker gave up; human reset required"); sys.exit(0)
            ok = capability_request(tag, dict(cfg, cap=1), quota, breaker, log, B.adapter_call, secret(cfg["key_env"]), gate=g); print(tag, "capability probe ok:", ok, "breaker:", breaker.b(cfg["bucket"])["state"])
        else:
            P, SH, FU = load_v1_bundles(); v6 = B.load_frozen()[1]; schema = B.load_frozen()[2]
            print(tag, gemini_stage(tag, cfg, P, SH, FU, schema, B.adapter_call, quota, breaker, HERE, log, secret(cfg["key_env"])))
