"""Pass 2 verifier v2 (Groq, independent family). Supports: frozen single-surface records, the NESTED per-surface shape, and Neo4j per-surface records; reads sources from any run (read-only) and
writes ONLY to a writable run directory (never baseline/ or work/). Verdicts are VERIFICATION FLAGS, never ground truth.
Independence: (1) different model family; (2) evidence is chosen by a DETERMINISTIC retriever over the app's/surface's WHOLE stored source set, not limited to Pass-1's cited quote;
(3) deterministic guardrails fix the known false-positive classes (see tests/test_verify_v2.py): absence != contradiction, quote must be about the item and contain an explicit negation, enum-semantics
conflicts are schema_limitation, OAuth version wording is ambiguous_needs_human, 'no credentials required' is schema_limitation(none_required), supported/contradicted need a verbatim passage quote.
Quota: only GROQ_API_KEY is read; mandatory call cap (APPROVED_PASS2.json); concurrency 1; backoff on 429 honouring Retry-After; stops + checkpoints when the cap or retries are exhausted; no key rotation.
Usage: python src/verify_v2.py --out runs/<run>/verify --records "<glob>" [--dry-run]   (real run needs <out>/APPROVED_PASS2.json {"max_calls": N})"""
import os, re, sys, json, math, copy, glob, time, hashlib, collections, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
MODEL = "openai/gpt-oss-120b"; sha = lambda b: hashlib.sha256(b).hexdigest(); iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")
VERDICTS = {"supported", "contradicted", "insufficient_evidence", "terminology_difference", "schema_limitation", "ambiguous_needs_human"}; NEEDS_HUMAN = {"contradicted", "terminology_difference", "schema_limitation", "ambiguous_needs_human"}
EVIDENCE_FIELDS = ["auth_methods", "access", "api_types", "existing_mcp"]; SET_FIELDS = {"auth_methods", "api_types"}
ANCHOR = {"auth_methods": {"oauth2": r"oauth", "api_key": r"api[ _-]?key|apikey|x-api-key", "basic": r"basic auth|basic authentication|\bbasic\b", "bearer_token": r"bearer|access token|api token|personal access token", "jwt_or_signed": r"\bjwt\b|json web token|hmac|signature|signed", "other": r".", "unknown": r"."},
          "api_types": {"rest": r"\brest\b|restful|http api|https", "graphql": r"graphql", "soap": r"\bsoap\b|wsdl", "sdk_or_cli_only": r"\bsdk\b|\bcli\b|command[- ]line|client librar", "websocket": r"websocket|web socket|wss://", "none": r"no public api|no api", "unknown": r"."},
          "existing_mcp": {"official": r"\bmcp\b|model context protocol", "community": r"\bmcp\b|model context protocol", "none_found": r"\bmcp\b|model context protocol", "unknown": r"."}}
ACCESS_ANCHOR = r"\\bfree\\b|trial|\\bplans?\\b|pricing|paid|enterprise|approval|approved|review|partner|contact sales|request access|sign up|signup|api key|account|credential|subscription|waitlist|invite"
NEG = re.compile(r"\b(not|no|never|cannot|can't|unsupported|doesn't|does not|isn't|aren't|without|instead of|deprecated|removed|discontinued|only)\b", re.I)
ABSENCE = re.compile(r"no mention|not mention|does not mention|doesn't mention|no evidence|not stated|not specified|only mentions|not described|no information|nothing (?:about|on)", re.I)
NONE_REQ = re.compile(r"(?:does not|doesn't|do not|no)\s+(?:require|need)[^.\n]{0,50}(?:api key|credential|login|authenticat|auth)|no authentication (?:is )?(?:required|needed)|without (?:an )?(?:api key|authentication|login)", re.I)
RULES = """You are an independent fact-checker. Judge ONLY from the PASSAGES (never from memory). For each ITEM give one verdict:
- supported: a passage states or clearly implies it. Give passage_id and a VERBATIM evidence_quote.
- contradicted: a passage EXPLICITLY says otherwise about THIS item (it must name the item and negate it). Give passage_id and a VERBATIM evidence_quote. Not being mentioned is NEVER a contradiction. A passage that says a DIFFERENT item exists (e.g. 'a REST API exists') does not contradict this item.
- insufficient_evidence: passages neither confirm nor refute.
- terminology_difference: same underlying thing in different words (OAuth / OAuth 2.0 / OAuth2; bearer token that is an access token or an API key).
- schema_limitation: the value cannot express the truth (e.g. 'unknown' while the passages say NO credentials are required).
- ambiguous_needs_human: passages conflict or the wording is ambiguous.
Reply JSON: {"items":[{"item":"<exact item>","verdict":"...","passage_id":"P#","evidence_quote":"<verbatim or ''>","suggested_value":"<optional>","reason":"<=25 words"}]}"""
def jload(p):
    with open(p) as f: return json.load(f)
def jdump(obj, path):
    with open(path, "w") as f: json.dump(obj, f, indent=1)
def rbytes(p):
    with open(p, "rb") as f: return f.read()
def norm(s): return re.sub(r"\s+", " ", re.sub(r"[*_`#>\[\]()]", "", s or "")).strip().lower()
def toks(s): return re.findall(r"[a-z0-9]+", s.lower())
# ------------------------------------------------------------------ shapes + sources
def load_record(path):
    r = jload(path); key = os.path.basename(path)[:-5]
    if "surfaces" in r: return dict(key=key, shape="nested", id=r["id"], name=r["name"], surfaces=r["surfaces"], raw=r)
    return dict(key=key, shape="frozen_single_surface", id=r["id"], name=r["name"], surfaces=[dict(r, surface_id=r.get("surface_id", "default"))], raw=r)
def find_text(path, url):
    d = jload(path)
    for v in d.values() if isinstance(d, dict) else []:
        if isinstance(v, list):
            for e in v:
                if isinstance(e, dict) and e.get("url") == url and e.get("text"): return e["text"]
    return None
def load_sources(rec, surface):
    """-> {url: text} for THIS surface only. Handles run_p1 meta (retrieval dict + retrieval_topup list), Neo4j per-surface meta (retrieval list), and baseline records (baseline raw for the id)."""
    meta = surface.get("_call_meta") or rec["raw"].get("meta") or surface.get("meta"); urls = surface.get("pages_read") or rec["raw"].get("pages_read") or []; out = {}
    if meta and isinstance(meta.get("retrieval"), list):
        for e in meta["retrieval"]: t = find_text(e["path"], e["url"]); out[e["url"]] = t if t else None
    elif meta and isinstance(meta.get("retrieval"), dict):
        for u in urls:
            for p in [meta["retrieval"]["path"]] + [s["path"] for s in (meta.get("retrieval_topup") or [])]:
                t = find_text(p, u)
                if t: out[u] = t; break
    else:
        bp = f"baseline/p1_v1/raw/{rec['id']}.json"
        if os.path.exists(bp):
            for e in jload(bp)["pages"]:
                if not urls or e["url"] in urls: out[e["url"]] = e["text"]
    return {u: t for u, t in out.items() if t}
def passages(pages, size=700):
    out = []
    for url, t in pages.items():
        buf = ""; i = 0
        for s in re.split(r"(?<=[.!?])\s+|\n+", t):
            s = s.strip()
            if not s: continue
            if buf and len(buf) + len(s) > size: out.append(dict(url=url, idx=i, text=buf)); i += 1; buf = ""
            buf += (" " if buf else "") + s
        if buf: out.append(dict(url=url, idx=i, text=buf))
    for n, p in enumerate(out): p["id"] = f"P{n + 1}"
    return out
def retrieve(terms, ps, k=3):
    if not ps: return []
    docs = [collections.Counter(toks(p["text"])) for p in ps]; N = len(ps); df = collections.Counter()
    for d in docs: df.update(d.keys())
    q = {w for t in terms for w in toks(t)}; sc = []
    for p, d in zip(ps, docs):
        s = sum(math.log(1 + (N - df[w] + .5) / (df[w] + .5)) * d[w] / (d[w] + 1.2) for w in q if w in d); s += sum(2 for t in terms if " " in t and t.lower() in p["text"].lower()); sc.append(s)
    order = sorted(range(N), key=lambda i: -sc[i]); return [ps[i] | {"score": round(sc[i], 3)} for i in order[:k] if sc[i] > 0]
QCTX = {"access": ["free", "trial", "plan", "pricing", "sign up", "account", "approval", "review", "partner", "contact sales", "request access", "api key", "paid", "enterprise"], "existing_mcp": ["mcp", "model context protocol", "mcp server"]}
def query_terms(field, item):
    if field in ANCHOR and item in ANCHOR[field]: return [ANCHOR[field][item].replace("\\b", "").replace("\\", "").split("|")[0]] + re.findall(r"[a-z0-9 ]{3,}", ANCHOR[field][item].replace("\\b", "")) + QCTX.get(field, [])
    return QCTX.get(field, []) + [item]
# ------------------------------------------------------------------ deterministic guardrails
def precheck_enum_conflict(field, items):
    """api_types lists sdk_or_cli_only TOGETHER with a network API: the enum means 'no public network API', so the record uses the value inconsistently -> schema_limitation (no model call)."""
    if field == "api_types" and "sdk_or_cli_only" in items and any(x in items for x in ("rest", "graphql", "soap", "websocket")): return {"sdk_or_cli_only": "enum_semantics_conflict: sdk_or_cli_only means no public network API but the record also lists " + "/".join(x for x in items if x in ("rest", "graphql", "soap", "websocket"))}
    return {}
def none_required_hit(field, items, passages_text):
    return field == "auth_methods" and (not items or set(items) <= {"unknown"}) and any(NONE_REQ.search(t) for t in passages_text)
def apply_guardrails(field, item, verdict, quote, reason, passages_text, items_in_field=()):
    flags = []; raw = verdict; quote = quote or ""; reason = reason or ""
    if verdict in ("supported", "contradicted", "terminology_difference") and not (quote and any(norm(quote) in norm(t) for t in passages_text)): verdict = "insufficient_evidence"; flags.append("quote_not_verbatim_in_retrieved_passages")
    if verdict == "contradicted":
        if ABSENCE.search(reason): verdict = "insufficient_evidence"; flags.append("absence_not_contradiction")
        elif not re.search(ACCESS_ANCHOR if field == "access" else ANCHOR.get(field, {}).get(item, "."), quote, re.I): verdict = "insufficient_evidence"; flags.append("quote_not_about_item")
        elif not NEG.search(quote): verdict = "insufficient_evidence"; flags.append("no_explicit_negation_in_quote")
        elif field == "auth_methods" and item == "oauth2" and re.search(r"oauth", quote, re.I) and not re.search(r"not supported|unsupported|no oauth|does not support oauth|doesn't support oauth", quote, re.I): verdict = "ambiguous_needs_human"; flags.append("oauth_version_wording")
    if verdict != raw: flags.append(f"downgraded_from:{raw}")
    return verdict, flags
# ------------------------------------------------------------------ cross-field deterministic checks (no model)
OPS = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(?:https?://[\w.\-]+)?(/[\w\-/{}.:$]*[\w}])")
def cross_checks(s, pages):
    out = []; ops = {f"{m.group(1)} {m.group(2)}" for t in pages.values() for m in OPS.finditer(t)}
    if s.get("buildability") == "yes" and s.get("access") in ("no_public_api", "partner_or_contact_sales"): out.append("buildability_yes_but_access_is_" + s["access"])
    if s.get("buildability") == "no" and s.get("access") == "self_serve_free" and set(s.get("api_types") or []) & {"rest", "graphql"}: out.append("buildability_no_despite_self_serve_free_public_api")
    if s.get("api_breadth") == "broad" and len(ops) < 3: out.append(f"api_breadth_broad_but_only_{len(ops)}_operations_in_sources(insufficient_evidence_for_breadth)")
    return out
# ------------------------------------------------------------------ verification
class Budget:
    def __init__(self, n): self.n = n; self.used = 0; self.retries = 0; self.stopped = None
class QuotaStop(Exception): pass
def groq_call(msgs, budget, key, sleep=time.sleep):
    body = json.dumps({"model": MODEL, "messages": msgs, "temperature": 0, "response_format": {"type": "json_object"}}).encode()
    for i in range(5):
        if budget.used >= budget.n: budget.stopped = "max_calls_reached"; raise QuotaStop(budget.stopped)
        budget.used += 1
        r = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", body, {"content-type": "application/json", "authorization": "Bearer " + key, "user-agent": "research-agent/0.1"})
        try: return json.loads(json.load(urllib.request.urlopen(r, timeout=90))["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as e:
            budget.retries += 1
            if e.code == 429: sleep(min(60, float(e.headers.get("retry-after") or 10 * (i + 1))))
            else: sleep(3)
        except Exception: budget.retries += 1; sleep(3)
    budget.stopped = "retries_exhausted"; raise QuotaStop(budget.stopped)
def items_for(s, field):
    v = s.get(field)
    if field == "access": return [f"{v} :: {s.get('access_note', '')}"]
    if field == "existing_mcp": return [v]
    return list(v or [])
def verify_surface(rec, s, call, budget):
    pages = load_sources(rec, s); ps = passages(pages); cited = {f: [e["quote"] for e in s.get("evidence", []) if e.get("field") == f] for f in EVIDENCE_FIELDS}; res = dict(surface_id=s.get("surface_id", "default"), sources=list(pages), fields={}, cross_checks=cross_checks(s, pages))
    for f in EVIDENCE_FIELDS:
        items = items_for(s, f); pre = precheck_enum_conflict(f, items); out = []; todo = []
        for it in items:
            if it in pre: out.append(dict(item=it, verdict="schema_limitation", model_verdict_raw=None, flags=["enum_semantics_conflict"], reason=pre[it], evidence_quote="", model_called=False, needs_human=True))
            elif f == "auth_methods" and it == "unknown" and none_required_hit(f, items, [p["text"] for p in ps]):
                q = next(NONE_REQ.search(p["text"]).group(0) for p in ps if NONE_REQ.search(p["text"])); out.append(dict(item=it, verdict="schema_limitation", model_verdict_raw=None, flags=["none_required_not_expressible"], suggested_value="none_required", evidence_quote=q, model_called=False, needs_human=True))
            elif it in ("unknown", "none_found") and f != "existing_mcp" and it == "unknown": out.append(dict(item=it, verdict="insufficient_evidence", model_verdict_raw=None, flags=["abstention_not_verified"], reason="'unknown' is an abstention; not model-verified", model_called=False, needs_human=False))
            else: todo.append(it)
        if todo:
            terms = [t for it in todo for t in query_terms(f, it)]; top = retrieve(terms, ps, 3) if ps else []
            if not top: out += [dict(item=it, verdict="insufficient_evidence", model_verdict_raw=None, flags=["no_relevant_passage_retrieved"], model_called=False, needs_human=False) for it in todo]
            else:
                ptxt = "\n".join(f"[{p['id']}] ({p['url']}) {p['text']}" for p in top); d = call([{"role": "user", "content": f"{RULES}\n\nFIELD: {f} for app '{rec['name']}'\nITEMS: {json.dumps(todo)}\nPASSAGES:\n{ptxt}"}], budget)
                by = {x.get("item"): x for x in (d or {}).get("items", [])}
                for it in todo:
                    x = by.get(it) or {}; v0 = x.get("verdict") if x.get("verdict") in VERDICTS else "insufficient_evidence"; v, fl = apply_guardrails(f, it, v0, x.get("evidence_quote"), x.get("reason"), [p["text"] for p in top], items)
                    pid = x.get("passage_id"); cited_hit = any(norm(c)[:60] and norm(c)[:60] in norm(p["text"]) for p in top for c in cited[f])
                    out.append(dict(item=it, verdict=v, model_verdict_raw=x.get("verdict"), passage_id=pid, evidence_quote=x.get("evidence_quote") or "", reason=x.get("reason", ""), suggested_value=x.get("suggested_value"), flags=fl, model_called=True,
                                    passages_retrieved=[p["id"] for p in top], retrieved_passage_overlaps_pass1_citation=cited_hit, independent_passages=sum(not any(norm(c)[:60] and norm(c)[:60] in norm(p["text"]) for c in cited[f]) for p in top), needs_human=v in NEEDS_HUMAN))
        res["fields"][f] = out
    return res
def verify_record(path, out_dir, call, budget):
    rec = load_record(path); fn = f"{out_dir}/{rec['key']}.json"; src_sha = sha(rbytes(path))
    cur = jload(fn) if os.path.exists(fn) else {}
    if cur.get("complete") and cur.get("source_record_sha256") == src_sha: return cur
    cur = dict(record_key=rec["key"], source_record_path=path, source_record_sha256=src_sha, shape=rec["shape"], verifier=dict(model=MODEL, rules_sha256=sha(RULES.encode()), code_sha256=sha(rbytes(__file__)), ground_truth=False, independent_retrieval=True, created=iso()), surfaces=[], complete=False)
    try:
        for s in rec["surfaces"]: cur["surfaces"].append(verify_surface(rec, s, call, budget))
        cur["complete"] = True
    except QuotaStop: cur["stopped"] = budget.stopped
    tmp = fn + ".tmp"; jdump(cur, tmp); os.replace(tmp, fn); return cur
def main():
    a = sys.argv; out = a[a.index("--out") + 1]; recs = sorted(glob.glob(a[a.index("--records") + 1]))
    assert not os.path.abspath(out).startswith((os.path.abspath("baseline"), os.path.abspath("work"))), "output must be a writable run dir, never baseline/ or work/"; os.makedirs(out, exist_ok=True)
    plan_calls = 0; indep = []
    for p in recs:
        r = load_record(p)
        for s in r["surfaces"]:
            pages = load_sources(r, s); ps = passages(pages)
            for f in EVIDENCE_FIELDS:
                items = items_for(s, f); pre = precheck_enum_conflict(f, items); todo = [i for i in items if i not in pre and i != "unknown"]
                if todo and ps: plan_calls += 1
    print(f"records: {len(recs)} | planned Groq calls (max, after deterministic shortcuts): {plan_calls}")
    if "--dry-run" in a or not os.path.exists(f"{out}/APPROVED_PASS2.json"): print("[no model call made] approval file present:", os.path.exists(f"{out}/APPROVED_PASS2.json")); return
    ap = jload(f"{out}/APPROVED_PASS2.json"); key = None
    with open(".env") as ef:
        for l in ef:
            if l.startswith("GROQ_API_KEY="): key = l.strip().split("=", 1)[1]              # only this variable is ever read
    assert key, "GROQ_API_KEY missing"; b = Budget(int(ap["max_calls"]))
    for p in recs:
        verify_record(p, out, lambda m, bud: groq_call(m, bud, key), b)
        if b.stopped: break
    print("calls used:", b.used, "retries:", b.retries, "stopped:", b.stopped)
if __name__ == "__main__": main()
