"""Build the human-evaluation sample + BLANK label sheets (offline). NO ground-truth labels are created or invented: every truth column is empty.
Frame A = the 26 existing baseline Pass-1 records (usable now as a pilot of the historical V1 output). Frame B = the 28 frozen v1f targets (pre-registered NOW, before any new model output exists).
Selection is seeded + deterministic (random.Random(SEED)), stratified, with balance constraints; Sherlock (#58, identity-contaminated) is excluded from Frame A.
Outputs: runs/human-eval-v1-20261124/{sample_frames.json, sample_overview.csv, label_sheet_blind_A.csv, label_sheet_blind_B.csv, scoring_sheet_A.csv, scoring_sheet_B_TEMPLATE.csv}"""
import os, json, csv, random, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
O = "runs/human-eval-v1-20261124"; os.makedirs(O, exist_ok=True); SEED = 20261124
REG = {a[0]: dict(cat=a[1], name=a[2]) for a in json.load(open("baseline/data/apps.json"))["apps"]}; CATS = json.load(open("baseline/data/apps.json"))["categories"]
plan = json.load(open("runs/p1-v1f-gemini-20261124/PLAN.json")); prov = plan["provenance"]
FIELDS = [("auth_methods", "set", "Authentication methods a developer can use with the PUBLIC API.", "oauth2; api_key; basic; bearer_token; jwt_or_signed; other; none_required (NOT in the frozen model enum)"),
          ("access", "enum", "Can a developer obtain API credentials themselves? Choose the best-fitting value; record enum_fit=forced if none fits.", "self_serve_free; self_serve_trial_or_paid_plan; approval_or_review_required; partner_or_contact_sales; no_public_api; undeterminable"),
          ("api_types", "set", "Types of public API offered.", "rest; graphql; soap; sdk_or_cli_only; websocket; none; undeterminable"),
          ("api_breadth", "enum", "Breadth of the documented public API (PROPOSED thresholds, fix before labelling): narrow = a handful of resources (<~15 operations); medium = several resource families (~15-100 operations); broad = >100 operations / dozens of resource families.", "narrow; medium; broad; undeterminable"),
          ("existing_mcp", "enum", "As of the access date, is there an MCP server for this app's API? official = published by the vendor; community = third party; none_found = none found after the documented search (list queries in notes).", "official; community; none_found; undeterminable"),
          ("buildability", "enum", "Could this be an agent toolkit today? yes = self-serve credentials + documented public API covering core use cases + no hard blocker; yes_with_caveats = feasible with notable constraints (approval, plan limits, partial API); no = infeasible without partnership/contact-sales or no public API.", "yes; yes_with_caveats; no; undeterminable"),
          ("blocker", "text", "Main obstacle to building a toolkit, or 'none'. (Free text; the model's blocker is judged later as correct / partial / incorrect.)", "free text")]
# ---------------- Frame A (26 baseline records)
A = {}
for f in os.listdir("baseline/p1_v1/pass1"):
    r = json.load(open(f"baseline/p1_v1/pass1/{f}")); v = json.load(open(f"baseline/p1_v1/verify/{f}")); items = [i for L in v["fields"].values() for i in L]
    A[r["id"]] = dict(id=r["id"], name=r["name"], cat=REG[r["id"]]["cat"], model=r["model"], flags=sum(bool(i.get("needs_human")) for i in items), provenance="notion" if r["id"] <= 50 else "reconstructed", auth=r["auth_methods"])
quota_A = {1: 3, 2: 3, 3: 3, 5: 1, 6: 1, 9: 1}; pool = {c: sorted(i for i, a in A.items() if a["cat"] == c and i != 58) for c in quota_A}
for attempt in range(2000):
    rng = random.Random(SEED + attempt); pick = sorted(i for c, q in quota_A.items() for i in rng.sample(pool[c], min(q, len(pool[c]))))
    if len({A[i]["model"] for i in pick}) == 2 and sum(A[i]["flags"] > 0 for i in pick) >= 3 and sum(A[i]["flags"] == 0 for i in pick) >= 3 and len(pick) == 12: break
else: raise SystemExit("no balanced sample found")
selA = dict(frame="A_baseline_26_existing_pass1", seed=SEED, attempt=attempt, ids=pick, quota_by_registry_category={str(k): v for k, v in quota_A.items()}, excluded=[dict(id=58, reason="identity-contaminated record (Sherlock)")],
            balance=dict(categories=sorted({CATS[A[i]['cat'] - 1] for i in pick}), models=dict(collections.Counter(A[i]["model"] for i in pick)), with_verifier_flags=sum(A[i]["flags"] > 0 for i in pick), without=sum(A[i]["flags"] == 0 for i in pick), provenance=dict(collections.Counter(A[i]["provenance"] for i in pick))))
# ---------------- Frame B (28 frozen v1f targets; selection uses PLAN info only - pre-registered before any new output)
B = {int(i): dict(id=int(i), name=REG[int(i)]["name"], cat=REG[int(i)]["cat"], tier=plan["tiers"][str(i)], prov="notion" if prov[str(i)]["original_notion_membership_verified"] else "reconstructed") for ph in ("1", "2") for i in plan["phases"][ph]}
quota_B = {"A_prior_access_evidence_sufficient": 3, "A_topup_access_explicit": 2, "B2_topup_access_explicit_phase2": 1, "B_access_inferred_self_serve": 2, "C_access_partial": 3, "D_added_access_explicit_account_gated": 1}
poolB = {t: sorted(i for i, b in B.items() if b["tier"] == t) for t in quota_B}
for attempt in range(2000):
    rng = random.Random(SEED + 1000 + attempt); pickB = sorted(i for t, q in quota_B.items() for i in rng.sample(poolB[t], min(q, len(poolB[t]))))
    if len(pickB) == 12 and len({B[i]["cat"] for i in pickB}) >= 5 and sum(B[i]["prov"] == "reconstructed" for i in pickB) >= 3 and sum(B[i]["prov"] == "notion" for i in pickB) >= 4: break
else: raise SystemExit("no balanced sample found (B)")
selB = dict(frame="B_frozen_v1f_28_targets", seed=SEED + 1000, attempt=attempt, ids=pickB, quota_by_tier=quota_B, preregistered="selected from plan metadata only, before any v1f model output exists",
            balance=dict(categories=sorted({CATS[B[i]['cat'] - 1] for i in pickB}), tiers=dict(collections.Counter(B[i]["tier"] for i in pickB)), provenance=dict(collections.Counter(B[i]["prov"] for i in pickB))))
json.dump(dict(note="Pre-registered sample. Labels are produced by humans only; none exist yet.", frame_A=selA, frame_B=selB, neo4j="Neo4j (#66) is evaluated separately per surface after its Option B run; not in these frames"), open(f"{O}/sample_frames.json", "w"), indent=1)
with open(f"{O}/sample_overview.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["frame", "registry_id", "app", "registry_category(reconstructed-list for >50)", "provenance", "stratum"])
    for i in pick: w.writerow(["A", i, A[i]["name"], CATS[A[i]["cat"] - 1], A[i]["provenance"], f"category {A[i]['cat']}; model {A[i]['model']}; verifier-flags {A[i]['flags']}"])
    for i in pickB: w.writerow(["B", i, B[i]["name"], CATS[B[i]["cat"] - 1], B[i]["prov"], B[i]["tier"]])
def blind(frame, ids, nm, prv):
    with open(f"{O}/label_sheet_blind_{frame}.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["frame", "registry_id", "app", "identity_note", "field", "field_type", "field_definition", "allowed_values", "truth_value", "enum_fit(exact|forced)", "truth_evidence_url", "truth_quote", "accessed_at", "undeterminable_from_public_sources(Y/N)", "confidence(1-3)", "labeler_id", "notes"])
        for i in ids:
            idn = "reconstructed list: confirm product identity from the vendor's own site first" if prv(i) == "reconstructed" else "original Notion list (hint domain given)"
            for f, t, d, a in FIELDS: w.writerow([frame, i, nm(i), idn, f, t, d, a, "", "", "", "", "", "", "", "", ""])
blind("A", pick, lambda i: A[i]["name"], lambda i: A[i]["provenance"]); blind("B", pickB, lambda i: B[i]["name"], lambda i: B[i]["prov"])
# scoring sheet A: model claims + verifier flags prefilled; label columns BLANK; labelers must not open it before blind labelling is finished
with open(f"{O}/scoring_sheet_A.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["frame", "registry_id", "app", "field", "model_value", "model_evidence_url_quote", "quote_found_auto", "pass2_verdicts(groq; flag not truth)", "pass2_needs_human", "evidence_support_label(supports|partial|none)", "blocker_label(correct|partial|incorrect|none_applicable)", "error_category", "adjudicator_id", "adjudication_notes"])
    for i in pick:
        r = json.load(open(f"baseline/p1_v1/pass1/{i}.json")); v = json.load(open(f"baseline/p1_v1/verify/{i}.json"))["fields"]
        for f, t, d, a in FIELDS:
            val = r.get(f); ev = [e for e in r["evidence"] if e["field"] == f]; vd = v.get(f, [])
            w.writerow(["A", i, r["name"], f, json.dumps(val) if not isinstance(val, str) else val, " || ".join(f"{e['url']} :: {e['quote'][:120]}" for e in ev), ";".join(str(e.get("quote_found")) for e in ev), "; ".join(f"{x['item'][:25]}={x['verdict']}" for x in vd), any(x.get("needs_human") for x in vd), "", "", "", "", ""])
with open(f"{O}/scoring_sheet_B_TEMPLATE.csv", "w", newline="") as fh:
    csv.writer(fh).writerow(["frame", "registry_id", "app", "field", "model_value", "model_evidence_url_quote", "quote_found_auto", "pass2_verdicts(groq; flag not truth)", "pass2_needs_human", "evidence_support_label(supports|partial|none)", "blocker_label(correct|partial|incorrect|none_applicable)", "error_category", "adjudicator_id", "adjudication_notes"])
json.dump(dict(labels_total_rows=len(pick) * 7 + len(pickB) * 7, labels_completed=0, status="0 labels exist; all truth columns are blank by construction. No ground truth has been invented."), open(f"{O}/LABELS_STATUS.json", "w"), indent=1)
for f in os.listdir(O): os.chmod(f"{O}/{f}", 0o444)
print("Frame A ids:", pick, "| balance:", selA["balance"]); print("Frame B ids:", pickB, "| balance:", selB["balance"]); print("blank label rows: A", len(pick) * 7, "B", len(pickB) * 7)
