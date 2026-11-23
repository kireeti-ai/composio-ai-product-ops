"""Provider-independent five-app BENCHMARK (extraction only). Python stdlib HTTP (no provider SDK is installed; none is invented) + pydantic v2 (installed).
Reuses frozen v1f prompt/schema (via runner v6 frozen()) and runner-v7 build_prompt (evidence assembly) WITHOUT modifying either. This benchmark is pipeline/model evaluation, NOT an accuracy claim.
Usage: python bench.py capability | build | run <provider_tag> | report"""
import os, sys, re, json, time, hashlib, importlib.util, urllib.request, urllib.error, datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, ValidationError
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sha = lambda b: hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()
iso = lambda t=None: datetime.datetime.fromtimestamp(t or time.time()).astimezone().isoformat(timespec="seconds")
APPS = [(27, "Telegram"), (32, "Meta Ads"), (41, "Shopify"), (53, "Ahrefs"), (61, "GitHub")]
PROVIDERS = {   # tag -> config. rpm for Groq/OpenRouter are CONSERVATIVE ASSUMPTIONS (not observed); tpm/rpd are observed (probe v2).
 "groq_orgA": dict(adapter="groq", model="openai/gpt-oss-120b", key_env="GROQ_API_KEY", bucket="groq:orgA:openai/gpt-oss-120b", limits=dict(rpm=10, tpm=8000, rpd=1000), cap=5, max_out=2000, note="existing key + P1 share this one bucket; P2-P4 are NOT used in this benchmark"),
 "openrouter_particle": dict(adapter="openrouter", model="particle-ai/particle-1:free", key_env="OPENROUTER_API_KEY", bucket="openrouter:main:particle-ai/particle-1:free", limits=dict(rpm=6, tpm=None, rpd=50), cap=5, max_out=2500, note="free-tier 50 req/day (observed via /key); also counts other free-model use today"),
 "gemini25_key1": dict(adapter="gemini", model="gemini-2.5-flash", key_env="GEMINI_API_KEY", bucket="gemini:key1:gemini-2.5-flash", limits=dict(rpm=5, tpm=250000, rpd=20), cap=5, max_out=8192, note="deferred until daily reset evidence; frozen model of the original plan"),
 "gemini36_key2": dict(adapter="gemini", model="gemini-3.6-flash", key_env="GEMINI_API_KEY_2", bucket="gemini:key2:gemini-3.6-flash", limits=dict(rpm=5, tpm=250000, rpd=20), cap=1, max_out=8192, note="1 optional capability test only; NOT adoptable without evaluation")}
RED_BUDGET, RED_BLOCK, RED_PER_PAGE = 12000, 1200, 5     # reduction-v1: same rule for every app and provider
KW = r"\b(api|oauth|token|api[- ]?key|authenticat|authoriz|access|mcp|model context|rest|graphql|webhook|sdk|bot|rate limit|pricing|free|plan|approv|review|partner|developer|credential|scope|endpoint|self[- ]serve|sign up|register)\w*"
class StopAll(Exception): pass
class StopProvider(Exception): pass
class QuotaStop(StopProvider): pass

# ---------------- pydantic model of the FROZEN schema (enum equality is unit-tested against the frozen schema)
Auth = Literal["oauth2", "api_key", "basic", "bearer_token", "jwt_or_signed", "other", "unknown"]
class Ev(BaseModel):
    model_config = ConfigDict(extra="forbid"); field: str; url: str; quote: str
class AppResearch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    one_liner: str; auth_methods: List[Auth]; access: Literal["self_serve_free", "self_serve_trial_or_paid_plan", "approval_or_review_required", "partner_or_contact_sales", "no_public_api", "unknown"]; access_note: str
    api_types: List[Literal["rest", "graphql", "soap", "sdk_or_cli_only", "websocket", "none", "unknown"]]; api_breadth: Literal["narrow", "medium", "broad", "unknown"]; existing_mcp: Literal["official", "community", "none_found", "unknown"]
    buildability: Literal["yes", "yes_with_caveats", "no", "unknown"]; blocker: str; evidence: List[Ev]
def json_schema_from_gemini(s):
    """Gemini OBJECT/ARRAY/STRING schema -> standard JSON Schema (lowercase types, additionalProperties false)."""
    t = s["type"].lower(); o = {"type": t}
    if t == "object": o["properties"] = {k: json_schema_from_gemini(v) for k, v in s["properties"].items()}; o["required"] = s.get("required", []); o["additionalProperties"] = False
    if t == "array": o["items"] = json_schema_from_gemini(s["items"])
    if "enum" in s: o["enum"] = s["enum"]
    return o

# ---------------- evidence reduction (deterministic, documented)
def reduce_pages(pages, budget=RED_BUDGET):
    scored = []
    for pi, p in enumerate(pages):
        blocks = [b.strip() for b in re.split(r"\n\s*\n|\n(?=#)", p["text"]) if len(b.strip()) >= 40]
        for bi, b in enumerate(blocks): scored.append((len(re.findall(KW, b, re.I)) + (3 if re.search(r"\bmcp\b|model context protocol", b, re.I) else 0), pi, bi, b[:RED_BLOCK]))
    keep, used, per = set(), 0, {}
    for sc, pi, bi, b in sorted(scored, key=lambda x: (-x[0], x[1], x[2])):
        if sc == 0 or per.get(pi, 0) >= RED_PER_PAGE or used + len(b) > budget: continue
        keep.add((pi, bi)); per[pi] = per.get(pi, 0) + 1; used += len(b)
    out = []
    for pi, p in enumerate(pages):
        bl = [b for sc, i, bi, b in sorted(scored, key=lambda x: (x[1], x[2])) if i == pi and (i, bi) in keep]
        if bl: out.append({"url": p["url"], "text": "\n\n".join(bl)})
    return out
est_tokens = lambda chars: int(chars / 3.2) + 1          # conservative (real tokenizers average ~4 chars/token on English prose)

# ---------------- quota manager: per (provider, account, model) bucket; rolling windows; persisted
class Quota:
    def __init__(s, path, limits, clock=time.time):
        s.path, s.limits, s.clock = path, limits, clock; s.d = json.load(open(path)) if os.path.exists(path) else {}
    def b(s, k): return s.d.setdefault(k, dict(req=[], tok=[], blocked_until=0, blocked_reason=None, observations=[]))
    def save(s): tmp = s.path + ".tmp"; json.dump(s.d, open(tmp, "w"), indent=1); os.replace(tmp, s.path)
    def wait_needed(s, k, est):
        """-> seconds to wait before a request of `est` tokens fits; raises QuotaStop when it can never fit today."""
        L, b, now = s.limits[k], s.b(k), s.clock(); b["req"] = [t for t in b["req"] if now - t < 86400]; b["tok"] = [e for e in b["tok"] if now - e[0] < 86400]
        if b["blocked_until"] > now and b["blocked_reason"] == "daily": raise QuotaStop(f"daily quota block until {iso(b['blocked_until'])}")
        w = max(0.0, b["blocked_until"] - now)
        if L.get("rpd") and len(b["req"]) >= L["rpd"]: raise QuotaStop("daily request limit reached")
        if L.get("rpm"):
            rec = sorted(t for t in b["req"] if now - t < 60)
            if len(rec) >= L["rpm"]: w = max(w, rec[len(rec) - L["rpm"]] + 60 - now)
        if L.get("tpm"):
            cap = int(L["tpm"] * 0.9)
            if est > cap: raise QuotaStop(f"request estimate {est} tokens exceeds 90% of TPM {L['tpm']}: can never be sent")
            ev = sorted(e for e in b["tok"] if now - e[0] < 60); tot = sum(e[1] for e in ev)
            for e in ev:
                if tot + est <= cap: break
                tot -= e[1]; w = max(w, e[0] + 60 - now)
        return w
    def reserve(s, k, est): b = s.b(k); b["req"].append(s.clock()); b["tok"].append([s.clock(), est]); s.save()
    def settle(s, k, actual):   # replace the reservation of the latest request by actual tokens (never below 0)
        b = s.b(k)
        if b["tok"] and actual is not None: b["tok"][-1][1] = actual
        s.save()
    def observe(s, k, **o): b = s.b(k); b["observations"].append(dict(t=iso(s.clock()), **o)); s.save()
    def block(s, k, seconds, reason): b = s.b(k); b["blocked_until"] = max(b["blocked_until"], s.clock() + seconds); b["blocked_reason"] = reason; s.save()

# ---------------- secrets (env first, then .env), never printed
_ENV = None
def secret(name):
    global _ENV
    if os.environ.get(name): return os.environ[name]
    if _ENV is None:
        _ENV = {}
        for l in open(f"{ROOT}/.env"):
            if "=" in l and not l.startswith("#"): k, v = l.strip().split("=", 1); _ENV[k] = v
    return _ENV[name]
def scrub(t, names=("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GROQ_API_KEY", "GROQ_KEY_P1", "GROQ_KEY_P2", "GROQ_KEY_P3", "GROQ_KEY_P4", "OPENROUTER_API_KEY", "COMPOSIO_API_KEY")):
    for n in names:
        try: v = secret(n); t = t.replace(v, "[REDACTED]") if len(v) > 12 else t
        except Exception: pass
    return t

# ---------------- provider adapters (raw HTTP; shapes taken from existing v6 code and probe v2 observations)
def http(url, headers, body, timeout=150):
    r = urllib.request.Request(url, json.dumps(body).encode(), {"content-type": "application/json", "user-agent": "research-agent/0.1", **headers}); t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f: return f.status, json.loads(f.read().decode()), dict(f.headers), time.time() - t0
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:1500], dict(e.headers), time.time() - t0
    except Exception as e: return None, type(e).__name__, {}, time.time() - t0
def adapter_call(cfg, prompt, schema_g, key):
    """-> dict(http, text, tin, tout, model_returned, headers, latency, cost, error). One request, no retry, model fixed by cfg."""
    m, js = cfg["model"], json_schema_from_gemini(schema_g)
    if cfg["adapter"] == "gemini":
        st, d, h, dt = http(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", {"x-goog-api-key": key}, {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema_g, "temperature": 0, "maxOutputTokens": cfg["max_out"]}})
        if st == 200:
            try: um = d.get("usageMetadata", {}); return dict(http=200, text=d["candidates"][0]["content"]["parts"][0]["text"], tin=um.get("promptTokenCount"), tout=(um.get("candidatesTokenCount") or 0) + (um.get("thoughtsTokenCount") or 0), model_returned=d.get("modelVersion"), headers={}, latency=dt, cost=0.0, error=None)
            except Exception: return dict(http=200, text=None, tin=None, tout=None, model_returned=d.get("modelVersion"), headers={}, latency=dt, cost=0.0, error="no candidate text: " + str(d)[:300])
    else:
        body = {"model": m, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens" if cfg["adapter"] == "openrouter" else "max_completion_tokens": cfg["max_out"], "response_format": {"type": "json_schema", "json_schema": {"name": "app_research", "schema": js}}}
        if cfg["adapter"] == "groq": body["reasoning_effort"] = "low"; url = "https://api.groq.com/openai/v1/chat/completions"
        else: url = "https://openrouter.ai/api/v1/chat/completions"
        st, d, h, dt = http(url, {"authorization": "Bearer " + key}, body)
        if st == 200:
            try: u = d.get("usage", {}); return dict(http=200, text=d["choices"][0]["message"]["content"], tin=u.get("prompt_tokens"), tout=u.get("completion_tokens"), model_returned=d.get("model"), headers={k: v for k, v in h.items() if k.lower().startswith(("x-ratelimit", "retry-after"))}, latency=dt, cost=u.get("cost", 0) or 0, error=None)
            except Exception: return dict(http=200, text=None, tin=None, tout=None, model_returned=d.get("model"), headers={}, latency=dt, cost=0.0, error="no choices: " + str(d)[:300])
    return dict(http=st, text=None, tin=None, tout=None, model_returned=None, headers={k: v for k, v in h.items() if k.lower().startswith(("x-ratelimit", "retry-after"))}, latency=dt, cost=0.0, error=(d if isinstance(d, str) else json.dumps(d))[:1200])
def classify_error(res):
    h, e = res["http"], (res["error"] or "").lower().replace("_", " ").replace("-", " ")
    if h is None: return "network_error"
    if h == 402 or "payment required" in e or "insufficient credit" in e: return "payment_required"
    if h == 429: return "daily_quota" if re.search(r"per ?day|daily", e) else ("rate_limit" if re.search(r"per ?minute|rate.?limit|temporarily", e) else "ambiguous_429")
    if h in (500, 502, 503, 504): return "server_5xx"
    return "client_error"
def model_ok(cfg, returned): return returned is None or returned.split(":")[0] == cfg["model"].split(":")[0]
def or_text_models(models):
    """OpenRouter filter: free (price 0), text output, text input, NOT music/image/audio/video generation."""
    out = []
    for m in models:
        a = m.get("architecture", {}); p = m.get("pricing", {}); outm, inm = a.get("output_modalities") or [], a.get("input_modalities") or []
        if float(p.get("prompt", 1)) == 0 and float(p.get("completion", 1)) == 0 and outm == ["text"] and "text" in inm and not re.search(r"lyria|image|audio|tts|music|video|embed", m["id"], re.I): out.append(m["id"])
    return out

# ---------------- logging / checkpoints / validation
class Log:
    def __init__(s, p): s.p, s.prev = p, "0" * 64; os.makedirs(os.path.dirname(p), exist_ok=True)
    def __call__(s, **k):
        ln = json.dumps({"t": iso(), "prev": s.prev, **k}); fd = os.open(s.p, os.O_WRONLY | os.O_APPEND | os.O_CREAT); os.write(fd, (ln + "\n").encode()); os.fsync(fd); os.close(fd); s.prev = sha(ln)
def atomic(path, obj): tmp = path + ".tmp"; json.dump(obj, open(tmp, "w"), indent=1); os.replace(tmp, path)
def validate_output(text, pages, full_pages, check_quotes):
    r = dict(json_ok=False, schema_ok=False, errors=[])
    try: obj = json.loads(text); r["json_ok"] = True
    except Exception as e: r["errors"].append("invalid_json: " + str(e)[:100]); return r, None
    try: AppResearch.model_validate(obj); r["schema_ok"] = True
    except ValidationError as e: r["errors"] += [f"{'.'.join(map(str, x['loc']))}: {x['type']}" for x in e.errors()[:8]]; return r, obj
    ev = check_quotes([dict(e) for e in obj["evidence"]], pages); full = " ".join(re.sub(r"\s+", " ", p["text"]).lower() for p in full_pages)
    for e in ev: e["quote_in_full_evidence"] = bool(e["quote"].strip()) and re.sub(r"\s+", " ", e["quote"]).strip().lower() in full
    r.update(n_evidence=len(ev), quote_found=sum(e["quote_found"] for e in ev), url_ok=sum(e["url_in_sources"] for e in ev), quote_only_in_full=sum(e["quote_in_full_evidence"] and not e["quote_found"] for e in ev)); obj = dict(obj, evidence=ev); return r, obj
CLAIM_FIELDS = ("auth_methods", "access", "api_types", "existing_mcp")
def unsupported_claims(obj):
    """claims that are not 'unknown' but have NO evidence entry or an unverified quote -> structural proxy, NOT correctness"""
    out = []
    for f in CLAIM_FIELDS:
        v = obj[f]; known = [x for x in v if x != "unknown"] if isinstance(v, list) else ([v] if v != "unknown" else [])
        if known and not any(e["field"] == f and e.get("quote_found") for e in obj["evidence"]): out.append(f)
    return out

# ---------------- benchmark runner (one provider, apps sequentially, hard cap incl. retries)
def run_provider(tag, cfg, apps, prompts, pages_map, full_map, schema_g, call, quota, out, log, check_quotes, sleep=time.sleep, key=None):
    d = f"{out}/outputs/{tag}"; os.makedirs(d, exist_ok=True); used = 0; k = cfg["bucket"]; res_all = {}
    done = lambda i: os.path.exists(f"{d}/{i}.json")
    for idx, (i, name) in enumerate(apps):
        if done(i): continue
        remaining_apps = sum(not done(j) for j, _ in apps) - 1; retried = False
        while True:
            if used >= cfg["cap"]: log(ev="stop", tag=tag, reason="provider_call_cap", app=i, used=used); return "cap_reached"
            est = est_tokens(len(prompts[i])) + cfg["max_out"]
            try: w = quota.wait_needed(k, est)
            except QuotaStop as e: log(ev="stop", tag=tag, reason="quota", app=i, detail=str(e)); return "quota_stop"
            if w > 0: log(ev="wait", tag=tag, seconds=round(w, 1)); sleep(w)
            quota.reserve(k, est); used += 1; log(ev="request_start", tag=tag, app=i, model=cfg["model"], n=used, est_tokens=est)
            res = call(cfg, prompts[i], schema_g, key); quota.settle(k, (res["tin"] or 0) + (res["tout"] or 0) if res["tin"] is not None else None)
            if res["headers"]: quota.observe(k, headers=res["headers"], app=i)
            cat = "ok" if res["http"] == 200 and res["text"] else classify_error(res)
            log(ev="request_end", tag=tag, app=i, model=cfg["model"], model_returned=res["model_returned"], http=res["http"], category=cat, latency=round(res["latency"], 2), tin=res["tin"], tout=res["tout"], cost=res["cost"])
            if res["cost"] and float(res["cost"]) > 0: log(ev="stop_all", reason="non_zero_cost"); raise StopAll("non-zero cost reported")
            if cat == "payment_required": log(ev="stop_all", reason="payment_required", tag=tag); raise StopAll("payment required")
            if cat == "ok":
                if not model_ok(cfg, res["model_returned"]): log(ev="stop", tag=tag, reason="model_mismatch", returned=res["model_returned"]); return "model_mismatch"
                break
            rec = dict(tag=tag, app=i, name=name, status="failed", category=cat, http=res["http"], error=scrub(res["error"] or ""), model=cfg["model"], attempt=used, at=iso()); atomic(f"{out}/outputs/{tag}/failed_{i}_{used}.json", rec)
            ra = res["headers"].get("retry-after") or res["headers"].get("Retry-After")
            if cat == "daily_quota": quota.block(k, 86400 if not ra else float(ra), "daily"); log(ev="stop", tag=tag, reason="daily_quota", app=i); return "daily_quota"
            if cat == "rate_limit" and ra:
                try: quota.block(k, float(ra), "rate")
                except ValueError: pass
            if cat in ("ambiguous_429", "client_error", "network_error") or retried or used + remaining_apps >= cfg["cap"]:   # a retry may not starve apps not yet attempted
                log(ev="app_failed", tag=tag, app=i, category=cat); break
            retried = True; log(ev="retry", tag=tag, app=i, category=cat)
        if cat != "ok": continue
        vr, obj = validate_output(res["text"], pages_map[i], full_map[i], check_quotes); rec = dict(tag=tag, app=i, name=name, status="ok" if vr["schema_ok"] else "invalid", model=cfg["model"], model_returned=res["model_returned"], model_identity_verified=res["model_returned"] is not None, attempts_for_app=used, latency_s=round(res["latency"], 2), tokens_in=res["tin"], tokens_out=res["tout"], cost_usd=res["cost"] or 0, validation=vr, output=obj, raw_text=None if vr["schema_ok"] else scrub(res["text"])[:6000], unsupported_claim_fields=unsupported_claims(obj) if vr["schema_ok"] else None, prompt_sha256=sha(prompts[i]), at=iso())
        atomic(f"{d}/{i}.json", rec); log(ev="checkpoint", tag=tag, app=i, status=rec["status"])
    return "completed"

# ---------------- CLI plumbing
def load_frozen():
    import glob; v7p = sorted(glob.glob(f"{ROOT}/runs/pilot5-v7-*/run_pilot5_v7.py"))[-1]; cwd = os.getcwd()
    spec = importlib.util.spec_from_file_location("v7", v7p); v7 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v7); v6 = v7.load_v6(); os.chdir(ROOT)
    schema, prompt, h_sch, h_pr = v6.frozen(); os.chdir(cwd); return v7, v6, schema, prompt, h_sch, h_pr, v7p
def cmd_build():
    v7, v6, schema, prompt, h_sch, h_pr, v7p = load_frozen(); os.chdir(ROOT); plan = json.load(open("runs/p1-v1f-gemini-20261124/PLAN.json")); M = json.load(open(os.path.dirname(v7p) + "/PILOT5_MANIFEST.json")); Dd = json.load(open("baseline/data/apps.json")); reg = {a[0]: a for a in Dd["apps"]}; apps_m = {a["id"]: a for a in M["apps"]}; man_apps = []
    for i, name in APPS:
        app = apps_m[i]; assert app["name"] == name; full_prompt, pages, top = v7.build_prompt(v6, M, app, prompt, plan); red = reduce_pages(pages); a = reg[i]
        src = "\n\n".join(f"### {p['url']}\n{p['text']}" for p in red); rp = prompt.format(name=a[2], cat=Dd["categories"][a[1] - 1], hint=a[3] or "none", src=src)
        stats = [dict(url=p["url"], original_chars=len(p["text"]), kept_chars=len(next((r["text"] for r in red if r["url"] == p["url"]), ""))) for p in pages]
        atomic(f"{HERE}/bundles_full/{i}.json", dict(app=name, id=i, provenance=app["provenance"], pages=pages, full_prompt_chars=len(full_prompt), full_prompt_sha256=sha(full_prompt), full_prompt_est_tokens=est_tokens(len(full_prompt)), topup_sources=top, note="FULL evidence preserved here; not truncated"))
        atomic(f"{HERE}/bundles/{i}.json", dict(app=name, id=i, provenance=app["provenance"], provenance_class=app["provenance_class"], reduction=dict(rule="reduction-v1", budget_chars=RED_BUDGET, max_block_chars=RED_BLOCK, max_blocks_per_page=RED_PER_PAGE, keyword_regex=KW, deterministic=True), pages=red, per_page_stats=stats, prompt=rp, prompt_sha256=sha(rp), prompt_chars=len(rp), est_tokens=est_tokens(len(rp)), full_prompt_est_tokens=est_tokens(len(full_prompt))))
        man_apps.append(dict(id=i, name=name, provenance=app["provenance"], provenance_class=app["provenance_class"], reduced_prompt_sha256=sha(rp), reduced_est_tokens=est_tokens(len(rp)), full_est_tokens=est_tokens(len(full_prompt))))
    cfg = dict(created=iso(), benchmark="bench5-v1", purpose="pipeline/model evaluation on 5 apps; NOT an accuracy claim", authorized_by="user instruction (five-app benchmark on free tiers only); no APPROVED.json involved; no paid access", apps=man_apps,
               prompt_sha256=h_pr, schema_sha256=h_sch, prompt_schema_source="frozen v1f prompt/schema via runner v6 frozen(); UNCHANGED", schema_delivery="Gemini: responseSchema (frozen, native). Groq/OpenRouter: response_format json_schema derived mechanically from the frozen schema (json_schema_from_gemini, additionalProperties=false). Prompt text identical for all providers.",
               evidence="reduction-v1 applied to ALL five apps and ALL providers (same bytes); full evidence kept in bundles_full/", providers={t: {k: v for k, v in c.items() if k != "key_env"} | dict(key_env_name=c["key_env"]) for t, c in PROVIDERS.items()},
               budget_rule="hard cap per provider incl. retries; a retry only if it cannot starve apps not yet attempted; no model/provider substitution", bench_py_sha256=sha(open(__file__, "rb").read()), runner_v6_untouched=True, frozen_v1f_untouched=True)
    atomic(f"{HERE}/BENCH_CONFIG.json", cfg); print(json.dumps([(a["id"], a["name"], a["reduced_est_tokens"], a["full_est_tokens"]) for a in man_apps]))
def load_bundles():
    P, PG, FG = {}, {}, {}
    for i, _ in APPS:
        b = json.load(open(f"{HERE}/bundles/{i}.json")); P[i], PG[i] = b["prompt"], b["pages"]; FG[i] = json.load(open(f"{HERE}/bundles_full/{i}.json"))["pages"]
    return P, PG, FG
def cmd_run(tag):
    v7, v6, schema, prompt, h_sch, h_pr, _ = load_frozen(); os.chdir(ROOT); cfg = PROVIDERS[tag]; P, PG, FG = load_bundles(); quota = Quota(f"{HERE}/quota.json", {c["bucket"]: c["limits"] for c in PROVIDERS.values()}); log = Log(f"{HERE}/logs/requests.jsonl"); key = secret(cfg["key_env"])
    if cfg["adapter"] == "openrouter":    # metadata read of the free-tier counter; refuse if not enough free requests remain
        r = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"authorization": "Bearer " + key}); info = json.load(urllib.request.urlopen(r, timeout=30))["data"]; fd = info.get("free_model_daily_requests") or {}; quota.observe(cfg["bucket"], key_info=dict(is_free_tier=info.get("is_free_tier"), usage_usd=info.get("usage"), free_model_daily_requests=fd))
        if info.get("usage") or (fd.get("remaining") is not None and fd["remaining"] < cfg["cap"]): print("STOP: OpenRouter usage>0 or too few free requests", fd); return
    if cfg["adapter"] == "gemini" and tag == "gemini25_key1":
        reset = datetime.datetime(2026, 11, 24, 8, 0, tzinfo=datetime.timezone.utc).timestamp()      # midnight Pacific (PST) after the observed 429 at ~19:08 IST on 2026-11-23
        if time.time() < reset and not quota.b(cfg["bucket"]).get("observations_cleared"): quota.block(cfg["bucket"], reset - time.time(), "daily"); quota.observe(cfg["bucket"], note="seeded from probe-v2 429 'exceeded your current quota'; blocked until daily reset 2026-11-24 08:00 UTC")
    try: st = run_provider(tag, cfg, APPS, P, PG, FG, schema, adapter_call, quota, HERE, log, v6.check_quotes, key=key)
    except StopAll as e: st = f"STOP_ALL: {e}"
    print(tag, st)
if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "build": cmd_build()
    elif a and a[0] == "run": cmd_run(a[1])
    elif a and a[0] in ("report", "capability"): import bench_report as BR; getattr(BR, a[0])(HERE)
