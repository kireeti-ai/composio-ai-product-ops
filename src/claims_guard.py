"""Claims guard: every reported metric must carry an evidence TIER, and only tier T3 (independent human-labelled evaluation against primary sources) may use the words accuracy / precision / recall / error rate.
T0 regression tests (synthetic or stored fixtures)            -> no quality claim at all
T1 controlled challenge tests (S1a replay, S1b planted, S1c)  -> "challenge-test result", NOT an accuracy estimate
T2 source-grounded pilot (S2; humans judge the STORED text)    -> "source-grounded agreement", NOT real-world accuracy
T3 independent human-labelled evaluation (>=2 labelers + adjudicator, frozen truth, intervals) -> the ONLY basis for an accuracy claim
Offline. Usage as a library: validate_metric(m) / render(m)."""
import re
TIERS = {"T0": "regression test", "T1": "controlled challenge test", "T2": "source-grounded pilot", "T3": "independent human-labelled evaluation"}
CLAIM_WORDS = re.compile(r"accura|precision|recall|error[ _]rate|correct(?:ness)?[ _]rate|reliab", re.I)
def wilson_upper(k, n, z=1.96):
    if n == 0: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); w = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** .5); return (c + w) / d
def validate_metric(m):
    errs = []
    for k in ("name", "value", "tier", "label"):
        if k not in m: errs.append(f"missing '{k}'")
    if errs: return errs
    t, name, label = m["tier"], m["name"], m["label"]
    if t not in TIERS: return [f"unknown tier {t!r}"]
    if t in ("T0", "T1", "T2"):
        if CLAIM_WORDS.search(name) and not re.match(r"(challenge|source_grounded|regression)_", name): errs.append(f"{t} metric '{name}' uses a claim word without a 'challenge_'/'source_grounded_'/'regression_' prefix")
        if t == "T1" and "not an accuracy estimate" not in label.lower(): errs.append("T1 label must state 'not an accuracy estimate'")
        if t == "T2" and "not real-world accuracy" not in label.lower(): errs.append("T2 label must state 'not real-world accuracy'")
        if t == "T0" and "synthetic" not in label.lower() and "regression" not in label.lower(): errs.append("T0 label must say regression/synthetic")
    if t == "T3":
        if not re.fullmatch(r"[0-9a-f]{64}", str(m.get("truth_sheet_sha256", ""))): errs.append("T3 needs truth_sheet_sha256 (frozen truth)")
        if int(m.get("labelers", 0)) < 2 or not m.get("adjudicated"): errs.append("T3 needs >= 2 independent labelers and an adjudicator")
        if not m.get("n_claims") or not m.get("ci95") or not m.get("n_apps"): errs.append("T3 needs n_claims, n_apps and a 95% interval")
        if m.get("agreement_pooled_kappa") is None or m.get("agreement_pooled_kappa") < 0.70: errs.append("T3 needs pooled agreement (kappa) >= 0.70")
    return errs
def render(m):
    e = validate_metric(m)
    if e: raise ValueError("; ".join(e))
    tag = {"T0": "[REGRESSION TEST]", "T1": "[CHALLENGE TEST - not an accuracy estimate]", "T2": "[SOURCE-GROUNDED - not real-world accuracy]", "T3": "[HUMAN-LABELLED EVALUATION]"}[m["tier"]]
    return f"{tag} {m['name']} = {m['value']} ({m['label']})"
