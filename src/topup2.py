"""Top-up v1r (reconcile + retry). Outputs under runs/topup-v1r-20261123/ ; never modifies runs/topup-v1-20261123 (read-only) or baseline/.
Stages: account  (offline)  URL-level reconciliation of the 68 first-attempt fetches with MUTUALLY EXCLUSIVE outcomes
        retryplan(offline)  alternative OFFICIAL URLs for failed/thin pages (+ Neo4j surfaces), from stored search hits / URL variants / targeted searches
        retry    (network)  free Composio TINYFISH only (instant_charge asserted 0); every attempt preserved with parent_url + reason; failed attempts are never replaced
        catalog  (network)  Composio catalog metadata for Neo4j (COMPOSIO_SEARCH_TOOLS / GET_TOOL_SCHEMAS only; no tool is executed)
No Gemini/Groq."""
import os, re, sys, json, time, hashlib, datetime, collections, csv
from urllib.parse import urlparse, urlunparse
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src")
for _l in open(".env"):
    if _l.startswith("COMPOSIO_API_KEY="): os.environ["COMPOSIO_API_KEY"] = _l.strip().split("=", 1)[1]   # only key ever read here
V1 = "runs/topup-v1-20261123"; OUT = "runs/topup-v1r-20261123"; os.makedirs(f"{OUT}/raw", exist_ok=True)
iso = lambda t=None: datetime.datetime.fromtimestamp(t or time.time()).astimezone().isoformat(timespec="seconds")
reg = lambda h: ".".join((h or "").split(".")[-2:])
A = {a["id"]: a for a in json.load(open("runs/audit-raw-v2-20261123/audit.json"))}
APPS18 = [29, 36, 46, 65, 66, 71, 72, 75, 20, 25, 26, 38, 44, 47, 61, 62, 63, 70]
EXCL = re.compile(r"blog|changelog|release-?notes|community|forum|career|/press|customers?/|case-?stud|webinar|status\.|legal|privacy|cookie|podcast|/events?/|academy|/jobs|/topics/|answers\.|labs/|stackoverflow|/discussions|ai-gateway|agent-memory|how-to-call|nitro|server-?boost", re.I)
BAD = re.compile(r"pinterest\.com/(ideas/|[a-z0-9_]+/[a-z0-9-]*plan)|support\.discord\.com/.*(subscription|pricing|nitro|boost)|how-to-call", re.I)
CATS = [("pricing", re.compile(r"pricing|/plans?\b|billing|subscription", re.I)), ("registration", re.compile(r"sign-?up|register|create[- ]?(an?[- ])?(account|app|application|developer)|developer[- ](account|portal|program|registration)|credentials|api[- ]?keys?|access[- ]?tokens?|personal[- ]access|api[- ]access|request[- ]access|\bapply\b", re.I)),
        ("review_partner", re.compile(r"app[- ]review|review[- ]process|partner|marketplace|submission|verification|approval|publish", re.I)), ("onboarding", re.compile(r"get(ting)?[- ]started|quick-?start|onboard|introduction|overview", re.I))]
cat_of = lambda u, t="": next((c for c, rx in CATS if rx.search(urlparse(u).path + " " + (t or ""))), "other")
nh = lambda t: hashlib.sha256(re.sub(r"\s+", " ", t[:400]).strip().lower().encode()).hexdigest()[:16]
def regs(i): return {reg(p["host"]) for p in A[i]["pages"] if p["official"] and p["usable"]}

def outcome(url, status, chars, i, text, seen, basehash):
    """Mutually exclusive, first match wins: fetch_error > fetch_empty > off_target_url > thin_or_js_shell > not_official_domain > duplicate_content > usable_unique"""
    if status == "error": return "fetch_error", None
    if status == "empty": return "fetch_empty", None
    if BAD.search(url): return "off_target_url", None
    if (chars or 0) < 500: return "thin_or_js_shell", None
    if reg(urlparse(url).hostname) not in regs(i): return "not_official_domain", None
    h = nh(text or "")
    if h in basehash: return "duplicate_content", "baseline_page"
    if h in seen: return "duplicate_content", seen[h]
    return "usable_unique", None

def account():
    rows = []
    for i in APPS18:
        rec = json.load(open(f"{V1}/raw/{i}.json")); base = {nh(p["text"]) for p in json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]}; seen = {}
        for e in rec["fetched"]:
            o, dup = outcome(e["url"], e["status"], e.get("chars"), i, e.get("text"), seen, base)
            if o == "usable_unique": seen[nh(e["text"])] = e["url"]
            rows.append(dict(attempt=1, app_id=i, app=rec["name"], url=e["url"], category=e["category"], source=e["source"], raw_status=e["status"], returned_content=e["status"] == "ok", chars=e.get("chars"), outcome=o, duplicate_of=dup, sha256=(e.get("sha256") or "")[:12], requested_at=e["requested_at"]))
    json.dump(rows, open(f"{OUT}/accounting_attempt1.json", "w"), indent=1)
    with open(f"{OUT}/accounting_attempt1.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    c = collections.Counter(r["outcome"] for r in rows); ret = sum(r["returned_content"] for r in rows)
    print("URL attempts:", len(rows), "| outcomes (exclusive):", dict(c), "| sum =", sum(c.values()))
    print("returned content (status ok):", ret, "= off_target_url", sum(r["returned_content"] and r["outcome"] == "off_target_url" for r in rows), "+ thin", sum(r["returned_content"] and r["outcome"] == "thin_or_js_shell" for r in rows), "+ duplicate", c["duplicate_content"], "+ usable_unique", c["usable_unique"], "+ not_official", c["not_official_domain"])
    for r in rows:
        if r["outcome"] in ("duplicate_content", "off_target_url", "thin_or_js_shell"): print(f"   {r['outcome']:<18} #{r['app_id']} {r['url'][8:80]} chars={r['chars']} dup_of={r['duplicate_of'] and r['duplicate_of'][8:60]}")

def host_ok(u):   # official-style hosts only (drops customer sites living on the vendor's domain, e.g. agency.squarespace.com)
    h = urlparse(u).hostname or ""; return h.count(".") == 1 or h.split(".")[0] in {"www", "support", "help", "docs", "doc", "developer", "developers", "dev", "api", "connect", "learn", "business", "apidocs"}

def variants(u):
    p = urlparse(u); path = p.path; h = p.hostname or ""; out = []
    if "(" in path: out.append(urlunparse(p._replace(path=path.split("/(")[0], query="", fragment="")))      # malformed search-hit URL
    if p.query: out.append(urlunparse(p._replace(query="")))
    out.append(urlunparse(p._replace(path=path.rstrip("/") if path.endswith("/") and path != "/" else path + "/")))
    if path.endswith(".md"): out.append(urlunparse(p._replace(path=path[:-3])))
    elif re.match(r"(docs|developers?)\.", h): out.append(urlunparse(p._replace(path=path.rstrip("/") + ".md")))
    if p.scheme == "http": out.append(urlunparse(p._replace(scheme="https")))
    if h.startswith("www.") or h.count(".") == 1: out.append(urlunparse(p._replace(netloc=h[4:] if h.startswith("www.") else "www." + h)))   # only apex <-> www
    return [x for x in dict.fromkeys(out) if x != u]

def stored_hits(i):
    hs = [h for h in json.load(open(f"{V1}/search_hits.json")).get(str(i), [])] + [h for h in json.load(open(f"baseline/p1_v1/raw/{i}.json"))["search_hits"] if "MCP server" not in h["q"]]
    return hs

def retryplan():
    rows = json.load(open(f"{OUT}/accounting_attempt1.json")); tried = {r["url"].rstrip("/") for r in rows}
    for i in APPS18: tried |= {p["url"].rstrip("/") for p in json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]}
    plan = {}
    for r in rows:
        if r["outcome"] not in ("fetch_error", "fetch_empty", "thin_or_js_shell"): continue
        i = r["app_id"]; alts = []
        for v in variants(r["url"]):
            if v.rstrip("/") not in tried and not BAD.search(v): alts.append(dict(url=v, kind="url_variant"))
        for h in stored_hits(i):
            u = h["url"].split("#")[0]
            if reg(urlparse(u).hostname) in regs(i) and host_ok(u) and u.rstrip("/") not in tried and not EXCL.search(u + " " + (h.get("title") or "")) and not BAD.search(u) and cat_of(u, h.get("title")) == r["category"] and u not in [a["url"] for a in alts]:
                alts.append(dict(url=u, kind="stored_search_hit"))
        plan.setdefault(str(i), {"app": r["app"], "targets": []})["targets"].append(dict(parent_url=r["url"], parent_outcome=r["outcome"], category=r["category"], alternatives=alts[:3]))
    # app-level discovery for apps that stayed unresolved + Neo4j surfaces (targeted free searches; results are candidates only)
    app_level = {"46": ["Squarespace developer API access commerce plan requirement", "Squarespace developers OAuth API key"], "20": ["Gladly API access developer tokens", "Gladly pricing"], "38": ["Pinterest API access trial standard access developers", "Pinterest developers get started app review"],
                 "66": ["Neo4j Query API HTTPS endpoint", "Neo4j Aura API authentication client credentials"]}
    plan["_app_level_searches"] = app_level; json.dump(plan, open(f"{OUT}/retryplan.json", "w"), indent=1)
    n = sum(len(t["alternatives"]) for k, v in plan.items() if k[0] != "_" for t in v["targets"]); print("targets:", sum(len(v["targets"]) for k, v in plan.items() if k[0] != "_"), "| candidate alternatives:", n)
    for k, v in plan.items():
        if k[0] == "_": continue
        for t in v["targets"]: print(f"#{k} {v['app']:<24} {t['parent_outcome']:<16} {t['parent_url'][8:62]:<54} -> {[(a['kind'][:5], a['url'][8:58]) for a in t['alternatives']]}")

def fetch_one(m, sid, url):
    e = dict(url=url, requested_at=iso())
    for k in range(2):
        try:
            r = m.call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": "TINYFISH_FETCH_URLS", "arguments": {"urls": [url], "purpose": "official pricing / developer registration / API access / onboarding evidence (retry)"}}], "sync_response_to_workbench": False, "session_id": sid, "thought": "free evidence retry"})
            d = json.loads(r["content"][0]["text"]); ch = (d.get("data", {}).get("instant_charge") or d.get("instant_charge") or {}); assert float(ch.get("amount", 0) or 0) == 0, f"NONZERO CHARGE {ch}"   # never spend
            resp = d["data"]["results"][0]["response"]; e["charge_usd"] = 0.0
            if not resp.get("successful"): e.update(status="error", error=str(resp)[:200]); break
            got = [x for x in resp["data"].get("results", []) if x.get("text")]
            if not got: e.update(status="empty", error=str(resp["data"].get("errors"))[:200]); break
            x = got[0]; t = x["text"]; e.update(status="ok", final_url=x.get("final_url"), title=x.get("title"), chars=len(t), sha256=hashlib.sha256(t.encode()).hexdigest(), text=t[:30000]); break
        except AssertionError: raise
        except Exception as ex: e.update(status="error", error=f"{type(ex).__name__}: {str(ex)[:150]}"); time.sleep(3)
    e["completed_at"] = iso(); return e

def retry_app(args):
    from mcp import MCP
    i, plan = args; f = f"{OUT}/raw/{i}.json"
    if os.path.exists(f): return json.load(open(f))
    m = MCP(); r = m.call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": "fetch a URL and return its page text"}], "session": {"generate_id": True}}); sid = json.loads(r["content"][0]["text"])["data"]["session"]["id"]
    base = {nh(p["text"]) for p in json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]}; seen = {}
    for rr in json.load(open(f"{V1}/raw/{i}.json"))["fetched"]:
        if rr["status"] == "ok" and rr["chars"] >= 500 and not BAD.search(rr["url"]): seen.setdefault(nh(rr["text"]), rr["url"])
    att = []; tried = set(); rec = dict(app_id=i, app=A[i]["name"], tool="composio:TINYFISH_FETCH_URLS", session=sid, attempts=[], app_level_search_hits=[])
    def do(url, kind, parent, why):
        if url.rstrip("/") in tried: return None
        tried.add(url.rstrip("/")); e = fetch_one(m, sid, url); o, dup = outcome(url, e["status"], e.get("chars"), i, e.get("text"), seen, base)
        if o == "usable_unique": seen[nh(e["text"])] = url
        e.update(app_id=i, kind=kind, parent_url=parent, reason=why, outcome=o, duplicate_of=dup, attempt=2); rec["attempts"].append(e); return e
    for t in (plan.get(str(i)) or {}).get("targets", []):
        done = False
        for a in t["alternatives"]:
            if done: rec["attempts"].append(dict(app_id=i, url=a["url"], kind=a["kind"], parent_url=t["parent_url"], reason=f"alternative for {t['parent_outcome']}", status="not_attempted", outcome="skipped_after_alternative_succeeded", attempt=2)); continue
            e = do(a["url"], a["kind"], t["parent_url"], f"alternative for {t['parent_outcome']}"); done = bool(e and e["outcome"] == "usable_unique")
    qs = plan.get("_app_level_searches", {}).get(str(i))
    if qs:
        hits = []
        for q in qs:
            try:
                r = m.call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": "TINYFISH_SEARCH_WEB", "arguments": {"query": q + " site:" + sorted(regs(i))[0], "purpose": "find official pages"}}], "sync_response_to_workbench": False, "session_id": sid, "thought": "free discovery"})
                d = json.loads(r["content"][0]["text"]); ch = (d.get("data", {}).get("instant_charge") or d.get("instant_charge") or {}); assert float(ch.get("amount", 0) or 0) == 0
                hits += [dict(q=q, url=x["url"], title=x.get("title"), searched_at=iso()) for x in d["data"]["results"][0]["response"].get("data", {}).get("results", [])]
            except AssertionError: raise
            except Exception: pass
        rec["app_level_search_hits"] = hits; pat = re.compile(r"query-api|aura/api|client|credential|graphql|http-api|driver|authenticat", re.I) if i == 66 else None
        picks = [h for h in hits if reg(urlparse(h["url"]).hostname) in regs(i) and host_ok(h["url"]) and not EXCL.search(h["url"]) and not BAD.search(h["url"]) and (pat.search(h["url"]) if pat else cat_of(h["url"], h.get("title")) != "other")]
        for h in picks[:3]: do(h["url"], "app_level_search", None, "discovery for unresolved app / scope assessment")
    tmp = f + ".tmp"; json.dump(rec, open(tmp, "w"), indent=1); os.replace(tmp, f); os.chmod(f, 0o444); return rec

def retry():
    plan = json.load(open(f"{OUT}/retryplan.json")); ids = sorted({int(k) for k in plan if k[0] != "_"} | {int(k) for k in plan["_app_level_searches"]})
    with ThreadPoolExecutor(3) as ex: recs = list(ex.map(retry_app, [(i, plan) for i in ids]))
    allatt = [a for r in recs for a in r["attempts"]]; c = collections.Counter(a["outcome"] for a in allatt)
    print("retry attempts:", len(allatt), dict(c), "| max charge:", max([a.get("charge_usd", 0) for a in allatt] or [0]))
    for r in recs:
        for a in r["attempts"]:
            if a["status"] != "not_attempted": print(f"  #{r['app_id']} {r['app'][:14]:<14} {a['kind'][:9]:<9} {a['outcome']:<18} chars={a.get('chars')} {a['url'][8:78]}")

def catalog():
    from mcp import MCP
    m = MCP(); out = dict(retrieved_at=iso(), note="metadata only: COMPOSIO_SEARCH_TOOLS + COMPOSIO_GET_TOOL_SCHEMAS; no tool executed", queries={})
    for uc in ("run a Cypher query against a Neo4j graph database", "manage Neo4j Aura database instances: create, pause, resume, delete", "Neo4j"):
        r = m.call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": uc}], "session": {"generate_id": True}}); d = json.loads(r["content"][0]["text"])["data"]
        res = d["results"][0]; out["queries"][uc] = dict(primary=res.get("primary_tool_slugs"), related=res.get("related_tool_slugs"), toolkits=[dict(toolkit=t.get("toolkit"), description=(t.get("description") or "")[:240], has_active_connection=t.get("has_active_connection"), status=(t.get("status_message") or "")[:200]) for t in d.get("toolkit_connection_statuses", [])],
                                              tool_slugs_in_schemas=[k if isinstance(k, str) else k[0] for k in (d["tool_schemas"] if isinstance(d["tool_schemas"], dict) else [x[0] for x in d["tool_schemas"]])])
    slugs = sorted({s for q in out["queries"].values() for s in (q["tool_slugs_in_schemas"] + (q["primary"] or []) + (q["related"] or [])) if "NEO4J" in s.upper()})
    out["neo4j_tool_slugs_found"] = slugs
    if slugs:
        r = m.call("COMPOSIO_GET_TOOL_SCHEMAS", {"tool_slugs": slugs[:12], "session_id": "x"}); t = json.loads(r["content"][0]["text"])
        out["schemas"] = {k: dict(description=(v.get("description") or "")[:300], required=(v.get("input_schema") or {}).get("required"), props=list(((v.get("input_schema") or {}).get("properties") or {}))[:12]) for k, v in (t.get("data", {}).get("tool_schemas") or {}).items()}
        out["schemas_raw_error"] = None if out["schemas"] else str(t)[:300]
    json.dump(out, open(f"{OUT}/catalog_neo4j.json", "w"), indent=1); os.chmod(f"{OUT}/catalog_neo4j.json", 0o444)
    print("neo4j tool slugs found:", slugs)
    for k, v in out.get("schemas", {}).items(): print(f"  {k}: {v['description'][:150]} | required={v['required']}")
    print("toolkits seen for the 3 queries:", {uc: [t["toolkit"] for t in q["toolkits"]] for uc, q in out["queries"].items()})

if __name__ == "__main__":
    {"account": account, "retryplan": retryplan, "retry": retry, "catalog": catalog}[sys.argv[1]]()
