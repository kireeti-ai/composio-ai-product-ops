"""Build plan p1-v1f-gemini-20261124: the 27 targets of v1e + Gladly at its ORIGINAL registry ID 20 (plan size 28; there is NO app '#28' - registry ID 28 is WhatsApp Business and is untouched).
Offline, no network, no LLM. Also runs registry-integrity validation. Outputs: runs/p1-v1f-gemini-20261124/{PLAN.json,APP_STATUS.json,eligibility.csv,registry_validation.json,README.md}"""
import os, json, csv, time, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
P = "runs/p1-v1f-gemini-20261124"; os.makedirs(P, exist_ok=True); S = "runs/topup-v1s-20261123"; iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")
old = json.load(open("runs/p1-v1e-gemini-20261124/PLAN.json")); st_old = json.load(open("runs/p1-v1e-gemini-20261124/APP_STATUS.json")); rows = json.load(open(f"{S}/page_evidence_table.json"))
REG = {a[0]: dict(cat=a[1], name=a[2], hint=a[3], src=a[4]) for a in json.load(open("baseline/data/apps.json"))["apps"]}; gl = json.load(open(f"{S}/gladly/gladly_final_result.json"))
r2 = json.load(open(f"{S}/gladly/attempts_round2.json"))["attempts"]; r1 = json.load(open(f"{S}/gladly/attempts.json"))["attempts"]
USE = ["https://help.gladly.com/implementation/docs/difference-between-sandbox-and-production", "https://help.gladly.com/docs/manage-app-integrations", "https://help.gladly.com/docs/set-up-mcp-connections"]
assert all(any(a["url"] == u and a["outcome"] == "usable_unique" for a in r2) for u in USE)
EXCL = [dict(url=a["url"], source="gladly_final_round1", reason="Chat/iOS SDK reference page: not about REST API, auth, access or MCP") for a in r1 if a["outcome"] == "usable_unique"]
EXCL += [dict(url="https://help.gladly.com/docs/migrating-to-new-auth", source="gladly_final_round2", reason="Ordergroove-integration auth migration (third-party credentials), could be misread as Gladly API auth"), dict(url="https://gladly.com/get-started-sidekick", source="topup_v1r_retry", reason="marketing/onboarding page with no API, auth, access or MCP content")]
plan = json.loads(json.dumps(old)); plan.update(run_id="p1-v1f-gemini-20261124", supersedes="p1-v1e-gemini-20261124", status="PREPARED - AWAITING EXPLICIT APPROVAL (no Gemini calls made; no APPROVED.json)", created=iso())
plan["phases"]["2"] = old["phases"]["2"] + [20]                                                                                       # Gladly appended to phase 2; registry id stays 20
plan["tiers"]["20"] = "D_added_access_explicit_account_gated"; plan["provenance"]["20"] = {"source": "original_notion_page_public_data", "original_notion_membership_verified": True, "note": "apps 1-50 were read from the original Notion page's public data endpoint at fetch time"}
plan["uncertainty"]["20"] = dict(access_state="explicit_account_gated", access_confirmed=True, rule="explicit account-gating evidenced by verified quotes (still subject to verification); pricing is UNKNOWN - never report a price or plan requirement",
                                 field_states=dict(auth="per_user_api_tokens", api_surface="partial", mcp="client_only_evidence (Gladly AI is an MCP CLIENT of external servers; no Gladly MCP server evidenced)", pricing="unknown"))
plan["api_surface"]["20"] = dict(measured_operations_count=0, state="partial", basis="REST API, Lookup API, App Platform, Chat SDK, Help Center API and webhooks are named; no operations itemized (REST reference fetch failed twice)")
plan["extra_retrieval"]["20"] = [dict(raw=f"{S}/gladly/attempts_round2.json", list_key="attempts", use_urls=USE)]
plan["excluded_usable_pages"] = {"20": EXCL}
plan["added_by_decision"] = [dict(id=20, name="Gladly", registry_id_retained=True, note="additional extraction target; NOT a new app; plan position is 28th but registry ID remains 20 (registry ID 28 = WhatsApp Business, untouched)", result=f"{S}/gladly/gladly_final_result.json")]
plan.pop("pending_approval_candidates", None); plan["not_eligible"] = {"identity_held_provisional": [73, 78], "scope_held": [66], "excluded_identity": [58, 80, 50]}
plan["held_pending_identity"] = [73, 78]; plan["excluded_identity"] = [58, 80, 50]; plan["held_scope"] = dict(id=66, record=f"{S}/neo4j_record.json", note="held until the schema decision; nested per-surface proposal in runs/schema-proposal-v1-20261124")
plan["status_file"] = f"{P}/APP_STATUS.json"
# ---- preservation asserts: everything of the 27 is identical to v1e
for k in ("tiers", "uncertainty", "api_surface", "extra_retrieval", "provenance"):
    for i in old[k]: assert plan[k][i] == old[k][i], (k, i)
assert plan["phases"]["1"] == old["phases"]["1"] and plan["phases"]["2"][:-1] == old["phases"]["2"]
ids = [int(i) for ph in ("1", "2") for i in plan["phases"][ph]]; assert len(ids) == 28
json.dump(plan, open(f"{P}/PLAN.json", "w"), indent=1)
# ---- status: v1e entries unchanged + Gladly
by = [r for r in rows if r["app_id"] == 20]; inp = [r for r in by if r["source"] == "baseline" or (r["url"] in USE and r["retrieval_usability"] == "usable")]
rel = {d: sum(1 for r in inp if isinstance(r["evidence_relevance"], dict) and r["evidence_relevance"][d] == "direct") for d in ("auth", "access", "api_surface")}
gst = dict(id=20, name="Gladly", extraction_eligibility=dict(eligible=True, phase=2, blocking_reasons=[], added_by="user decision (registry ID 20 retained; not a new app)"),
           research_completeness=dict(identity="resolved_by_original_hint", auth="per_user_api_tokens (code-verified quote)", api_surface="partial", measured_operations=0, access="explicit_account_gated", pricing="unknown", mcp="client_only_evidence", buildability_blocker="not evidenced pre-extraction (model inference, to be verified)", open_items=["pricing page never retrieved (empty on 3 attempts)", "REST reference never retrieved"]),
           provenance=plan["provenance"]["20"], candidate_research_target_from_reconstructed_list=False,
           retrieval=dict(usable_planned_input_pages=len([r for r in inp if r["retrieval_usability"] == "usable"]), input_pages_total=len([r for r in by if r["source"] == "baseline"]) + len(USE), baseline_pages=len([r for r in by if r["source"] == "baseline"]), topup_pages=len(USE), excluded_usable_pages=len(EXCL), note="retrieval usability only; baseline developer.gladly.com/ was mislabelled 'blocked' by the audit login-wall heuristic but is a real landing page and IS an input"),
           evidence_relevance_summary=dict(pages_with_direct_relevance=rel, method="heuristic_v1_not_ground_truth"))
status = [x for x in st_old if x["id"] != 20] + [gst]   # replace (never duplicate) the old not-eligible Gladly entry carried over from v1e
assert len({x["id"] for x in status}) == len(status) and len([x for x in status if x["extraction_eligibility"]["eligible"]]) == 28
json.dump(status, open(f"{P}/APP_STATUS.json", "w"), indent=1)
# ---- registry validation
chk = []
def c(name, ok, detail=""): chk.append(dict(check=name, passed=bool(ok), detail=detail)); return ok
c("28 plan targets", len(ids) == 28, f"{len(ids)} ids"); c("no duplicate registry IDs in plan", len(set(ids)) == len(ids)); c("all IDs within registry 1..100 and present in registry", all(i in REG for i in ids))
names = [REG[i]["name"] for i in ids]; c("no duplicate app names among targets", len(set(names)) == len(names))
c("no duplicate IDs in APP_STATUS (one entry per registry ID)", len({x["id"] for x in status}) == len(status), f"{len(status)} entries")
c("every APP_STATUS entry matches registry id/name", all(REG[s["id"]]["name"] == s["name"] for s in status), "")
c("Gladly keeps registry ID 20 and name 'Gladly'", REG[20]["name"] == "Gladly" and 20 in ids); c("no app was assigned ID 28 as a new app: registry 28 is WhatsApp Business and is NOT in the plan", REG[28]["name"] == "WhatsApp Business" and 28 not in ids)
bp = {int(f[:-5]) for f in os.listdir("baseline/p1_v1/pass1")}; c("no target already has a baseline Pass-1 record (nothing is regenerated)", not (set(ids) & bp), f"overlap={sorted(set(ids) & bp)}")
c("held/excluded apps absent from plan (Linear 73, Coda 78, Neo4j 66, Sherlock 58, Harvest 80, fanbasis 50)", not (set(ids) & {73, 78, 66, 58, 80, 50}))
c("provenance present for every target", all(str(i) in plan["provenance"] for i in ids)); c("12 reconstructed-list targets all flagged membership-NOT-verified", all(plan["provenance"][str(i)]["original_notion_membership_verified"] is False for i in ids if i > 50) and sum(1 for i in ids if i > 50) == 12)
c("apps 1-50 flagged verified; none of #51-100 flagged verified", all(plan["provenance"][str(i)]["original_notion_membership_verified"] == (i <= 50) for i in ids))
c("registry source field agrees with provenance", all((REG[i]["src"] == "notion") == (plan["provenance"][str(i)]["source"] == "original_notion_page_public_data") for i in ids))
c("27 v1e targets unchanged + exactly one addition (20)", sorted(ids) == sorted([int(i) for ph in ("1", "2") for i in old["phases"][ph]] + [20]))
c("uncertainty states preserved for all 27 and present for Gladly", all(plan["uncertainty"][str(i)] == old["uncertainty"][str(i)] for i in old["uncertainty"]) and "20" in plan["uncertainty"])
c("Gladly excluded pages (SDK, Ordergroove auth, sidekick) are not in its inputs", not any(e["url"] in USE for e in EXCL))
json.dump(dict(created=iso(), passed=all(x["passed"] for x in chk), checks=chk), open(f"{P}/registry_validation.json", "w"), indent=1)
with open(f"{P}/eligibility.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["position", "registry_id", "name", "phase", "provenance", "notion_membership_verified", "tier", "access_state", "access_confirmed", "api_surface", "input_pages"])
    pos = 0
    for ph in ("1", "2"):
        for i in plan["phases"][ph]:
            pos += 1; s = next(x for x in status if x["id"] == int(i)); w.writerow([pos, i, REG[int(i)]["name"], ph, plan["provenance"][str(i)]["source"], plan["provenance"][str(i)]["original_notion_membership_verified"], plan["tiers"][str(i)], plan["uncertainty"][str(i)]["access_state"], plan["uncertainty"][str(i)]["access_confirmed"], plan["api_surface"][str(i)]["state"], s["retrieval"].get("input_pages_total") or s["retrieval"]["usable_planned_input_pages"]])
open(f"{P}/README.md", "w").write("""# p1-v1f (prepared, NOT approved) - 28 extraction targets = the 27 of p1-v1e + Gladly at its ORIGINAL registry ID 20
- Plan position 28 is NOT a registry ID: registry ID 28 is WhatsApp Business (has a baseline record, untouched, not in this plan).
- Gladly: access explicit_account_gated, auth per-user API tokens, api_surface partial, MCP client-only evidence, pricing UNKNOWN. Curated inputs: 4 baseline pages + 3 round-2 pages (SDK pages, Ordergroove auth page and sidekick page excluded with reasons).
- Neo4j (66) held until the schema decision; nested per-surface PROPOSAL (not applied): runs/schema-proposal-v1-20261124. Linear/Coda held; Sherlock/Harvest/fanbasis excluded.
- 12 targets from #51-100 are candidate research targets from a reconstructed secondary list: original Notion membership NOT verified.
- The frozen extraction prompt and schema are unchanged. No APPROVED.json exists. Runner: src/run_p1.py --run p1-v1f-gemini-20261124 [--dry-run]
""")
for f in os.listdir(P): os.chmod(f"{P}/{f}", 0o444)
print("plan:", len(ids), "targets | phase1:", len(plan["phases"]["1"]), "phase2:", len(plan["phases"]["2"])); print("registry validation:", "ALL PASSED" if all(x["passed"] for x in chk) else [x for x in chk if not x["passed"]])
for x in chk: print(("  PASS " if x["passed"] else "  FAIL ") + x["check"] + (f" [{x['detail']}]" if x["detail"] else ""))
