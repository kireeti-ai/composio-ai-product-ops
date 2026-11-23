"""Provenance-by-status cross-tab for the 100 registry apps, derived INDEPENDENTLY from primary artifacts (registry, baseline files, frozen v1f ids, Neo4j plan, identity records, expansion plan) and then reconciled
cell-by-cell against runs/master-coverage-v1-20261124 and the execution ledger. Original IDs 1-50 must sum to 50; reconstructed IDs 51-100 to 50. Offline. Writes ONLY runs/provenance-crosstab-v2-20261124/."""
import os, json, csv, collections, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); O = "runs/provenance-crosstab-v2-20261124"; iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")
REG = {a[0]: dict(name=a[2], src=a[4]) for a in json.load(open("baseline/data/apps.json"))["apps"]}; assert sorted(REG) == list(range(1, 101))
base = {int(f[:-5]) for f in os.listdir("baseline/p1_v1/pass1")}; frozen = json.load(open("runs/p1-v1f-gemini-20261124/FROZEN.json"))["ids"]; vplan = json.load(open("runs/p1-v1f-gemini-20261124/PLAN.json"))["phases"]
neo = json.load(open("runs/p1-neo4j-optionB-20261124/PLAN.json"))["app"]["id"]; idv3 = {e["id"]: e for e in json.load(open("runs/topup-v1r-20261123/identity_v3.json")) if "id" in e}; expansion = {a["registry_id"]: a for a in json.load(open("runs/p1-expansion-v1-20261124/PLAN.json"))["apps"]}
prov = lambda i: "ORIGINAL_NOTION_LIST_1_50" if REG[i]["src"] == "notion" else "RECONSTRUCTED_LIST_51_100"; assert all((REG[i]["src"] == "notion") == (i <= 50) for i in REG)
held = {i for i, e in idv3.items() if e["status"].startswith("PROVISIONAL") and "held" in e["status"]}; excluded = {i for i, e in idv3.items() if e["status"].startswith("EXCLUDED") and i not in base}; quarantined = {58} & base
def status(i):
    if i in quarantined: return "COMPLETED_BASELINE_QUARANTINED"
    if i in base: return "COMPLETED_BASELINE"
    if i in frozen: return "PLANNED_FROZEN_V1F"
    if i == neo: return "HELD_NEO4J_OPTION_B_PREPARED"
    if i in held: return "HELD_IDENTITY_PROVISIONAL"
    if i in excluded: return "EXCLUDED_IDENTITY_UNRESOLVED"
    return "UNPLANNED"
ST = ["COMPLETED_BASELINE", "COMPLETED_BASELINE_QUARANTINED", "PLANNED_FROZEN_V1F", "HELD_NEO4J_OPTION_B_PREPARED", "HELD_IDENTITY_PROVISIONAL", "EXCLUDED_IDENTITY_UNRESOLVED", "UNPLANNED"]; PR = ["ORIGINAL_NOTION_LIST_1_50", "RECONSTRUCTED_LIST_51_100"]
cell = collections.defaultdict(list)
for i in range(1, 101): cell[(prov(i), status(i))].append(i)
M = json.load(open("runs/master-coverage-v1-20261124/MASTER_COVERAGE.json")); mrows = {r["registry_id"]: r for r in M["rows"]}; L = json.load(open("runs/execution-ledger-v1-20261124/EXECUTION_LEDGER.json")); lap = {a["registry_id"]: a for a in L["apps"]}
checks = []
def chk(name, ok, detail=""): checks.append(dict(check=name, passed=bool(ok), detail=detail)); assert ok, (name, detail)
rows = {p: {s: len(cell[(p, s)]) for s in ST} for p in PR}; rs = {p: sum(rows[p].values()) for p in PR}; cs = {s: sum(rows[p][s] for p in PR) for s in ST}
chk("original IDs 1-50 sum to 50", rs[PR[0]] == 50, str(rs[PR[0]])); chk("reconstructed IDs 51-100 sum to 50", rs[PR[1]] == 50, str(rs[PR[1]])); chk("grand total 100", sum(rs.values()) == 100)
chk("independent status == master coverage status for EVERY app", all(status(i) == mrows[i]["master_status"] for i in range(1, 101)), f"{sum(status(i) != mrows[i]['master_status'] for i in range(1, 101))} mismatches")
chk("every status column total == master coverage count", all(cs[s] == M["counts"].get(s, 0) for s in ST), json.dumps({s: (cs[s], M["counts"].get(s, 0)) for s in ST}))
chk("provenance == master coverage provenance for every app", all(prov(i) == ("ORIGINAL_NOTION_LIST_1_50" if mrows[i]["provenance"].startswith("original") else "RECONSTRUCTED_LIST_51_100") for i in range(1, 101)))
chk("ledger provenance_group agrees for every app", all(lap[i]["provenance_group"] == ("ORIGINAL_NOTION_LIST_1_50" if i <= 50 else "RECONSTRUCTED_LIST_51_100") for i in range(1, 101)))
chk("status == ledger master_status for every app", all(status(i) == lap[i]["master_status"] for i in range(1, 101)))
ph = {p: {k: sum(1 for i in vplan[k] if prov(i) == p) for k in ("1", "2")} for p in PR}; chk("v1f phase split sums to the PLANNED column (15 + 13 = 28)", sum(ph[p][k] for p in PR for k in ("1", "2")) == cs["PLANNED_FROZEN_V1F"] == 28 and sum(len(vplan[k]) for k in ("1", "2")) == 28)
wv = collections.defaultdict(lambda: {p: 0 for p in PR})
for i, a in expansion.items(): wv[a["wave"]][prov(i)] += 1
chk("expansion waves sum to the UNPLANNED column (41) and to the expansion plan", sum(sum(v.values()) for v in wv.values()) == cs["UNPLANNED"] == 41 and set(expansion) == {i for i in range(1, 101) if status(i) == "UNPLANNED"})
chk("a reconstructed app is never flagged as notion-verified (master + ledger)", all(not mrows[i]["notion_membership_verified"] and not lap[i]["original_notion_membership_verified"] for i in range(51, 101)) and all(mrows[i]["notion_membership_verified"] for i in range(1, 51)))
chk("baseline records: 25 + 1 quarantined = 26 = files in baseline/p1_v1/pass1", cs["COMPLETED_BASELINE"] + cs["COMPLETED_BASELINE_QUARANTINED"] == len(base) == 26)
json.dump(dict(created=iso(), derivation="independent (primary artifacts) then reconciled against master coverage + ledger", matrix=rows, row_sums=rs, column_sums=cs, master_counts=M["counts"], id_lists={f"{p}|{s}": cell[(p, s)] for p in PR for s in ST}, planned_phase_split=ph, expansion_wave_split={w: dict(v) for w, v in wv.items()}, checks=checks), open(f"{O}/CROSSTAB.json", "w"), indent=1)
with open(f"{O}/CROSSTAB.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["provenance"] + ST + ["ROW_TOTAL"]); [w.writerow([p] + [rows[p][s] for s in ST] + [rs[p]]) for p in PR]; w.writerow(["COLUMN_TOTAL"] + [cs[s] for s in ST] + [100]); w.writerow(["master_coverage_count"] + [M["counts"].get(s, 0) for s in ST] + [100])
short = {"COMPLETED_BASELINE": "Completed baseline", "COMPLETED_BASELINE_QUARANTINED": "Completed, quarantined", "PLANNED_FROZEN_V1F": "Planned (frozen v1f)", "HELD_NEO4J_OPTION_B_PREPARED": "Held: Neo4j", "HELD_IDENTITY_PROVISIONAL": "Held: identity", "EXCLUDED_IDENTITY_UNRESOLVED": "Excluded: identity", "UNPLANNED": "Unplanned"}
md = ["# Provenance-by-status cross-tab (100 apps)", "", "Status derived INDEPENDENTLY from primary artifacts, then reconciled against the master coverage matrix and the execution ledger (all checks below passed).", "", "| Provenance | " + " | ".join(short[s] for s in ST) + " | **Row total** |", "|---|" + "---|" * (len(ST) + 1)]
md += [f"| {p} | " + " | ".join(str(rows[p][s]) for s in ST) + f" | **{rs[p]}** |" for p in PR] + ["| **Column total** | " + " | ".join(f"**{cs[s]}**" for s in ST) + " | **100** |", "| Master coverage count | " + " | ".join(str(M["counts"].get(s, 0)) for s in ST) + " | 100 |", ""]
md += ["## Exact IDs per cell", "", "| Provenance | Status | IDs |", "|---|---|---|"] + [f"| {p} | {short[s]} | {', '.join(map(str, cell[(p, s)])) or '-'} |" for p in PR for s in ST]
md += ["", "## Sub-splits that reconcile to the columns", "", f"Planned (frozen v1f) by phase: original {ph[PR[0]]['1']}+{ph[PR[0]]['2']} = {ph[PR[0]]['1'] + ph[PR[0]]['2']}, reconstructed {ph[PR[1]]['1']}+{ph[PR[1]]['2']} = {ph[PR[1]]['1'] + ph[PR[1]]['2']}; total 28.", "", "| Unplanned: expansion wave | Original | Reconstructed | Total |", "|---|---|---|---|"] + [f"| {w} | {v[PR[0]]} | {v[PR[1]]} | {sum(v.values())} |" for w, v in sorted(wv.items())]
md += ["", "## Reconciliation checks", ""] + [f"- PASS: {c['check']}" + (f" [{c['detail']}]" if c['detail'] and len(c['detail']) < 160 else "") for c in checks]
open(f"{O}/CROSSTAB.md", "w").write("\n".join(md) + "\n")
for f in os.listdir(O): os.chmod(f"{O}/{f}", 0o444)
print("\n".join(md[:14])); print("checks passed:", sum(c["passed"] for c in checks), "of", len(checks))
