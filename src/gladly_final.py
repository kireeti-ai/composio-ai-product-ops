"""Gladly: ONE final targeted search across official developer-documentation / API-reference domains (free Composio TINYFISH only; $0 asserted). All hits and attempts preserved.
Output: runs/topup-v1s-20261123/gladly/{search_hits.json,attempts.json}. No Gemini/Groq."""
import os, sys, re, json, time, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src"); sys.argv = ["x"]
import topup2 as T
from mcp import MCP
from urllib.parse import urlparse
OUT = "runs/topup-v1s-20261123/gladly"; os.makedirs(OUT, exist_ok=True); I = 20
DOMS = ["developer.gladly.com", "connect.gladly.com", "help.gladly.com", "gladly.com"]
QS = ["API authentication API tokens", "REST API reference", "API access requirements who can create API users", "developer sandbox access API"]
ALLOWED = set(DOMS) | {"www.gladly.com"}
m = MCP(); r = m.call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": "search the web"}], "session": {"generate_id": True}}); sid = json.loads(r["content"][0]["text"])["data"]["session"]["id"]
hits = []
for d in DOMS:
    for q in QS:
        try:
            r = m.call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": "TINYFISH_SEARCH_WEB", "arguments": {"query": f"{q} site:{d}", "purpose": "find official Gladly developer / API documentation"}}], "sync_response_to_workbench": False, "session_id": sid, "thought": "free final Gladly search"})
            dd = json.loads(r["content"][0]["text"]); ch = (dd.get("data", {}).get("instant_charge") or dd.get("instant_charge") or {}); assert float(ch.get("amount", 0) or 0) == 0, f"NONZERO CHARGE {ch}"
            hits += [dict(q=f"{q} site:{d}", url=x["url"], title=x.get("title"), snippet=(x.get("snippet") or "")[:200], searched_at=T.iso()) for x in dd["data"]["results"][0]["response"].get("data", {}).get("results", [])]
        except AssertionError: raise
        except Exception as e: hits.append(dict(q=f"{q} site:{d}", error=str(e)[:100]))
json.dump(hits, open(f"{OUT}/search_hits.json", "w"), indent=1)
tried = {p["url"].rstrip("/") for p in json.load(open("baseline/p1_v1/raw/20.json"))["pages"]}
tried |= {e["url"].rstrip("/") for e in json.load(open("runs/topup-v1-20261123/raw/20.json"))["fetched"]}; tried |= {a["url"].rstrip("/") for a in json.load(open("runs/topup-v1r-20261123/raw/20.json"))["attempts"]}
score = lambda u: (0 if "developer.gladly.com" in u else 1 if "connect.gladly.com" in u else 2 if "help.gladly.com" in u else 3, 0 if re.search(r"api|auth|token|rest|sandbox|developer", u, re.I) else 1)
cand = {}
for h in hits:
    u = h.get("url", "").split("#")[0]
    if u and (urlparse(u).hostname in ALLOWED) and u.rstrip("/") not in tried and not T.EXCL.search(u) and not T.BAD.search(u): cand.setdefault(u, h)
picks = sorted(cand, key=score)[:8]
base = {T.nh(p["text"]) for p in json.load(open("baseline/p1_v1/raw/20.json"))["pages"]}; seen = {}
for e in json.load(open("runs/topup-v1-20261123/raw/20.json"))["fetched"]:
    if e["status"] == "ok" and e["chars"] >= 500: seen.setdefault(T.nh(e["text"]), e["url"])
att = []
for u in picks:
    e = T.fetch_one(m, sid, u); o, dup = T.outcome(u, e["status"], e.get("chars"), I, e.get("text"), seen, base)
    if o == "usable_unique": seen[T.nh(e["text"])] = u
    e.update(app_id=I, kind="gladly_final_search", outcome=o, duplicate_of=dup, attempt=3); att.append(e)
json.dump(dict(app_id=I, run="gladly-final", session=sid, hits_total=len(hits), candidates=len(cand), attempts=att), open(f"{OUT}/attempts.json", "w"), indent=1)
print("search hits:", len(hits), "| unique official candidates not tried before:", len(cand), "| fetched:", len(att), "| max charge:", max([a.get("charge_usd", 0) for a in att] or [0]))
for a in att: print(f"  {a['outcome']:<18} chars={a.get('chars')} {a['url'][8:90]}")
