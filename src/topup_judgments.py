"""Persist the top-up outputs (all under runs/topup-v1-20261123/): access_judgments.json, api_surface_reassessment.json, identity_v2.json, retrieval_results.json,
and build the revised plan runs/p1-v1c-gemini-20261124/PLAN.json. Offline, no LLM API. Judgments are the ASSISTANT'S reading (provisional); every cited quote is verified
to exist in the stored page text. Levels: explicit | inferred_self_serve | partial | unresolved (absence of a restriction is NOT evidence of no restriction)."""
import os, re, json, hashlib, time, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
T = "runs/topup-v1-20261123"; norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
ASS = json.load(open(f"{T}/assessment.json")); RAW = {i: json.load(open(f"{T}/raw/{i}.json")) for i in map(int, ASS)}
BASE = {i: json.load(open(f"baseline/p1_v1/raw/{i}.json")) for i in set(RAW) | {20, 33, 47, 66, 71}}
iso = lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z")

# ---------------- access judgments (level, note, [(url_fragment, quote)])
J = {
 65: ("explicit", "free plan documented with unlimited API requests; keys created in project settings", [("supabase.com/pricing", "Unlimited API requests")]),
 72: ("explicit", "free plan exists; API usage capped by plan; enterprise admins can set token policies", [("airtable.com/pricing", "Our Free plan is available to teams for no charge"), ("airtable.com/pricing", "For automations and API limits, you will be capped at the usage limit on your current plan.")]),
 71: ("explicit", "free plan on pricing page; token creation governed by a plan-dependent workspace PAT policy (workspace-owner control = admin policy, not OAuth consent)", [("developers.notion.com/guides/connections", "Only full workspace members can create tokens, subject to the workspace’s PAT creation policy below."), ("notion.com/pricing", "Free$0 per seat/month")]),
 61: ("explicit", "app registration open to personal accounts and organizations; GitHub pricing page fetch returned empty; marketplace paid plans are a separate gate", [("docs.github.com/en/apps/creating-github-apps", "You can register a GitHub App under your personal account or under any organization you own.")]),
 62: ("inferred_self_serve", "Hobby/Pro/Enterprise plans on pricing docs + account-token creation documented; no restriction stated (inference, not proof)", [("vercel.com/docs/pricing", "Hobby Included"), ("vercel.com/docs/accounts/access-tokens", "requires a full-account token")]),
 63: ("inferred_self_serve", "Free/Personal/Pro plans documented + personal-access-token guide; no API restriction stated (inference)", [("docs.netlify.com/manage/accounts-and-billing", "standard plans include the Free, Personal, and Pro plans"), ("developers.netlify.com/guides/generating", "generate a Personal Access Token")]),
 36: ("inferred_self_serve", "free plan on pricing page + private API keys created by account users; no plan restriction stated (inference)", [("klaviyo.com/pricing", "Klaviyo free plan"), ("help.klaviyo.com", "When you create a private API key, choose an access level for each API scope.")]),
 29: ("partial", "marketplace/partner gating evidenced (application review, technology-partner criteria); API-key plan requirement not evidenced", [("developer.aircall.io/build", "while your application is under review"), ("developer.aircall.io/build", "To be eligible for the Technology Partner program, your product must meet the following criteria")]),
 47: ("partial", "developer sign-up and app review for the App Market evidenced; plan requirement for store API tokens not evidenced; developers.ecwid.com/register fetch empty", [("support.ecwid.com", "Sign up as a developer to create an Ecwid account."), ("support.ecwid.com", "contact the Ecwid team to submit your app for review.")]),
 44: ("partial", "only Commerce App registry review (marketplace) evidenced; API-client access/plan not evidenced", [("developer.salesforce.com/docs/commerce", "Submit your Commerce App to the registry for review and publication.")]),
 26: ("partial", "app registration in the Developer Portal evidenced; no pricing/verification/intents gating retrieved (developers/home is a JS shell)", [("docs.discord.com/developers/quick-start", "is backed by an application registered in the Discord Developer Portal")]),
 66: ("partial", "Aura trial/plans evidenced; pricing fetch failed; and API scope is ambiguous (Aura management API vs database HTTP/Query API)", [("neo4j.com/docs/aura/getting-started", "prompted to start a 14-day free trial")]),
 70: ("partial", "plan structure only (free Developer + paid plans); no statement about API/token access by plan", [("docs.sentry.io/pricing", "Sentry has one free Developer plan and three paid plans: Team, Business, and Enterprise.")]),
 25: ("partial", "pricing/plan pages only; the only 'free' statement is about integrations, not API access", [("pumble.com/pricing", "These integrations are free to use and do not affect your Pumble subscription plan limits.")]),
 75: ("partial", "personal-access-token doc only; pricing and registration pages failed to fetch", [("developers.asana.com/docs/personal-access-token", "regularly review the list of personal access tokens you have created")]),
 46: ("unresolved", "3 of 4 Squarespace pages failed to fetch (support articles); only the generic pricing page was retrieved", []),
 20: ("unresolved", "pricing page empty and onboarding page thin; no usable top-up evidence", []),
 38: ("unresolved", "developers.pinterest.com pages are JS shells (<500 chars); business.pinterest.com page is about business accounts, not API access", [])}
out = {}
for i, (lvl, note, quotes) in J.items():
    pages = {e["url"]: e["text"] for e in RAW[i]["fetched"] if e["status"] == "ok"}; ev = []
    for frag, q in quotes:
        url = next((u for u, t in pages.items() if frag in u and norm(q) in norm(t)), None); ev.append(dict(url=url, quote=q, verified=url is not None))
    assert all(e["verified"] for e in ev), (i, ev)
    out[i] = dict(name=RAW[i]["name"], level=lvl, note=note, evidence=ev, kept_separate_not_counted=dict(end_user_consent=ASS[str(i)]["bucket_counts"].get("end_user_consent", 0), admin_consent=ASS[str(i)]["bucket_counts"].get("admin_consent", 0), generic_approval_unclassified=ASS[str(i)]["bucket_counts"].get("generic_approval_unclassified", 0)))
json.dump(dict(provenance="assistant's reading of stored pages; provisional; quotes verified by code", levels=dict(collections.Counter(v["level"] for v in out.values())), apps=out), open(f"{T}/access_judgments.json", "w"), indent=1)

# ---------------- API-surface reassessment of the 5 borderline apps (measured from stored pages)
OP = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(?:https?://[\w.\-]+)?(/[\w\-/{}.:$]*[\w}])")
API = {20: ("insufficient", "REST API exists (developer.gladly.com lists it) but 0 operations and no resource catalogue in the retrieved pages; only webhook/API-token tutorials", "fetch the Gladly REST API reference index"),
       33: ("resource-level sufficient; operations not itemized", "pages name core resources Ad Accounts, Account Users, Campaign Groups, Campaigns, Creatives and 6 API product areas (Advertising, Community Management, Lead Sync, Conversions, Event Management, Marketing Program); 0 METHOD+path pairs", "operation-level detail optional"),
       47: ("partial", "REST confirmed with 1 operation (POST /api/v3/{storeId}/customers); orders/products only mentioned in a glossary; legacy api-docs host plus docs.ecwid.com", "fetch the docs.ecwid.com REST reference index"),
       66: ("partial + scope ambiguous", "1 operation (GET /v1/instances) = Aura management API; the database HTTP API is a separate surface ('Not available on Aura', deprecated)", "decide which Neo4j API the toolkit targets"),
       71: ("partial", "2 operations with paths (POST /v1/pages, GET /v1/users/me); guides name pages, databases/data sources, blocks, comments, users, search, webhooks; reference index not retrieved", "fetch the Notion API reference index")}
rows = {}
for i, (verdict, why, need) in API.items():
    pgs = [p["text"] for p in BASE[i]["pages"]] + [e["text"] for e in RAW[i]["fetched"] if e["status"] == "ok" and e["chars"] >= 500] if i in RAW else [p["text"] for p in BASE[i]["pages"]]
    ops = sorted({f"{m.group(1)} {m.group(2)}" for t in pgs for m in OP.finditer(t)})
    rows[i] = dict(name=json.load(open("runs/audit-raw-v2-20261123/audit.json")) and next(a["name"] for a in json.load(open("runs/audit-raw-v2-20261123/audit.json")) if a["id"] == i), measured_operations=ops, verdict=verdict, basis=why, to_resolve=need)
json.dump(dict(method="resource/operation coverage measured from stored pages (METHOD+path pairs, headings naming resources), not keyword counts", apps=rows), open(f"{T}/api_surface_reassessment.json", "w"), indent=1)

# ---------------- identity v2 (per your directives)
IDV2 = [
 dict(id=58, app="Sherlock", status="EXCLUDED - pending authoritative identity resolution", note="4 unrelated products retrieved; baseline Pass-1 record #58 is identity-contaminated and must not be used"),
 dict(id=80, app="Harvest", status="EXCLUDED - pending authoritative identity resolution", note="getharvest.com (time tracking) vs harvestapi.io vs Greenhouse Harvest API"),
 dict(id=50, app="fanbasis", status="EXCLUDED until fanbasis.io is confirmed", note="openstage.live EXCLUDED from official evidence; dev-docs.fanbasis.com is password-gated"),
 dict(id=73, app="Linear", status="PROVISIONAL identity (not confirmed) - held from extraction", note="category 8 + linear.app; no authoritative hint for #51-100"),
 dict(id=78, app="Coda", status="PROVISIONAL identity (not confirmed) - held from extraction", note="category 8 + coda.io; superhuman.com hits suggest docs may be migrating"),
 dict(id=60, app="Clay", status="PROVISIONAL identity (not confirmed)", note="not in the extraction plan (access evidence incomplete: READY_CORE)"),
 dict(id=59, app="Waterfall.io", status="PROVISIONAL identity (not confirmed)", note="not in the extraction plan (READY_CORE)"),
 dict(id=15, app="Pylon", status="Resolved (original Notion hint)", note="not in plan (PARTIAL retrieval)"), dict(id=20, app="Gladly", status="Resolved (original Notion hint)", note="in plan tier D: evidence unresolved"),
 dict(id=24, app="Lark", status="Resolved (original Notion hint)", note="not in plan"), dict(id=39, app="Threads (Meta)", status="Resolved (original Notion hint)", note="phase 1"),
 dict(id=69, app="Datadog", status="Domain conflict = FALSE ALARM (alias docs host)", note="not in plan"), dict(id=79, app="Smartsheet", status="Domain conflict = FALSE ALARM (deprecated redoc.ly docs host)", note="not in plan"),
 dict(id=55, app="Apify", status="use-apify.com excluded (third-party)", note="not in plan"),
 dict(id=66, app="Neo4j", status="NEW: product-scope ambiguity (Aura management API vs database HTTP/Query API) - held", note="needs your decision on which API the toolkit targets"),
 dict(id=14, app="Front", status="retrieval defect (dev.frontapp.com never fetched); baseline record preserved", note="correct in a later run after confirming frontapp.com"), dict(id=31, app="Google Ads", status="held: needs developer-token / access-level page", note="not in the 18-app top-up")]
json.dump(IDV2, open(f"{T}/identity_v2.json", "w"), indent=1)

# ---------------- retrieval results
rr = {}; tot = collections.Counter()
for i in RAW:
    pg = ASS[str(i)]["pages"]; rr[i] = dict(name=RAW[i]["name"], pages=pg, usable_evidence_pages=sum(p["used_as_evidence"] for p in pg))
    for p in pg: tot["requested"] += 1; tot["fetched_ok"] += p["status"] == "ok"; tot["usable_evidence"] += p["used_as_evidence"]; tot[p["excluded_reason"] or "kept"] += 1
json.dump(dict(totals=dict(tot), charge_usd_max=0.0, note="first fetch ran with an exclusion-regex escaping bug: 2 Pinterest user pages and 2 Discord Nitro/subscription pages were fetched although off-target; they are excluded from evidence", apps=rr), open(f"{T}/retrieval_results.json", "w"), indent=1)

# ---------------- revised plan (new run id); phases + tiers + top-up retrieval map
prior_sufficient = [27, 32, 33, 34, 39, 41, 43, 52, 53, 56, 76]
phase1 = prior_sufficient + [65, 72, 71, 61]; phase2 = [62, 63, 36, 29, 47, 44, 26, 70, 25, 75]
tiers = {**{str(i): "A_prior_access_evidence_sufficient" for i in prior_sufficient}, **{str(i): "A_topup_access_explicit" for i in (65, 72, 71, 61)}, **{str(i): "B_access_inferred_self_serve" for i in (62, 63, 36)}, **{str(i): "C_access_partial" for i in (29, 47, 44, 26, 70, 25, 75)}}
extra = {str(i): dict(raw=f"{T}/raw/{i}.json", use_urls=[p["url"] for p in ASS[str(i)]["pages"] if p["used_as_evidence"]]) for i in phase1 + phase2 if i in RAW}
os.makedirs("runs/p1-v1c-gemini-20261124", exist_ok=True)
plan = dict(run_id="p1-v1c-gemini-20261124", status="PREPARED - AWAITING EXPLICIT APPROVAL (no Gemini calls made; no APPROVED.json)", supersedes="p1-v1b-gemini-20261124",
            purpose="Resume Pass 1 for apps without a baseline record; same prompt/schema/models as baseline V1; sources = baseline cached pages + verified official top-up pages", phases={"1": phase1, "2": phase2}, tiers=tiers, extra_retrieval=extra, exclude_urls={},
            not_eligible={"unresolved_evidence": [46, 20, 38], "identity_held": [73, 78], "scope_ambiguity_held": [66], "excluded_identity": [58, 80, 50]},
            candidate_models=["gemini-2.5-flash", "gemini-3.5-flash"], key_policy="GEMINI_API_KEY only; GEMINI_API_KEY_2 is never read",
            approval_file_needed='runs/p1-v1c-gemini-20261124/APPROVED.json = {"models":[...],"cap_per_model":{model:N},"phases":[1]}  (written only after your explicit approval and the active-quota check)', created=iso())
json.dump(plan, open("runs/p1-v1c-gemini-20261124/PLAN.json", "w"), indent=1)
print("access levels (18):", dict(collections.Counter(v["level"] for v in out.values())))
print("retrieval totals:", dict(tot)); print("phase1:", len(phase1), "phase2:", len(phase2), "| not eligible: 3 unresolved + 2 identity-held + 1 scope-held")
print("top-up pages per planned app:", {k: len(v["use_urls"]) for k, v in extra.items()})
for f in os.listdir(T):
    if f.endswith(".json") and os.path.isfile(f"{T}/{f}"): os.chmod(f"{T}/{f}", 0o444)
