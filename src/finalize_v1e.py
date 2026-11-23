"""Finalize v1e (offline): Gladly final result, Neo4j single-record two-surface assessment, provenance + separated retrieval/relevance summaries, plan p1-v1e (same 27 apps as v1d).
Outputs: runs/topup-v1s-20261123/{gladly/gladly_final_result.json, neo4j_record.json}, runs/p1-v1e-gemini-20261124/{PLAN.json,APP_STATUS.json,eligibility.csv,README.md}. No network, no LLM."""
import os, re, json, csv, time, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
S = "runs/topup-v1s-20261123"; P = "runs/p1-v1e-gemini-20261124"; os.makedirs(P, exist_ok=True); R1 = "runs/topup-v1r-20261123"; V1 = "runs/topup-v1-20261123"
norm = lambda s: re.sub(r"\s+", " ", s).strip().lower(); iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")
rows = json.load(open(f"{S}/page_evidence_table.json")); apps = {a[0]: a for a in json.load(open("baseline/data/apps.json"))["apps"]}
def pages_of(i):
    d = {p["url"]: p["text"] for p in json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]}
    for f, k in ((f"{V1}/raw/{i}.json", "fetched"), (f"{R1}/raw/{i}.json", "attempts"), (f"{S}/gladly/attempts.json", "attempts"), (f"{S}/gladly/attempts_round2.json", "attempts")):
        if os.path.exists(f) and (i != 20 or "gladly" in f or "gladly" not in f):
            for e in json.load(open(f))[k]:
                if e.get("status") == "ok" and (i == 20 or "gladly" not in f): d[e["url"]] = e["text"]
    return d
def verify(i, frag, q):
    u = next((u for u, t in pages_of(i).items() if frag in u and norm(q) in norm(t)), None); assert u, (i, frag, q); return dict(url=u, quote=q, verified=True)

# ---------------- Gladly final result
g = [r for r in rows if r["app_id"] == 20]; cnt = collections.Counter((r["source"], r["retrieval_usability"]) for r in g)
GL = dict(app_id=20, name="Gladly", identity="resolved by original Notion hint gladly.com (apps 1-50)", final_search="1 targeted search (4 official domains x 4 queries = 16 searches, 159 hits, free) + 2 fetch rounds from the SAME hits (8 + 9 pages); no new queries; all attempts preserved in gladly/attempts*.json",
  retrieval=dict(attempts_by_source_and_usability={f"{k[0]}|{k[1]}": v for k, v in cnt.items()}, still_failing=["gladly.com pricing (empty on 3 attempts)", "developer.gladly.com/rest and /rest/ (REST reference: error on 2 attempts)", "connect.gladly.com API-token / environment-access / postman / answers-rest pages (empty)"]),
  evidence=dict(
    access=dict(state="explicit_account_gated", reading="API credentials exist only inside a customer's Gladly instance: tokens are created in the Gladly UI by users holding the API User role set up by Administrators; sandbox is bought via CSM or included in an implementation package. No public self-serve registration or pricing page retrieved (absence not proof).",
                quotes=[verify(20, "get-your-api-tokens", "These can be created within the Gladly UI, for users who have the `API User` role."), verify(20, "setup-and-testing", "Gladly Administrators can set API permissions on an Agent-by-Agent basis."), verify(20, "setup-and-testing", "If you do not have a sandbox environment and are interested in purchasing one, please contact your Gladly CSM or Gladly Support team."), verify(20, "difference-between-sandbox-and-production", "Some implementation packages include a Sandbox environment.")]),
    auth=dict(state="api_token (per user account; created in UI)", quotes=[verify(20, "generate-api-tokens", "API tokens are tied to a single user account")]),
    api_surface=dict(state="partial", reading="REST API, Lookup API, App Platform, Chat SDK, Help Center API and webhooks are NAMED; 0 operations itemized because the REST reference never fetched", quotes=[verify(20, "developer.gladly.com/", "calling Gladly's REST APIs, or implementing the Lookup API to provide data from your own services")]),
    mcp=dict(state="not an MCP server: Gladly AI is an MCP CLIENT that connects to external MCP servers", quotes=[verify(20, "set-up-mcp-connections", "Connect Gladly AI to an external MCP server so it can call that server's tools during Customer conversations.")])),
  decision="Evidence now sufficient for auth and access; API surface partial; pricing never retrieved. NOT added to the 27-app plan (plan preserved). Offered as pending-approval candidate #28 (phase 2, access explicit_account_gated, api_surface partial).",
  correction="The earlier 'insufficient' access rating for Gladly came from keyword snippets; the baseline pages already contained the gating statements. Other 'insufficient' access ratings made the same way may understate evidence (see limitations).")
json.dump(GL, open(f"{S}/gladly/gladly_final_result.json", "w"), indent=1)

# ---------------- Neo4j: ONE app record, two surfaces (not in the 27: frozen extraction schema cannot represent two surfaces without conflation)
cat = json.load(open(f"{R1}/catalog_neo4j.json"))
N = dict(app_id=66, name="Neo4j", record_type="single app record with two API surfaces", identity="resolved by original Notion? NO - #66 is in the reconstructed list (apps 51-100); identity authority none; brand/domain unambiguous but unverified against original Notion",
  surfaces=[
   dict(surface="aura_management_api", description="REST API to manage Aura instances and projects", evidence=[verify(66, "aura/api/overview", "The Aura API allows you to programmatically perform actions on your Aura instances without the need to log in to the Console."), verify(66, "aura/api/overview", "Before using the API, you must follow the steps outlined in Authentication to create")],
        measured_operations=["GET /v1/instances"], auth="credentials created per the Aura Authentication page (not retrieved): mechanism unconfirmed", access=dict(state="partial", reading="needs an Aura account; free trial = $150 credits on Professional/Business Critical; whether the API is available on every tier is not stated in retrieved pages"),
        surface_evidence="partial (1 operation measured)", composio=dict(covered=True, tools=cat["neo4j_tool_slugs_found"])),
   dict(surface="database_query_api", description="HTTPS endpoint that executes Cypher statements against a Neo4j database (supersedes the deprecated HTTP API); distinct from Bolt drivers", evidence=[verify(66, "query-api/current", "The Query API allows to execute Cypher statements against a Neo4j server through HTTP requests."), verify(66, "query-api/current", "This API supersedes the deprecated HTTP API."), verify(66, "http-api/current/authentication-authorization", "Not available on Aura")],
        measured_operations=[], auth="database user credentials, basic or bearer (stated on the legacy HTTP API page; the Query API's own 'Authorize requests' page was not retrieved)", access=dict(state="unresolved", reading="no developer registration; needs a reachable database (self-managed, or Aura if the Query API is offered there - not stated in retrieved text); disabled by default on self-managed < 5.25"),
        surface_evidence="partial (surface documented; 0 operations; auth page missing)", composio=dict(covered=False, reading="Cypher querying is NOT demonstrated by the current Composio toolkit"))],
  composio_toolkit=dict(toolkit="neo4j", tools=cat["neo4j_tool_slugs_found"], statement="The current Composio `neo4j` toolkit covers the Aura MANAGEMENT API (instance and project tools; several are beta endpoints). It does not demonstrate Cypher querying; no Cypher/Query-API tool was returned by the catalog search.", limitation="metadata-only catalog search (3 queries): absence is not proof; no tool was executed", retrieved_at=cat["retrieved_at"]),
  eligibility=dict(eligible=False, status="HELD", reason="the frozen extraction schema has single auth_methods/api_types fields and would conflate the two surfaces; options needing approval: (a) per-surface extraction runs with surface-labelled inputs, or (b) a schema change"),
  follow_up_retrievals_not_executed=["Aura API 'Authentication' page (credential mechanism)", "Query API 'Authorize requests' page", "Aura tier availability of the Query API and Aura API"])
json.dump(N, open(f"{S}/neo4j_record.json", "w"), indent=1)

# ---------------- plan v1e = v1d + provenance + separated summaries (asserted identical in ids/phases/tiers/uncertainty/api_surface/extra_retrieval)
old = json.load(open("runs/p1-v1d-gemini-20261124/PLAN.json")); st_old = json.load(open("runs/p1-v1d-gemini-20261124/APP_STATUS.json"))
ids27 = [int(i) for ph in ("1", "2") for i in old["phases"][ph]]; assert len(ids27) == 27
CAND = [52, 53, 56, 61, 62, 63, 65, 70, 71, 72, 75, 76]; assert set(CAND) <= set(ids27) and sorted(i for i in ids27 if i > 50) == sorted(CAND)
prov = {str(i): ({"source": "original_notion_page_public_data", "original_notion_membership_verified": True, "note": "apps 1-50 were read from the original Notion page's public data endpoint at fetch time"} if apps[i][4] == "notion"
                 else {"source": "reconstructed_secondary_source", "original_notion_membership_verified": False, "note": "name/category/order come from a secondary public report; membership in the original Notion list is NOT verified; no identity authority"}) for i in ids27}
plan = dict(old, run_id="p1-v1e-gemini-20261124", supersedes="p1-v1d-gemini-20261124", status="PREPARED - AWAITING EXPLICIT APPROVAL (no Gemini calls made; no APPROVED.json)", provenance=prov, candidate_research_targets_from_reconstructed_list=CAND,
            held_pending_identity=[73, 78], excluded_identity=[58, 80, 50], held_scope=dict(id=66, record=f"{S}/neo4j_record.json"), pending_approval_candidates=[dict(id=20, name="Gladly", proposed="phase 2 (#28)", result=f"{S}/gladly/gladly_final_result.json")],
            page_evidence_table=f"{S}/page_evidence_table.json", status_file=f"{P}/APP_STATUS.json", created=iso())
plan["not_eligible"] = {"unresolved_or_pending": [20], "identity_held_provisional": [73, 78], "scope_held": [66], "excluded_identity": [58, 80, 50]}
for k in ("phases", "tiers", "uncertainty", "api_surface", "extra_retrieval", "candidate_models", "key_policy"): assert plan[k] == old[k], k          # 27-app plan and uncertainty states preserved
json.dump(plan, open(f"{P}/PLAN.json", "w"), indent=1)
by = collections.defaultdict(list)
for r in rows: by[r["app_id"]].append(r)
status = []
for s in st_old:
    i = s["id"]; planned = set(p["url"] for ex in (plan["extra_retrieval"].get(str(i)) or []) for p in [{"url": u} for u in ex["use_urls"]]); inp = [r for r in by.get(i, []) if (r["source"] == "baseline" and r["retrieval_usability"] == "usable") or (r["source"] != "baseline" and r["url"] in planned and r["retrieval_usability"] == "usable")]
    rel = {d: sum(1 for r in inp if isinstance(r["evidence_relevance"], dict) and r["evidence_relevance"][d] == "direct") for d in ("auth", "access", "api_surface")}
    status.append(dict(s, provenance=prov.get(str(i)), candidate_research_target_from_reconstructed_list=i in CAND,
                       retrieval=dict(usable_planned_input_pages=len(inp), baseline_pages=sum(r["source"] == "baseline" for r in inp), topup_pages=sum(r["source"] != "baseline" for r in inp), note="retrieval usability only; says nothing about whether the content answers the question"),
                       evidence_relevance_summary=dict(pages_with_direct_relevance=rel, method="heuristic_v1_not_ground_truth; can miss relevant pages (e.g. Gladly sandbox page) and over-credit generic ones")))
json.dump(status, open(f"{P}/APP_STATUS.json", "w"), indent=1)
with open(f"{P}/eligibility.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["id", "name", "phase", "provenance", "notion_verified", "tier", "access_state", "access_confirmed", "api_surface", "usable_input_pages", "direct_pages_auth/access/api"])
    for s in status:
        i = s["id"]
        if not s["extraction_eligibility"]["eligible"]: continue
        d = s["evidence_relevance_summary"]["pages_with_direct_relevance"]; w.writerow([i, s["name"], s["extraction_eligibility"]["phase"], s["provenance"]["source"], s["provenance"]["original_notion_membership_verified"], plan["tiers"][str(i)], plan["uncertainty"][str(i)]["access_state"], plan["uncertainty"][str(i)]["access_confirmed"], plan["api_surface"][str(i)]["state"], s["retrieval"]["usable_planned_input_pages"], f"{d['auth']}/{d['access']}/{d['api_surface']}"])
open(f"{P}/README.md", "w").write("""# p1-v1e (prepared, NOT approved) - same 27 apps as p1-v1d, plus provenance and separated retrieval/relevance summaries
- 12 apps numbered 51-100 are CANDIDATE research targets from a reconstructed secondary list: original Notion membership is NOT verified (see PLAN.json provenance).
- Held/excluded: Linear, Coda (identity pending); Sherlock, Harvest, fanbasis (excluded); Neo4j (one record, two surfaces; held); Gladly (pending-approval candidate #28).
- retrieval_usability and evidence_relevance are separate fields (page_evidence_table). Relevance is heuristic, not ground truth.
- The frozen extraction prompt and schema are unchanged. No APPROVED.json exists. Runner: src/run_p1.py --run p1-v1e-gemini-20261124 [--dry-run]
""")
for d_, fs in ((S, ["neo4j_record.json"]), (f"{S}/gladly", ["gladly_final_result.json", "attempts.json", "attempts_round2.json", "search_hits.json"]), (P, ["PLAN.json", "APP_STATUS.json", "eligibility.csv", "README.md"])):
    for f in fs: os.chmod(f"{d_}/{f}", 0o444)
print("27-app plan preserved (ids/phases/tiers/uncertainty/api_surface/extra_retrieval identical to v1d); provenance:", dict(collections.Counter(v["source"] for v in prov.values())))
print("Gladly attempts by source|usability:", GL["retrieval"]["attempts_by_source_and_usability"])
