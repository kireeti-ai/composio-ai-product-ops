"""Human-evaluation package v2 (offline). Keeps Frames A and B BYTE-IDENTICAL to v1; adds Frame C (12 of the 41 expansion apps, pre-registered from plan metadata only) and a 3-app calibration set;
writes the final protocol and templates. NO labels are created. Output: runs/human-eval-v2-20261124/"""
import os, json, csv, random, shutil, hashlib, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
V1 = "runs/human-eval-v1-20261124"; O = "runs/human-eval-v2-20261124"; os.makedirs(O, exist_ok=True); SEED = 20261124
sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
REG = {a[0]: dict(cat=a[1], name=a[2]) for a in json.load(open("baseline/data/apps.json"))["apps"]}; CATS = json.load(open("baseline/data/apps.json"))["categories"]
fr = json.load(open(f"{V1}/sample_frames.json")); exp = json.load(open("runs/p1-expansion-v1-20261124/PLAN.json"))["apps"]
for f in ("label_sheet_blind_A.csv", "label_sheet_blind_B.csv", "scoring_sheet_A.csv", "scoring_sheet_B_TEMPLATE.csv"):
    shutil.copy2(f"{V1}/{f}", f"{O}/{f}"); assert sh(f"{V1}/{f}") == sh(f"{O}/{f}")
E_ = {a["registry_id"]: a for a in exp if not a["wave"].startswith("3H")}; quota = {"3A_core_ready_access_topup": 5, "3B_partial_targeted_reretrieval": 2, "4_no_retrieval_full_discovery": 5}; pool = {w: sorted(i for i, a in E_.items() if a["wave"] == w) for w in quota}
for attempt in range(3000):
    rng = random.Random(SEED + 2000 + attempt); pc = sorted(i for w, q in quota.items() for i in rng.sample(pool[w], q))
    if len({REG[i]["cat"] for i in pc}) >= 6 and sum(i <= 50 for i in pc) >= 3 and sum(i > 50 for i in pc) >= 5: break
else: raise SystemExit("no balanced Frame C")
used = set(fr["frame_A"]["ids"]) | {58}; calpool = {c: sorted(i for i in json.load(open(f"{V1}/sample_frames.json"))["frame_A"]["ids"] if False) for c in (1, 2, 3)}
base_ids = sorted(int(f[:-5]) for f in os.listdir("baseline/p1_v1/pass1")); rng = random.Random(SEED + 3000); cal = []
for c in (1, 2, 3):
    cands = [i for i in base_ids if i not in used and REG[i]["cat"] == c]; cal.append(rng.choice(cands))
cal = sorted(cal)
src = list(csv.reader(open(f"{V1}/label_sheet_blind_A.csv"))); hdr = src[0]; defs = [r for r in src[1:8]]                 # field definitions are copied from the v1 sheet (no drift)
def blind(name, ids, prov):
    with open(f"{O}/label_sheet_blind_{name}.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(hdr)
        for i in ids:
            idn = "reconstructed list: confirm product identity from the vendor's own site first" if prov(i) == "reconstructed" else "original Notion list (hint domain given)"
            for d in defs: w.writerow([name, i, REG[i]["name"], idn] + d[4:])
blind("C", pc, lambda i: "reconstructed" if i > 50 else "notion"); blind("CAL", cal, lambda i: "reconstructed" if i > 50 else "notion")
with open(f"{O}/scoring_sheet_C_TEMPLATE.csv", "w", newline="") as fh: csv.writer(fh).writerow(list(csv.reader(open(f"{O}/scoring_sheet_B_TEMPLATE.csv")))[0])
fr2 = dict(note="Pre-registered sample v2. Frames A and B are byte-identical to v1. Labels are produced by humans only; none exist yet.", frame_A=fr["frame_A"], frame_B=fr["frame_B"],
           frame_C=dict(frame="C_expansion_41_apps", seed=SEED + 2000, attempt=attempt, ids=pc, quota_by_wave=quota, preregistered="selected from expansion-plan metadata only, before any retrieval/extraction for these apps",
                        balance=dict(categories=sorted({CATS[REG[i]['cat'] - 1] for i in pc}), waves=dict(collections.Counter(E_[i]["wave"] for i in pc)), provenance=dict(notion=sum(i <= 50 for i in pc), reconstructed=sum(i > 50 for i in pc)))),
           calibration=dict(ids=cal, purpose="both labelers label these independently first, then meet to align definitions; NOT scored and NOT used in any accuracy figure", seed=SEED + 3000), neo4j="evaluated separately per surface after its Option B run")
json.dump(fr2, open(f"{O}/sample_frames_v2.json", "w"), indent=1)
with open(f"{O}/sample_overview_v2.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["frame", "registry_id", "app", "registry_category", "provenance", "stratum"])
    for i in fr["frame_A"]["ids"]: w.writerow(["A", i, REG[i]["name"], CATS[REG[i]["cat"] - 1], "reconstructed" if i > 50 else "notion", "baseline pilot"])
    for i in fr["frame_B"]["ids"]: w.writerow(["B", i, REG[i]["name"], CATS[REG[i]["cat"] - 1], "reconstructed" if i > 50 else "notion", "frozen v1f target"])
    for i in pc: w.writerow(["C", i, REG[i]["name"], CATS[REG[i]["cat"] - 1], "reconstructed" if i > 50 else "notion", E_[i]["wave"]])
    for i in cal: w.writerow(["CAL", i, REG[i]["name"], CATS[REG[i]["cat"] - 1], "reconstructed" if i > 50 else "notion", "calibration only (not scored)"])
json.dump(dict(labels_total_rows=dict(A=84, B=84, C=84, CAL=21), labels_completed=0, status="0 labels exist; every truth column is blank by construction. No ground truth has been invented."), open(f"{O}/LABELS_STATUS.json", "w"), indent=1)
with open(f"{O}/adjudication_log_TEMPLATE.csv", "w", newline="") as fh: csv.writer(fh).writerow(["registry_id", "field", "labeler1_value", "labeler2_value", "adjudicated_value", "evidence_url", "quote", "accessed_at", "rationale", "adjudicator_id", "date"])
open(f"{O}/labeler_instructions.md", "w").write("""# Labeler instructions (one page)
1. Open ONLY your label sheet (`label_sheet_blind_*.csv`). Do not open scoring sheets, model outputs, Groq verdicts, plans, tiers or any file under runs/ other than your sheet and these instructions.
2. Work alone. Do not discuss an app with the other labeler until the agreement report exists. Do not ask an LLM what the answer is.
3. For each app first confirm which product it is from the vendor's own site (reconstructed-list apps have no identity authority). If identity is doubtful write it in `notes` and mark the app's rows `undeterminable` only if no public source decides the field.
4. Use official documentation, pricing pages, developer portals and official repositories only. For every non-blank truth cell fill URL, a verbatim quote and the access date (docs change). Save a page copy or hash if you can.
5. Set fields (`auth_methods`, `api_types`): separate values with `;`. Enum fields: pick one allowed value; if none fits choose the closest and set `enum_fit` = forced.
6. `undeterminable_from_public_sources` = Y only when no public source decides the field. `existing_mcp = none_found` needs the search queries listed in `notes`.
7. `blocker` is free text: the main obstacle, or `none`.
8. Calibration set first (3 apps), then meet once with the other labeler to align definitions. Definitions are then FROZEN: changes need a written amendment before any frame is labelled.
""")
for f in os.listdir(O): os.chmod(f"{O}/{f}", 0o644 if f == "PROTOCOL_v2_FINAL.md" else 0o444)
print("Frame C:", pc, fr2["frame_C"]["balance"]); print("Calibration:", cal)
print("A/B sheets byte-identical to v1: True | blind-sheet rows: A", sum(1 for _ in open(f"{O}/label_sheet_blind_A.csv")) - 1, "B", sum(1 for _ in open(f"{O}/label_sheet_blind_B.csv")) - 1, "C", sum(1 for _ in open(f"{O}/label_sheet_blind_C.csv")) - 1, "CAL", sum(1 for _ in open(f"{O}/label_sheet_blind_CAL.csv")) - 1)
