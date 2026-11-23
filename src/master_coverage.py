"""Master 100-app coverage matrix + separately versioned expansion plan for the UNPLANNED apps. Offline. Reads registry, baseline, v1f plan (frozen, read-only), Neo4j plan, audit-raw-v2.
Writes ONLY runs/master-coverage-v1-20261124/ and runs/p1-expansion-v1-20261124/. Hard checks: every registry ID 1..100 appears exactly once; statuses are mutually exclusive.
Provenance of reconstructed apps 51-100 is carried on every row (membership in the original Notion list is NOT verified)."""
import os, json, csv, collections, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
M = "runs/master-coverage-v1-20261124"; X = "runs/p1-expansion-v1-20261124"; os.makedirs(M, exist_ok=True); os.makedirs(X, exist_ok=True); iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")
D = json.load(open("baseline/data/apps.json")); REG = {a[0]: dict(cat=a[1], name=a[2], hint=a[3], src=a[4]) for a in D["apps"]}; CATS = D["categories"]
plan = json.load(open("runs/p1-v1f-gemini-20261124/PLAN.json")); FZ = json.load(open("runs/p1-v1f-gemini-20261124/FROZEN.json")); audit = {a["id"]: a for a in json.load(open("runs/audit-raw-v2-20261123/audit.json"))}
base = {int(f[:-5]) for f in os.listdir("baseline/p1_v1/pass1")}; raw = {int(f[:-5]) for f in os.listdir("baseline/p1_v1/raw")}
p28 = {int(i): ph for ph in ("1", "2") for i in plan["phases"][ph]}; HELD_ID = {73: "Linear", 78: "Coda"}; EXCL_ID = {80: "Harvest", 50: "fanbasis"}; NEO = 66
PROVISIONAL = {59, 60}          # Waterfall.io, Clay: provisional identity (user decision), kept out of waves until confirmed
def flags_of(i):
    f = []
    if REG[i]["src"] == "recovered": f.append("reconstructed_list_membership_NOT_verified")
    if i == 58: f.append("baseline_record_identity_contaminated_QUARANTINED")
    if i == 14: f.append("baseline_record_weak_sources(dev.frontapp.com never fetched)")
    if i in (1, 2, 3, 5): f.append("baseline_record_written_twice(final version verified)")
    if i in PROVISIONAL: f.append("identity_PROVISIONAL_not_confirmed")
    return f
rows = []
for i in range(1, 101):
    r = REG[i]; v = audit.get(i); st = plan_ref = nxt = None
    if i in base and i == 58: st, plan_ref, nxt = "COMPLETED_BASELINE_QUARANTINED", "baseline Pass 1 + Pass 2 exist", "identity resolution needed; then re-extract in a later versioned run (record must not be used)"
    elif i in base: st, plan_ref, nxt = "COMPLETED_BASELINE", "baseline Pass 1 (V1, reconstructed code) + Pass 2 (old verifier flags)", "re-verify with Pass 2 v2 (optional, for before/after accuracy); human evaluation sample may include it"
    elif i in p28: st, plan_ref, nxt = "PLANNED_FROZEN_V1F", f"p1-v1f phase {p28[i]} ({plan['tiers'][str(i)]})", "awaits approval + quota check; then Pass 2 v2"
    elif i == NEO: st, plan_ref, nxt = "HELD_NEO4J_OPTION_B_PREPARED", "p1-neo4j-optionB (2 surface calls), outside the 28", "3 official-page retrievals (need approval), then approval of 2 calls"
    elif i in HELD_ID: st, plan_ref, nxt = "HELD_IDENTITY_PROVISIONAL", "held pending identity confirmation (no authority for #51-100)", "confirm identity; access-evidence top-up; then add to an expansion wave"
    elif i in EXCL_ID: st, plan_ref, nxt = "EXCLUDED_IDENTITY_UNRESOLVED", "excluded pending authoritative identity resolution", "authoritative identity (Notion hint) required before any retrieval or extraction"
    else: st = "UNPLANNED"
    rows.append(dict(registry_id=i, app=r["name"], registry_category=CATS[r["cat"] - 1], provenance="original_notion_page_public_data" if r["src"] == "notion" else "reconstructed_secondary_source", notion_membership_verified=r["src"] == "notion", hint=r["hint"] or "",
                     master_status=st, plan_ref=plan_ref, pass1_record=(f"baseline/p1_v1/pass1/{i}.json" if i in base else ""), cached_retrieval=i in raw, audit_verdict=(v["verdict"] if v else ""), audit_gaps=";".join(v["gaps"]) if v else "", flags=flags_of(i), next_step=nxt))
# ---------------- expansion plan for UNPLANNED apps (separately versioned; plan only)
un = [r for r in rows if r["master_status"] == "UNPLANNED"]
def wave(r):
    i = r["registry_id"]
    if i in PROVISIONAL: return "3H_provisional_identity_hold"
    if not r["cached_retrieval"]: return "4_no_retrieval_full_discovery"
    return "3A_core_ready_access_topup" if r["audit_verdict"] == "READY_CORE" else "3B_partial_targeted_reretrieval"
STEPS = {"3A_core_ready_access_topup": ["free Composio fetch of official pricing/registration/API-access pages", "relevance audit (separate usability vs relevance)", "identity confirmation if reconstructed", "1 Gemini extraction (frozen prompt/schema)", "Pass 2 v2 verification (4 Groq calls)"],
         "3B_partial_targeted_reretrieval": ["targeted re-retrieval of the named gap (see audit_gaps)", "relevance audit", "identity confirmation if reconstructed", "1 Gemini extraction", "Pass 2 v2 verification"],
         "3H_provisional_identity_hold": ["HOLD until identity is confirmed by the user", "then as wave 3A"], "4_no_retrieval_full_discovery": ["official-docs discovery (3 free searches) + fetch (<=8 pages)", "relevance audit", "access top-up fetch", "identity confirmation if reconstructed", "1 Gemini extraction", "Pass 2 v2 verification"]}
COST = {"3A_core_ready_access_topup": 4, "3B_partial_targeted_reretrieval": 6, "3H_provisional_identity_hold": 4, "4_no_retrieval_full_discovery": 11}                         # estimated free Composio calls per app
HIGH_RISK = {59: "name is a domain", 60: "common word", 85: "unknown brand (iPayX)", 91: "product vs feature name", 92: "multiple products named Otter", 93: "common word (Fathom)", 94: "common word (Consensus)", 95: "unknown brand", 96: "common word (Devin)", 97: "unknown brand", 98: "CLI tool, not a hosted app", 99: "generic name", 100: "common word (Grain)", 54: "unknown brand", 55: "third-party site named like the product"}
STRESS = {91: "may lack a public REST API", 98: "CLI tool; may fit sdk_or_cli_only", 99: "generic name; may not be a single product"}              # HYPOTHESES to test against evidence, not findings
exp_apps = []
for r in un:
    i = r["registry_id"]; w = wave(r); prov = r["provenance"]
    exp_apps.append(dict(registry_id=i, app=r["app"], wave=w, provenance=prov, notion_membership_verified=r["notion_membership_verified"], identity_gate=("resolved_by_original_hint" if i <= 50 else "NO AUTHORITY (reconstructed list): confirm against original Notion table"), identity_risk=HIGH_RISK.get(i, "normal"),
                         schema_stress_hypothesis=STRESS.get(i), cached_retrieval=r["cached_retrieval"], audit_verdict=r["audit_verdict"], audit_gaps=r["audit_gaps"], steps=STEPS[w], est_free_composio_calls=COST[w], est_gemini_calls_min=0 if w.startswith("3H") else 1, est_groq_calls_min=0 if w.startswith("3H") else 4))
for r in rows:
    if r["master_status"] in ("UNPLANNED",): r["plan_ref"] = "p1-expansion-v1 " + next(a["wave"] for a in exp_apps if a["registry_id"] == r["registry_id"]); r["next_step"] = "see expansion plan steps"
# ---------------- hard checks
ids = [r["registry_id"] for r in rows]; assert ids == list(range(1, 101)); cnt = collections.Counter(r["master_status"] for r in rows); assert sum(cnt.values()) == 100
assert cnt["UNPLANNED"] == 41 and len(exp_apps) == 41 and cnt["PLANNED_FROZEN_V1F"] == 28 and cnt["COMPLETED_BASELINE"] + cnt["COMPLETED_BASELINE_QUARANTINED"] == 26
assert sorted(p28) == sorted(FZ["ids"]); assert all(r["provenance"] == "reconstructed_secondary_source" and not r["notion_membership_verified"] for r in rows if r["registry_id"] > 50)
wv = collections.Counter(a["wave"] for a in exp_apps)
json.dump(dict(created=iso(), counts=dict(cnt), expansion_waves=dict(wv), rows=rows), open(f"{M}/MASTER_COVERAGE.json", "w"), indent=1)
with open(f"{M}/MASTER_COVERAGE.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["registry_id", "app", "registry_category", "provenance", "notion_verified", "hint", "master_status", "plan_ref", "pass1_record", "cached_retrieval", "audit_verdict", "flags", "next_step"])
    for r in rows: w.writerow([r["registry_id"], r["app"], r["registry_category"], r["provenance"], r["notion_membership_verified"], r["hint"], r["master_status"], r["plan_ref"], r["pass1_record"], r["cached_retrieval"], r["audit_verdict"], ";".join(r["flags"]), r["next_step"]])
md = [f"# Master coverage of the 100 registry apps (generated {iso()})", "", "Every original registry ID 1..100 appears exactly once. Apps 51-100 come from a reconstructed secondary list: membership in the original Notion list is NOT verified.", "", "| Status | Apps |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(cnt.items())]
md += ["", "## The 41 unplanned apps and their expansion waves", "", "| Wave | Apps | Count |", "|---|---|---|"]
for k in sorted(wv): md.append(f"| {k} | {', '.join(str(a['registry_id']) + ' ' + a['app'] for a in exp_apps if a['wave'] == k)} | {wv[k]} |")
open(f"{M}/MASTER_COVERAGE.md", "w").write("\n".join(md) + "\n")
plan_x = dict(run_id="p1-expansion-v1-20261124", status="PLAN ONLY - NOT ELIGIBLE FOR EXTRACTION YET (retrieval, relevance audit and identity gates come first); no model calls; no APPROVED.json", separate_from="p1-v1f-gemini-20261124 (frozen, unchanged)",
              frozen_prompt_schema="unchanged; any schema change needs explicit approval", waves={k: [a["registry_id"] for a in exp_apps if a["wave"] == k] for k in sorted(wv)}, apps=exp_apps,
              gates=["identity: apps 51-100 have NO authority; the user must confirm each against the original Notion table (or paste its hint column)", "retrieval: free Composio only; zero-charge assertion; official domains only", "relevance audit: usability and relevance kept as separate fields", "quota: per-model caps required; stop at first daily-quota 429; no key rotation"],
              held_identity_not_in_waves={"73": "Linear", "78": "Coda", "80": "Harvest (excluded)", "50": "fanbasis (excluded)", "58": "Sherlock (quarantined baseline)", "66": "Neo4j (Option B plan)"}, created=iso())
json.dump(plan_x, open(f"{X}/PLAN.json", "w"), indent=1)
open(f"{X}/README.md", "w").write("# p1-expansion-v1 (PLAN ONLY, not approved)\nCovers the 41 apps that no record/plan/hold covered. Separate from the frozen v1f plan. Waves: 3A (14 cached, access top-up), 3B (6 partial, targeted re-retrieval), 3H (2 provisional-identity holds), 4 (19 with no retrieval). Nothing here is executable until its gates pass and you approve.\n")
for d in (M, X):
    for f in os.listdir(d): os.chmod(f"{d}/{f}", 0o444)
print("status counts:", dict(cnt)); print("expansion waves:", dict(wv)); print("expansion app ids <=50 (hint-resolved):", [a["registry_id"] for a in exp_apps if a["registry_id"] <= 50]); print("reconstructed in expansion:", sum(a["registry_id"] > 50 for a in exp_apps))
print("est free Composio calls (expansion):", sum(a["est_free_composio_calls"] for a in exp_apps), "| est Gemini min:", sum(a["est_gemini_calls_min"] for a in exp_apps), "| est Groq min:", sum(a["est_groq_calls_min"] for a in exp_apps))
