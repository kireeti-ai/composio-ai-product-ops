"""App-ID-level EXECUTION LEDGER for all 100 registry apps + exact reconciliation of the Gemini call estimate (75 = 28 + 2 + 39 + 6). Offline; reads frozen/prepared plans only; writes ONLY runs/execution-ledger-v1-20261124/.
Every proposed Gemini call is one row: app ID, API surface, model policy, purpose, prerequisites. Hard assertions: unique (app, surface) pairs, disjoint groups, 26 baseline + 74 apps with a new call = 100.
A model is assigned at RUN time by the approved model list + per-model caps (primary first, fallback when a daily quota is hit); the record stores the model actually used."""
import os, sys, json, csv, collections, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src")
O = "runs/execution-ledger-v1-20261124"; os.makedirs(O, exist_ok=True); iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")
MC = json.load(open("runs/master-coverage-v1-20261124/MASTER_COVERAGE.json")); rows = {r["registry_id"]: r for r in MC["rows"]}
P = json.load(open("runs/p1-v1f-gemini-20261124/PLAN.json")); FZ = json.load(open("runs/p1-v1f-gemini-20261124/FROZEN.json")); X = json.load(open("runs/p1-expansion-v1-20261124/PLAN.json")); NEO = json.load(open("runs/p1-neo4j-optionB-20261124/PLAN.json"))
REG = {a[0]: a for a in json.load(open("baseline/data/apps.json"))["apps"]}; MODELS = P["candidate_models"]
assert FZ["plan_sha256"] and P["phases"]
GATED = {73: ("Linear", "HELD_IDENTITY_PROVISIONAL", "identity provisional (name + domain consistency only)", "user confirms identity; access-evidence top-up (free retrieval)"),
         78: ("Coda", "HELD_IDENTITY_PROVISIONAL", "identity provisional; superhuman.com hits suggest docs migration", "user confirms identity and canonical docs; access top-up"),
         80: ("Harvest", "EXCLUDED_IDENTITY_UNRESOLVED", "3 different products retrieved (getharvest / harvestapi / Greenhouse Harvest API); #80 has NO hint (reconstructed list)", "authoritative identity (Notion hint) then fresh targeted retrieval"),
         50: ("fanbasis", "EXCLUDED_IDENTITY_UNRESOLVED", "fanbasis.io unconfirmed; openstage.live excluded; dev-docs password-gated", "user confirms fanbasis.io; retrieval of public docs may be impossible (docs gated)"),
         59: ("Waterfall.io", "EXPANSION_3H_PROVISIONAL_IDENTITY", "provisional identity (user decision); reconstructed list", "user confirms identity; access top-up"),
         60: ("Clay", "EXPANSION_3H_PROVISIONAL_IDENTITY", "provisional identity (user decision); reconstructed list", "user confirms identity; access top-up")}
calls = []; n = 0
def add(i, surface, group, ref, purpose, inputs, prereq, commit):
    global n; n += 1; calls.append(dict(call_id=f"G{n:03d}", registry_id=i, app=REG[i][2], surface_id=surface, group=group, plan_ref=ref, model_policy=f"primary {MODELS[0]} -> fallback {MODELS[1]} (decided at run time by approved list + per-model caps; record stores the actual model)", purpose=purpose, inputs=inputs,
                                    prerequisites=prereq, commitment=commit, min_attempts=1, max_attempts_per_model=3, verification_groq_calls_min=4, source_provenance=("original_notion_page_public_data" if REG[i][4] == "notion" else "reconstructed_secondary_source")))
def npages(i):
    b = len(json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]) if os.path.exists(f"baseline/p1_v1/raw/{i}.json") else 0
    return b, sum(len(s["use_urls"]) for s in (P["extra_retrieval"].get(str(i)) or []))
# ---- group A: frozen v1f (28)
for ph in ("1", "2"):
    for i in P["phases"][ph]:
        b, t = npages(i); u = P["uncertainty"][str(i)]
        add(i, "default", "A_v1f_frozen", f"p1-v1f phase {ph} ({P['tiers'][str(i)]})", f"Pass-1 extraction (frozen prompt+schema); access state '{u['access_state']}'" + ("" if u["access_confirmed"] else " - NEVER report as confirmed"), f"{b} baseline + {t} verified top-up pages (cached)", ["APPROVED.json for p1-v1f", "per-model caps", "quota check"], "COMMITTED_AFTER_APPROVAL")
# ---- group B: Neo4j Option B (2 calls = 1 app, 2 surfaces)
for c in NEO["calls"]:
    pg = sum(len(s["urls"]) for s in c["inputs"]); add(66, c["surface_id"], "B_neo4j_optionB", f"p1-neo4j-optionB call {c['order']}", f"Surface-labelled extraction '{c['display_name']}' (frozen prompt+schema; combined into one app record in reporting only)", f"{pg} cached page(s) specific to this surface", ["APPROVED.json for neo4j plan", "recommended: 3 gap retrievals first (need approval)", "identity: reconstructed list (#66 membership unverified)"], "CONDITIONAL_RETRIEVAL_RECOMMENDED")
# ---- group C: expansion waves 3A / 3B / 4 (39)
for w in ("3A_core_ready_access_topup", "3B_partial_targeted_reretrieval", "4_no_retrieval_full_discovery"):
    for a in X["apps"]:
        if a["wave"] != w: continue
        i = a["registry_id"]; b = len(json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]) if a["cached_retrieval"] else 0
        add(i, "default", "C_expansion", f"p1-expansion-v1 wave {w}", f"Pass-1 extraction after wave retrieval; schema stress hypothesis: {a['schema_stress_hypothesis'] or 'none'}", f"{b} cached page(s) + top-up/discovery pages NOT YET RETRIEVED", ["free retrieval (approval needed)", "relevance audit", "identity: " + a["identity_gate"], "new versioned plan after retrieval", "APPROVED.json for that plan"], "CONDITIONAL_ON_RETRIEVAL_AND_IDENTITY")
# ---- group D: identity-gated (6)
for i, (nm, st, why, unlock) in GATED.items():
    add(i, "default", "D_identity_gated", f"{st}", f"Pass-1 extraction ONLY after identity is confirmed and evidence is retrieved ({why})", "retrieval required first", ["identity confirmation by the user", unlock, "new versioned plan + approval"], "CONDITIONAL_ON_IDENTITY")
# ---- hard assertions / reconciliation
grp = collections.Counter(c["group"] for c in calls); assert dict(grp) == {"A_v1f_frozen": 28, "B_neo4j_optionB": 2, "C_expansion": 39, "D_identity_gated": 6} and len(calls) == 75
assert len({(c["registry_id"], c["surface_id"]) for c in calls}) == 75, "duplicate (app, surface) pair"
ids = collections.defaultdict(set)
for c in calls: ids[c["group"]].add(c["registry_id"])
keys = list(ids); assert all(not (ids[a] & ids[b]) for k, a in enumerate(keys) for b in keys[k + 1:]), "groups overlap"
new_apps = set().union(*ids.values()); base = {i for i, r in rows.items() if r["master_status"].startswith("COMPLETED_BASELINE")}; assert len(new_apps) == 74 and not (new_apps & base) and len(new_apps | base) == 100
assert ids["D_identity_gated"] == set(GATED) and not (ids["D_identity_gated"] & {a["registry_id"] for a in X["apps"] if not a["wave"].startswith("3H")})
exp41 = {a["registry_id"] for a in X["apps"]}; assert len(exp41) == 41 and exp41 == ids["C_expansion"] | {59, 60}
assert ids["A_v1f_frozen"] == set(FZ["ids"]) and 58 not in new_apps and 14 not in new_apps
# ---- per-app ledger (100 rows)
by_app = collections.defaultdict(list)
for c in calls: by_app[c["registry_id"]].append(c["call_id"])
import verify_v2 as V
vplan = {}
for i in sorted(base):
    r = V.load_record(f"baseline/p1_v1/pass1/{i}.json"); s = r["surfaces"][0]; ps = V.passages(V.load_sources(r, s)); k = 0
    for f in V.EVIDENCE_FIELDS:
        items = V.items_for(s, f); pre = V.precheck_enum_conflict(f, items); todo = [x for x in items if x not in pre and x != "unknown"]; k += 1 if (todo and ps) else 0
    vplan[i] = k
apps = []
for i in range(1, 101):
    r = rows[i]; cl = by_app.get(i, []); grpc = next((c["group"] for c in calls if c["registry_id"] == i), None)
    apps.append(dict(registry_id=i, app=r["app"], provenance_group="ORIGINAL_NOTION_LIST_1_50" if i <= 50 else "RECONSTRUCTED_LIST_51_100", original_notion_membership_verified=r["notion_membership_verified"], registry_category=r["registry_category"], master_status=r["master_status"], plan_ref=r["plan_ref"],
                     execution_group=grpc or "E_baseline_record_exists_no_new_gemini_call", gemini_call_ids=cl, gemini_calls_min=len(cl), groq_verification_calls_planned=(vplan[i] if i in base else (4 * max(1, len(cl)) if cl else 0)), groq_note=("re-verify baseline record with verifier v2 (measured plan)" if i in base else ("~4 field calls per record (estimate)" if cl else "")),
                     flags=r["flags"], optional_calls=("re-extraction after identity/source fix (NOT in the 75)" if i in (58, 14) else "")))
assert sum(a["gemini_calls_min"] for a in apps) == 75
vt = [dict(record_ref=f"baseline/p1_v1/pass1/{i}.json", registry_id=i, app=REG[i][2], surface_id="default", kind="re-verify baseline record (v2)", groq_calls_planned=vplan[i]) for i in sorted(base)] + [dict(record_ref=f"(new record from {c['call_id']})", registry_id=c["registry_id"], app=c["app"], surface_id=c["surface_id"], kind="verify new record (v2)", groq_calls_planned=4) for c in calls]
gq = sum(v["groq_calls_planned"] for v in vt)
fm = {"committed_after_approval(A)": 28, "conditional_retrieval_recommended(B)": 2, "conditional_on_retrieval_and_identity(C)": 39, "conditional_on_identity(D)": 6}
rec = dict(created=iso(), total_apps=100, apps_with_existing_baseline_record=len(base), apps_with_a_new_gemini_call=len(new_apps), gemini_calls_total_minimum=75, formula="28 (v1f) + 2 (Neo4j, 1 app) + 39 (expansion waves 3A+3B+4) + 6 (identity-gated) = 75 calls over 74 apps", calls_by_group=dict(grp), apps_by_group={k: len(v) for k, v in ids.items()},
           the_six_identity_gated_calls={str(i): dict(app=v[0], status=v[1], why_gated=v[2], what_unlocks_it=v[3], provenance=("original" if i <= 50 else "reconstructed")) for i, v in GATED.items()}, commitment_breakdown=fm,
           why_no_double_counting=["the 6 gated apps are NOT in the 28 (v1f) nor in the 39: wave 3H (Waterfall.io, Clay) is excluded from the 39 and counted once in the 6", "Neo4j (#66) is not in the 28 and not in the 39; its 2 calls are 1 app x 2 surfaces", "Sherlock (#58) and Front (#14) already have baseline records and are NOT counted (optional re-extraction listed separately)", "41 unplanned apps = 39 (group C) + 2 (3H, counted in group D): checked", "unique (app, surface) pairs = 75; apps with a new call = 74; 26 baseline + 74 = 100: checked"],
           not_in_the_75=dict(optional_reextraction_58_and_14=2, corrected_pass_estimate_20pct=15, note="a corrected pass would be a new versioned run"), groq_verification=dict(records=len(vt), planned_calls=gq, note="baseline records use the measured plan (103); new records use 4 per record (estimate)"), approvable_now=dict(count=28, group="A_v1f_frozen (needs your approval + quota check only)"), conditional=dict(count=47, note="B + C + D need retrieval and/or identity confirmation and their own approved plans"))
json.dump(dict(reconciliation=rec, apps=apps, gemini_calls=calls, verification_tasks=vt), open(f"{O}/EXECUTION_LEDGER.json", "w"), indent=1)
def wcsv(name, data):
    with open(f"{O}/{name}", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(data[0]), extrasaction="ignore"); w.writeheader()
        for d in data: w.writerow({k: (";".join(v) if isinstance(v, list) else v) for k, v in d.items()})
wcsv("ledger_apps_100.csv", apps); wcsv("ledger_gemini_calls_75.csv", calls); wcsv("ledger_verification_tasks.csv", vt)
json.dump(rec, open(f"{O}/RECONCILIATION.json", "w"), indent=1)
print("calls by group:", dict(grp), "| apps by group:", rec["apps_by_group"], "| apps with new call:", len(new_apps), "| baseline:", len(base)); print("groq planned:", gq, "over", len(vt), "tasks"); print("per-app calls sum:", sum(a["gemini_calls_min"] for a in apps))
print("first/last call ids:", calls[0]["call_id"], calls[-1]["call_id"], "| commitment:", dict(collections.Counter(c["commitment"] for c in calls)))
