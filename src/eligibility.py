"""Eligibility + identity analysis for the next Pass-1 run. Offline: reads baseline/ and runs/audit-raw-v2-20261123 only; writes ONLY runs/eligibility-v1-20261123/.
Auth/API sufficiency is computed from stored pages; ACCESS sufficiency and all identity resolutions below are the ASSISTANT'S READING of stored pages/snippets
(provisional, not ground truth) and are labelled as such in the outputs."""
import os, re, json, csv, hashlib, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
RUN = "eligibility-v1-20261123"; OUT = f"runs/{RUN}"; assert not os.path.exists(OUT); os.makedirs(OUT)
A = {a["id"]: a for a in json.load(open("runs/audit-raw-v2-20261123/audit.json"))}
ready = [i for i, a in A.items() if a["verdict"] == "READY_FULL" and not a["has_pass1"]]

# ---- identity: the 10 common-word names flagged by the audit among the 55 un-extracted apps (+ Sherlock, which already has a Pass-1 record)
IDENT = [
 dict(id=15, name="Pylon", resolved_by="original Notion hint usepylon.com", pages="docs.usepylon.com", other_same_name="pylonapi.com, getpylon.com (different products, in search results only)", status="RESOLVED (authoritative hint)", in_ready_full=False),
 dict(id=20, name="Gladly", resolved_by="original Notion hint gladly.com", pages="developer.gladly.com, help.gladly.com", other_same_name="gladly.ai (1 search hit)", status="RESOLVED (authoritative hint)", in_ready_full=True),
 dict(id=24, name="Lark (Larksuite)", resolved_by="original Notion hint open.larksuite.com", pages="open.larksuite.com", other_same_name="none", status="RESOLVED (authoritative hint)", in_ready_full=False),
 dict(id=39, name="Threads (Meta)", resolved_by="original Notion hint developers.facebook.com/docs/threads", pages="developers.facebook.com", other_same_name="none", status="RESOLVED (authoritative hint)", in_ready_full=True),
 dict(id=50, name="fanbasis", resolved_by="original Notion hint fanbasis.com resolves the brand, but pages come from 3 domains (see conflicts)", pages="dev-docs.fanbasis.com (password-gated), demo.embedded.fanbasis.io, fanbaseapi.openstage.live", other_same_name="'Fanbase API' on openstage.live looks like a different product (spelling Fanbase vs Fanbasis)", status="NEEDS CONFIRMATION (domain conflict)", in_ready_full=False),
 dict(id=59, name="Waterfall.io", resolved_by="name contains domain waterfall.io; pages only on docs.waterfall.io/api.waterfall.io (no hint available for apps 51-100)", pages="docs.waterfall.io", other_same_name="none seen", status="PROPOSED RESOLVED (high confidence); confirm", in_ready_full=False),
 dict(id=60, name="Clay", resolved_by="category 6 + developers.clay.com (data enrichment); no hint available", pages="developers.clay.com", other_same_name="none seen in doc hits", status="PROPOSED RESOLVED (high confidence); confirm", in_ready_full=False),
 dict(id=73, name="Linear", resolved_by="category 8 (project mgmt) + linear.app GraphQL docs; no hint available", pages="linear.app", other_same_name="none (stray third-party hits only)", status="PROPOSED RESOLVED (high confidence); HOLD until confirmed", in_ready_full=True),
 dict(id=78, name="Coda", resolved_by="category 8 + coda.io Packs/API docs; no hint available", pages="coda.io, community.coda.io", other_same_name="superhuman.com (Coda was acquired; docs may be migrating) - confirm which docs are canonical", status="PROPOSED RESOLVED (high confidence); HOLD until confirmed", in_ready_full=True),
 dict(id=80, name="Harvest", resolved_by="category 8 suggests time tracking (getharvest.com) but pages mix THREE products; no hint available", pages="help.getharvest.com (time tracking, V1 API deprecated), docs.harvestapi.io (different product), github.com", other_same_name="greenhouse.io 'Harvest API' (recruiting) in search hits", status="UNRESOLVED - needs explicit confirmation", in_ready_full=False),
 dict(id=58, name="Sherlock (already has a Pass-1 record)", resolved_by="none possible: 4 unrelated products retrieved; no hint available", pages="app.sherlock.sh (Sherlock Interview API), sherlock.gnoss.com (GNOSS semantic annotation), sher-lock.readthedocs.org (Python locking library), github.com/bellingcat (username-search tool)",
      other_same_name="Pass-1 record #58 describes 'an open-source CLI for finding usernames' while citing all four sources -> record is identity-contaminated", status="UNRESOLVED - EXPLICIT CONFIRMATION REQUIRED; existing record must not be used", in_ready_full=False)]

CONFLICTS = [
 dict(id=69, app="Datadog", domains="docs.datadoghq.com, docs.datadog.com", classification="SAME PRODUCT - alias/legacy docs host (FALSE ALARM)", evidence="docs.datadoghq.com pages self-reference 'https://docs.datadoghq.com/...'; docs.datadog.com page shows the official datadog-api-client (groupId com.datadoghq)", action="keep both; canonical = docs.datadoghq.com"),
 dict(id=79, app="Smartsheet", domains="developers.smartsheet.com, smartsheet.redoc.ly", classification="SAME PRODUCT - vendor-operated DOCUMENTATION-HOSTING domain, deprecated (FALSE ALARM)", evidence="redoc.ly page text: '(DEPRECATED site) ... The new Smartsheet API reference documentation site is located at https://developers.smartsheet.com/'", action="drop the deprecated redoc page from evidence; canonical = developers.smartsheet.com"),
 dict(id=55, app="Apify", domains="docs.apify.com, use-apify.com", classification="docs.apify.com = genuine product docs; use-apify.com = THIRD-PARTY tutorial site", evidence="use-apify.com page is a 'Quick answer' how-to blog, not on an apify.com domain", action="exclude use-apify.com page; 3 official pages remain"),
 dict(id=50, app="fanbasis", domains="dev-docs.fanbasis.com, demo.embedded.fanbasis.io, fanbaseapi.openstage.live", classification="fanbasis.com = genuine (original hint); fanbasis.io = PROBABLE same vendor (unconfirmed registrable-domain link); openstage.live = LIKELY DIFFERENT product ('Fanbase API', third-party host)", evidence="dev-docs.fanbasis.com page text: 'Sign in to access API Docs / Password / Login' (docs themselves gated); embedded.fanbasis.io page titled 'Fanbasis Payment SDK'", action="needs your confirmation of fanbasis.io; exclude openstage.live; note docs-gated finding"),
 dict(id=58, app="Sherlock", domains="app.sherlock.sh, sherlock.gnoss.com, sher-lock.readthedocs.org, github.com/bellingcat", classification="FOUR DIFFERENT PRODUCTS (genuine identity ambiguity, not a hosting issue)", evidence="Interview API | semantic text annotation | Python lock library | username-search OSINT tool", action="EXPLICIT identity confirmation required")]

EXCEPTIONS = [
 dict(id=14, app="Front (has Pass-1 record)", type="RETRIEVAL-SELECTION DEFECT (not a rubric problem)", finding="12 stored search hits point to dev.frontapp.com (reference/introduction, core-api-overview, create-and-manage-apps) but none were fetched: V1 picked help.front.com/academy/integrations.sh pages because it prefers the hint domain (front.com). Existing Pass-1 record #14 therefore rests on help-center articles plus a third-party page.", action="do not re-extract in this run; baseline record stays; fetch dev.frontapp.com in a later run after you confirm it is Front's developer domain"),
 dict(id=31, app="Google Ads", type="RUBRIC FALSE-NEGATIVE (API surface) + GENUINE ACCESS GAP", finding="4 pages are all official (developers.google.com/google-ads); OAuth page present; 'rest' appears twice and no endpoint-style patterns, so the keyword API check failed; no page covers developer-token / access-level requirements (access evidence 0).", action="hold: free top-up fetch of the developer-token / access-levels page before extraction")]

# ---- access sufficiency = assistant's provisional reading of stored snippets (see summary)
ACC = {33: ("sufficient", "Development vs Standard tier; upgrade request with video"), 34: ("sufficient", "'API access is available across HighLevel subscription plans'"), 39: ("sufficient", "permissions need App Review"), 32: ("sufficient", "production use requires app review"),
       41: ("sufficient", "'Some APIs also require Shopify's approval or a specific Shopify plan'"), 52: ("sufficient", "subscription limits + credit balance for Data API"), 53: ("sufficient", "'available on eligible paid plans'; limited free test queries"),
       56: ("sufficient", "free account gives API key; 'neither needs approval'"), 27: ("sufficient", "'free of charge' for developers"), 76: ("sufficient", "sign up + trial account for building apps"), 43: ("sufficient", "free trial/sandbox store for API testing"),
       71: ("partial", "PAT creation restricted on Business/Enterprise by default"), 72: ("partial", "some features Enterprise Scale/Business only"), 75: ("partial", "Enterprise+ admin controls affect PATs"), 66: ("partial", "AuraDB Free/Professional trial rate limits"),
       65: ("partial", "pricing section exists but about Auth MAU"), 36: ("partial", "OAuth for tech partners; no explicit access terms"), 46: ("partial", "OAuth/API-key availability notes only"), 29: ("partial", "private vs approved tech partner integrations"),
       20: ("insufficient", ""), 25: ("insufficient", "matches are about integrations' pricing, not API access"), 26: ("insufficient", "'approval' hits are OAuth consent"), 38: ("insufficient", ""), 44: ("insufficient", ""), 47: ("insufficient", ""),
       61: ("insufficient", "'approval' hits are org PAT policy"), 62: ("insufficient", "'approval' hits are OAuth consent"), 63: ("insufficient", "'waitlist' is for a new UI, not the API"), 70: ("insufficient", ""), 73: ("insufficient", ""), 78: ("insufficient", "'approval' is OAuth consent screen")}
AUTHK = re.compile(r"oauth|api[ _-]?key|apikey|bearer|access token|personal access token|api token|basic auth|client[_ ]secret|jwt|hmac", re.I)
APIK = re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/[\w\-/{}.:]+|rest api|restful|graphql|openapi|swagger|endpoints?\b", re.I)
HOLD = {73: "identity unconfirmed (Linear)", 78: "identity unconfirmed (Coda)"}
rows = []
for i in ready:
    raw = {p["url"]: p for p in json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]}
    off = [p for p in A[i]["pages"] if p["usable"] and p["official"]]
    kinds = sorted({m.group(0).lower() for p in off for m in AUTHK.finditer(raw[p["url"]]["text"])}); api = sum(len(APIK.findall(raw[p["url"]]["text"])) for p in off)
    acc, note = ACC[i]
    rows.append(dict(id=i, name=A[i]["name"], official_usable_pages=len(off), auth_sufficient=len(kinds) >= 1, auth_kinds_seen=kinds[:5], api_sufficient=api >= 2, api_hits=api, api_borderline=api < 5,
                     access_evidence=acc, access_note=note, hold_reason=HOLD.get(i), mcp_official_domain_hits=A[i]["mcp_hits_official_domain"], truncated=("truncated_pages" in A[i]["gaps"])))
order = {"sufficient": 0, "partial": 1, "insufficient": 2}
elig = sorted([r for r in rows if not r["hold_reason"]], key=lambda r: (order[r["access_evidence"]], r["id"]))
held = [r for r in rows if r["hold_reason"]]
json.dump(dict(provenance="identity/conflict/exception/access judgments are the assistant's reading of stored pages (offline, no LLM API); provisional", identity=IDENT, domain_conflicts=CONFLICTS, rubric_exceptions=EXCEPTIONS), open(f"{OUT}/identity_resolution.json", "w"), indent=1)
json.dump(dict(ready_full_total=len(rows), eligible_identity_clear=[r["id"] for r in elig], held=held, rows=rows,
               access_counts={k: sum(r["access_evidence"] == k for r in elig) for k in order}), open(f"{OUT}/eligibility.json", "w"), indent=1)
with open(f"{OUT}/eligibility.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["id", "name", "official_pages", "auth_ok", "api_ok", "api_hits", "access_evidence", "access_note", "hold_reason"])
    for r in rows: w.writerow([r["id"], r["name"], r["official_usable_pages"], r["auth_sufficient"], r["api_sufficient"], r["api_hits"], r["access_evidence"], r["access_note"], r["hold_reason"] or ""])
json.dump(dict(run_id=RUN, code="src/eligibility.py", code_sha256=hashlib.sha256(open(__file__, "rb").read()).hexdigest(), baseline_manifest_sha256=hashlib.sha256(open("baseline/MANIFEST.json", "rb").read()).hexdigest(),
               created=time.strftime("%Y-%m-%dT%H:%M:%S%z"), network=False, llm=None), open(f"{OUT}/RUN.json", "w"), indent=1)
for f in os.listdir(OUT): os.chmod(f"{OUT}/{f}", 0o444)
print("ready_full:", len(rows), "| eligible (identity-clear):", len(elig), "| held:", [(r["id"], r["name"]) for r in held], "| access among eligible:", {k: sum(r["access_evidence"] == k for r in elig) for k in order})
print("auth_sufficient all:", all(r["auth_sufficient"] for r in rows), "| api_sufficient all:", all(r["api_sufficient"] for r in rows), "| api borderline (<5 hits):", [(r["id"], r["name"], r["api_hits"]) for r in rows if r["api_borderline"]])
print("eligible order:", [(r["id"], r["name"], r["access_evidence"][0].upper()) for r in elig])
