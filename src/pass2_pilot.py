"""Pass 2 REAL-PILOT plan builder / gated runner / evaluators.  The pilot uses REAL Groq calls on REAL stored sources (after approval). Synthetic tests (tests/*.py) are regression tests, NOT evidence.
Stages (all offline to BUILD; the model stage is gated by <pilot dir>/APPROVED_PASS2_PILOT.json {"max_calls": N}):
  S1a  replay of the old verifier's known false-contradicted items with the real model (behaviour check)
  S1b  source-grounded NEGATIVE controls: real records with ONE planted claim that NO stored source supports (false-supported sensitivity). Planted = by construction; says nothing about real-world accuracy.
  S1c  POSITIVE controls: real claims strongly supported by their own quote (false-contradicted / false-insufficient sensitivity)
  S2   real pilot on Frame A (12 baseline apps, all evidence fields) judged against HUMAN source-grounding labels (blind to verifier verdicts)
Usage: python src/pass2_pilot.py build | dry-run | run <stage>"""
import os, sys, re, json, csv, random, copy, hashlib, collections, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src"); import verify_v2 as V
O = "runs/pass2-pilot-plan-v1-20261124"; SEED = 20261124; iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")
BASE_IDS = sorted(int(f[:-5]) for f in os.listdir("baseline/p1_v1/pass1")); FRAME_A = json.load(open("runs/human-eval-v2-20261124/sample_frames_v2.json"))["frame_A"]["ids"]
REPLAYS = [(14, "existing_mcp", "'beta' MCP read as contradicting 'official'"), (49, "existing_mcp", "OAuth/LWA quote used to contradict 'none_found'"), (28, "auth_methods", "'OAuth (not 2.0)' wording vs oauth2"), (5, "access", "adversarial survivor: unrelated 'no static API reference' quote")]
DETERMINISTIC = [(2, "api_types"), (4, "api_types"), (22, "api_types"), (84, "api_types"), (58, "auth_methods")]
PLANT = [("api_types", "soap", r"soap|wsdl"), ("api_types", "websocket", r"websocket|web socket|wss://"), ("auth_methods", "jwt_or_signed", r"\bjwt\b|json web token|hmac|signature|signed"), ("existing_mcp", "official", r"\bmcp\b|model context protocol")]
def srcs(i):
    r = V.load_record(f"baseline/p1_v1/pass1/{i}.json"); s = r["surfaces"][0]; return r, s, V.load_sources(r, s)
def build():
    os.makedirs(f"{O}/controls", exist_ok=True); rng = random.Random(SEED); neg = []; order = BASE_IDS[:]; rng.shuffle(order); used = set(); kinds = collections.Counter()
    for i in order:
        if i in used or i == 58 or len(neg) >= 12: continue
        r, s, pages = srcs(i); text = " ".join(pages.values())
        for fld, item, rx in sorted(PLANT, key=lambda p: kinds[p[1]]):
            cur = s.get(fld)
            if kinds[item] >= 3 or (item in (cur if isinstance(cur, list) else [cur])): continue
            if re.search(rx, text, re.I): continue                                          # planted claim must have ZERO lexical support anywhere in the sources
            rec = copy.deepcopy(r["raw"]); rec["planted_control"] = dict(field=fld, planted_item=item, original_value=cur, proof="regex found no support in any stored source page: " + rx)
            if fld in ("api_types", "auth_methods"): rec[fld] = [x for x in cur if x != "unknown"] + [item]
            else: rec[fld] = item
            cid = f"N{len(neg) + 1:02d}_{i}_{item}"; json.dump(rec, open(f"{O}/controls/{cid}.json", "w"), indent=1); neg.append(dict(control_id=cid, registry_id=i, field=fld, planted_item=item, expected="NOT supported (insufficient_evidence expected; contradicted only with an explicit negating quote)")); kinds[item] += 1; used.add(i); break
    pos = []; cands = []
    for i in BASE_IDS:
        if i == 58: continue
        r, s, pages = srcs(i)
        for e in s.get("evidence", []):
            f = e["field"]
            if f in ("api_types", "auth_methods", "existing_mcp", "access") and e.get("quote_found"):
                items = V.items_for(s, f); anchor = V.ACCESS_ANCHOR if f == "access" else None
                for it in items:
                    a = anchor or V.ANCHOR.get(f, {}).get(it.split(" :: ")[0] if f == "access" else it)
                    if f == "existing_mcp" and it not in ("official", "community"): continue
                    if a and it not in ("unknown", "other") and re.search(a, e["quote"], re.I): cands.append((i, f, it))
    rng.shuffle(cands); per = collections.Counter()
    for i, f, it in cands:
        if len(pos) >= 12 or per[f] >= 4 or any(p["registry_id"] == i for p in pos): continue
        per[f] += 1; pos.append(dict(control_id=f"P{len(pos) + 1:02d}_{i}_{f}", registry_id=i, field=f, item=it, expected="supported (Pass-1 quote is verbatim in the sources and names the item)"))
    s1 = dict(S1a_replays=[dict(registry_id=i, field=f, old_problem=w, model_calls=1) for i, f, w in REPLAYS], S1a_deterministic_no_model_call=[dict(registry_id=i, field=f) for i, f in DETERMINISTIC], S1b_negative_controls=neg, S1c_positive_controls=pos)
    json.dump(dict(created=iso(), seed=SEED, note="REAL model calls on REAL stored sources after approval. Controls are sensitivity checks, not accuracy.", **s1), open(f"{O}/stage1_items.json", "w"), indent=1)
    # ---- Stage 2: blind source-grounding sheet for ALL claim items of Frame A (no verifier verdicts shown)
    rowsx = []
    for i in FRAME_A:
        r, s, pages = srcs(i); ps = V.passages(pages)
        for f in V.EVIDENCE_FIELDS:
            for it in V.items_for(s, f):
                if it == "unknown": continue
                top = V.retrieve([t for t in V.query_terms(f, it)], ps, 5); rowsx.append([i, r["name"], f, it, " || ".join(f"({p['url'][8:70]}) {p['text'][:260]}" for p in top), ";".join(pages), "", "", "", ""])
    with open(f"{O}/stage2_source_grounding_sheet_TEMPLATE.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["registry_id", "app", "field", "claim_item", "candidate_passages(top5, for convenience; read the full sources)", "source_pages", "source_supports_claim(supports|contradicts|neither|cannot_tell)", "decisive_url_and_quote", "labeler_id", "notes"]); w.writerows(rowsx)
    calls_s2 = 0
    for i in FRAME_A:
        r, s, pages = srcs(i); ps = V.passages(pages)
        for f in V.EVIDENCE_FIELDS:
            items = V.items_for(s, f); pre = V.precheck_enum_conflict(f, items); todo = [x for x in items if x not in pre and x != "unknown"]; calls_s2 += 1 if (todo and ps) else 0
    plan = dict(S1a=len(REPLAYS), S1b=len(neg), S1c=len(pos), S1_total_min=len(REPLAYS) + len(neg) + len(pos), S2_planned_max=calls_s2, S2_claim_items_to_label=len(rowsx), retry_ratio_observed=1.71, S1_attempts_expected=round((len(REPLAYS) + len(neg) + len(pos)) * 1.71), S2_attempts_expected=round(calls_s2 * 1.71))
    json.dump(plan, open(f"{O}/pilot_call_budget.json", "w"), indent=1); print(json.dumps(plan)); print("negative controls:", [(c["registry_id"], c["planted_item"]) for c in neg]); print("positive controls:", [(c["registry_id"], c["field"], c["item"]) for c in pos])
def run(stage):
    ap = f"{O}/APPROVED_PASS2_PILOT.json"
    if not os.path.exists(ap): sys.exit("REFUSING: no APPROVED_PASS2_PILOT.json (explicit approval + max_calls required)")
    apd = json.load(open(ap)); cap = int(apd["max_calls"]); key = None
    if float(apd.get("min_interval_s", 0)): import verify_v2_paced as PV; V.groq_call = PV.paced(float(apd["min_interval_s"]))      # respect the observed RPM/TPM limits
    with open(".env") as f:
        for l in f:
            if l.startswith("GROQ_API_KEY="): key = l.strip().split("=", 1)[1]
    b = V.Budget(cap); out = f"{O}/results_{stage}"; os.makedirs(out, exist_ok=True); items = json.load(open(f"{O}/stage1_items.json")); call = lambda m, bud: V.groq_call(m, bud, key)
    def one(path, field):
        V.EVIDENCE_FIELDS = [field]; return V.verify_record(path, out, call, b)
    if stage == "S1a":
        for x in items["S1a_replays"]: one(f"baseline/p1_v1/pass1/{x['registry_id']}.json", x["field"])
    elif stage == "S1b":
        for x in items["S1b_negative_controls"]: one(f"{O}/controls/{x['control_id']}.json", x["field"])
    elif stage == "S1c":
        for x in items["S1c_positive_controls"]: one(f"baseline/p1_v1/pass1/{x['registry_id']}.json", x["field"])
    elif stage == "S2":
        V.EVIDENCE_FIELDS = ["auth_methods", "access", "api_types", "existing_mcp"]
        for i in FRAME_A: V.verify_record(f"baseline/p1_v1/pass1/{i}.json", out, call, b)
    print("calls used:", b.used, "retries:", b.retries, "stopped:", b.stopped)
# ---------------- evaluators (pure; unit-tested with SYNTHETIC inputs only - not evidence)
def wilson(k, n, z=1.96):
    if n == 0: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); w = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** .5); return (round((c - w) / d, 4), round((c + w) / d, 4))
def eval_negative_controls(results):    # results: list of final verdicts for the planted items
    n = len(results); fs = sum(v == "supported" for v in results); return dict(n=n, false_supported=fs, false_supported_wilson95=wilson(fs, n), contradicted_without_explicit_negation_possible=sum(v == "contradicted" for v in results), note="sensitivity control, NOT accuracy")
def eval_positive_controls(results):
    n = len(results); c = collections.Counter(results); return dict(n=n, supported=c["supported"], false_contradicted=c["contradicted"], insufficient=c["insufficient_evidence"], other=n - c["supported"] - c["contradicted"] - c["insufficient_evidence"], sensitivity_supported=(c["supported"] / n if n else None), note="sensitivity control, NOT accuracy")
def eval_stage2(pairs):                 # pairs: (verifier_final_verdict, human_source_label) where human_source_label in supports|contradicts|neither|cannot_tell
    ok = [p for p in pairs if p[1] in ("supports", "contradicts", "neither")]; sup = [p for p in ok if p[0] == "supported"]; con = [p for p in ok if p[0] == "contradicted"]; ins = [p for p in ok if p[0] == "insufficient_evidence"]
    fs = sum(p[1] != "supports" for p in sup); fc = sum(p[1] != "contradicts" for p in con); miss_s = sum(p[1] == "supports" for p in ins); miss_c = sum(p[1] == "contradicts" for p in ins)
    return dict(n_labelled=len(ok), n_cannot_tell_excluded=len(pairs) - len(ok), verdict_supported=len(sup), false_supported=fs, false_supported_wilson95=wilson(fs, len(sup)), verdict_contradicted=len(con), false_contradicted=fc, false_contradicted_wilson95=wilson(fc, len(con)), insufficient_but_sources_support=miss_s, insufficient_but_sources_contradict=miss_c, note="source-grounded (stored text), NOT real-world accuracy")
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build": build()
    elif a[0] == "dry-run": print(open(f"{O}/pilot_call_budget.json").read()); print("[no model call made] approval file present:", os.path.exists(f"{O}/APPROVED_PASS2_PILOT.json"))
    elif a[0] == "run": run(a[1])
