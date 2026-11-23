"""NOTE: the first fetch ran with an EXCL regex escaping bug (pinterest user pages / discord nitro pages slipped through); assess() excludes them from evidence.
Evidence top-up for the 18 apps whose access/gating evidence was partial/insufficient. Run id: topup-v1-20261123 (all output under runs/).
Stages:  search (network)  -> search_hits.json  free domain-targeted TinyFish searches (3 queries/app), query + timestamp preserved
         plan   (offline)  -> candidates.json   official pricing / developer-registration / API-access / onboarding URLs, from STORED search hits (+ /pricing guesses, flagged)
         fetch  (network)  -> raw/<id>.json     free Composio TINYFISH_FETCH_URLS only; every call asserts instant_charge == 0; url, timestamp, sha256 preserved
         assess (offline)  -> assessment.json   sentences classified into SEPARATE buckets: dev_access_gate | end_user_consent | admin_consent | pricing_info | generic_approval
No Gemini/Groq. Never reads or writes baseline/ or work/ except reading baseline/p1_v1/raw + audit outputs."""
import os, re, sys, json, time, hashlib, datetime, collections
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src")
for _l in open(".env"):   # only the Composio key is ever read here (no Gemini/Groq keys)
    if _l.startswith("COMPOSIO_API_KEY="): os.environ["COMPOSIO_API_KEY"] = _l.strip().split("=", 1)[1]
OUT = "runs/topup-v1-20261123"; os.makedirs(f"{OUT}/raw", exist_ok=True)
APPS18 = [29, 36, 46, 65, 66, 71, 72, 75, 20, 25, 26, 38, 44, 47, 61, 62, 63, 70]   # partial(8) + insufficient(10) from eligibility-v1
iso = lambda t=None: datetime.datetime.fromtimestamp(t or time.time()).astimezone().isoformat(timespec="seconds")
reg = lambda h: ".".join((h or "").split(".")[-2:])
A = {a["id"]: a for a in json.load(open("runs/audit-raw-v2-20261123/audit.json"))}
EXCL = re.compile(r"blog|changelog|release-?notes|community|forum|career|/press|customers?/|case-?stud|webinar|status\.|legal|privacy|cookie|podcast|/events?/|academy|/jobs|/topics/|answers\.|labs/|stackoverflow|/discussions|ai-gateway|agent-memory|pinterest\.com/(ideas/|[a-z0-9_]+/[a-z0-9-]*plan)|how-to-call|nitro|server-?boost", re.I)
CATS = [("pricing", re.compile(r"pricing|/plans?\b|billing|subscription", re.I)),
        ("registration", re.compile(r"sign-?up|register|create[- ]?(an?[- ])?(account|app|application|developer)|developer[- ](account|portal|program|registration)|credentials|api[- ]?keys?|access[- ]?tokens?|personal[- ]access|api[- ]access|request[- ]access|\bapply\b", re.I)),
        ("review_partner", re.compile(r"app[- ]review|review[- ]process|partner|marketplace|submission|verification|approval|publish", re.I)),
        ("onboarding", re.compile(r"get(ting)?[- ]started|quick-?start|onboard|introduction|overview", re.I))]

def official_regs(i):
    return {reg(p["host"]) for p in A[i]["pages"] if p["official"] and p["usable"]}

def plan():
    out = {}
    for i in APPS18:
        raw = json.load(open(f"baseline/p1_v1/raw/{i}.json")); have = {p["url"].split("#")[0].rstrip("/") for p in raw["pages"]}; regs = official_regs(i); cand = {}
        fresh = json.load(open(f"{OUT}/search_hits.json")).get(str(i), []) if os.path.exists(f"{OUT}/search_hits.json") else []
        for h in fresh + [h for h in raw["search_hits"] if "MCP server" not in h["q"]]:
            u = h["url"].split("#")[0];
            if reg(urlparse(u).hostname) not in regs or u.rstrip("/") in have or EXCL.search(u + " " + (h.get("title") or "")): continue
            blob = urlparse(u).path + " " + (h.get("title") or "")
            for c, rx in CATS:
                if rx.search(blob): cand.setdefault(u, dict(url=u, category=c, source="stored_search_hit", title=h.get("title"))); break
        picked = []; per = collections.Counter()
        for c in ("pricing", "registration", "review_partner", "onboarding"):
            for v in [v for v in cand.values() if v["category"] == c]:
                if per[c] < (1 if c in ("review_partner", "onboarding") else 2) and len(picked) < 4: picked.append(v); per[c] += 1
        if not any(p["category"] == "pricing" for p in picked) and len(picked) < 4:        # fallback: conventional /pricing on the main official domain (flagged as a guess)
            main = sorted(regs, key=len)[0] if regs else None
            if main: picked.append(dict(url=f"https://www.{main}/pricing", category="pricing", source="pattern_guess_unverified", title=None))
        out[i] = dict(name=A[i]["name"], official_registrable_domains=sorted(regs), already_fetched_pages=len(raw["pages"]), candidates_total=len(cand), chosen=picked)
    json.dump(out, open(f"{OUT}/candidates.json", "w"), indent=1)
    for i, v in out.items(): print(f"#{i:>3} {v['name']:<26} cands={v['candidates_total']:>2} chosen={[ (c['category'][:4], c['source'][:5], urlparse(c['url']).hostname + urlparse(c['url']).path[:34]) for c in v['chosen']]}")
    print("total chosen:", sum(len(v["chosen"]) for v in out.values()), "| apps with 0 chosen:", [i for i, v in out.items() if not v["chosen"]])

def search_app(i):
    from mcp import MCP
    m = MCP(); r = m.call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": "search the web"}], "session": {"generate_id": True}}); sid = json.loads(r["content"][0]["text"])["data"]["session"]["id"]
    regs = sorted(official_regs(i)); dom = regs[0] if regs else ""; nm = A[i]["name"]; hits = []
    for q in (f"{nm} pricing plans site:{dom}", f"{nm} developer account register create app API key site:{dom}", f"{nm} API access requirements plan app review approval site:{dom}"):
        for attempt in range(2):
            try:
                r = m.call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": "TINYFISH_SEARCH_WEB", "arguments": {"query": q, "purpose": "find official pricing / developer registration / API access pages"}}], "sync_response_to_workbench": False, "session_id": sid, "thought": "free evidence top-up discovery"})
                d = json.loads(r["content"][0]["text"]); ch = (d.get("data", {}).get("instant_charge") or d.get("instant_charge") or {}); assert float(ch.get("amount", 0) or 0) == 0, f"NONZERO CHARGE {ch}"
                for x in d["data"]["results"][0]["response"].get("data", {}).get("results", []): hits.append(dict(q=q, url=x["url"], title=x.get("title"), snippet=(x.get("snippet") or "")[:300], searched_at=iso()))
                break
            except AssertionError: raise
            except Exception: time.sleep(3)
    return i, hits

def search():
    with ThreadPoolExecutor(3) as ex: res = dict(ex.map(search_app, APPS18))
    json.dump({str(k): v for k, v in res.items()}, open(f"{OUT}/search_hits.json", "w"), indent=1); print("search hits per app:", {k: len(v) for k, v in res.items()})

def fetch_app(i):
    from mcp import MCP
    f = f"{OUT}/raw/{i}.json"
    if os.path.exists(f): return json.load(open(f))
    pl = json.load(open(f"{OUT}/candidates.json"))[str(i)]; m = MCP()
    r = m.call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": "fetch a URL and return its page text"}], "session": {"generate_id": True}})
    sid = json.loads(r["content"][0]["text"])["data"]["session"]["id"]; rec = dict(app_id=i, name=pl["name"], tool="composio:TINYFISH_FETCH_URLS", session=sid, fetched=[])
    for c in pl["chosen"]:
        t0 = time.time(); e = dict(url=c["url"], category=c["category"], source=c["source"], requested_at=iso(t0))
        for attempt in range(2):
            try:
                r = m.call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": "TINYFISH_FETCH_URLS", "arguments": {"urls": [c["url"]], "purpose": "official pricing / developer registration / API access / onboarding evidence"}}], "sync_response_to_workbench": False, "session_id": sid, "thought": "free evidence top-up"})
                d = json.loads(r["content"][0]["text"]); ch = (d.get("data", {}).get("instant_charge") or d.get("instant_charge") or {}); amt = float(ch.get("amount", 0) or 0)
                assert amt == 0, f"NONZERO CHARGE {ch}"                                   # never spend
                resp = d["data"]["results"][0]["response"]; e["charge_usd"] = amt
                if not resp.get("successful"): e.update(status="error", error=str(resp)[:200]); break
                got = [x for x in resp["data"].get("results", []) if x.get("text")]
                if not got: e.update(status="empty", error=str(resp["data"].get("errors"))[:200]); break
                x = got[0]; txt = x["text"]; e.update(status="ok", final_url=x.get("final_url"), title=x.get("title"), chars=len(txt), truncated_at_30000=len(txt) > 30000, sha256=hashlib.sha256(txt.encode()).hexdigest(), text=txt[:30000]); break
            except AssertionError: raise
            except Exception as ex: e.update(status="error", error=f"{type(ex).__name__}: {str(ex)[:150]}"); time.sleep(3)
        e["completed_at"] = iso(); rec["fetched"].append(e)
    tmp = f + ".tmp"; json.dump(rec, open(tmp, "w"), indent=1); os.replace(tmp, f); os.chmod(f, 0o444); return rec

def fetch():
    with ThreadPoolExecutor(3) as ex: recs = list(ex.map(fetch_app, APPS18))
    for r in recs: print(f"#{r['app_id']:>3} {r['name']:<26}", [(e["category"][:4], e["status"], e.get("chars")) for e in r["fetched"]])
    print("total fetched ok:", sum(e["status"] == "ok" for r in recs for e in r["fetched"]), "of", sum(len(r["fetched"]) for r in recs), "| max charge:", max([e.get("charge_usd", 0) for r in recs for e in r["fetched"]] or [0]))

BAD = re.compile(r"pinterest\.com/(ideas/|[a-z0-9_]+/[a-z0-9-]*plan)|support\.discord\.com/.*(subscription|pricing|nitro|boost)|how-to-call", re.I)
CONSENT = re.compile(r"users?\b[^.\n]{0,60}\b(?:approve|authoriz|grant|consent|allow)|consent (?:screen|page|prompt)|authorization (?:screen|page|prompt)|asks? (?:the )?user|approval screen|user (?:approval|consent)", re.I)
ADMIN = re.compile(r"admin(?:istrator)?s?\b[^.\n]{0,60}\b(?:consent|approv|install|authoriz|enable|restrict|control|disable)|(?:workspace|organization|org|account) (?:owners?|admins?)[^.\n]{0,60}(?:approv|install|enable|restrict)|requires? admin", re.I)
GATES = {"plan_gate": [re.compile(r"(?:api|developer|integration|token|rest)[^.\n]{0,80}(?:available (?:on|for|to|with|in)|requires?|only (?:on|for|available|to)|included (?:in|with)|limited to|restricted to)[^.\n]{0,80}(?:plans?|tiers?|enterprise|premium|paid|business|\bpro\b|subscription)", re.I), re.compile(r"(?:enterprise|business|premium|paid|\bpro\b|growth|team|scale)\s+(?:plans?|tiers?|accounts?)[^.\n]{0,100}(?:api|developer|integration|token|rest)", re.I)],
         "review_gate": [re.compile(r"(?:app|api|developer|partner)\s+(?:review|verification|approval)|submit[^.\n]{0,50}(?:review|approval|verification)|apply (?:for|to)[^.\n]{0,50}(?:api|access|program|developer|partner)|request (?:api )?access|developer program|partner program|become a (?:tech )?partner|waitlist|private beta|contact (?:our )?sales|business verification|developer token|access level|standard access|basic access", re.I)],
         "free_signup": [re.compile(r"(?:api|developer|token|key)[^.\n]{0,60}(?:free|no cost|at no charge|no credit card)|(?:free|no cost)[^.\n]{0,60}(?:api|developer account|sign ?up|key|token)|(?:create|register|sign up for)[^.\n]{0,40}(?:free )?(?:developer |an? )?(?:account|app|application)", re.I)]}
PRICING = re.compile(r"\$\s?\d|€\s?\d|per (?:month|user|seat|member)|/mo\b|/month|free plan|free tier|free trial|\btrial\b|\bpricing\b", re.I)
GENERIC = re.compile(r"\bapprov(?:al|ed|e|es|ing)\b", re.I)

def classify(text):
    out = collections.defaultdict(list)
    for sent in re.split(r"(?<=[.!?])\s+|\n+", text):
        sent = re.sub(r"\s+", " ", sent).strip()
        if not (25 <= len(sent) <= 500): continue
        if CONSENT.search(sent): out["end_user_consent"].append(sent)
        elif ADMIN.search(sent): out["admin_consent"].append(sent)
        else:
            hit = next((k for k, rxs in GATES.items() if any(rx.search(sent) for rx in rxs)), None)
            if hit: out["dev_access_gate:" + hit].append(sent)
            elif PRICING.search(sent): out["pricing_info"].append(sent)
            elif GENERIC.search(sent): out["generic_approval_unclassified"].append(sent)
    return out

def assess():
    res = {}
    for i in APPS18:
        rec = json.load(open(f"{OUT}/raw/{i}.json")); regs = official_regs(i); pages = []; buckets = collections.defaultdict(list)
        for e in rec["fetched"]:
            why = None
            if e["status"] != "ok": why = "fetch_" + e["status"]
            elif e["chars"] < 500: why = "thin_or_js_shell(<500 chars)"
            elif reg(urlparse(e["url"]).hostname) not in regs: why = "not_official_domain"
            elif BAD.search(e["url"]): why = "off_target_not_official_api_page"
            pages.append(dict(url=e["url"], category=e["category"], status=e["status"], chars=e.get("chars"), sha256=e.get("sha256"), fetched_at=e["completed_at"], used_as_evidence=why is None, excluded_reason=why))
            if why is None:
                for k, v in classify(e["text"]).items():
                    for s_ in v: buckets[k].append(dict(url=e["url"], sentence=s_[:300]))
        res[i] = dict(name=rec["name"], pages=pages, evidence_pages=sum(p["used_as_evidence"] for p in pages), bucket_counts={k: len(v) for k, v in buckets.items()}, top={k: v[:3] for k, v in buckets.items()})
    json.dump(res, open(f"{OUT}/assessment.json", "w"), indent=1)
    for i, r in res.items():
        print(f"\n#{i} {r['name']}: evidence_pages={r['evidence_pages']}/{len(r['pages'])} buckets={r['bucket_counts']}")
        for p in r["pages"]:
            if not p["used_as_evidence"]: print(f"    EXCLUDED {p['url'][8:70]} -> {p['excluded_reason']}")
        for k in ("dev_access_gate:plan_gate", "dev_access_gate:review_gate", "dev_access_gate:free_signup"):
            for x in r["top"].get(k, [])[:2]: print(f"    [{k.split(':')[1][:6]}] ({x['url'][8:44]}) {x['sentence'][:170]}")

if __name__ == "__main__":
    {"search": search, "plan": plan, "fetch": fetch, "assess": assess}[sys.argv[1]]()
