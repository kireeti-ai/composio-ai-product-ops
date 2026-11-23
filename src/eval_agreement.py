"""Independent labelling -> agreement -> adjudication queue -> merged TRUTH sheet. Pure functions + CLI. It never invents labels: blank cells stay blank; with no labels no statistic is produced.
Inputs: two blind label sheets (same columns as label_sheet_blind_*.csv) filled independently by two human labelers; optional adjudicated sheet (same columns) for disagreements.
Agreement: Cohen's kappa for enum fields (category 'undeterminable' included); mean Jaccard for set fields; free-text fields (blocker) are judged later by the adjudicator and excluded here.
Usage: python src/eval_agreement.py L1.csv L2.csv --out DIR [--adjudicated ADJ.csv]"""
import csv, json, os, sys, collections
SET_FIELDS = {"auth_methods", "api_types"}; TEXT_FIELDS = {"blocker"}
def rows(path):
    with open(path, newline="") as f: return {(r["registry_id"], r["field"]): r for r in csv.DictReader(f)}
def labelled(r): return bool((r.get("truth_value") or "").strip()) or (r.get("undeterminable_from_public_sources(Y/N)") or "").strip().upper() == "Y"
def value(r):
    if (r.get("undeterminable_from_public_sources(Y/N)") or "").strip().upper() == "Y": return "undeterminable"
    v = (r.get("truth_value") or "").strip().lower()
    return frozenset(x.strip() for x in v.replace("|", ";").split(";") if x.strip()) if r["field"] in SET_FIELDS else v
def kappa(pairs):
    n = len(pairs)
    if n == 0: return None
    po = sum(a == b for a, b in pairs) / n; c1 = collections.Counter(a for a, _ in pairs); c2 = collections.Counter(b for _, b in pairs); pe = sum((c1[k] / n) * (c2[k] / n) for k in set(c1) | set(c2))
    return None if pe >= 1 else (po - pe) / (1 - pe)
def jaccard(a, b):
    if a == "undeterminable" or b == "undeterminable": return 1.0 if a == b else 0.0
    u = a | b; return 1.0 if not u else len(a & b) / len(u)
def agreement(l1, l2):
    keys = sorted(k for k in l1 if k in l2 and l1[k]["field"] not in TEXT_FIELDS and labelled(l1[k]) and labelled(l2[k])); out = dict(n_double_labelled=len(keys), per_field={}, queue=[]); pooled_enum = []; jac = []
    for f in sorted({k[1] for k in keys}):
        ks = [k for k in keys if k[1] == f]
        if f in SET_FIELDS: js = [jaccard(value(l1[k]), value(l2[k])) for k in ks]; out["per_field"][f] = dict(n=len(ks), mean_jaccard=sum(js) / len(js), exact_agreement=sum(j == 1 for j in js) / len(js)); jac += js
        else: pr = [(value(l1[k]), value(l2[k])) for k in ks]; out["per_field"][f] = dict(n=len(ks), kappa=kappa(pr), observed_agreement=sum(a == b for a, b in pr) / len(pr)); pooled_enum += pr
    out["pooled_enum_kappa"] = kappa(pooled_enum); out["pooled_set_mean_jaccard"] = (sum(jac) / len(jac)) if jac else None
    for k in keys:
        a, b = value(l1[k]), value(l2[k])
        if a != b: out["queue"].append(dict(registry_id=k[0], field=k[1], labeler1=("; ".join(sorted(a)) if isinstance(a, frozenset) else a), labeler2=("; ".join(sorted(b)) if isinstance(b, frozenset) else b)))
    unl = [k for k in l1 if k in l2 and l1[k]["field"] not in TEXT_FIELDS and not (labelled(l1[k]) and labelled(l2[k]))]; out["not_double_labelled_keys"] = len(unl); return out
def merge(l1, l2, adj=None):
    """truth rows (blind-sheet columns): agreed -> filled (from labeler 1's row, evidence preserved); disagreement -> adjudicated row if provided else left BLANK (never guessed)."""
    adj = adj or {}; truth = []; status = collections.Counter()
    for k in sorted(l1):
        r = dict(l1[k])
        if k in l2 and labelled(l1[k]) and labelled(l2[k]):
            if value(l1[k]) == value(l2[k]) or r["field"] in TEXT_FIELDS: status["agreed" if r["field"] not in TEXT_FIELDS else "text_field"] += 1
            elif k in adj and labelled(adj[k]): r = dict(adj[k]); status["adjudicated"] += 1
            else:
                for c in ("truth_value", "enum_fit(exact|forced)", "truth_evidence_url", "truth_quote", "accessed_at", "undeterminable_from_public_sources(Y/N)", "confidence(1-3)", "labeler_id", "notes"): r[c] = ""
                status["disagreement_awaiting_adjudication"] += 1
        else:
            for c in ("truth_value", "enum_fit(exact|forced)", "truth_evidence_url", "truth_quote", "accessed_at", "undeterminable_from_public_sources(Y/N)", "confidence(1-3)", "labeler_id", "notes"): r[c] = ""
            status["not_double_labelled"] += 1
        truth.append(r)
    return truth, dict(status)
def main():
    a = sys.argv; l1 = rows(a[1]); l2 = rows(a[2]); out = a[a.index("--out") + 1]; os.makedirs(out, exist_ok=True); adj = rows(a[a.index("--adjudicated") + 1]) if "--adjudicated" in a else None
    ag = agreement(l1, l2); truth, st = merge(l1, l2, adj); ag["merge_status"] = st
    with open(f"{out}/agreement.json", "w") as f: json.dump(ag, f, indent=1, default=list)
    with open(f"{out}/adjudication_queue.csv", "w", newline="") as f: w = csv.DictWriter(f, fieldnames=["registry_id", "field", "labeler1", "labeler2"]); w.writeheader(); w.writerows(ag["queue"])
    with open(f"{out}/truth_sheet.csv", "w", newline="") as f: w = csv.DictWriter(f, fieldnames=list(truth[0])); w.writeheader(); w.writerows(truth) if truth else None
    print(json.dumps({k: ag[k] for k in ("n_double_labelled", "pooled_enum_kappa", "pooled_set_mean_jaccard", "merge_status")}, indent=1, default=list))
if __name__ == "__main__": main()
