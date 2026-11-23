"""Minimal QUOTA PROBE (user-requested): one tiny request per provider/key/model to read live availability and any rate-limit info. NOT extraction; no APPROVED.json; no secret is printed or stored.
Gemini: 1 generateContent per (key, model) with maxOutputTokens=8 (429 bodies reveal quota; success consumes ~1 request). Groq: GET /models + 1 chat call (max_tokens=1) -> x-ratelimit-* headers.
OpenRouter: GET /key + GET /credits (metadata only, NO generation). Output: runs/quota-probe-v1-20261124/probe_<ts>.json (status codes, quota text, rate-limit headers only)."""
import os, re, json, time, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
ENV = {}
with open(".env") as f:
    for l in f:
        if "=" in l and not l.startswith("#"): k, v = l.strip().split("=", 1); ENV[k] = v
def req(url, headers, body=None, timeout=60):
    r = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, {"content-type": "application/json", "user-agent": "research-agent/0.1", **headers})
    try:
        resp = urllib.request.urlopen(r, timeout=timeout); return resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as e: return e.code, dict(e.headers or {}), e.read().decode()
    except Exception as e: return 0, {}, f"{type(e).__name__}"
def scrub(s):
    for v in ENV.values():
        if v: s = s.replace(v, "***")
    return s
RL = lambda h: {k.lower(): v for k, v in h.items() if k.lower().startswith("x-ratelimit") or k.lower() == "retry-after"}
out = dict(probed_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), note="metadata + 1-token probes only; no extraction; no approval file", gemini={}, groq={}, openrouter={})
for label, var in (("key1", "GEMINI_API_KEY"), ("key2_separate_account_NOT_for_execution", "GEMINI_API_KEY_2")):
    if var not in ENV: out["gemini"][label] = "key not present"; continue
    h = {"x-goog-api-key": ENV[var]}; res = {}
    c, _, b = req("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", h)
    names = [m["name"].split("/")[-1] for m in json.loads(b).get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])] if c == 200 else []
    res["models_list_status"] = c; res["candidate_models_listed"] = {m: (m in names) for m in ("gemini-2.5-flash", "gemini-3.5-flash")}
    for m in ("gemini-2.5-flash", "gemini-3.5-flash"):
        c, hd, b = req(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", h, {"contents": [{"parts": [{"text": "Reply with OK"}]}], "generationConfig": {"maxOutputTokens": 8}})
        d = {}
        try: d = json.loads(b)
        except Exception: pass
        msg = scrub((d.get("error", {}) or {}).get("message", "") if isinstance(d, dict) else "")[:420]
        res[m] = dict(status=c, ok=(c == 200), per_day_quota_exhausted=("per day" in msg.lower()), error_message=msg or None, error_status=(d.get("error", {}) or {}).get("status") if isinstance(d, dict) else None)
    out["gemini"][label] = res
if "GROQ_API_KEY" in ENV:
    h = {"authorization": "Bearer " + ENV["GROQ_API_KEY"]}; c, _, b = req("https://api.groq.com/openai/v1/models", h); ids = [m["id"] for m in json.loads(b).get("data", [])] if c == 200 else []
    c2, hd, b2 = req("https://api.groq.com/openai/v1/chat/completions", h, {"model": "openai/gpt-oss-120b", "messages": [{"role": "user", "content": "Reply with OK"}], "max_tokens": 1, "temperature": 0})
    out["groq"] = dict(models_list_status=c, gpt_oss_120b_listed=("openai/gpt-oss-120b" in ids), chat_status=c2, ok=(c2 == 200), ratelimit_headers=RL(hd), error=(scrub(b2)[:300] if c2 != 200 else None))
if "OPENROUTER_API_KEY" in ENV:
    h = {"authorization": "Bearer " + ENV["OPENROUTER_API_KEY"]}; c, _, b = req("https://openrouter.ai/api/v1/key", h); d = json.loads(b).get("data", {}) if c == 200 else {}
    c3, _, b3 = req("https://openrouter.ai/api/v1/credits", h)
    out["openrouter"] = dict(key_status=c, is_free_tier=d.get("is_free_tier"), usage=d.get("usage"), usage_daily=d.get("usage_daily"), limit=d.get("limit"), limit_remaining=d.get("limit_remaining"), credits_status=c3, credits=(json.loads(b3).get("data") if c3 == 200 else scrub(b3)[:200]), note="metadata only; no generation call made; free-model daily limits depend on credits (not shown by the API)")
p = f"runs/quota-probe-v1-20261124/probe_{time.strftime('%Y%m%d_%H%M%S')}.json"; json.dump(out, open(p, "w"), indent=1); os.chmod(p, 0o444)
print("written:", p)
for k, v in out["gemini"].items():
    print("GEMINI", k, "| list:", v.get("models_list_status"), v.get("candidate_models_listed")) if isinstance(v, dict) else print("GEMINI", k, v)
    if isinstance(v, dict):
        for m in ("gemini-2.5-flash", "gemini-3.5-flash"): print("   ", m, "status", v[m]["status"], "OK" if v[m]["ok"] else ("PER-DAY QUOTA EXHAUSTED" if v[m]["per_day_quota_exhausted"] else "not ok"), "|", (v[m]["error_message"] or "")[:230])
g = out["groq"]; print("GROQ listed:", g.get("gpt_oss_120b_listed"), "| chat", g.get("chat_status"), "| headers:", g.get("ratelimit_headers"), "|", g.get("error") or "")
o = out["openrouter"]; print("OPENROUTER key", o.get("key_status"), "free_tier", o.get("is_free_tier"), "usage", o.get("usage"), "limit", o.get("limit"), "| credits", o.get("credits"))
