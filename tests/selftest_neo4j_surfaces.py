import sys, os, json, importlib.util
ROOT="/Users/kireeti/Desktop/notes/Assignment"; os.chdir(ROOT)
spec=importlib.util.spec_from_file_location("rn",ROOT+"/src/run_neo4j_surfaces.py"); N=importlib.util.module_from_spec(spec); spec.loader.exec_module(N); R=N.R
schema,prompt,hs,hp=R.frozen(); D=json.load(open("baseline/data/apps.json")); plan=json.load(open("runs/p1-neo4j-optionB-20261124/PLAN.json")); T=sys.argv[1]; allok=True
def ok(c,m):
    global allok; allok&=bool(c); print(("PASS " if c else "FAIL ")+m)
prompts=[]
def fake(m,p,s):
    prompts.append(p); lab="Aura" if "Aura Management API" in p.split("\\n")[0] else "Query"
    return "ok",{"one_liner":f"FAKE {lab}","auth_methods":["unknown"],"access":"unknown","access_note":"","api_types":["rest"],"api_breadth":"unknown","existing_mcp":"unknown","buildability":"unknown","blocker":"","evidence":[{"field":"api_types","url":"x","quote":"zz"}]}
out=T+"/ok"; r=N.run(plan,{"models":["m1"],"cap_per_model":{"m1":4}},out,fake,schema,prompt,(hs,hp),D["categories"],sleep=lambda s:None)
ok(r=="completed" and len(prompts)==2,"two calls made, run completed")
ok("Neo4j - Aura Management API" in prompts[0] and "Neo4j - Database Query API" in prompts[1] and "Database Query API" not in prompts[0].split("SOURCES:")[0].split("App:")[1][:60],"each call is labelled with its own surface name in the frozen prompt")
ok("query-api/current" not in prompts[0] and "aura/api/overview" not in prompts[1],"no cross-surface source pages")
ok(not any("http-api" in p or "operations-manual" in p for p in prompts),"legacy HTTP API and generic auth pages are in neither call")
a=json.load(open(out+"/pass1/66__aura_management_api.json")); q=json.load(open(out+"/pass1/66__database_query_api.json"))
ok(a["meta"]["prompt_sha256"]==hp==json.load(open("baseline/MANIFEST.json"))["hashes"]["PROMPT_sha256_V1"] and a["meta"]["schema_sha256"]==hs,"frozen prompt+schema hashes recorded and equal to the baseline manifest")
ok(len(a["meta"]["retrieval"])==4 and len(q["meta"]["retrieval"])==1 and all(len(x["sha256"])==64 for x in a["meta"]["retrieval"]),"per-page provenance (url, sha256, fetched_at, raw hash) recorded: 4 + 1 pages")
ok(a["meta"]["registry_provenance"]["original_notion_membership_verified"] is False,"reconstructed-list provenance flag carried (membership NOT verified)")
c=json.load(open(out+"/reports/66_neo4j_combined.json")); ok(c["id"]==66 and len(c["surfaces"])==2 and [s["surface_id"] for s in c["surfaces"]]==["aura_management_api","database_query_api"],"ONE combined app record (registry id 66) with two surfaces")
ok(c["annotations_not_model_output"]["database_query_api"].startswith("Cypher querying NOT demonstrated"),"combined record carries the Composio annotation (Aura covered; Cypher querying not demonstrated)")
ok(os.stat(out+"/pass1/66__aura_management_api.json").st_mode&0o222==0,"records are read-only; lock removed: "+str(not os.path.exists(out+"/.lock")))
# quota stop on 2nd call, then resume
n={"k":0}
def fq(m,p,s):
    n["k"]+=1
    return fake(m,p,s) if n["k"]==1 else ("daily_quota","per day")
out2=T+"/q"; r=N.run(plan,{"models":["m1"],"cap_per_model":{"m1":5}},out2,fq,schema,prompt,(hs,hp),D["categories"],sleep=lambda s:None)
ok(r=="quota_or_cap_exhausted" and os.path.exists(out2+"/pass1/66__aura_management_api.json") and not os.path.exists(out2+"/reports/66_neo4j_combined.json"),"daily quota on call 2: stops, keeps call 1, NO combined record yet")
before=open(out2+"/pass1/66__aura_management_api.json").read(); r=N.run(plan,{"models":["m1"],"cap_per_model":{"m1":5}},out2,fake,schema,prompt,(hs,hp),D["categories"],sleep=lambda s:None)
ok(r=="completed" and open(out2+"/pass1/66__aura_management_api.json").read()==before and os.path.exists(out2+"/reports/66_neo4j_combined.json"),"resume: call 1 not regenerated or overwritten; call 2 done; combined record written")
ok(not os.path.exists("baseline/p1_v1/pass1/66.json"),"no baseline Pass-1 record for id 66 (nothing regenerated)")
print("NEO4J TESTS PASSED" if allok else "NEO4J TESTS FAILED")
