"""Build runs/p1-neo4j-optionB-20261124/PLAN.json (offline). Option B: two separately labelled calls with surface-specific inputs; Neo4j stays OUTSIDE the frozen 28-target plan."""
import os, json, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
O = "runs/p1-neo4j-optionB-20261124"; os.makedirs(O, exist_ok=True)
rec = json.load(open("runs/topup-v1s-20261123/neo4j_record.json")); cat = json.load(open("runs/topup-v1r-20261123/catalog_neo4j.json")); man = json.load(open("baseline/MANIFEST.json"))["hashes"]
REG = {a[0]: a for a in json.load(open("baseline/data/apps.json"))["apps"]}; assert REG[66][2] == "Neo4j" and REG[66][4] == "recovered"
B, V1, VR = "baseline/p1_v1/raw/66.json", "runs/topup-v1-20261123/raw/66.json", "runs/topup-v1r-20261123/raw/66.json"
def url(path, key, frag):
    u = [e["url"] for e in json.load(open(path))[key] if frag in e["url"] and e.get("status", "ok") == "ok"]; assert len(u) == 1, (frag, u); return u[0]
aura = [dict(raw=B, list_key="pages", urls=[url(B, "pages", "aura/api/overview")]), dict(raw=V1, list_key="fetched", urls=[url(V1, "fetched", "getting-started/free-trial"), url(V1, "fetched", "billing/payment-options")]), dict(raw=VR, list_key="attempts", urls=[url(VR, "attempts", "billing-dimensions")])]
query = [dict(raw=VR, list_key="attempts", urls=[url(VR, "attempts", "query-api/current")])]
plan = dict(run_id="p1-neo4j-optionB-20261124", status="PREPARED - HELD - NOT APPROVED (no model calls made; no APPROVED.json)", decision="Option B (user decision): two separately labelled extraction calls under the FROZEN prompt+schema; combined under one app record in REPORTING only",
 app=dict(id=66, name="Neo4j", registry_category=REG[66][1], provenance={"source": "reconstructed_secondary_source", "original_notion_membership_verified": False, "note": "name/category/order from a secondary public report; membership in the original Notion list is NOT verified; no identity authority"}),
 frozen=dict(prompt_sha256=man["PROMPT_sha256_V1"], schema_sha256=man["SCHEMA_sha256_V1"], note="unchanged; only the app label in the prompt differs per call"), outside_the_28_target_plan=True,
 calls=[dict(order=1, surface_id="aura_management_api", display_name="Neo4j - Aura Management API", inputs=aura, expected_requests=1), dict(order=2, surface_id="database_query_api", display_name="Neo4j - Database Query API", inputs=query, expected_requests=1)],
 excluded_pages=[dict(url_fragment="http-api/current (3 pages: overview + 2 authentication pages)", reason="legacy/deprecated HTTP API: a third, separate surface ('Not available on Aura'); would contaminate both calls"), dict(url_fragment="operations-manual/current/authentication-authorization", reason="generic database authentication, not specific to either API surface"),
                 dict(url_fragment="neo4j.com/pricing", reason="fetch failed on 2 attempts (error)")],
 uncertainty=dict(aura_management_api=dict(access_state="partial", note="account + credentials needed; credential mechanism and tier availability not retrieved", surface_evidence="partial (1 operation measured: GET /v1/instances)"),
                  database_query_api=dict(access_state="unresolved", note="needs a reachable database; Query API authorize page and Aura availability not retrieved", surface_evidence="partial (surface documented; 0 operations)")),
 evidence_gaps=["Aura API 'Authentication' page not retrieved (credential mechanism unconfirmed)", "Query API 'Authorize requests' page not retrieved", "Aura tier availability of the Query API and Aura API not retrieved", "Database Query API call has ONE input page: expect mostly 'unknown' outputs", "neo4j.com pricing page never retrieved (2 errors)"],
 recommended_pre_execution_fetches_NOT_EXECUTED=["Aura API Authentication page", "Query API 'Authorize requests' page", "Aura API specification / tier availability"],
 composio_annotation=dict(toolkit="neo4j", aura_management_api="covered (8 NEO4J_* tools; several are v1beta endpoints)", database_query_api="Cypher querying NOT demonstrated by the current Composio toolkit (metadata-only catalog search; absence is not proof)", tools=cat["neo4j_tool_slugs_found"]),
 combined_report=dict(path="reports/66_neo4j_combined.json (written only after both calls succeed)", shape="nested per-surface record from runs/schema-proposal-v1-20261124 (reporting only; extraction uses the frozen schema)", counts="one app in the 100-app denominator; two sub-rows (surfaces) in surface-level tables"),
 quota=dict(min_requests=2, per_call_retry_limit=2, note="adds at least 2 requests per model-day on top of the 28 targets (30 total); caps are mandatory in APPROVED.json"), created=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
json.dump(plan, open(f"{O}/PLAN.json", "w"), indent=1); os.chmod(f"{O}/PLAN.json", 0o444)
open(f"{O}/README.md", "w").write("# p1-neo4j-optionB (prepared, HELD, NOT approved)\nTwo separately labelled calls (Aura Management API, Database Query API) under the frozen prompt/schema; combined in reporting only. Neo4j is outside the 28-target plan. Runner: src/run_neo4j_surfaces.py [--dry-run]. No APPROVED.json exists.\n"); os.chmod(f"{O}/README.md", 0o444)
print("plan written | aura pages:", sum(len(s["urls"]) for s in aura), "| query pages:", sum(len(s["urls"]) for s in query))
