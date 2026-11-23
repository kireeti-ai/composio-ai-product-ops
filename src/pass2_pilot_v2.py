"""Pass 2 pilot v2 = every DISTINCT Groq call runs exactly once (no double counting). Corrects pilot v1, whose stages repeated calls that are identical to ledger calls (63 of 75; 7 repeated inside the pilot itself).
Stages: CORE = full-record verification of the 13 records behind S1a/S1c (results are the OFFICIAL baseline re-verification files, reused later); S1b = 12 planted-control calls (the only NEW calls);
S2REST = the Frame-A records not already in CORE (also official baseline re-verification). S1a/S1c/S2 are ANALYSES of those results, not extra calls.
Everything here is a CHALLENGE / SOURCE-GROUNDED pilot: none of it is an accuracy estimate (see src/claims_guard.py). Gated by <dir>/APPROVED_PASS2_PILOT_V2.json {"max_calls": N, "min_interval_s": s}. NO call is made by build/dry-run.
Usage: python src/pass2_pilot_v2.py build | dry-run | run <core|S1b|S2rest> | grade"""
import os, sys, json, hashlib, math, time, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src"); import verify_v2 as V
O = "runs/pass2-pilot-plan-v2-20261124"; PV1 = "runs/pass2-pilot-plan-v1-20261124"; REC = json.load(open("runs/groq-call-reconciliation-v2-20261124/v2_record_plan.json")); iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
S1A_ITEMS = [(14, "existing_mcp", lambda it: it == "official"), (49, "existing_mcp", lambda it: it == "none_found"), (28, "auth_methods", lambda it: it == "oauth2"), (5, "access", lambda it: it.startswith("self_serve_free"))]
CRITERIA = dict(version="v2-PROPOSED (the user may change it BEFORE the pilot; it is hashed and frozen at that point)", stop_rule="run CORE -> grade S1a/S1c; then S1b -> grade; stop at the first FAIL, fix by versioning the verifier (v2.1), re-run only the affected stage",
                S1a="PASS iff 0 of the 4 replayed known-false items has final verdict 'contradicted' (the 5 deterministic known cases are covered by the unit tests, which are regression only)",
                S1b="PASS iff 0 of 12 planted claims has final verdict 'supported'; any 'contradicted' on a planted claim must carry an explicit negating quote and is reported",
                S1c="PASS iff 0 of 12 positive controls is 'contradicted' AND at least 9 of 12 are 'supported' (sensitivity floor 75%, proposed)",
                S2="needs >= 40 human-labelled claim items else INCONCLUSIVE; PASS iff false_supported <= 1 AND false_contradicted <= 1 AND no failure cause repeats; CONDITIONAL iff false_supported + false_contradicted <= 3 AND no cause repeats; otherwise FAIL",
                meaning="ALL of S1 is a controlled challenge test and S2 is a source-grounded check: neither supports an accuracy claim. Only independent human-labelled evaluation (protocol v2, tier T3) does.")
def final(res, field, pred):
    for s in res["surfaces"]:
        for x in s["fields"].get(field, []):
            if pred(x["item"]): return x["verdict"]
    return None
def grade_s1a(v): v = [x for x in v if x is not None]; return dict(status="PASS" if len(v) == 4 and "contradicted" not in v else "FAIL", n=len(v), contradicted=v.count("contradicted"))
def grade_s1b(v): v = [x for x in v if x is not None]; return dict(status="PASS" if len(v) == 12 and v.count("supported") == 0 else "FAIL", n=len(v), false_supported=v.count("supported"), contradicted=v.count("contradicted"))
def grade_s1c(v): v = [x for x in v if x is not None]; return dict(status="PASS" if len(v) == 12 and v.count("contradicted") == 0 and v.count("supported") >= 9 else "FAIL", n=len(v), supported=v.count("supported"), false_contradicted=v.count("contradicted"))
def grade_s2(n_labelled, fs, fc, repeated_cause):
    if n_labelled < 40: return dict(status="INCONCLUSIVE", reason=f"only {n_labelled} labelled items (< 40)")
    if fs <= 1 and fc <= 1 and not repeated_cause: return dict(status="PASS")
    if fs + fc <= 3 and not repeated_cause: return dict(status="CONDITIONAL")
    return dict(status="FAIL")
def build():
    items = json.load(open(f"{PV1}/stage1_items.json")); cpr = {int(k): v for k, v in REC["calls_per_record"].items()}; core = REC["core_records"]; rest = REC["s2_rest_records"]
    st = dict(CORE=dict(records=core, calls=sum(cpr[i] for i in core), reuse="official baseline re-verification files"), S1b=dict(controls=[dict(control_id=c["control_id"], path=f"{PV1}/controls/{c['control_id']}.json", sha256=sha(f"{PV1}/controls/{c['control_id']}.json"), field=c["field"], planted_item=c["planted_item"]) for c in items["S1b_negative_controls"]], calls=12, reuse="none: distinct prompts (planted claims)"), S2REST=dict(records=rest, calls=sum(cpr[i] for i in rest), reuse="official baseline re-verification files"))
    total = st["CORE"]["calls"] + 12 + st["S2REST"]["calls"]; plan = dict(created=iso(), replaces="runs/pass2-pilot-plan-v1-20261124 (unchanged, superseded for call accounting)", stages=st, pilot_real_calls=total, of_which_ledger_calls=total - 12, of_which_new=12, expected_attempts=math.ceil(total * 1.71), worst_case_attempts=total * 5,
                                  analyses_not_extra_calls=dict(S1a="4 items inside CORE results", S1c="12 items inside CORE results", S2="Frame-A claims inside CORE + S2REST results (68 labelled items; human source-grounding sheet unchanged: " + f"{PV1}/stage2_source_grounding_sheet_TEMPLATE.csv)"), criteria=CRITERIA)
    json.dump(plan, open(f"{O}/PILOT_PLAN_v2.json", "w"), indent=1); json.dump(CRITERIA, open(f"{O}/CRITERIA_PREREGISTRATION.json", "w"), indent=1); open(f"{O}/CRITERIA_SHA256.txt", "w").write(sha(f"{O}/CRITERIA_PREREGISTRATION.json") + "  CRITERIA_PREREGISTRATION.json\n")
    for f in os.listdir(O): os.chmod(f"{O}/{f}", 0o444) if os.path.isfile(f"{O}/{f}") else None
    print(json.dumps(dict(CORE=st["CORE"]["calls"], S1b=12, S2REST=st["S2REST"]["calls"], total=total, ledger=total - 12, new=12, expected_attempts=plan["expected_attempts"], worst=plan["worst_case_attempts"])))
def run(stage):
    ap = f"{O}/APPROVED_PASS2_PILOT_V2.json"
    if not os.path.exists(ap): sys.exit("REFUSING: no APPROVED_PASS2_PILOT_V2.json (explicit approval + max_calls required)")
    apd = json.load(open(ap)); b = V.Budget(int(apd["max_calls"])); key = None
    with open(".env") as f:
        for l in f:
            if l.startswith("GROQ_API_KEY="): key = l.strip().split("=", 1)[1]
    if float(apd.get("min_interval_s", 0)): import verify_v2_paced as PV; V.groq_call = PV.paced(float(apd["min_interval_s"]))
    call = lambda m, bud: V.groq_call(m, bud, key); official = f"{O}/results_verify_baseline"; os.makedirs(official, exist_ok=True); plan = json.load(open(f"{O}/PILOT_PLAN_v2.json"))
    if stage in ("core", "S2rest"):
        for i in plan["stages"]["CORE" if stage == "core" else "S2REST"]["records"]: V.verify_record(f"baseline/p1_v1/pass1/{i}.json", official, call, b)
    elif stage == "S1b":
        out = f"{O}/results_S1b"; os.makedirs(out, exist_ok=True)
        for c in plan["stages"]["S1b"]["controls"]:
            assert sha(c["path"]) == c["sha256"], "control file changed"; V.EVIDENCE_FIELDS = [c["field"]]; V.verify_record(c["path"], out, call, b)
    print("calls used:", b.used, "retries:", b.retries, "stopped:", b.stopped)
def grade():
    off = f"{O}/results_verify_baseline"; items = json.load(open(f"{PV1}/stage1_items.json")); R = lambda i: json.load(open(f"{off}/{i}.json"))
    s1a = grade_s1a([final(R(i), f, p) for i, f, p in S1A_ITEMS]); s1c = grade_s1c([final(R(c["registry_id"]), c["field"], lambda it, x=c["item"]: it == x) for c in items["S1c_positive_controls"]])
    s1b = grade_s1b([final(json.load(open(f"{O}/results_S1b/{c['control_id']}.json")), c["field"], lambda it, x=c["planted_item"]: it == x) for c in items["S1b_negative_controls"]]); print(json.dumps(dict(S1a=s1a, S1b=s1b, S1c=s1c, note="CHALLENGE-TEST grades only; not an accuracy estimate")))
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build": build()
    elif a[0] == "dry-run": print(open(f"{O}/PILOT_PLAN_v2.json").read()[:600]); print("[no model call made] approval present:", os.path.exists(f"{O}/APPROVED_PASS2_PILOT_V2.json"))
    elif a[0] == "run": run(a[1])
    elif a[0] == "grade": grade()
