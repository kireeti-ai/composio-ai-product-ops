"""Pass 2: independent verification of Pass-1 (Gemini) records using Groq. Never modifies Pass 1.
Verdicts are VERIFICATION FLAGS, not ground truth; ambiguous ones are marked needs_human.
  supported | contradicted | insufficient_evidence | terminology_difference | schema_limitation
Rules enforced in code: a 'contradicted' verdict must carry a verbatim quote from the excerpt (else downgraded to
insufficient_evidence); absence of mention is never a contradiction.
Checkpointing: work/verify/{id}.json updated after every field; complete apps are skipped on restart.
Usage: python src/verify.py [--watch] [--once] [ids...]   (--watch: keep picking up newly finished Pass-1 records)"""
import os, sys, json, re, time, hashlib, pathlib, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
ROOT = pathlib.Path(__file__).resolve().parent.parent
for l in (ROOT / ".env").read_text().splitlines():
    if "=" in l: k, v = l.split("=", 1); os.environ.setdefault(k, v)
W = ROOT / "work"; (W / "verify").mkdir(exist_ok=True)
MODEL = "openai/gpt-oss-120b"
VERDICTS = {"supported", "contradicted", "insufficient_evidence", "terminology_difference", "schema_limitation"}
NEEDS_HUMAN = {"contradicted", "terminology_difference", "schema_limitation"}  # insufficient_evidence is flagged separately
FIELDS = ["auth_methods", "access", "api_types", "existing_mcp"]

def log(**kw):
    kw["t"] = time.strftime("%H:%M:%S"); open(W / "verify_log.jsonl", "a").write(json.dumps(kw) + "\n")

def groq(msg, app):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": msg}], "temperature": 0, "response_format": {"type": "json_object"}}).encode()
    for i in range(6):
        r = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", body, {"content-type": "application/json", "authorization": "Bearer " + os.environ["GROQ_API_KEY"], "user-agent": "research-agent/0.1"})
        try: return json.loads(json.load(urllib.request.urlopen(r, timeout=90))["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as e:
            log(ev="groq_retry", id=app, code=e.code, attempt=i + 1); time.sleep(10 * (i + 1) if e.code == 429 else 3)
        except Exception as e:
            log(ev="groq_retry", id=app, code=type(e).__name__, attempt=i + 1); time.sleep(3)
    log(ev="groq_gave_up", id=app); return None

def norm(s): return re.sub(r"[\s​]+", " ", re.sub(r"[*_`#>\[\]()]", "", s)).strip().lower()

def excerpt(text, quote, n=1800):
    i = text.lower().find((quote or "").lower()[:60]) if quote else -1
    return text[max(0, i - n // 2): i + n // 2] if i >= 0 else text[:n]

RULES = """You are an independent fact-checker. Judge ONLY from the EXCERPTS (never from memory).
For each ITEM give one verdict:
- supported: excerpts state or clearly imply it.
- contradicted: excerpts EXPLICITLY say otherwise (e.g. the feature is not supported, a different method is required). You MUST give "evidence_quote", copied verbatim from the excerpts. Not being mentioned is NEVER a contradiction.
- insufficient_evidence: excerpts neither confirm nor refute.
- terminology_difference: same underlying thing, different wording. Check semantics before judging: "OAuth" / "OAuth 2.0" / "OAuth2" are the same unless the text names another version (e.g. OAuth 1.0a); "Bearer token" can be an OAuth2 access token or an API key sent as a Bearer header; "access token"/"personal access token"/"API token" overlap with api_key. If the real mechanism matches the claim, say terminology_difference, not contradicted.
- schema_limitation: the claim cannot express the truth, e.g. the item is 'unknown' but the excerpts show NO credentials are required (suggest "none_required"), or the value set lacks the right option.
Reject (contradicted/insufficient) any auth method or API capability (REST/GraphQL/websocket/MCP) not backed by the excerpts.
Reply JSON: {"items":[{"item":"<exact item>","verdict":"...","evidence_quote":"<verbatim, required if contradicted, else ''>","suggested_value":"<optional>","reason":"<=25 words"}]}"""

def items_for(r, field):
    v = r[field]
    if field == "access": return [f"{r['access']} :: {r['access_note']}"]
    if field == "existing_mcp": return [r[field]]
    return list(v)

def check_field(r, pages, field, app):
    evs = [e for e in r["evidence"] if e["field"] == field and e["url"] in pages]
    items = items_for(r, field)
    if not evs:
        return [{"item": it, "verdict": "insufficient_evidence", "reason": "pass 1 cited no usable evidence for this field", "evidence_quote": "", "needs_human": True, "flag": "no_evidence_cited"} for it in items]
    ex = "\n---\n".join(f"[{e['url']}]\n{excerpt(pages[e['url']], e['quote'])}" for e in evs[:2])
    d = groq(f"{RULES}\n\nFIELD: {field} for app '{r['name']}'\nITEMS: {json.dumps(items)}\nEXCERPTS:\n{ex}", app)
    if d is None or "items" not in d:
        return [{"item": it, "verdict": "error", "reason": "groq failed", "evidence_quote": "", "needs_human": True} for it in items]
    out, exn = [], norm(ex)
    for it in d["items"]:
        v = it.get("verdict")
        if v not in VERDICTS: v, it["flag"] = "insufficient_evidence", "invalid_verdict_from_model"
        q = it.get("evidence_quote") or ""
        if v == "contradicted" and not (q and norm(q) in exn):  # enforce: contradiction needs verbatim evidence
            v, it["flag"] = "insufficient_evidence", "contradiction_without_verifiable_quote"
        out.append({**it, "verdict": v, "needs_human": v in NEEDS_HUMAN or "flag" in it})
    return out

def path(i): return W / "verify" / f"{i}.json"

def verify(r):
    f = path(r["id"]); p1 = W / "pass1" / f"{r['id']}.json"; sha = hashlib.sha256(p1.read_bytes()).hexdigest()[:16]
    cur = json.load(open(f)) if f.exists() else {}
    if cur.get("complete") and cur.get("pass1_sha") == sha: return cur
    if cur.get("pass1_sha") != sha: cur = {}
    raw = json.load(open(W / "raw" / f"{r['id']}.json")); pages = {p["url"]: p["text"] for p in raw["pages"]}
    cur = {"id": r["id"], "name": r["name"], "pass1_sha": sha, "model": MODEL, "ground_truth": False, "fields": cur.get("fields", {}), "complete": False}
    for fld in FIELDS:
        if fld in cur["fields"]: continue  # checkpoint: resume mid-app
        cur["fields"][fld] = check_field(r, pages, fld, r["id"])
        json.dump(cur, open(f, "w"), indent=1)
    cur["complete"] = True; json.dump(cur, open(f, "w"), indent=1)
    try: os.chmod(p1, 0o444)  # pass 1 is immutable once verified
    except OSError: pass
    log(ev="verified", id=r["id"], name=r["name"]); return cur

def safe(r):
    try: return verify(r)
    except Exception as e: log(ev="verify_FAILED", id=r["id"], err=str(e)[:200])

def pending():
    out = []
    for p in sorted((W / "pass1").glob("*.json"), key=lambda p: int(p.stem)):
        try: r = json.load(open(p))
        except Exception: continue  # Pass 1 still writing this file
        v = path(r["id"]); sha = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        if v.exists():
            c = json.load(open(v))
            if c.get("complete") and c.get("pass1_sha") == sha: continue
        out.append(r)
    return out

if __name__ == "__main__":
    flags = {a for a in sys.argv[1:] if a.startswith("--")}; ids = [a for a in sys.argv[1:] if not a.startswith("--")]
    while True:
        todo = [r for r in pending() if not ids or str(r["id"]) in ids]
        with ThreadPoolExecutor(2) as ex:
            list(ex.map(safe, todo))
        done = len(list((W / "pass1").glob("*.json")))
        if "--watch" not in flags or "--once" in flags: break
        if done >= 100 and not pending(): break
        time.sleep(30)
    print("verify finished; pending:", len(pending()))
