"""Offline semantic-quality audit of cached retrievals. NO network, NO LLM. Reads baseline/p1_v1 (read-only), writes ONLY to runs/<run_id>/.
Deterministic, keyword/URL heuristics: they measure whether a retrieval LOOKS sufficient (official, relevant, covers auth/access/API/MCP topics),
not whether any claim is true. Rubric version: raw-audit-v1.   Usage: python src/audit_raw.py"""
import os, re, json, glob, csv, hashlib, time, collections
from urllib.parse import urlparse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
RUN = "audit-raw-v1-20261123"; OUT = f"runs/{RUN}"
assert not os.path.exists(OUT), "run dir exists; refusing to overwrite"
os.makedirs(OUT)
APPS = {a[0]: dict(id=a[0], cat=a[1], name=a[2], hint=a[3]) for a in json.load(open("baseline/data/apps.json"))["apps"]}

# extra vendor-domain tokens where the product name is not in the vendor's domain (heuristic; used only for the 'official' flag)
ALIAS = {"Jira": ["atlassian"], "Meta Ads": ["facebook", "meta"], "Threads (Meta)": ["facebook", "meta", "threads"], "WhatsApp Business": ["facebook", "meta", "whatsapp"],
         "Google Ads": ["google"], "LinkedIn Ads": ["linkedin", "microsoft"], "Magento (Adobe Commerce)": ["adobe", "magento"], "Salesforce Commerce Cloud": ["salesforce"],
         "QuickBooks": ["intuit"], "MongoDB Atlas": ["mongodb"], "Amazon Selling Partner": ["amazon"], "NotebookLM": ["google"], "SendGrid": ["twilio", "sendgrid"],
         "Freshdesk": ["freshworks", "freshdesk"], "Zoho CRM": ["zoho"], "Zoho Cliq": ["zoho"], "Lark (Larksuite)": ["larksuite", "feishu"], "Mermaid CLI": ["mermaid"],
         "Harvest": ["getharvest", "harvestapp"], "Fathom": ["fathom"], "Otter AI": ["otter"], "Devin": ["devin", "cognition"], "Help Scout": ["helpscout"], "Vonage": ["vonage"]}
AMBIGUOUS = {"Close", "Front", "Plain", "Twenty", "Pylon", "Linear", "Coda", "Ramp", "Grain", "Consensus", "Clay", "Sherlock", "Copper", "Harvest", "Lark (Larksuite)", "Fathom", "Devin",
             "Threads (Meta)", "Mermaid CLI", "YouTube Transcript", "Waterfall.io", "Paygent Connect", "iPayX", "fanbasis", "higgsfield", "Podio", "Gladly", "Otter AI", "Reducto", "Plaid"}

def host(u): return (urlparse(u).hostname or "").lower()
def tokens(app):
    n = re.sub(r"\(.*?\)", "", app["name"]).lower(); toks = {re.sub(r"[^a-z0-9]", "", n)} | {t for t in re.split(r"[^a-z0-9]+", n) if len(t) >= 4}
    if app["hint"]:
        h = host("https://" + app["hint"].split(" ")[0].split("/")[0]); toks |= {h.split(".")[-2]} if h.count(".") else set()
    toks |= set(ALIAS.get(app["name"], [])); return {t for t in toks if t}

BLOCK = re.compile(r"access denied|just a moment|attention required|403 forbidden|verify you are human|captcha", re.I)
NOTFOUND = re.compile(r"page not found|404|not found|doesn.t exist", re.I)
JSSHELL = re.compile(r"enable javascript|requires javascript|you need to enable|loading\.\.\.", re.I)
AUTH = re.compile(r"oauth|api[ _-]?key|apikey|bearer|access token|client[_ ]secret|client[_ ]id|basic auth|authorization:|\bjwt\b|hmac|refresh token|personal access token|api token|x-api-key", re.I)
ACCESS = re.compile(r"pricing|free plan|free tier|free trial|\btrial\b|paid plan|contact sales|partner program|\bpartners?\b|app review|approval|approved|request access|developer account|developer program|enterprise|sandbox|rate limit|scopes?|waitlist|apply for", re.I)
API = re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/[\w\-/{}.:]+|rest api|restful|graphql|\bsoap\b|openapi|swagger|endpoints?\b", re.I)
MCP = re.compile(r"\bmcp\b|model context protocol", re.I)
INJ = re.compile(r"ignore (all |any )?(previous|prior) instructions|disregard .{0,30}instructions|system prompt|you are an? (ai|assistant)", re.I)

def classify_url(u, title):
    s = (urlparse(u).path + " " + (title or "")).lower(); h = host(u)
    if re.search(r"stackoverflow|medium\.com|reddit|quora|forum|community", h + s): return "community_or_blog"
    if "github.com" in h: return "github"
    if re.search(r"auth|oauth|token|credential|api-?key|login|sign-?in", s): return "auth"
    if re.search(r"pricing|plans|billing", s): return "pricing"
    if re.search(r"reference|api-?ref|endpoints|openapi|swagger|/rest|/api", s): return "reference"
    if re.search(r"changelog|release|blog|news", s): return "changelog_or_blog"
    if re.search(r"docs|guide|tutorial|quickstart|getting-?started|developer", s + h): return "docs_guide"
    return "other"

def audit_page(p, app, toks):
    t = p["text"]; tl = t.lower(); h = host(p["url"]); head = tl[:300]
    off = any(tok in h for tok in toks)
    f = {"url": p["url"], "host": h, "kind": classify_url(p["url"], p.get("title")), "len": len(t), "official": off,
         "thin": len(t) < 500, "truncated": len(t) >= 9000, "blocked": bool(BLOCK.search(tl[:600])),
         "notfound": bool(NOTFOUND.search(head)) and len(t) < 1500, "js_shell": bool(JSSHELL.search(tl[:800])) and len(t) < 1000,
         "login_wall": len(t) < 1500 and bool(re.search(r"sign in|log in", tl[:500])),
         "auth_hits": len(AUTH.findall(t)), "auth_kinds": sorted({m.lower() for m in AUTH.findall(t)})[:6], "access_kinds": sorted({m.lower() for m in ACCESS.findall(t)})[:8],
         "api_hits": len(API.findall(t)), "mcp_hits": len(MCP.findall(t)), "injection_markers": len(INJ.findall(t)),
         "name_hits": sum(tl.count(tok) for tok in toks), "in_title": any(tok in (p.get("title") or "").lower() for tok in toks), "text_hash": hashlib.sha256(t[:400].encode()).hexdigest()[:12]}
    f["usable"] = not (f["thin"] or f["blocked"] or f["notfound"] or f["js_shell"] or f["login_wall"])
    return f

def audit_app(i):
    app = APPS[i]; raw = json.load(open(f"baseline/p1_v1/raw/{i}.json")); toks = tokens(app)
    pages = [audit_page(p, app, toks) for p in raw["pages"]]
    seen = collections.Counter(p["text_hash"] for p in pages)
    for p in pages: p["duplicate"] = seen[p["text_hash"]] > 1
    U = [p for p in pages if p["usable"] and not p["duplicate"] or (p["usable"] and p["duplicate"])]
    uo = [p for p in pages if p["usable"] and p["official"]]
    cov = lambda pool, k, n: any(p[k] >= n if isinstance(p[k], int) else len(p[k]) >= n for p in pool)
    c = {"auth": cov([p for p in pages if p["usable"]], "auth_hits", 3), "auth_official": cov(uo, "auth_hits", 3),
         "access": cov([p for p in pages if p["usable"]], "access_kinds", 2), "access_official": cov(uo, "access_kinds", 2),
         "api": cov([p for p in pages if p["usable"]], "api_hits", 2), "api_official": cov(uo, "api_hits", 2), "mcp_text": any(p["mcp_hits"] for p in pages)}
    hits = [h for h in raw["search_hits"] if "MCP server" in h["q"]]
    mcp_hits = [h for h in hits if re.search(r"mcp", (h["title"] or "") + h["url"] + (h["snippet"] or ""), re.I)]
    gaps = []
    if not uo: gaps.append("no_official_usable_page")
    if not c["auth"]: gaps.append("no_auth_evidence")
    if not c["access"]: gaps.append("no_access_or_pricing_evidence")
    if not c["api"]: gaps.append("no_api_surface_evidence")
    if any(p["truncated"] for p in pages): gaps.append("truncated_pages")
    if any(p["injection_markers"] for p in pages): gaps.append("injection_markers_present")
    if len(uo) >= 2 and c["auth_official"] and (c["api_official"] or c["access_official"]): v = "READY"
    elif uo and (c["auth"] or c["api"] or c["access"]): v = "PARTIAL"
    elif any(p["usable"] for p in pages): v = "WEAK"
    else: v = "UNUSABLE"
    if app["name"] in AMBIGUOUS: gaps.append("identity_check_needed")
    return {"id": i, "name": app["name"], "category": app["cat"], "hint": app["hint"], "verdict": v, "gaps": gaps, "n_pages": len(pages), "n_usable": sum(p["usable"] for p in pages),
            "n_official_usable": len(uo), "coverage": c, "mcp_query_hits_mentioning_mcp": len(mcp_hits), "mcp_candidate_urls": [h["url"] for h in mcp_hits[:3]],
            "fetch_failed": len(raw.get("fetch_failed", [])), "has_pass1": os.path.exists(f"baseline/p1_v1/pass1/{i}.json"), "pages": pages}

ids = sorted(int(os.path.basename(f)[:-5]) for f in glob.glob("baseline/p1_v1/raw/*.json"))
A = [audit_app(i) for i in ids]
json.dump(A, open(f"{OUT}/audit.json", "w"), indent=1)
with open(f"{OUT}/audit_table.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["id", "name", "has_pass1", "verdict", "pages", "usable", "official_usable", "auth", "access", "api", "mcp_text", "mcp_hits", "gaps"])
    for a in A: w.writerow([a["id"], a["name"], a["has_pass1"], a["verdict"], a["n_pages"], a["n_usable"], a["n_official_usable"], a["coverage"]["auth"], a["coverage"]["access"], a["coverage"]["api"], a["coverage"]["mcp_text"], a["mcp_query_hits_mentioning_mcp"], ";".join(a["gaps"])])
# ---- summary + calibration against the existing 26 Pass-1/Pass-2 results
def dist(S): return dict(collections.Counter(a["verdict"] for a in S))
new = [a for a in A if not a["has_pass1"]]; old = [a for a in A if a["has_pass1"]]
cal = {}
for a in old:
    p1 = json.load(open(f"baseline/p1_v1/pass1/{a['id']}.json")); v = json.load(open(f"baseline/p1_v1/verify/{a['id']}.json"))
    ev = p1["evidence"]; its = [x for L in v["fields"].values() for x in L]
    cal.setdefault(a["verdict"], []).append({"id": a["id"], "quote_found": sum(e["quote_found"] for e in ev), "quotes": len(ev), "insufficient": sum(x["verdict"] == "insufficient_evidence" for x in its), "items": len(its), "needs_human": sum(x.get("needs_human", False) for x in its)})
cal_s = {k: {"n_apps": len(L), "quote_found_rate": round(sum(x["quote_found"] for x in L) / max(1, sum(x["quotes"] for x in L)), 2), "insufficient_rate": round(sum(x["insufficient"] for x in L) / max(1, sum(x["items"] for x in L)), 2), "needs_human_rate": round(sum(x["needs_human"] for x in L) / max(1, sum(x["items"] for x in L)), 2)} for k, L in cal.items()}
S = {"run_id": RUN, "rubric": "raw-audit-v1", "inputs": "baseline/p1_v1/raw (81 files, read-only)", "network": "none", "llm_calls": 0,
     "all_81": dist(A), "without_pass1_55": dist(new), "with_pass1_26": dist(old),
     "coverage_55": {k: sum(a["coverage"][k] for a in new) for k in ["auth", "auth_official", "access", "access_official", "api", "api_official", "mcp_text"]},
     "gap_counts_55": dict(collections.Counter(g for a in new for g in a["gaps"])), "identity_check_needed_55": [a["name"] for a in new if "identity_check_needed" in a["gaps"]],
     "mcp_query_hits_apps_55": sum(a["mcp_query_hits_mentioning_mcp"] > 0 for a in new), "injection_marker_pages": sum(p["injection_markers"] > 0 for a in A for p in a["pages"]),
     "pages_total": sum(a["n_pages"] for a in A), "pages_usable": sum(a["n_usable"] for a in A), "pages_official_usable": sum(a["n_official_usable"] for a in A),
     "calibration_on_26_(indicative_only_small_n)": cal_s,
     "by_verdict_ids_55": {v: [a["id"] for a in new if a["verdict"] == v] for v in ["READY", "PARTIAL", "WEAK", "UNUSABLE"]}}
json.dump(S, open(f"{OUT}/summary.json", "w"), indent=1)
json.dump({"run_id": RUN, "code": "src/audit_raw.py", "code_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "baseline_manifest_sha256": hashlib.sha256(open("baseline/MANIFEST.json", "rb").read()).hexdigest(),
           "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "network": False, "llm": None, "caveat": "heuristic keyword/URL checks; measure sufficiency of retrieval, not truth of claims"}, open(f"{OUT}/RUN.json", "w"), indent=1)
for f in glob.glob(f"{OUT}/*"): os.chmod(f, 0o444)
print(json.dumps({k: S[k] for k in ["all_81", "without_pass1_55", "with_pass1_26", "coverage_55", "gap_counts_55", "mcp_query_hits_apps_55", "injection_marker_pages", "pages_total", "pages_usable", "pages_official_usable", "calibration_on_26_(indicative_only_small_n)"]}, indent=1))
