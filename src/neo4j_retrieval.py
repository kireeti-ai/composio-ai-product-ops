"""Neo4j gap retrievals (3 official pages) - PREPARED, GATED. Makes NO external call unless runs/neo4j-retrieval-prep-20261124/RETRIEVAL_APPROVED.json exists (explicit user approval).
Free Composio TINYFISH only; every call asserts instant_charge == 0; all attempts (including failures) are preserved in attempts.json; official neo4j.com docs only (blogs excluded).
Usage: python src/neo4j_retrieval.py [--dry-run]"""
import os, sys, re, json, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
P = "runs/neo4j-retrieval-prep-20261124"; plan = json.load(open(f"{P}/RETRIEVAL_PLAN.json"))
print(f"gaps: {len(plan['gaps'])} | planned fetches: {sum(len(g['candidate_urls']) for g in plan['gaps'])} | conditional search+fetch: {len(plan['conditional_discovery'])} | max external calls: {plan['max_external_calls']}")
for g in plan["gaps"]: print(f"  gap {g['gap_id']} {g['name']}: {g['candidate_urls']}")
if "--dry-run" in sys.argv or not os.path.exists(f"{P}/RETRIEVAL_APPROVED.json"):
    print("[dry-run / not approved] NO external call made. approval file present:", os.path.exists(f"{P}/RETRIEVAL_APPROVED.json")); sys.exit(0 if "--dry-run" in sys.argv else "REFUSING: no RETRIEVAL_APPROVED.json")
sys.argv = ["x"]; sys.path.insert(0, "src"); import topup2 as T; from mcp import MCP                      # imported only after approval (reads only COMPOSIO_API_KEY)
m = MCP(); r = m.call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": "fetch a URL and return its page text"}], "session": {"generate_id": True}}); sid = json.loads(r["content"][0]["text"])["data"]["session"]["id"]
done = {a["url"] for a in plan.get("already_have", [])}; att = []
def fetch(u, gap, why):
    e = T.fetch_one(m, sid, u); o, dup = T.outcome(u, e["status"], e.get("chars"), 66, e.get("text"), {}, set()); e.update(app_id=66, gap_id=gap, reason=why, outcome=o, attempt=4); att.append(e); return e
for g in plan["gaps"]:
    for u in g["candidate_urls"]: fetch(u, g["gap_id"], g["name"])
for c in plan["conditional_discovery"]:                                                                        # only if the gap is still open after its candidates
    gid = c["gap_id"]; open_gap = not any(a["gap_id"] == gid and a["outcome"] == "usable_unique" and re.search(c["must_match_in_text"], a.get("text", ""), re.I) for a in att)
    if open_gap:
        rs = m.call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": "TINYFISH_SEARCH_WEB", "arguments": {"query": c["query"], "purpose": "find the official Neo4j Query API authorization page"}}], "sync_response_to_workbench": False, "session_id": sid, "thought": "free targeted discovery"})
        d = json.loads(rs["content"][0]["text"]); ch = (d.get("data", {}).get("instant_charge") or d.get("instant_charge") or {}); assert float(ch.get("amount", 0) or 0) == 0, "NONZERO CHARGE"
        hits = [x for x in d["data"]["results"][0]["response"].get("data", {}).get("results", []) if re.search(c["url_must_match"], x["url"], re.I) and "blog" not in x["url"]]
        att.append(dict(app_id=66, gap_id=gid, kind="discovery_search", query=c["query"], hits=[x["url"] for x in hits[:8]], outcome="search_done"))
        for x in hits[:1]: fetch(x["url"], gid, "discovered by targeted search")
json.dump(dict(app_id=66, session=sid, attempts=att), open(f"{P}/attempts.json", "w"), indent=1); os.chmod(f"{P}/attempts.json", 0o444)
print("attempts:", [(a.get("outcome"), (a.get("url") or a.get("query"))[8:80]) for a in att], "| max charge:", max([a.get("charge_usd", 0) for a in att] or [0]))
