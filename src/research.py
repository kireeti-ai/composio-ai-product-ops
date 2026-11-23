"""Pass-1 research agent. For each app: search (Composio MCP/TinyFish, free) -> fetch docs -> Gemini extracts
structured JSON with verbatim quotes -> code checks every quote exists in fetched text.
Resumable: results cached per app in work/. Usage: python src/research.py [ids...|all] [--redo]"""
import sys as _sys
if __name__ == "__main__": _sys.exit("LEGACY SCRIPT - DO NOT RUN. Superseded by src/run_p1.py (Gemini extraction) and src/verify_v2.py (Groq verification). Kept for provenance only; exact original copies are in baseline/code/. It loads EVERY .env variable and (research.py) contains a second-key rotation path, which is not allowed: no key rotation to bypass quotas.")
import os, sys, json, time, re, hashlib, pathlib, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
ROOT = pathlib.Path(__file__).resolve().parent.parent
for l in (ROOT / ".env").read_text().splitlines():
    if "=" in l: k, v = l.split("=", 1); os.environ.setdefault(k, v)
sys.path.insert(0, str(ROOT / "src"))
from mcp import MCP

W = ROOT / "work"; (W / "raw").mkdir(parents=True, exist_ok=True); (W / "pass1").mkdir(exist_ok=True)
APPS = json.load(open(ROOT / "data/apps.json")); CATS = APPS["categories"]
# (key env var, model) combos tried in order; a combo is retired when its daily quota is gone or the model is unavailable.
# Prompt, schema and models are unchanged from the first run (flash-lite removed: it 404s). Key 2 is a second free account.
COMBOS = [("GEMINI_API_KEY", "gemini-2.5-flash"), ("GEMINI_API_KEY", "gemini-3.5-flash")]   # second-key combo REMOVED: no key rotation to bypass quotas (original in baseline/code/)
DEAD = set()
class QuotaExhausted(Exception): pass
SID = "sell"  # Composio session id from COMPOSIO_SEARCH_TOOLS; refreshed in tf()
_mcp = None

def log(**kw):
    kw["t"] = time.strftime("%H:%M:%S")
    open(W / "log.jsonl", "a").write(json.dumps(kw) + "\n")

def tf(slug, args, retries=3):
    """Run a free TinyFish tool through Composio MCP; returns inner data dict."""
    global _mcp
    for i in range(retries):
        try:
            _mcp = _mcp or MCP()
            r = _mcp.call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": slug, "arguments": args}], "sync_response_to_workbench": False, "session_id": SID, "thought": "free web research"})
            d = json.loads(r["content"][0]["text"])
            ch = d.get("data", {}).get("instant_charge") or d.get("instant_charge") or {}
            assert float(ch.get("amount", 0) or 0) == 0, f"NONZERO CHARGE {ch}"  # never spend
            res = d["data"]["results"][0]["response"]
            if res.get("successful"): return res["data"]
            raise RuntimeError(str(res)[:200])
        except AssertionError: raise
        except Exception as e:
            log(ev="tf_retry", slug=slug, err=str(e)[:150]); _mcp = None; time.sleep(2 * (i + 1))
    return {}

def gather(app):
    f = W / "raw" / f"{app['id']}.json"
    if f.exists(): return json.load(open(f))
    name, hint = app["name"], app["hint"]
    qs = [f"{name} API documentation authentication", f"{name} developer API get API key access requirements pricing", f"{name} MCP server"]
    if hint: qs[0] += f" {hint.split(' ')[0]}"
    hits, seen = [], set()
    for q in qs:
        for r in tf("TINYFISH_SEARCH_WEB", {"query": q, "purpose": "find official developer documentation"}).get("results", []):
            if r["url"] not in seen: seen.add(r["url"]); hits.append({"q": q, "url": r["url"], "title": r.get("title"), "snippet": (r.get("snippet") or "")[:300]})
    # pick pages to read: first 2 hits of query 0/1 (docs/auth), prefer hint domain
    dom = re.sub(r"^https?://", "", hint.split(" ")[0]).split("/")[0] if hint else ""
    pick = sorted([h for h in hits if h["q"] != qs[2]], key=lambda h: (dom not in h["url"] if dom else 0))[:8]
    pages, fails = [], []
    for h in pick:  # one URL per call: a single bad URL must not sink the batch
        if len(pages) >= 4: break
        d = tf("TINYFISH_FETCH_URLS", {"urls": [h["url"]], "purpose": f"{name} API auth, access, pricing, endpoints"}, retries=1)
        got = [p for p in d.get("results", []) if p.get("text")]
        pages += [{"url": p["url"], "title": p.get("title"), "text": p["text"][:9000]} for p in got]
        if not got: fails.append(h["url"])
    out = {"search_hits": hits, "pages": pages, "fetch_failed": fails}
    json.dump(out, open(f, "w")); return out

SCHEMA = {"type": "OBJECT", "required": ["one_liner", "auth_methods", "access", "access_note", "api_types", "api_breadth", "existing_mcp", "buildability", "blocker", "evidence"], "properties": {
    "one_liner": {"type": "STRING"},
    "auth_methods": {"type": "ARRAY", "items": {"type": "STRING", "enum": ["oauth2", "api_key", "basic", "bearer_token", "jwt_or_signed", "other", "unknown"]}},
    "access": {"type": "STRING", "enum": ["self_serve_free", "self_serve_trial_or_paid_plan", "approval_or_review_required", "partner_or_contact_sales", "no_public_api", "unknown"]},
    "access_note": {"type": "STRING"},
    "api_types": {"type": "ARRAY", "items": {"type": "STRING", "enum": ["rest", "graphql", "soap", "sdk_or_cli_only", "websocket", "none", "unknown"]}},
    "api_breadth": {"type": "STRING", "enum": ["narrow", "medium", "broad", "unknown"]},
    "existing_mcp": {"type": "STRING", "enum": ["official", "community", "none_found", "unknown"]},
    "buildability": {"type": "STRING", "enum": ["yes", "yes_with_caveats", "no", "unknown"]},
    "blocker": {"type": "STRING"},
    "evidence": {"type": "ARRAY", "items": {"type": "OBJECT", "required": ["field", "url", "quote"], "properties": {"field": {"type": "STRING"}, "url": {"type": "STRING"}, "quote": {"type": "STRING"}}}}}}

PROMPT = """You research apps for an agent-toolkit builder. App: {name} (category: {cat}; hint: {hint}).
Using ONLY the SOURCES below, fill the schema. Rules:
- access: can a developer get credentials themselves for free (self_serve_free), only on a paid plan/trial, only after app review/approval, or only via partnership/contact sales?
- buildability: could this be an agent toolkit today (yes / yes_with_caveats / no); blocker = main obstacle, else "none".
- existing_mcp only if SOURCES show it; otherwise none_found (or unknown if sources are silent).
- evidence: for each of auth_methods, access, api_types, existing_mcp give a url from SOURCES and a SHORT VERBATIM quote (<=200 chars) copied exactly from that source's text. No quote available -> say unknown, do not invent.
- If sources are insufficient, use "unknown". Never guess from memory.
SOURCES:
{src}"""

def gemini(prompt):
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0}}
    for attempt in range(8):
        live = [c for c in COMBOS if c not in DEAD and os.environ.get(c[0])]
        if not live: raise QuotaExhausted("all gemini key/model combos exhausted")
        kv, m = live[attempt % len(live)]
        r = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", json.dumps(body).encode(), {"content-type": "application/json", "x-goog-api-key": os.environ[kv]})
        try:
            d = json.load(urllib.request.urlopen(r, timeout=150))
            return json.loads(d["candidates"][0]["content"]["parts"][0]["text"]), f"{m}@{kv[-1] if kv.endswith('2') else '1'}"
        except urllib.error.HTTPError as e:
            b = e.read().decode().lower()
            if e.code == 404 or (e.code == 429 and "per day" in b): DEAD.add((kv, m)); log(ev="combo_retired", key=kv, model=m, code=e.code)
            else: log(ev="gemini_err", model=m, code=e.code); time.sleep(5 * (attempt + 1))
        except Exception as e:
            log(ev="gemini_exc", model=m, err=str(e)[:150]); time.sleep(5)
    raise RuntimeError("gemini failed")

def norm(s): return re.sub(r"[\s​]+", " ", re.sub(r"[*_`#>\[\]()]", "", s)).strip().lower()

def check_quotes(ev, pages):
    """Automatic verification: is each quote verbatim in the fetched page it cites?"""
    by = {p["url"]: norm(p["text"]) for p in pages}
    allt = " ".join(by.values())
    for e in ev:
        q = norm(e["quote"]); e["quote_found"] = bool(q) and (q in by.get(e["url"], "") or q in allt)
        e["url_in_sources"] = e["url"] in by
    return ev

def research(app):
    f = W / "pass1" / f"{app['id']}.json"
    if f.exists() and "--redo" not in sys.argv: return json.load(open(f))
    if not [c for c in COMBOS if c not in DEAD and os.environ.get(c[0])]: raise QuotaExhausted("no gemini capacity")
    raw = gather(app)
    if not raw["pages"]: log(ev="NO_PAGES", id=app["id"]); raise RuntimeError("no pages fetched; not calling model (would hallucinate)")
    src = "\n\n".join(f"### {p['url']}\n{p['text']}" for p in raw["pages"]) or "(no pages fetched)"
    res, model = gemini(PROMPT.format(name=app["name"], cat=CATS[app["cat"] - 1], hint=app["hint"] or "none", src=src))
    res["evidence"] = check_quotes(res["evidence"], raw["pages"])
    out = {"id": app["id"], "name": app["name"], "category": CATS[app["cat"] - 1], "model": model, "pages_read": [p["url"] for p in raw["pages"]], **res}
    json.dump(out, open(f, "w"), indent=1); log(ev="done", id=app["id"], name=app["name"], model=model)
    return out

def apps():
    return [{"id": a[0], "cat": a[1], "name": a[2], "hint": a[3], "src": a[4]} for a in APPS["apps"]]

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sel = apps() if args in ([], ["all"]) else [a for a in apps() if str(a["id"]) in args]
    def safe(a):
        try: return research(a)
        except Exception as e: log(ev="FAILED", id=a["id"], err=str(e)[:200]); print("FAILED", a["name"], e); return None
    with ThreadPoolExecutor(3) as ex: rs = [r for r in ex.map(safe, sel) if r]
    for r in rs:
        ev = r["evidence"]; ok = sum(e["quote_found"] for e in ev)
        print(f"{r['id']:>3} {r['name']:<24} auth={r['auth_methods']} access={r['access']} api={r['api_types']} mcp={r['existing_mcp']} build={r['buildability']} quotes={ok}/{len(ev)}")
