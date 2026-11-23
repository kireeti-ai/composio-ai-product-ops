"""Gladly final search, fetch round 2: URLs chosen from the SAME search hits (no new queries) - REST reference, API tokens/auth, environment access, sandbox vs production, MCP connections.
Appends nothing to round 1: writes runs/topup-v1s-20261123/gladly/attempts_round2.json. Free Composio only ($0 asserted)."""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src"); sys.argv = ["x"]
import topup2 as T
from mcp import MCP
OUT = "runs/topup-v1s-20261123/gladly"; I = 20
URLS = ["https://developer.gladly.com/rest/", "https://connect.gladly.com/docs/implementation/article/environment-access", "https://connect.gladly.com/docs/implementation/article/get-your-api-tokens", "https://help.gladly.com/docs/migrating-to-new-auth",
        "https://help.gladly.com/implementation/docs/difference-between-sandbox-and-production", "https://help.gladly.com/docs/manage-app-integrations", "https://help.gladly.com/docs/set-up-mcp-connections", "https://connect.gladly.com/docs2/other-resources/postman", "https://connect.gladly.com/docs2/answers-rest-api-tutorials/manage-public-answers"]
m = MCP(); r = m.call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": "fetch a URL and return its page text"}], "session": {"generate_id": True}}); sid = json.loads(r["content"][0]["text"])["data"]["session"]["id"]
base = {T.nh(p["text"]) for p in json.load(open("baseline/p1_v1/raw/20.json"))["pages"]}; seen = {}
for e in json.load(open(f"{OUT}/attempts.json"))["attempts"]:
    if e["outcome"] == "usable_unique": seen[T.nh(e["text"])] = e["url"]
att = []
for u in URLS:
    e = T.fetch_one(m, sid, u); o, dup = T.outcome(u, e["status"], e.get("chars"), I, e.get("text"), seen, base)
    if o == "usable_unique": seen[T.nh(e["text"])] = u
    e.update(app_id=I, kind="gladly_final_search_round2", outcome=o, duplicate_of=dup, attempt=3); att.append(e)
json.dump(dict(app_id=I, session=sid, selection="from the same search hits; no new queries", attempts=att), open(f"{OUT}/attempts_round2.json", "w"), indent=1)
print("fetched:", len(att), "| max charge:", max([a.get("charge_usd", 0) for a in att] or [0]))
for a in att: print(f"  {a['outcome']:<18} chars={a.get('chars')} {a['url'][8:96]}")
