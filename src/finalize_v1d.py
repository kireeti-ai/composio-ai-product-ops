"""Finalize offline preparation: ledger, judgments v2, Neo4j scope, identity v3 (all in runs/topup-v1r-20261123/) and the revised plan run runs/p1-v1d-gemini-20261124/
(PLAN.json, APP_STATUS.json, eligibility.csv, README.md). Offline; no network, no LLM. Judgments are the assistant's reading (provisional); every cited quote is verified in stored text."""
import os, re, json, csv, time, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
R = "runs/topup-v1r-20261123"; V1 = "runs/topup-v1-20261123"; P = "runs/p1-v1d-gemini-20261124"; os.makedirs(P, exist_ok=True)
norm = lambda s: re.sub(r"\s+", " ", s).strip().lower(); iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")
a1 = json.load(open(f"{R}/accounting_attempt1.json")); plan_r = json.load(open(f"{R}/retryplan.json"))
att = []                                                                          # attempt-2 rows (all preserved, incl. skipped)
for f in sorted(os.listdir(f"{R}/raw")):
    if f.endswith(".json"):
        rec = json.load(open(f"{R}/raw/{f}"))
        for a in rec["attempts"]: att.append(dict(attempt=2, app_id=rec["app_id"], app=rec["app"], url=a["url"], kind=a["kind"], parent_url=a.get("parent_url"), reason=a.get("reason"), raw_status=a["status"], chars=a.get("chars"), outcome=a["outcome"], duplicate_of=a.get("duplicate_of"), sha256=(a.get("sha256") or "")[:12], requested_at=a.get("requested_at")))
with open(f"{R}/ledger_all_attempts.csv", "w", newline="") as fh:
    keys = ["attempt", "app_id", "app", "url", "kind", "parent_url", "reason", "raw_status", "chars", "outcome", "duplicate_of", "sha256", "requested_at"]; w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore"); w.writeheader()
    for r in a1: w.writerow(dict(r, kind="first_attempt"));
    for r in att: w.writerow(r)
final = []
for r in a1:                                                                      # per ORIGINAL url: first outcome -> final status (failed attempts are kept, never replaced)
    rec = [a for a in att if a["parent_url"] == r["url"] and a["outcome"] == "usable_unique"]
    fs = "usable_first_attempt" if r["outcome"] == "usable_unique" else ("recovered_by_alternative" if rec else ("not_retried_" + r["outcome"] if r["outcome"] in ("off_target_url", "duplicate_content", "not_official_domain") else "unrecovered_after_retry"))
    final.append(dict(app_id=r["app_id"], app=r["app"], url=r["url"], first_outcome=r["outcome"], final_status=fs, recovered_by=rec[0]["url"] if rec else None))
c1 = collections.Counter(r["outcome"] for r in a1); c2 = collections.Counter(a["outcome"] for a in att); cf = collections.Counter(f["final_status"] for f in final)
with open(f"{R}/final_url_status.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(final[0])); w.writeheader(); w.writerows(final)
usable = collections.defaultdict(list)                                           # final usable_unique pages per app across both attempts
for r in a1:
    if r["outcome"] == "usable_unique": usable[r["app_id"]].append(("v1", r["url"]))
for a in att:
    if a["outcome"] == "usable_unique": usable[a["app_id"]].append(("v1r", a["url"]))
acct = dict(first_attempt_68=dict(c1), first_attempt_returned_content=sum(r["returned_content"] for r in a1), retry_attempts=len(att), retry_outcomes=dict(c2), original_url_final_status=dict(cf),
            usable_unique_pages_after_retry=sum(len(v) for v in usable.values()), usable_unique_from_first_attempt=c1["usable_unique"], usable_unique_from_retry=c2["usable_unique"],
            reconciliation="68 first attempts = 45 usable_unique + 4 duplicate_content + 4 off_target_url + 5 thin_or_js_shell + 5 fetch_error + 5 fetch_empty (exclusive, precedence: error>empty>off_target>thin>not_official>duplicate>usable). 58 returned content = 45+4+4+5. Earlier report of '49 usable' counted 4 duplicates; earlier 'thin 7/off-target 2' was a precedence artifact (2 Pinterest user pages counted as thin)")
json.dump(acct, open(f"{R}/accounting_final.json", "w"), indent=1)

# ------------- pages index (text lookup for quote verification)
def pages_of(i):
    d = {}
    for p in json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]: d[p["url"]] = p["text"]
    if os.path.exists(f"{V1}/raw/{i}.json"):
        for e in json.load(open(f"{V1}/raw/{i}.json"))["fetched"]:
            if e["status"] == "ok": d[e["url"]] = e["text"]
    if os.path.exists(f"{R}/raw/{i}.json"):
        for e in json.load(open(f"{R}/raw/{i}.json"))["attempts"]:
            if e.get("status") == "ok": d[e["url"]] = e["text"]
    return d
def verify(i, frag, q):
    u = next((u for u, t in pages_of(i).items() if frag in u and norm(q) in norm(t)), None); assert u, (i, frag, q); return dict(url=u, quote=q, verified=True)

# ------------- access judgments v2 = v1 (kept) + changes from the retry
J1 = json.load(open(f"{V1}/access_judgments.json"))["apps"]; J2 = {int(k): dict(v, changed_in_v2=False) for k, v in J1.items()}
J2[38] = dict(name="Pinterest", level="explicit", changed_in_v2=True, note="app review gates API access: apps are reviewed and approved or denied; Trial access; some features closed-beta by invitation (upgrade page is a JS shell)",
              evidence=[verify(38, "dev.pinterest.com/docs/getting-started", "You will receive an email notification after your app has been reviewed, letting you know whether it was approved or denied access."), verify(38, "using-beta-and-restricted", "Closed beta features are available to specific invited developers and organizations.")])
J2[46] = dict(name="Squarespace", level="partial", changed_in_v2=True, note="Commerce API docs (OAuth) and a pricing page are retrieved; nothing states the API access requirement (support article on API keys still fails to fetch)",
              evidence=[verify(46, "developers.squarespace.com/commerce-apis/discounts-overview", "The Discounts API provides create, read, update, delete and list (CRUDL) access to discount records.")])
J2[20] = dict(J2[20], changed_in_v2=True, note="still unresolved after retry: pricing page empty on both attempts; get-started pages are thin or irrelevant")
json.dump(dict(provenance="assistant reading, provisional; supersedes v1 only where changed_in_v2 is true; v1 file preserved", levels=dict(collections.Counter(v["level"] for v in J2.values())), apps={str(k): v for k, v in J2.items()}), open(f"{R}/access_judgments_v2.json", "w"), indent=1)

# ------------- Neo4j: two surfaces assessed separately + Composio coverage
cat = json.load(open(f"{R}/catalog_neo4j.json"))
N = dict(question="Which Neo4j API surface is 'Neo4j' for the toolkit? Two different products/APIs share the name.",
 surfaces=dict(
  aura_management_api=dict(what="REST API to manage Aura instances/projects (create, get, list, pause, update)", evidence=[verify(66, "aura/api/overview", "The Aura API allows you to programmatically perform actions on your Aura instances without the need to log in to the Console."), verify(66, "aura/api/overview", "Before using the API, you must follow the steps outlined in Authentication to create")],
      measured_operations=["GET /v1/instances"], auth="credentials created per the Aura 'Authentication' page (page not retrieved) - mechanism unconfirmed", access="needs an Aura account; free trial gives $150 credits on Professional/Business Critical; tier availability of the API not stated in retrieved pages", state=dict(surface="partial", access="partial")),
  database_query_api=dict(what="HTTPS endpoint executing Cypher statements against a Neo4j database (supersedes the deprecated HTTP API); separate from Bolt drivers", evidence=[verify(66, "query-api/current", "The Query API allows to execute Cypher statements against a Neo4j server through HTTP requests."), verify(66, "query-api/current", "This API supersedes the deprecated HTTP API."), verify(66, "http-api/current/authentication-authorization", "Not available on Aura")],
      measured_operations=[], auth="DB user credentials, basic or bearer (stated for the legacy HTTP API page; Query API authorize page not retrieved)", access="no developer registration: requires a reachable database (self-managed, or Aura if the Query API is available there - not stated in retrieved text); disabled by default on self-managed <5.25", state=dict(surface="partial", access="unresolved"))),
 composio_coverage=dict(toolkit="neo4j", tools=cat["neo4j_tool_slugs_found"], targets="Aura management API only (instance + project tools; several are v1beta endpoints)", query_api_tools_found=False,
                        limitation="catalog metadata search only (3 queries); absence of a Query-API toolkit is not proof it does not exist", retrieved_at=cat["retrieved_at"]),
 status="HELD - decision needed: research as two separate rows (aura_management_api, database_query_api) or pick one; the 100-app count would not change if reported as sub-rows")
json.dump(N, open(f"{R}/neo4j_scope.json", "w"), indent=1)

# ------------- identity v3 (no authority is inferred from the reconstructed list)
IDV3 = [dict(id=58, app="Sherlock", status="EXCLUDED", basis="4 unrelated products retrieved; baseline Pass-1 record #58 identity-contaminated"), dict(id=80, app="Harvest", status="EXCLUDED", basis="3 different products"), dict(id=50, app="fanbasis", status="EXCLUDED until fanbasis.io confirmed", basis="openstage.live excluded from official evidence; dev-docs.fanbasis.com password-gated"),
 dict(id=73, app="Linear", status="PROVISIONAL (not confirmed) - held", basis="name+domain consistency only (linear.app GraphQL docs). Category membership comes from the reconstructed secondary list and is NOT used as evidence"),
 dict(id=78, app="Coda", status="PROVISIONAL (not confirmed) - held", basis="name+domain consistency only; superhuman.com hits suggest docs migration. Reconstructed-list category not used as evidence"),
 dict(id=60, app="Clay", status="PROVISIONAL (not confirmed) - not planned", basis="as above"), dict(id=59, app="Waterfall.io", status="PROVISIONAL (not confirmed) - not planned", basis="name is a domain; reconstructed-list category not used"),
 dict(id=66, app="Neo4j", status="HELD - scope decision", basis="two API surfaces; see neo4j_scope.json"),
 dict(ids=[15, 20, 24, 38, 39], app="Pylon, Gladly, Lark, Pinterest, Threads (Meta)", status="Resolved by ORIGINAL Notion hint (apps 1-50 only)", basis="authoritative source"),
 dict(ids=list(range(51, 101)), app="all apps 51-100", status="identity authority = NONE (reconstructed secondary list; no hints)", basis="names/order only; confirm each against the original Notion table before final analysis")]
json.dump(IDV3, open(f"{R}/identity_v3.json", "w"), indent=1)

# ------------- plan: phases / tiers / uncertainty / API-surface flags / extra retrieval (usable_unique only, two sources)
phase1 = [27, 32, 33, 34, 39, 41, 43, 52, 53, 56, 76, 65, 72, 71, 61]                                             # unchanged from v1c
phase2 = [38, 62, 63, 36, 29, 47, 44, 26, 70, 25, 75, 46]                                                          # Pinterest (explicit) first, then inferred, then partial
tier = {**{str(i): "A_prior_access_evidence_sufficient" for i in (27, 32, 33, 34, 39, 41, 43, 52, 53, 56, 76)}, **{str(i): "A_topup_access_explicit" for i in (65, 72, 71, 61)}, "38": "B2_topup_access_explicit_phase2",
        **{str(i): "B_access_inferred_self_serve" for i in (62, 63, 36)}, **{str(i): "C_access_partial" for i in (29, 47, 44, 26, 70, 25, 75, 46)}}
unc = {}
for i in phase1 + phase2:
    lvl = J2[i]["level"] if i in J2 else "explicit_prior"
    unc[str(i)] = dict(access_state=lvl, access_confirmed=lvl in ("explicit", "explicit_prior"), rule={"inferred_self_serve": "NEVER report as confirmed self-serve; label 'inferred'; model output on `access` is a hypothesis", "partial": "report `access` as partial/unknown unless the model quotes explicit gating", "explicit": "may be reported as evidenced, subject to verification", "explicit_prior": "may be reported as evidenced, subject to verification"}[lvl])
extra = {}
for i in phase1 + phase2:
    src = []
    v1u = [u for s, u in usable.get(i, []) if s == "v1"]; vru = [u for s, u in usable.get(i, []) if s == "v1r"]
    if v1u: src.append(dict(raw=f"{V1}/raw/{i}.json", list_key="fetched", use_urls=v1u))
    if vru: src.append(dict(raw=f"{R}/raw/{i}.json", list_key="attempts", use_urls=vru))
    if src: extra[str(i)] = src
OP = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(?:https?://[\w.\-]+)?(/[\w\-/{}.:$]*[\w}])"); api = {}
for i in phase1 + phase2:
    ops = sorted({f"{m.group(1)} {m.group(2)}" for t in pages_of(i).values() for m in OP.finditer(t)}); api[str(i)] = dict(measured_operations_count=len(ops), state="not_individually_assessed")
api["33"].update(state="partial", basis="resource-level only: Ad Accounts, Account Users, Campaign Groups, Campaigns, Creatives + 6 product APIs; operations not itemized"); api["71"].update(state="partial", basis="2 operations with paths, 7 resource types named; reference index not retrieved"); api["47"].update(state="partial", basis="1 operation (customers); REST confirmed")
names = {a[0]: a[2] for a in json.load(open("baseline/data/apps.json"))["apps"]}
status = []
for i in phase1 + phase2 + [20, 73, 78, 66]:
    elig = i in phase1 + phase2; why = [] if elig else {20: ["official evidence still unresolved after retry (pricing empty on 2 attempts; onboarding page thin)"], 73: ["identity provisional, not confirmed"], 78: ["identity provisional, not confirmed"], 66: ["API scope ambiguity (Aura management vs database Query API)"]}[i]
    status.append(dict(id=i, name=names[i], extraction_eligibility=dict(eligible=elig, phase=(1 if i in phase1 else 2) if elig else None, blocking_reasons=why),
                       research_completeness=dict(identity="resolved_by_original_hint" if i <= 50 else "reconstructed_list_name_only_not_authoritative", auth="present_keyword_verified_not_individually_read", api_surface=api.get(str(i), dict(state="not_assessed"))["state"], measured_operations=api.get(str(i), {}).get("measured_operations_count"),
                                                  access=(J2[i]["level"] if i in J2 else ("explicit_prior" if elig else "n/a")), mcp="not_retrieved (search candidates only)", buildability_blocker="not evidenced pre-extraction (model inference, to be verified)", open_items=[])))
plan = dict(run_id="p1-v1d-gemini-20261124", status="PREPARED - AWAITING EXPLICIT APPROVAL (no Gemini calls made; no APPROVED.json)", supersedes="p1-v1c-gemini-20261124", purpose="Resume Pass 1; same frozen prompt/schema/models; sources = baseline cached pages + verified official top-up pages (usable_unique only)",
            phases={"1": phase1, "2": phase2}, tiers=tier, uncertainty=unc, api_surface=api, extra_retrieval=extra, exclude_urls={}, status_file=f"{P}/APP_STATUS.json",
            not_eligible={"unresolved_evidence": [20], "identity_held_provisional": [73, 78], "scope_held": [66], "excluded_identity": [58, 80, 50]}, candidate_models=["gemini-2.5-flash", "gemini-3.5-flash"], key_policy="GEMINI_API_KEY only; GEMINI_API_KEY_2 is never read",
            approval_file_needed='runs/p1-v1d-gemini-20261124/APPROVED.json = {"models":[...],"cap_per_model":{model:N},"phases":[1]}  (only after your explicit approval and the active-quota check)', created=iso())
json.dump(plan, open(f"{P}/PLAN.json", "w"), indent=1); json.dump(status, open(f"{P}/APP_STATUS.json", "w"), indent=1)
with open(f"{P}/eligibility.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["id", "name", "eligible", "phase", "blocking", "identity", "api_surface", "ops", "access"])
    for s in status: w.writerow([s["id"], s["name"], s["extraction_eligibility"]["eligible"], s["extraction_eligibility"]["phase"], "; ".join(s["extraction_eligibility"]["blocking_reasons"]), s["research_completeness"]["identity"], s["research_completeness"]["api_surface"], s["research_completeness"]["measured_operations"], s["research_completeness"]["access"]])
open(f"{P}/README.md", "w").write("""# p1-v1d (prepared, NOT approved)
Two separate axes per app (APP_STATUS.json):
- extraction_eligibility: may we call the model for this app? (identity ok, enough official usable pages, scope clear, phase assigned)
- research_completeness: how much do we actually know? (identity authority, auth, api_surface, access, mcp, buildability) - eligible apps can be INCOMPLETE.
Uncertainty is carried into every record (meta.uncertainty): `inferred_self_serve` is never reported as confirmed; `partial` may be reported as partial/unknown.
The extraction PROMPT and SCHEMA are unchanged (hash-verified). Adding per-field evidence states to the extraction schema is a separate change that needs approval.
No APPROVED.json exists. Runner: src/run_p1.py --run p1-v1d-gemini-20261124 [--dry-run]
""")
for f in os.listdir(R):
    if f.endswith((".json", ".csv")) and os.path.isfile(f"{R}/{f}"): os.chmod(f"{R}/{f}", 0o444)
print("first-attempt exclusive:", dict(c1), "| retry outcomes:", dict(c2)); print("original URL final status:", dict(cf)); print("usable_unique pages total:", acct["usable_unique_pages_after_retry"])
print("access v2 levels:", dict(collections.Counter(v["level"] for v in J2.values()))); print("phase1:", len(phase1), "phase2:", len(phase2)); print("api partial:", [k for k, v in api.items() if v["state"] == "partial"])
