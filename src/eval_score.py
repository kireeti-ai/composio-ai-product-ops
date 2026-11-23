"""Field-level accuracy scoring for the human evaluation. Pure functions + CSV pipeline. It NEVER invents labels: blank truth cells => UNLABELLED (excluded), and with zero labelled claims all metrics are None.
Scoring rules (see runs/human-eval-v1-20261124/PROTOCOL.md):
  outcomes: CORRECT | PARTIAL | INCORRECT | ABSTAINED_MISSED | CORRECT_ABSTENTION | UNSUPPORTABLE_CLAIM | SCHEMA_LIMITATION(excluded) | UNLABELLED(excluded) | NOT_APPLICABLE(excluded)
  'unknown' (or ['unknown']) = abstention. Truth 'undeterminable_from_public_sources' = Y means no public source decides the field.
  strict score: CORRECT / CORRECT_ABSTENTION = 1, everything else 0.  lenient score: partial credit (set F1; ordinal-adjacent enum 0.5; blocker 'partial' 0.5).
Usage: python src/eval_score.py <blind_sheet.csv> <scoring_sheet.csv>"""
import csv, json, math, random, sys, collections
SET_FIELDS = {"auth_methods", "api_types"}; ENUM_FIELDS = {"access", "api_breadth", "existing_mcp", "buildability"}; TEXT_FIELDS = {"blocker"}
ORDINAL = {"api_breadth": ["narrow", "medium", "broad"]}; EXCLUDED = {"SCHEMA_LIMITATION", "UNLABELLED", "NOT_APPLICABLE"}
def as_set(v):
    if isinstance(v, str): v = [x.strip() for x in v.replace("|", ";").split(";") if x.strip()]
    return {str(x).strip().lower() for x in (v or [])}
def is_unknown(field, v):
    if field in SET_FIELDS: s = as_set(v); return not s or s == {"unknown"}
    return str(v).strip().lower() in ("unknown", "", "none_given")
def score_claim(field, model, truth=None, undeterminable=False, enum_fit=None, evidence_label=None, blocker_label=None):
    r = dict(field=field, outcome=None, strict=None, lenient=None, answered=False, forced_fit=(enum_fit == "forced"), evidence_label=evidence_label, f1=None, over_claimed=[], missed=[], right_for_wrong_reasons=False)
    unk = is_unknown(field, model); r["answered"] = not unk
    if field in TEXT_FIELDS:
        m = {"correct": (1, 1), "partial": (0, .5), "incorrect": (0, 0)}.get((blocker_label or "").strip().lower())
        if m is None: r["outcome"] = "NOT_APPLICABLE" if (blocker_label or "").strip().lower() == "none_applicable" else "UNLABELLED"; return r
        r["outcome"] = {"correct": "CORRECT", "partial": "PARTIAL", "incorrect": "INCORRECT"}[blocker_label.strip().lower()]; r["strict"], r["lenient"] = m
    elif undeterminable:
        r["outcome"], r["strict"], r["lenient"] = ("CORRECT_ABSTENTION", 1, 1) if unk else ("UNSUPPORTABLE_CLAIM", 0, 0)
    else:
        t = as_set(truth) if field in SET_FIELDS else str(truth or "").strip().lower()
        if not t: r["outcome"] = "UNLABELLED"; return r
        if field in SET_FIELDS:
            if "none_required" in t: r["outcome"] = "SCHEMA_LIMITATION"; return r                       # frozen enum cannot express it: excluded + reported
            M = as_set(model) - {"unknown"}
            if not M: r["outcome"], r["strict"], r["lenient"] = "ABSTAINED_MISSED", 0, 0
            else:
                tp = len(M & t); p = tp / len(M); rc = tp / len(t); f1 = 0 if tp == 0 else 2 * p * rc / (p + rc); r["f1"] = f1; r["over_claimed"] = sorted(M - t); r["missed"] = sorted(t - M)
                r["outcome"] = "CORRECT" if M == t else ("PARTIAL" if tp else "INCORRECT"); r["strict"] = 1 if M == t else 0; r["lenient"] = f1
        else:
            mv = str(model).strip().lower()
            if unk: r["outcome"], r["strict"], r["lenient"] = "ABSTAINED_MISSED", 0, 0
            elif mv == t: r["outcome"], r["strict"], r["lenient"] = "CORRECT", 1, 1
            else:
                r["outcome"], r["strict"], r["lenient"] = "INCORRECT", 0, 0
                o = ORDINAL.get(field)
                if o and mv in o and t in o and abs(o.index(mv) - o.index(t)) == 1: r["lenient"] = .5
    if r["answered"] and evidence_label: r["right_for_wrong_reasons"] = r["outcome"] == "CORRECT" and evidence_label.strip().lower() != "supports"
    return r
def wilson(k, n, z=1.96):
    if n == 0: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return ((c - w) / d, (c + w) / d)
def boot(vals_by_app, B=2000, seed=20261124):                                      # cluster bootstrap over APPS (claims within an app are not independent)
    apps = list(vals_by_app); rng = random.Random(seed); ms = []
    for _ in range(B):
        xs = [v for a in (rng.choice(apps) for _ in apps) for v in vals_by_app[a]]
        if xs: ms.append(sum(xs) / len(xs))
    ms.sort(); return (ms[int(.025 * len(ms))], ms[int(.975 * len(ms)) - 1]) if ms else None
def aggregate(claims, B=2000):
    sc = [c for c in claims if c["outcome"] not in EXCLUDED and c["outcome"] is not None]; out = dict(n_claims=len(claims), n_scored=len(sc), excluded=dict(collections.Counter(c["outcome"] for c in claims if c["outcome"] in EXCLUDED)), outcomes=dict(collections.Counter(c["outcome"] for c in sc)))
    if not sc: out.update(accuracy_all_strict=None, accuracy_all_lenient=None, note="no labelled claims: no metrics computed (none are invented)"); return out
    s = lambda xs, k: sum(c[k] for c in xs) / len(xs) if xs else None
    det = [c for c in sc if c["outcome"] not in ("CORRECT_ABSTENTION", "UNSUPPORTABLE_CLAIM")]; ans = [c for c in det if c["answered"]]; und = [c for c in sc if c["outcome"] in ("CORRECT_ABSTENTION", "UNSUPPORTABLE_CLAIM")]
    ev = [c for c in sc if c["answered"] and c["evidence_label"]]; k = sum(c["strict"] for c in sc)
    out.update(accuracy_all_strict=s(sc, "strict"), accuracy_all_lenient=s(sc, "lenient"), accuracy_all_strict_wilson95=wilson(k, len(sc)),
               accuracy_answered_strict=s(ans, "strict"), coverage_of_determinable=(len(ans) / len(det) if det else None), abstained_missed=sum(c["outcome"] == "ABSTAINED_MISSED" for c in sc),
               correct_abstentions=sum(c["outcome"] == "CORRECT_ABSTENTION" for c in sc), unsupportable_assertions=sum(c["outcome"] == "UNSUPPORTABLE_CLAIM" for c in sc), overclaim_rate_when_undeterminable=(sum(c["outcome"] == "UNSUPPORTABLE_CLAIM" for c in und) / len(und) if und else None),
               mean_set_f1=(lambda xs: sum(xs) / len(xs) if xs else None)([c["f1"] for c in sc if c["f1"] is not None]), evidence_supported_rate_strict=(sum((c["evidence_label"] or "").lower() == "supports" for c in ev) / len(ev) if ev else None),
               right_for_wrong_reasons=sum(c["right_for_wrong_reasons"] for c in sc), forced_fit_claims=sum(c["forced_fit"] for c in sc), accuracy_all_strict_excluding_forced_fit=s([c for c in sc if not c["forced_fit"]], "strict"))
    by = collections.defaultdict(list)
    for c in sc: by[c["app"]].append(c["strict"])
    out["accuracy_all_strict_cluster_bootstrap95_over_apps"] = boot(by, B) if len(by) >= 2 else None; out["n_apps"] = len(by); return out
def mcnemar_exact(b, c):                                                         # two-sided exact binomial on discordant pairs
    n = b + c
    if n == 0: return 1.0
    k = min(b, c); return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
def flag_metrics(items):                                                         # items: dict(flagged: bool, wrong: bool) ; verifier flags vs HUMAN-determined wrongness
    tp = sum(i["flagged"] and i["wrong"] for i in items); fp = sum(i["flagged"] and not i["wrong"] for i in items); fn = sum((not i["flagged"]) and i["wrong"] for i in items)
    return dict(precision=tp / (tp + fp) if tp + fp else None, recall=tp / (tp + fn) if tp + fn else None, tp=tp, fp=fp, fn=fn)
def score_from_csvs(blind_csv, scoring_csv):
    with open(blind_csv, newline="") as fb: truth = {(r["registry_id"], r["field"]): r for r in csv.DictReader(fb)}
    with open(scoring_csv, newline="") as fs: srows = list(csv.DictReader(fs))
    claims = []
    for r in srows:
        t = truth.get((r["registry_id"], r["field"]), {}); f = r["field"]; mv = r["model_value"]
        try: mv = json.loads(mv) if mv.startswith("[") else mv
        except Exception: pass
        unde = (t.get("undeterminable_from_public_sources(Y/N)", "") or "").strip().upper() == "Y"; tv = t.get("truth_value", "")
        c = score_claim(f, mv, tv, unde, (t.get("enum_fit(exact|forced)") or None), r.get("evidence_support_label(supports|partial|none)") or None, r.get("blocker_label(correct|partial|incorrect|none_applicable)") or None)
        if not tv and not unde and f not in TEXT_FIELDS: c["outcome"] = "UNLABELLED"
        c["app"] = r["registry_id"]; claims.append(c)
    return claims
if __name__ == "__main__":
    cl = score_from_csvs(sys.argv[1], sys.argv[2]); res = dict(overall=aggregate(cl), by_field={f: aggregate([c for c in cl if c["field"] == f]) for f in sorted({c["field"] for c in cl})}); print(json.dumps(res, indent=1, default=list))
