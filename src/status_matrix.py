"""Exact 100-app status matrix: ORIGINAL-LIST apps (1-50, verified from the original Notion page's public data) and RECONSTRUCTED apps (51-100, secondary list; membership NOT verified) in separate blocks.
Offline; reads the execution ledger; writes runs/execution-ledger-v1-20261124/STATUS_MATRIX_100.{md,csv}"""
import os, json, csv, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); O = "runs/execution-ledger-v1-20261124"
L = json.load(open(f"{O}/EXECUTION_LEDGER.json")); A = L["apps"]; assert [a["registry_id"] for a in A] == list(range(1, 101))
orig = [a for a in A if a["registry_id"] <= 50]; rec = [a for a in A if a["registry_id"] > 50]; assert len(orig) == len(rec) == 50 and all(a["original_notion_membership_verified"] for a in orig) and not any(a["original_notion_membership_verified"] for a in rec)
S = lambda a: a["master_status"]; statuses = sorted({S(a) for a in A})
md = ["# Exact 100-app status matrix", "", "**Provenance is kept separate.** Block 1 = apps 1-50: read from the ORIGINAL Notion page's public data (membership verified at fetch time). Block 2 = apps 51-100: a RECONSTRUCTED secondary list; names, categories and order are NOT verified against the original Notion table and carry no website hints.", "",
      "## Cross-tab: status x provenance", "", "| Status | Original list (1-50) | Reconstructed list (51-100) | Total |", "|---|---|---|---|"]
for s in statuses: o = sum(S(a) == s for a in orig); r = sum(S(a) == s for a in rec); md.append(f"| {s} | {o} | {r} | {o + r} |")
md += [f"| **Total** | **{len(orig)}** | **{len(rec)}** | **100** |", "", "## Cross-tab: Gemini call group x provenance (75 proposed calls over 74 apps)", "", "| Group | Original | Reconstructed | Apps | Calls |", "|---|---|---|---|---|"]
for g in sorted({a["execution_group"] for a in A}):
    ga = [a for a in A if a["execution_group"] == g]; md.append(f"| {g} | {sum(a['registry_id'] <= 50 for a in ga)} | {sum(a['registry_id'] > 50 for a in ga)} | {len(ga)} | {sum(a['gemini_calls_min'] for a in ga)} |")
def block(title, rows):
    out = ["", f"## {title}", "", "| ID | App | Status | Plan reference | Gemini call(s) | Flags |", "|---|---|---|---|---|---|"]
    for a in rows: out.append(f"| {a['registry_id']} | {a['app']} | {a['master_status']} | {a['plan_ref'] or ''} | {','.join(a['gemini_call_ids']) or '-'} | {';'.join(a['flags']).replace('reconstructed_list_membership_NOT_verified', 'RECONSTRUCTED') or '-'} |")
    return out
md += block("Block 1 - ORIGINAL Notion list (1-50), membership verified", orig) + block("Block 2 - RECONSTRUCTED list (51-100), membership NOT verified", rec)
open(f"{O}/STATUS_MATRIX_100.md", "w").write("\n".join(md) + "\n")
with open(f"{O}/STATUS_MATRIX_100.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["registry_id", "app", "provenance_block", "original_membership_verified", "master_status", "execution_group", "gemini_call_ids", "plan_ref", "flags"])
    for a in A: w.writerow([a["registry_id"], a["app"], "ORIGINAL_1_50" if a["registry_id"] <= 50 else "RECONSTRUCTED_51_100", a["original_notion_membership_verified"], a["master_status"], a["execution_group"], ";".join(a["gemini_call_ids"]), a["plan_ref"], ";".join(a["flags"])])
for f in os.listdir(O): os.chmod(f"{O}/{f}", 0o444)
print("\n".join(md[:30]))
