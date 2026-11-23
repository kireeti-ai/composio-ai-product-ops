"""Call-level reconciliation of Groq calls: pilot (v1 plan: 4 + 12 + 12 + 48 = 76 calls) vs the 403-call execution ledger. OFFLINE: prompts are captured with a fake model function; no network.
A call is identified by (record, surface, field). Two calls OVERLAP only if their PROMPTS are byte-identical (same items, same retrieved passages). Writes ONLY runs/groq-call-reconciliation-v2-20261124/."""
import os, sys, json, csv, hashlib, math, collections, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src"); import verify_v2 as V
O = "runs/groq-call-reconciliation-v2-20261124"; os.makedirs(O, exist_ok=True); iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z"); h = lambda s: hashlib.sha256(s.encode()).hexdigest()[:16]
PV1 = "runs/pass2-pilot-plan-v1-20261124"; items = json.load(open(f"{PV1}/stage1_items.json")); FRAME_A = json.load(open("runs/human-eval-v2-20261124/sample_frames_v2.json"))["frame_A"]["ids"]
LEDGER = json.load(open("runs/execution-ledger-v1-20261124/EXECUTION_LEDGER.json")); BASE = sorted(int(f[:-5]) for f in os.listdir("baseline/p1_v1/pass1"))
def prompts_for(path, fields=None):
    out = {}; r = V.load_record(path); s = r["surfaces"][0]; old = V.EVIDENCE_FIELDS
    def cap(msgs, b): t = msgs[0]["content"]; out[t.split("FIELD: ")[1].split(" for app")[0]] = h(t); b.used += 1; return {"items": []}
    V.EVIDENCE_FIELDS = list(fields or old)
    try: V.verify_surface(r, s, cap, V.Budget(999))
    finally: V.EVIDENCE_FIELDS = old
    return out
LB = {}                                                         # the ledger's baseline re-verification: (record, field) -> prompt hash
for i in BASE:
    for f, ph in prompts_for(f"baseline/p1_v1/pass1/{i}.json").items(): LB[(i, f)] = ph
CEIL = sum(v["groq_calls_planned"] for v in LEDGER["verification_tasks"] if v["kind"].startswith("re-verify")); assert CEIL == 103 and len(LB) <= CEIL   # 103 = planned CEILING; len(LB) = calls that would ACTUALLY be sent (retriever must return a passage)
rows = []
def add(stage, rec, field, ph, note=""): rows.append(dict(stage=stage, record=rec, field=field, prompt_hash=ph, in_ledger_baseline_reverify=(rec, field) in LB and LB.get((rec, field)) == ph, same_key_but_different_prompt=((rec, field) in LB and LB.get((rec, field)) != ph), note=note))
for x in items["S1a_replays"]: add("S1a", x["registry_id"], x["field"], prompts_for(f"baseline/p1_v1/pass1/{x['registry_id']}.json", [x["field"]])[x["field"]])
for x in items["S1b_negative_controls"]: add("S1b", x["registry_id"], x["field"], prompts_for(f"{PV1}/controls/{x['control_id']}.json", [x["field"]])[x["field"]], f"planted '{x['planted_item']}'")
for x in items["S1c_positive_controls"]: add("S1c", x["registry_id"], x["field"], prompts_for(f"baseline/p1_v1/pass1/{x['registry_id']}.json", [x["field"]])[x["field"]])
for i in FRAME_A:
    for f, ph in prompts_for(f"baseline/p1_v1/pass1/{i}.json").items(): add("S2", i, f, ph)
stage_n = dict(collections.Counter(r["stage"] for r in rows)); assert stage_n["S1a"] == 4 and stage_n["S1b"] == 12 and stage_n["S1c"] == 12 and len(rows) == sum(stage_n.values())
seen = {}
for r in rows:                                                  # duplicates INSIDE the pilot (same identical prompt appearing in more than one stage)
    k = (r["record"], r["field"], r["prompt_hash"]); r["duplicate_of_stage"] = seen.get(k, ""); seen.setdefault(k, r["stage"])
for r in rows: r["classification"] = "NEW_distinct_prompt (planted control)" if r["stage"] == "S1b" else ("DUPLICATE_inside_pilot (identical to an earlier pilot call AND to a ledger call)" if r["duplicate_of_stage"] else "IDENTICAL_to_ledger_call")
cl = collections.Counter(r["classification"] for r in rows); by_stage = {s: collections.Counter(r["classification"] for r in rows if r["stage"] == s) for s in ("S1a", "S1b", "S1c", "S2")}
ident = sum(r["in_ledger_baseline_reverify"] for r in rows); distinct_in_ledger = len({(r["record"], r["field"]) for r in rows if r["in_ledger_baseline_reverify"]}); assert not any(r["same_key_but_different_prompt"] and r["stage"] != "S1b" for r in rows) and all(r["same_key_but_different_prompt"] for r in rows if r["stage"] == "S1b")
new = 12; BASE_ACT = len(LB); NEWREC = 300; LED = BASE_ACT + NEWREC; RET = 1.71; MAXA = 5; n_pilot = len(rows)
def scen(calls): return dict(minimum_planned_calls=calls, expected_attempts=math.ceil(calls * RET), worst_case_attempts=calls * MAXA)
sc = {"0_as_reported_before (ceilings: 403 ledger + 28)": scen(403 + 28), "A_actual_calls, S2 reused, S1a/S1c run separately": scen(LED + stage_n["S1a"] + 12 + stage_n["S1c"]), "B_actual_calls, no reuse at all": scen(LED + n_pilot), "C_RECOMMENDED pilot v2 (every distinct call once)": scen(LED + new)}
out = dict(created=iso(), key="a call = (record, surface, field); identical = byte-identical prompt", ledger_reported_ceiling=403, baseline_reverify_planned_ceiling=CEIL, baseline_reverify_ACTUAL_calls=BASE_ACT, baseline_planned_but_no_call=CEIL - BASE_ACT, new_records_estimate_75x4=NEWREC, ledger_corrected_total_actual_baseline_plus_new_estimate=LED, pilot_v1_calls_actual=n_pilot, pilot_by_stage=stage_n,
           classification_of_the_76=dict(cl), per_stage=({s: dict(c) for s, c in by_stage.items()}), identical_to_ledger_calls=ident, distinct_ledger_calls_covered_by_pilot=distinct_in_ledger, pilot_internal_duplicates=ident - distinct_in_ledger, new_calls_not_in_ledger=new,
           arithmetic=f"{n_pilot} pilot calls = {new} NEW (S1b planted) + {ident} identical to ledger calls; of those {ident} only {distinct_in_ledger} are DISTINCT ledger calls ({ident - distinct_in_ledger} are repeats of the same call inside the pilot)", scenarios=sc, assumptions=["retry ratio 1.71 is OBSERVED in the baseline Groq log", "worst case = 5 attempts per call (verify_v2 limit)", "new-record verification = 4 calls per record is an ESTIMATE; deterministic shortcuts can only lower it", "baseline calls are captured from the real records: only calls whose retriever returns a passage are counted (the 103 in the ledger was a ceiling)", "the 300 new-record calls remain an estimate (ceiling): deterministic shortcuts can only lower it"])
json.dump(out, open(f"{O}/RECONCILIATION.json", "w"), indent=1)
with open(f"{O}/call_level_overlap.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["stage", "record", "field", "prompt_hash", "in_ledger_baseline_reverify", "same_key_but_different_prompt", "duplicate_of_stage", "classification", "note"]); w.writeheader(); w.writerows(rows)
print(json.dumps({k: out[k] for k in ("classification_of_the_76", "per_stage", "identical_to_ledger_calls", "distinct_ledger_calls_covered_by_pilot", "pilot_internal_duplicates", "arithmetic")}, indent=1)); print(json.dumps(sc, indent=1))
# records needed by the recommended v2 pilot (full-record verification in priority order)
core = sorted({x["registry_id"] for x in items["S1a_replays"]} | {x["registry_id"] for x in items["S1c_positive_controls"]}); s2rest = [i for i in FRAME_A if i not in core]; calls_per = collections.Counter(r for (r, f) in LB)
print("S1 core records:", core, "->", sum(calls_per[i] for i in core), "ledger calls | Frame A records not in core:", s2rest, "->", sum(calls_per[i] for i in s2rest), "ledger calls | union", len(set(core) | set(FRAME_A)), "records ->", sum(calls_per[i] for i in set(core) | set(FRAME_A)), "ledger calls")
json.dump(dict(core_records=core, s2_rest_records=s2rest, calls_per_record={str(i): calls_per[i] for i in BASE}), open(f"{O}/v2_record_plan.json", "w"), indent=1)
