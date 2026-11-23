"""QUOTA PROBE v2 (user-authorized, 2026-11-23): one tiny GENERATION request per (provider, key, model) + metadata; records status, error text, rate-limit headers, context limits. NOT extraction; no APPROVED.json.
Keys are read from .env at runtime; output is scrubbed (labels only, never key values). Groq: each key probed once, sequentially, so a shared remaining-requests counter reveals keys that share an organization.
OpenRouter: lists free models (price 0), then one 1-token generation on up to 3 free models with context>=32k; no paid model is ever called. Output: runs/quota-probe-v2-<ts>/probe.json"""
import os, re, json, time, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); ENV = {}
for l in open(".env"):
    if "=" in l and not l.startswith("#"): k, v = l.strip().split("=", 1); ENV[k] = v
SECRETS = [v for v in ENV.values() if len(v) > 12]
def scrub(x):
    t = json.dumps(x)
    for s in SECRETS: t = t.replace(s, "[REDACTED]")
    return json.loads(t)
def req(url, headers, body=None, timeout=90):
    r = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, {"content-type": "application/json", "user-agent": "research-agent/0.1", **headers}); t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f: return f.status, f.read().decode(), dict(f.headers), time.time() - t0
    except urllib.error.HTTPError as e: return e.code, e.read().decode(), dict(e.headers), time.time() - t0
    except Exception as e: return None, type(e).__name__, {}, time.time() - t0
RL = lambda h: {k: v for k, v in h.items() if k.lower().startswith(("x-ratelimit", "retry-after"))}
def short(b): return re.sub(r"\s+", " ", b)[:400]
out = dict(probed_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), note="1-token generation probes + metadata; no extraction; labels only")
# ---- Gemini: (key label, models); key2 skips 2.5 (404 known) and 3.5 (503 known) to avoid pointless calls; key1 skips 3.5 for the same reason
G = {}
for lab, kv, models in (("gemini_key1", "GEMINI_API_KEY", ["gemini-2.5-flash", "gemini-3.6-flash"]), ("gemini_key2", "GEMINI_API_KEY_2", ["gemini-3.6-flash"])):
    G[lab] = {}
    for m in models:
        st, b, h, dt = req(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", {"x-goog-api-key": ENV[kv]}, {"contents": [{"parts": [{"text": "Reply with: ok"}]}], "generationConfig": {"maxOutputTokens": 16, "temperature": 0}})
        mv = None
        try: d = json.loads(b); mv = d.get("modelVersion")
        except Exception: d = {}
        st2, b2, _, _ = req(f"https://generativelanguage.googleapis.com/v1beta/models/{m}", {"x-goog-api-key": ENV[kv]})
        try: info = json.loads(b2); lim = dict(inputTokenLimit=info.get("inputTokenLimit"), outputTokenLimit=info.get("outputTokenLimit"))
        except Exception: lim = {}
        G[lab][m] = dict(generate_status=st, ok=st == 200, latency_s=round(dt, 2), returned_modelVersion=mv, error=None if st == 200 else short(b), limits=lim, daily_quota_429=(st == 429 and "per day" in b.lower().replace("_", " ")) or None)
        time.sleep(13)
out["gemini"] = G
# ---- Groq: every key, sequential, same model
GR = {}; prev = None
for lab in ["GROQ_API_KEY", "GROQ_KEY_P1", "GROQ_KEY_P2", "GROQ_KEY_P3", "GROQ_KEY_P4"]:
    st, b, h, dt = req("https://api.groq.com/openai/v1/chat/completions", {"authorization": "Bearer " + ENV[lab]}, {"model": "openai/gpt-oss-120b", "messages": [{"role": "user", "content": "Reply with: ok"}], "max_tokens": 16, "temperature": 0})
    mdl = req("https://api.groq.com/openai/v1/models", {"authorization": "Bearer " + ENV[lab]}); ctx = None
    try: ctx = next((m.get("context_window") for m in json.loads(mdl[1])["data"] if m["id"] == "openai/gpt-oss-120b"), None)
    except Exception: pass
    rl = RL(h); rem = rl.get("x-ratelimit-remaining-requests")
    GR[lab if lab == "GROQ_API_KEY" else lab.replace("GROQ_KEY_", "")] = dict(generate_status=st, ok=st == 200, latency_s=round(dt, 2), error=None if st == 200 else short(b), ratelimit_headers=rl, context_window=ctx, remaining_requests_prev_probe=prev, **({"shares_counter_with_previous_probe_candidate": (prev is not None and rem is not None and prev.isdigit() and rem.isdigit() and int(rem) < int(prev) and int(prev) - int(rem) <= 2)} if prev else {}))
    prev = rem; time.sleep(3)
out["groq"] = GR
# ---- OpenRouter
st, b, h, dt = req("https://openrouter.ai/api/v1/models", {}); free = []
try:
    for m in json.loads(b)["data"]:
        p = m.get("pricing", {})
        if float(p.get("prompt", 1)) == 0 and float(p.get("completion", 1)) == 0 and "text" in (m.get("architecture", {}).get("output_modalities") or ["text"]): free.append(dict(id=m["id"], context=m.get("context_length"), supports_response_format="response_format" in (m.get("supported_parameters") or []) or "structured_outputs" in (m.get("supported_parameters") or [])))
except Exception: pass
big = sorted([m for m in free if (m["context"] or 0) >= 32000], key=lambda m: -(m["context"] or 0))
ks, kb, _, _ = req("https://openrouter.ai/api/v1/key", {"authorization": "Bearer " + ENV["OPENROUTER_API_KEY"]}); OR = dict(models_list_status=st, free_models_total=len(free), free_models_ctx_ge_32k=len(big), free_model_ids_top20=[m["id"] for m in big[:20]], key_info=(json.loads(kb).get("data") if ks == 200 else short(kb)), generation_tests={})
# prefer models likely able to do structured JSON; test up to 3
pick = [m for m in big if m["supports_response_format"]][:3] or big[:3]
for m in pick:
    st, b, h, dt = req("https://openrouter.ai/api/v1/chat/completions", {"authorization": "Bearer " + ENV["OPENROUTER_API_KEY"]}, {"model": m["id"], "messages": [{"role": "user", "content": "Reply with: ok"}], "max_tokens": 16, "temperature": 0})
    OR["generation_tests"][m["id"]] = dict(generate_status=st, ok=st == 200, latency_s=round(dt, 2), context=m["context"], error=None if st == 200 else short(b), ratelimit_headers=RL(h)); time.sleep(5)
out["openrouter"] = OR
d = f"runs/quota-probe-v2-{time.strftime('%Y%m%d_%H%M%S')}"; os.makedirs(d); json.dump(scrub(out), open(f"{d}/probe.json", "w"), indent=1); print(d)
print(json.dumps(scrub(out), indent=1)[:9000])
