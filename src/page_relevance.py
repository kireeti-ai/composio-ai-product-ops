"""Page-level evidence table with TWO SEPARATE FIELDS per page:
  retrieval_usability  = did we get a usable page? (usable | duplicate_content | thin_or_js_shell | blocked_or_notfound | fetch_error | fetch_empty | off_target_url | skipped)
  evidence_relevance   = does the content bear on the question? per dimension auth / access / api_surface / mcp : direct | indirect | none   (heuristic, NOT ground truth)
Offline. Reads baseline + runs/topup-v1 + runs/topup-v1r + runs/topup-v1s/gladly; writes runs/topup-v1s-20261123/page_evidence_table.{json,csv}. No network, no LLM."""
import os, re, sys, json, csv, hashlib, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src"); sys.argv = ["x"]
import topup2 as T
from urllib.parse import urlparse
OUT = "runs/topup-v1s-20261123"; os.makedirs(OUT, exist_ok=True)
AUTH = re.compile(r"oauth|api[ _-]?key|apikey|bearer|access token|personal access token|api token|basic auth|client[_ ]secret|client[_ ]id|jwt|hmac|x-api-key|api user", re.I)
CONS = re.compile(r"users?\b[^.\n]{0,60}\b(?:approve|authoriz|grant|consent|allow)|consent|authorization (?:screen|page)|approval screen|admins?\b[^.\n]{0,60}\b(?:consent|approv|install|enable|restrict|disable)|requires? admin approval", re.I)
G1 = re.compile(r"\b(?:api|developer|tokens?|keys?|apps?|integrations?)\b[^.\n]{0,100}\b(?:plans?|tiers?|paid|premium|enterprise|subscription|trial|free (?:plan|tier|trial|of charge)|contact (?:your |our )?(?:sales|csm|support|account)|purchas\w+|app review|review process|invite|waitlist|apply|eligib\w+|requires? (?:an? )?(?:admin|role|account|plan|approval|subscription)|can be created[^.\n]{0,40}(?:role|admin))", re.I)
G2 = re.compile(r"\b(?:plans?|tiers?|paid|premium|enterprise|subscription|trial|app review|approved? (?:for|by)|invite[- ]only|waitlist)\b[^.\n]{0,100}\b(?:api|developer|tokens?|keys?|integrations?)\b", re.I)
G3 = re.compile(r"\b(?:administrators?|admins?)\b[^.\n]{0,80}\b(?:set|create|generate|grant)[^.\n]{0,40}\b(?:api|tokens?|keys?)\b|\bAPI User\b[^.\n]{0,40}role", re.I)
PRICE = re.compile(r"\$\s?\d|€\s?\d|per (?:month|user|seat|member)|/mo\b|free plan|free tier|free trial|\bpricing\b", re.I)
OPS = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(?:https?://[\w.\-]+)?(/[\w\-/{}.:$]*[\w}])"); APIW = re.compile(r"rest api|restful|graphql|openapi|swagger|\bendpoints?\b|api reference", re.I); MCP = re.compile(r"\bmcp\b|model context protocol", re.I)
def sentences(t): return [re.sub(r"\s+", " ", s).strip() for s in re.split(r"(?<=[.!?])\s+|\n+", t) if 25 <= len(re.sub(r"\s+", " ", s).strip()) <= 400]
def relevance(url, text):
    ss = sentences(text); gate = [s for s in ss if not CONS.search(s) and (G1.search(s) or G2.search(s) or G3.search(s))]; price = [s for s in ss if PRICE.search(s)]
    auth = len(AUTH.findall(text)); ops = sorted({f"{m.group(1)} {m.group(2)}" for m in OPS.finditer(text)}); apiw = len(APIW.findall(text)); mcp = len(MCP.findall(text))
    return dict(auth=("direct" if auth >= 3 else "indirect" if auth else "none"), access=("direct" if gate else "indirect" if len(price) >= 2 else "none"),
                api_surface=("direct" if ops else "indirect" if apiw >= 3 or re.search(r"reference|openapi|/rest", url, re.I) and apiw else "none"), mcp_mentions=mcp,
                basis=dict(access=(gate[0][:200] if gate else None), api_ops=ops[:4]), counts=dict(auth_hits=auth, gate_sentences=len(gate), pricing_sentences=len(price), api_words=apiw))
audit = {a["id"]: a for a in json.load(open("runs/audit-raw-v2-20261123/audit.json"))}
a1 = {(r["app_id"], r["url"]): r for r in json.load(open("runs/topup-v1r-20261123/accounting_attempt1.json"))}
plan = json.load(open("runs/p1-v1d-gemini-20261124/PLAN.json")); S = sorted({int(i) for v in plan["phases"].values() for i in v} | {20, 66} | set(T.APPS18))
rows = []
def add(i, source, url, usab, text, chars, sha, when, official):
    rel = relevance(url, text) if text else None
    rows.append(dict(app_id=i, app=audit[i]["name"], source=source, url=url, host=urlparse(url).hostname, official_domain=official, retrieval_usability=usab, chars=chars, sha256_12=(sha or "")[:12], fetched_at=when,
                     evidence_relevance=(rel or "n/a_no_content"), method="heuristic_v1_not_ground_truth"))
for i in S:
    raw = json.load(open(f"baseline/p1_v1/raw/{i}.json")); pm = {p["url"]: p for p in audit[i]["pages"]}; seen = set()
    for p in raw["pages"]:
        q = pm.get(p["url"], {}); h = T.nh(p["text"]); dup = h in seen; seen.add(h)
        u = "duplicate_content" if dup else "blocked_or_notfound" if (q.get("blocked") or q.get("notfound") or q.get("login_wall")) else "thin_or_js_shell" if (q.get("thin") or q.get("js_shell")) else "usable"
        add(i, "baseline", p["url"], u, p["text"], len(p["text"]), hashlib.sha256(p["text"].encode()).hexdigest(), os.stat(f"baseline/p1_v1/raw/{i}.json").st_mtime and None, q.get("official"))
    f1 = f"runs/topup-v1-20261123/raw/{i}.json"
    if os.path.exists(f1):
        for e in json.load(open(f1))["fetched"]:
            r = a1[(i, e["url"])]; add(i, "topup_v1_attempt1", e["url"], r["outcome"].replace("usable_unique", "usable"), e.get("text"), e.get("chars"), e.get("sha256"), e["completed_at"], T.reg(urlparse(e["url"]).hostname) in T.regs(i))
    f2 = f"runs/topup-v1r-20261123/raw/{i}.json"
    if os.path.exists(f2):
        for e in json.load(open(f2))["attempts"]:
            if e["status"] == "not_attempted": add(i, "topup_v1r_retry", e["url"], "skipped", None, None, None, None, None); continue
            add(i, "topup_v1r_retry", e["url"], e["outcome"].replace("usable_unique", "usable"), e.get("text"), e.get("chars"), e.get("sha256"), e["completed_at"], T.reg(urlparse(e["url"]).hostname) in T.regs(i))
for fn, src in (("attempts.json", "gladly_final_round1"), ("attempts_round2.json", "gladly_final_round2")):
    for e in json.load(open(f"{OUT}/gladly/{fn}"))["attempts"]:
        add(20, src, e["url"], e["outcome"].replace("usable_unique", "usable"), e.get("text"), e.get("chars"), e.get("sha256"), e["completed_at"], True)
json.dump(rows, open(f"{OUT}/page_evidence_table.json", "w"), indent=1)
with open(f"{OUT}/page_evidence_table.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["app_id", "app", "source", "url", "official_domain", "retrieval_usability", "chars", "sha256_12", "fetched_at", "rel_auth", "rel_access", "rel_api_surface", "mcp_mentions"])
    for r in rows:
        v = r["evidence_relevance"]; ok = isinstance(v, dict); w.writerow([r["app_id"], r["app"], r["source"], r["url"], r["official_domain"], r["retrieval_usability"], r["chars"], r["sha256_12"], r["fetched_at"], v["auth"] if ok else "n/a", v["access"] if ok else "n/a", v["api_surface"] if ok else "n/a", v["mcp_mentions"] if ok else "n/a"])
for f in ("page_evidence_table.json", "page_evidence_table.csv"): os.chmod(f"{OUT}/{f}", 0o444)
use = [r for r in rows if r["retrieval_usability"] == "usable"]
print("rows:", len(rows), "| apps:", len(S), "| usable:", len(use))
print("usability x access-relevance (usable pages only):", dict(collections.Counter(r["evidence_relevance"]["access"] for r in use)))
print("usable pages with NO relevance on any dimension:", sum(1 for r in use if all(r["evidence_relevance"][d] == "none" for d in ("auth", "access", "api_surface"))))
print("Gladly rows:", [(r["source"][-6:], r["retrieval_usability"], r["evidence_relevance"]["access"] if isinstance(r["evidence_relevance"], dict) else "n/a", r["url"][8:60]) for r in rows if r["app_id"] == 20 and r["retrieval_usability"] in ("usable",)][:12])
