import sys, os, json, hashlib, importlib.util
ROOT="/Users/kireeti/Desktop/notes/Assignment"; os.chdir(ROOT)
spec=importlib.util.spec_from_file_location("run_p1",ROOT+"/src/run_p1.py"); R=importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
schema,prompt,hs,hp=R.frozen(); D=json.load(open("baseline/data/apps.json")); apps={a[0]:dict(name=a[2],cat=a[1],hint=a[3]) for a in D["apps"]}
T=sys.argv[1]; P=json.load(open("runs/p1-v1f-gemini-20261124/PLAN.json")); ok=lambda c,m: (print(("PASS " if c else "FAIL ")+m), c)[1]; allok=True
prompts={}
def fake_ok(m,p,s): prompts["last"]=p; return "ok",{"one_liner":"FAKE","auth_methods":["unknown"],"access":"unknown","access_note":"","api_types":["unknown"],"api_breadth":"unknown","existing_mcp":"unknown","buildability":"unknown","blocker":"","evidence":[{"field":"access","url":"x","quote":"zz"}]}
def run(name,ids,approved,call,extra=None):
    out=f"{T}/{name}"; plan=dict(P,run_id=name,ids=ids); return R.run(plan,approved,out,call,schema,prompt,(hs,hp),apps,D["categories"],sleep=lambda s:None),out
ids=P["phases"]["1"][:5]
# regression from earlier versions
r,o=run("a",ids,{"models":["m1","m2"],"cap_per_model":{"m1":2,"m2":1}},fake_ok); allok&=ok(r=="quota_or_cap_exhausted" and len(os.listdir(o+"/pass1"))==3,"cap stop: 3 records then stop")
cnt={"m1":0}
def fq(m,p,s):
    if m=="m1": cnt["m1"]+=1; return "daily_quota","Quota exceeded per day"
    return fake_ok(m,p,s)
r,o=run("b",ids,{"models":["m1","m2"],"cap_per_model":{"m1":5,"m2":2}},fq); allok&=ok(cnt["m1"]==1 and len(os.listdir(o+"/pass1"))==2,"daily quota: ONE request to m1 then fallback, no retry loop")
before={f:open(f"{o}/pass1/{f}").read() for f in os.listdir(o+"/pass1")}
r=R.run(dict(P,run_id="b",ids=[1]+ids),{"models":["m2"],"cap_per_model":{"m2":10}},o,fake_ok,schema,prompt,(hs,hp),apps,D["categories"],sleep=lambda s:None); after={f:open(f"{o}/pass1/{f}").read() for f in os.listdir(o+"/pass1")}
allok&=ok(all(after[f]==before[f] for f in before) and "1.json" not in after and len(after)==5,"resume: no overwrite, baseline id skipped")
os.makedirs(T+"/l",exist_ok=True); open(T+"/l/.lock","w").close()
try: R.run(dict(P,run_id="l",ids=ids),{"models":["m1"],"cap_per_model":{"m1":1}},T+"/l",fake_ok,schema,prompt,(hs,hp),apps,D["categories"]); allok&=ok(False,"lock")
except FileExistsError: allok&=ok(True,"lock: second writer refused")
# new in v3: multi-source merge for the two apps that gained retry pages (46 Squarespace, 38 Pinterest) + a v1-only app (71 Notion)
r,o=run("c",[46,38,71],{"models":["m1"],"cap_per_model":{"m1":10}},fake_ok)
for i in (46,38,71):
    rec=json.load(open(f"{o}/pass1/{i}.json")); top=rec["meta"]["retrieval_topup"]; urls=[u for t in top for x in t["pages"] for u in [x["url"]]]
    allok&=ok(len(urls)==len(set(urls)) and len(rec["pages_read"])==len(set(rec["pages_read"])),f"#{i}: no duplicate URLs in sources ({len(rec['pages_read'])} pages)")
    allok&=ok(all(u in rec["pages_read"] for u in urls),f"#{i}: every top-up URL is in pages_read; sources used: {[t['path'].split('/')[1] for t in top]}")
    # hashes of top-up pages match stored text
    bad=0
    for t in top:
        recraw=json.load(open(t["path"])); lst=recraw.get("fetched") or recraw["attempts"]; byu={e["url"]:e for e in lst if e.get("status")=="ok"}
        for x in t["pages"]:
            if hashlib.sha256(byu[x["url"]]["text"].encode()).hexdigest()!=x["sha256"]: bad+=1
    allok&=ok(bad==0,f"#{i}: per-page sha256 in meta matches stored text")
    allok&=ok(not any(("pinterest.com/ideas" in u or "support.discord.com" in u) for u in rec["pages_read"]),f"#{i}: no off-target pages")
rec=json.load(open(f"{o}/pass1/46.json")); allok&=ok(len(rec["meta"]["retrieval_topup"])==2,"#46: two top-up sources (first attempt + retry) merged")
allok&=ok(rec["meta"]["uncertainty"]["access_state"]=="partial" and rec["meta"]["uncertainty"]["access_confirmed"] is False,"#46: uncertainty partial / not confirmed in meta")
r,o2=run("d",[62,63,36,38,65],{"models":["m1"],"cap_per_model":{"m1":10}},fake_ok)
st={i:json.load(open(f"{o2}/pass1/{i}.json"))["meta"]["uncertainty"] for i in (62,63,36,38,65)}
allok&=ok(all(st[i]["access_state"]=="inferred_self_serve" and st[i]["access_confirmed"] is False and "NEVER report as confirmed" in st[i]["rule"] for i in (62,63,36)),"inferred_self_serve apps (62,63,36) carry 'never report as confirmed' and access_confirmed=false")
allok&=ok(st[38]["access_confirmed"] and st[65]["access_confirmed"],"explicit apps (38,65) access_confirmed=true (still subject to verification)")
m33=json.load(open(f"{T}/a/pass1/{ids[0]}.json")) if False else None
r,o3=run("e",[33,71],{"models":["m1"],"cap_per_model":{"m1":5}},fake_ok); allok&=ok(json.load(open(f"{o3}/pass1/33.json"))["meta"]["api_surface_state"]["state"]=="partial" and json.load(open(f"{o3}/pass1/71.json"))["meta"]["api_surface_state"]["state"]=="partial","LinkedIn Ads (33) and Notion (71) carry api_surface_state=partial")
allok&=ok(hp==json.load(open("baseline/MANIFEST.json"))["hashes"]["PROMPT_sha256_V1"] and hs==json.load(open("baseline/MANIFEST.json"))["hashes"]["SCHEMA_sha256_V1"],"prompt+schema hashes equal the frozen baseline manifest")
print("ALL SELFTESTS PASSED" if allok else "SOME TESTS FAILED")
# v4 additions
r,o=run("p",[52,10],{"models":["m1"],"cap_per_model":{"m1":5}},fake_ok) if False else (None,None)
P2=json.load(open("runs/p1-v1f-gemini-20261124/PLAN.json")); out=T+"/prov"
R.run(dict(P2,run_id="prov",ids=[52,27]),{"models":["m1"],"cap_per_model":{"m1":5}},out,fake_ok,schema,prompt,(hs,hp),apps,D["categories"],sleep=lambda s:None)
a=json.load(open(out+"/pass1/52.json"))["meta"]["registry_provenance"]; b=json.load(open(out+"/pass1/27.json"))["meta"]["registry_provenance"]
print(("PASS " if a["original_notion_membership_verified"] is False and a["source"]=="reconstructed_secondary_source" else "FAIL ")+"#52 (reconstructed list): notion membership NOT verified, carried into the record")
print(("PASS " if b["original_notion_membership_verified"] is True else "FAIL ")+"#27 (original Notion): verified")
ids27=[i for ph in ("1","2") for i in P2["phases"][ph]]; old=json.load(open("runs/p1-v1e-gemini-20261124/PLAN.json"))
print(("PASS " if len(ids27)==28 and all(P2["uncertainty"][k]==old["uncertainty"][k] and P2["tiers"][k]==old["tiers"][k] and P2["extra_retrieval"].get(k)==old["extra_retrieval"].get(k) for k in old["uncertainty"]) else "FAIL ")+"28 targets; the 27 of v1e have identical uncertainty/tiers/sources")
print(("PASS " if not any(x in ids27 for x in (58,80,50,73,78,66,28)) and 20 in ids27 else "FAIL ")+"excluded/held apps (Sherlock, Harvest, fanbasis, Linear, Coda, Neo4j) and registry ID 28 (WhatsApp Business) are NOT in the plan; Gladly IS (registry ID 20)")

# Gladly-specific (v1f)
out=T+"/gl"; seenp={}
def cap(m,p,sc): seenp["p"]=p; return fake_ok(m,p,sc)
R.run(dict(P2,run_id="gl",ids=[20]),{"models":["m1"],"cap_per_model":{"m1":5}},out,cap,schema,prompt,(hs,hp),apps,D["categories"],sleep=lambda s:None)
g=json.load(open(out+"/pass1/20.json")); mt=g["meta"]
ok2=lambda c,m:print(("PASS " if c else "FAIL ")+m)
ok2(g["id"]==20 and g["name"]=="Gladly","record keeps registry ID 20 / name Gladly")
ok2(len(g["pages_read"])==7 and len(set(g["pages_read"]))==7,"Gladly inputs = 4 baseline + 3 curated round-2 pages (7, no duplicates)")
ok2(not any(x in " ".join(g["pages_read"]) for x in ("ios-sdk","developer.gladly.com/chat","migrating-to-new-auth","get-started-sidekick")),"SDK / Ordergroove-auth / sidekick pages are NOT in Gladly inputs")
ok2("set-up-mcp-connections" in " ".join(g["pages_read"]) and "difference-between-sandbox" in " ".join(g["pages_read"]),"MCP-client and sandbox pages ARE in Gladly inputs")
ok2(mt["uncertainty"]["access_state"]=="explicit_account_gated" and mt["uncertainty"]["field_states"]["pricing"]=="unknown" and "client_only" in mt["uncertainty"]["field_states"]["mcp"],"Gladly uncertainty: access explicit_account_gated, pricing unknown, MCP client-only")
ok2(mt["api_surface_state"]["state"]=="partial" and mt["registry_provenance"]["original_notion_membership_verified"] is True and mt["tier"].startswith("D_"),"Gladly api_surface partial; provenance verified (#<=50); tier D")
ok2(len(mt["retrieval_topup"])==1 and mt["retrieval_topup"][0]["path"].endswith("attempts_round2.json") and mt["retrieval_topup"][0]["tool"]=="composio:TINYFISH_FETCH_URLS","top-up source = round-2 attempts file referenced directly with default tool")
ok2("### https://help.gladly.com/docs/set-up-mcp-connections" in seenp["p"],"MCP page text is in the prompt sent to the (fake) model")
print("GLADLY TESTS DONE")
