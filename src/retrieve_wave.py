"""Free official-source retrieval for apps without (sufficient) cached evidence. Composio TINYFISH_SEARCH_WEB / TINYFISH_FETCH_URLS only (instant_charge asserted 0; stops on any charge). No LLM.
Per app: 4 searches -> candidate hits kept verbatim in the ledger -> accepted hosts = registrable domain whose label contains the normalised app name (identity heuristic, flagged for review when >1 domain) -> up to 6 pages fetched (priority: api/auth/pricing/mcp).
Output (new dir per run): raw/<id>.json (resumable; failures preserved), LEDGER.json. Usage: python src/retrieve_wave.py <out_dir> <id,id,...>"""
import os, re, sys, json, time, hashlib, datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src")
for l in open(".env"):
    if l.startswith("COMPOSIO_API_KEY="): os.environ["COMPOSIO_API_KEY"] = l.strip().split("=", 1)[1]
iso = lambda: datetime.datetime.now().astimezone().isoformat(timespec="seconds"); sha = lambda t: hashlib.sha256(t.encode()).hexdigest()
D = json.load(open("data/apps.json")); NAME = {a[0]: a[2] for a in D["apps"]}
reg = lambda h: ".".join((h or "").lower().split(".")[-2:]) if not re.search(r"\.(co|com|org|net)\.[a-z]{2}$", h or "") else ".".join(h.split(".")[-3:])
PRIO = [("mcp", re.compile(r"mcp|model-context", re.I)), ("auth", re.compile(r"auth|oauth|token|api-?key|credential|security", re.I)), ("api", re.compile(r"api|developer|reference|docs", re.I)), ("pricing", re.compile(r"pricing|plans?|billing", re.I)), ("access", re.compile(r"register|sign-?up|app-?review|partner|get-?started|quick-?start", re.I))]
BAD = re.compile(r"blog|changelog|release-?notes|community|forum|career|/press|case-?stud|webinar|status\.|legal|privacy|cookie|podcast|/jobs|stackoverflow|github\.com/.*/issues|youtube|linkedin|twitter|facebook", re.I)
def prio(u): return next((i for i, (_, rx) in enumerate(PRIO) if rx.search(u)), 9)
def call(m, sid, slug, args):
    for k in range(2):
        try:
            r = m.call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": slug, "arguments": args}], "sync_response_to_workbench": False, "session_id": sid, "thought": "free official-source retrieval", "current_step": "RETRIEVE", "current_step_metric": "1/1"})
            d = json.loads(r["content"][0]["text"]); ch = (d.get("data", {}).get("instant_charge") or d.get("instant_charge") or {}); assert float(ch.get("amount", 0) or 0) == 0, f"NONZERO CHARGE {ch}"
            return d["data"]["results"][0]["response"]
        except AssertionError: raise
        except Exception as e: err = f"{type(e).__name__}: {str(e)[:150]}"; time.sleep(3)
    return {"successful": False, "error": err}
OVERRIDE = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}     # {"id": "host/optional/path"}: official hint from the ORIGINAL list (ids 1-50); restricts accepted hits
def one(args):
    out, i = args; f = f"{out}/raw/{i}.json"
    if os.path.exists(f): return json.load(open(f))
    from mcp import MCP
    m = MCP(); r = m.call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": "search the web and fetch pages"}], "session": {"generate_id": True}}); sid = json.loads(r["content"][0]["text"])["data"]["session"]["id"]; nm = NAME[i]; norm = re.sub(r"[^a-z0-9]", "", nm.lower().split("(")[0]); rec = dict(id=i, name=nm, started=iso(), searches=[], fetched=[])
    hits = []
    ov = OVERRIDE.get(str(i)); site = f" site:{ov}" if ov else ""
    for q in (f"{nm} API documentation{site}", f"{nm} API authentication OAuth API key developer{site}", f"{nm} API access pricing plans developer account{site}", f"{nm} MCP server official" + (f" site:{ov.split('/')[0]}" if ov else "")):
        resp = call(m, sid, "TINYFISH_SEARCH_WEB", {"query": q, "purpose": "find official developer documentation"}); got = resp.get("data", {}).get("results", []) if resp.get("successful") else []
        rec["searches"].append(dict(q=q, ok=bool(resp.get("successful")), n=len(got), error=None if resp.get("successful") else str(resp)[:200], at=iso())); hits += [dict(q=q, url=x["url"], title=x.get("title"), snippet=(x.get("snippet") or "")[:300]) for x in got]
    doms = {}
    for h in hits:
        d = reg(urlparse(h["url"]).hostname)
        if ov: 
            if reg(urlparse(h["url"]).hostname) == reg(ov.split("/")[0]) and (("/" not in ov) or ov.split("/", 1)[1] in h["url"]): doms.setdefault(d, []).append(h["url"])
        elif len(norm) >= 3 and norm in re.sub(r"[^a-z0-9]", "", d.split(".")[0]): doms.setdefault(d, []).append(h["url"])
    rec["candidate_hits"] = hits; rec["official_domain_candidates"] = {d: len(u) for d, u in doms.items()}; rec["override_hint"] = ov; rec["identity_flag"] = ("hint_domain_from_original_list" if doms else "no_hint_domain_hits") if ov else "no_domain_matched_name" if not doms else ("multiple_candidate_domains_review_identity" if len(doms) > 1 else "single_domain_name_match")
    if doms:
        top = max(doms, key=lambda d: len(doms[d])); urls = []
        for h in hits:
            u = h["url"].split("#")[0]
            if reg(urlparse(u).hostname) == top and not BAD.search(u) and u not in urls: urls.append(u)
        urls = sorted(urls, key=prio)[:6]; rec["selected_domain"] = top
        for u in urls:
            resp = call(m, sid, "TINYFISH_FETCH_URLS", {"urls": [u], "purpose": "official developer documentation"}); e = dict(url=u, requested_at=iso())
            if not resp.get("successful"): e.update(status="error", error=str(resp)[:200])
            else:
                got = [x for x in resp.get("data", {}).get("results", []) if x.get("text")]
                if not got: e.update(status="empty")
                else: x = got[0]; t = x["text"]; e.update(status="ok", final_url=x.get("final_url"), title=x.get("title"), chars=len(t), sha256=sha(t), text=t[:30000], retrieved_at=iso())
            e["charge_usd"] = 0.0; rec["fetched"].append(e)
    rec["completed"] = iso(); tmp = f + ".tmp"; json.dump(rec, open(tmp, "w"), indent=1); os.replace(tmp, f); return rec
if __name__ == "__main__":
    out = sys.argv[1]; ids = [int(x) for x in sys.argv[2].split(",")]; os.makedirs(f"{out}/raw", exist_ok=True)
    with ThreadPoolExecutor(3) as ex: res = list(ex.map(one, [(out, i) for i in ids]))
    led = [dict(id=r["id"], name=r["name"], identity_flag=r["identity_flag"], domains=r["official_domain_candidates"], selected=r.get("selected_domain"), pages_ok=sum(e["status"] == "ok" for e in r["fetched"]), pages_failed=sum(e["status"] != "ok" for e in r["fetched"])) for r in res]
    json.dump(led, open(f"{out}/LEDGER.json", "w"), indent=1); print(json.dumps(led)[:3000])
